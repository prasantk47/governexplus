"""Stabilization fixes: ENUM→VARCHAR columns, audit_logs tenant_id, missing indexes

Revision ID: 20261102_100000
Revises: 20261031_100000
Create Date: 2026-11-02

Consolidates all manual DB changes applied during v1.0 stabilization:
- 27 PostgreSQL ENUM columns → VARCHAR(50) across 15 tables
- audit_logs.tenant_id column + index
- risk_workflow_steps tenant_id index
- Audit log immutability triggers
"""
from alembic import op
import sqlalchemy as sa

revision = '20261102_100000'
down_revision = '20261031_100000'
branch_labels = None
depends_on = None


# All columns that were PostgreSQL ENUM types, now VARCHAR(50)
ENUM_TO_VARCHAR = [
    ('bcm_plans', 'plan_type', 'bcmplantype'),
    ('bcm_plans', 'status', 'bcmplanstatus'),
    ('bcm_test_exercises', 'exercise_type', 'bcmexercisetype'),
    ('bcm_test_exercises', 'outcome', 'bcmexerciseoutcome'),
    ('bia_records', 'criticality', 'bcmcriticality'),
    ('fraud_alerts', 'status', 'fraudalertstatus'),
    ('fraud_cases', 'severity', 'fraudcaseseverity'),
    ('fraud_cases', 'status', 'fraudcasestatus'),
    ('fraud_rules', 'rule_type', 'fraudruletype'),
    ('incident_activations', 'severity', 'bcmactivationseverity'),
    ('incident_activations', 'status', 'bcmactivationstatus'),
    ('jml_events', 'event_type', 'jmleventtype'),
    ('jml_events', 'status', 'jmleventstatus'),
    ('jml_policies', 'event_type', 'jmleventtype'),
    ('standalone_surveys', 'status', 'surveystatus'),
    ('standalone_surveys', 'survey_type', 'surveytype'),
    ('survey_distributions', 'status', 'surveydistributionstatus'),
    ('vendor_assessments', 'risk_rating', 'vendorriskrating'),
    ('vendor_assessments', 'status', 'vendorassessmentstatus'),
    ('vendor_contracts', 'status', 'vendorcontractstatus'),
    ('vendor_issues', 'severity', 'vendorissueseverity'),
    ('vendor_issues', 'status', 'vendorissuestatus'),
    ('vendors', 'status', 'vendorstatus'),
    ('whistleblower_cases', 'category', 'whistleblowercategory'),
    ('whistleblower_cases', 'priority', 'whistleblowerpriority'),
    ('whistleblower_cases', 'status', 'whistleblowerstatus'),
    ('whistleblower_messages', 'sender', 'whistleblowersender'),
]


def upgrade() -> None:
    # 1. Convert ENUM columns to VARCHAR(50)
    for table, column, enum_name in ENUM_TO_VARCHAR:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE VARCHAR(50) USING {column}::VARCHAR"
        )

    # 2. Drop old ENUM types (they're no longer used)
    enum_names = set(e[2] for e in ENUM_TO_VARCHAR)
    for enum_name in sorted(enum_names):
        op.execute(f"DROP TYPE IF EXISTS {enum_name} CASCADE")

    # 3. Add tenant_id to audit_logs
    op.add_column('audit_logs', sa.Column('tenant_id', sa.String(100), nullable=True))
    op.create_index('ix_audit_logs_tenant_id', 'audit_logs', ['tenant_id'])

    # 4. Add missing index on risk_workflow_steps.tenant_id
    op.create_index(
        'ix_risk_workflow_steps_tenant_id',
        'risk_workflow_steps',
        ['tenant_id'],
        if_not_exists=True,
    )

    # 5. Audit log immutability triggers
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit log entries cannot be modified or deleted';
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS audit_log_immutable_update ON audit_logs
    """)
    op.execute("""
        CREATE TRIGGER audit_log_immutable_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification()
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS audit_log_immutable_delete ON audit_logs
    """)
    op.execute("""
        CREATE TRIGGER audit_log_immutable_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification()
    """)


def downgrade() -> None:
    # Remove immutability triggers
    op.execute("DROP TRIGGER IF EXISTS audit_log_immutable_delete ON audit_logs")
    op.execute("DROP TRIGGER IF EXISTS audit_log_immutable_update ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_modification()")

    # Remove audit_logs.tenant_id
    op.drop_index('ix_audit_logs_tenant_id', 'audit_logs')
    op.drop_column('audit_logs', 'tenant_id')

    # Note: ENUM types are NOT recreated in downgrade — columns remain VARCHAR
    # This is intentional: re-creating PG ENUM types and casting back is fragile
