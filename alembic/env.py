"""
Alembic Environment Configuration

Manages database migrations for the GovernexPlus GRC platform.

Behaviour:
- Loads .env via python-dotenv so DATABASE_URL is available before
  SQLAlchemy or Alembic read configuration.
- Falls back to the sqlalchemy.url value in alembic.ini when DATABASE_URL
  is not set in the environment (useful for local development with SQLite).
- Imports every model module so that Base.metadata contains all table
  definitions — this is required for `alembic revision --autogenerate` to
  detect schema changes accurately.
- Supports both offline (SQL script) and online (live connection) modes.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that `db` and other packages
# can be imported when alembic is invoked from any working directory.
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Load environment variables from .env (if present) before any import that
# reads os.getenv(), including the DATABASE_URL used by db.database.
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    _env_file = os.path.join(PROJECT_ROOT, ".env")
    load_dotenv(_env_file, override=False)  # do not override variables already in the shell
except ImportError:
    # python-dotenv is optional; if it is absent the env must be pre-populated
    pass

# ---------------------------------------------------------------------------
# Import all models so Base.metadata is fully populated.
# Autogenerate will not detect tables whose models have not been imported.
# ---------------------------------------------------------------------------
from db.models.base import Base  # noqa: F401 — registers DeclarativeBase

# Core models
from db.models.tenant import AdminSession, Tenant, TenantStatus, TenantTier  # noqa: F401
from db.models.user import User, Role, UserRole, UserEntitlement  # noqa: F401
from db.models.risk import (  # noqa: F401
    RiskViolation,
    MitigationControl,
    RiskRuleModel,
    TenantRulePreference,
)
from db.models.firefighter import (  # noqa: F401
    FirefighterRequest,
    FirefighterSession,
    FirefighterActivity,
)
from db.models.audit import AuditLog, AccessRequestLog  # noqa: F401
from db.models.approver import ApproverModel, ApprovalRuleModel  # noqa: F401
from db.models.sap_security_controls import (  # noqa: F401
    SAPSecurityControl,
    ControlValueMapping,
    ControlEvaluation,
    ControlException,
    SystemSecurityProfile,
)
from db.models.operations import (  # noqa: F401
    OrgRule,
    OrgUserAssignment,
    OrgRoleRestriction,
    BulkJob,
    SyncConfig,
    SyncHistory,
    TransportRecord,
    NotificationRecord,
    NotificationPreference,
    CustomTcodeRecord,
    ModelTemplate,
    MitigationMonitorRecord,
    OrchestrationContextRecord,
)
from db.models.intelligence import (  # noqa: F401
    TroubleshooterKBUser,
    TroubleshooterKBRole,
    TroubleshooterKBTransaction,
    RoleIntelligenceRecord,
    DriftSnapshot,
    FioriAppRecord,
    IdentityAccount,
    IdentityClusterRecord,
    MigrationMapping,
    TimelineEvent,
    AuditEvidenceItem,
)
from db.models.engines import (  # noqa: F401
    EvidenceRecord,
    FindingRecord,
    ExecutionPlanRecord,
    DecisionWorkflowRecord,
)

# ---------------------------------------------------------------------------
# Alembic context setup
# ---------------------------------------------------------------------------

# The Alembic Config object — provides access to the values within alembic.ini
config = context.config

# Configure Python logging from the [loggers] / [handlers] / [formatters]
# sections of alembic.ini (skipped when the file path is not set, e.g. in tests).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata object used by --autogenerate
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------

def get_url() -> str:
    """
    Return the database URL to use for migrations.

    Priority order:
    1. DATABASE_URL environment variable (set in .env or shell)
    2. sqlalchemy.url value from alembic.ini
    """
    return os.getenv(
        "DATABASE_URL",
        config.get_main_option("sqlalchemy.url"),
    )


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (emit SQL to stdout / a file).

    The database engine is not created; a URL is sufficient.
    Useful for generating SQL scripts for DBA review before applying.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,  # required for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (apply directly to a live database).

    An Engine is created and a Connection is associated with the context.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,  # required for SQLite ALTER TABLE support
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
