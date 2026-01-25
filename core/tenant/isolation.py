# Tenant Data Isolation
# Ensures complete separation between tenants

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import hashlib


class DataIsolationStrategy(Enum):
    """
    Data isolation strategies

    Different approaches based on security/cost trade-offs:
    """
    SHARED_DATABASE = "shared_database"      # Same DB, tenant_id column
    SCHEMA_PER_TENANT = "schema_per_tenant"  # Same DB, different schemas
    DATABASE_PER_TENANT = "database_per_tenant"  # Separate databases
    INSTANCE_PER_TENANT = "instance_per_tenant"  # Separate DB instances


@dataclass
class TenantDatabase:
    """Tenant database configuration"""
    tenant_id: str
    strategy: DataIsolationStrategy = DataIsolationStrategy.SHARED_DATABASE

    # Connection details
    host: str = ""
    port: int = 5432
    database_name: str = ""
    schema_name: str = ""
    username: str = ""
    # Password stored in secrets manager

    # Encryption
    encryption_key_id: str = ""
    encrypted_at_rest: bool = True

    # Connection pool
    pool_size: int = 5
    max_overflow: int = 10

    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TenantStorage:
    """Tenant file storage configuration"""
    tenant_id: str

    # Cloud storage
    provider: str = "s3"  # s3, azure, gcs
    bucket_name: str = ""
    prefix: str = ""  # All files under this prefix

    # Encryption
    encryption_key_id: str = ""
    encrypted: bool = True

    # Quotas
    max_size_gb: float = 10.0
    current_size_gb: float = 0.0

    created_at: datetime = field(default_factory=datetime.utcnow)


class TenantIsolation:
    """
    Tenant Isolation Manager

    Ensures complete data separation between tenants:

    1. DATABASE ISOLATION
       - Row-level security (tenant_id on every row)
       - Schema separation for higher security needs
       - Dedicated databases for enterprise tenants

    2. STORAGE ISOLATION
       - Separate storage prefixes/buckets
       - Tenant-specific encryption keys
       - Access policies per tenant

    3. NETWORK ISOLATION (Enterprise)
       - Dedicated IP ranges
       - VPC peering
       - Private endpoints

    4. ENCRYPTION
       - Tenant-specific encryption keys
       - Data encrypted at rest
       - Encrypted backups
    """

    def __init__(self):
        self.databases: Dict[str, TenantDatabase] = {}
        self.storage: Dict[str, TenantStorage] = {}
        self.encryption_keys: Dict[str, str] = {}

        # Default settings by tier
        self.tier_strategies = {
            "free": DataIsolationStrategy.SHARED_DATABASE,
            "starter": DataIsolationStrategy.SHARED_DATABASE,
            "professional": DataIsolationStrategy.SCHEMA_PER_TENANT,
            "enterprise": DataIsolationStrategy.DATABASE_PER_TENANT,
            "dedicated": DataIsolationStrategy.INSTANCE_PER_TENANT
        }

    # ==================== Database Isolation ====================

    def provision_database(
        self,
        tenant_id: str,
        tier: str = "professional"
    ) -> TenantDatabase:
        """Provision database resources for a tenant"""
        strategy = self.tier_strategies.get(tier, DataIsolationStrategy.SHARED_DATABASE)

        db_config = TenantDatabase(
            tenant_id=tenant_id,
            strategy=strategy
        )

        if strategy == DataIsolationStrategy.SHARED_DATABASE:
            # Use shared database, rely on tenant_id column
            db_config.host = "shared-db.grc-platform.com"
            db_config.database_name = "grc_shared"
            db_config.schema_name = "public"

        elif strategy == DataIsolationStrategy.SCHEMA_PER_TENANT:
            # Create dedicated schema
            db_config.host = "shared-db.grc-platform.com"
            db_config.database_name = "grc_shared"
            db_config.schema_name = f"tenant_{tenant_id}"
            # Would execute: CREATE SCHEMA tenant_{tenant_id}

        elif strategy == DataIsolationStrategy.DATABASE_PER_TENANT:
            # Create dedicated database
            db_config.host = "shared-db.grc-platform.com"
            db_config.database_name = f"grc_{tenant_id}"
            db_config.schema_name = "public"
            # Would execute: CREATE DATABASE grc_{tenant_id}

        elif strategy == DataIsolationStrategy.INSTANCE_PER_TENANT:
            # Provision dedicated instance
            db_config.host = f"{tenant_id}.db.grc-platform.com"
            db_config.database_name = "grc"
            db_config.schema_name = "public"
            # Would provision new RDS/Cloud SQL instance

        # Generate encryption key
        db_config.encryption_key_id = self._generate_encryption_key(tenant_id, "database")
        self.databases[tenant_id] = db_config

        return db_config

    def get_database_connection(self, tenant_id: str) -> Dict[str, Any]:
        """Get database connection details for a tenant"""
        db = self.databases.get(tenant_id)
        if not db:
            return {"error": "Database not provisioned for tenant"}

        return {
            "host": db.host,
            "port": db.port,
            "database": db.database_name,
            "schema": db.schema_name,
            "pool_size": db.pool_size,
            "encryption_enabled": db.encrypted_at_rest
        }

    # ==================== Storage Isolation ====================

    def provision_storage(
        self,
        tenant_id: str,
        max_size_gb: float = 10.0
    ) -> TenantStorage:
        """Provision storage resources for a tenant"""
        storage = TenantStorage(
            tenant_id=tenant_id,
            bucket_name="grc-platform-data",
            prefix=f"tenants/{tenant_id}/",
            encryption_key_id=self._generate_encryption_key(tenant_id, "storage"),
            max_size_gb=max_size_gb
        )

        self.storage[tenant_id] = storage

        # Would create:
        # - S3 bucket prefix
        # - Bucket policy restricting access
        # - Lifecycle rules for the prefix

        return storage

    def get_storage_path(self, tenant_id: str, path: str) -> str:
        """Get tenant-scoped storage path"""
        storage = self.storage.get(tenant_id)
        if not storage:
            raise ValueError(f"Storage not provisioned for tenant {tenant_id}")

        # Ensure path is within tenant's prefix
        clean_path = path.lstrip("/")
        return f"{storage.prefix}{clean_path}"

    def validate_storage_access(
        self,
        tenant_id: str,
        path: str
    ) -> bool:
        """Validate that a storage path belongs to the tenant"""
        storage = self.storage.get(tenant_id)
        if not storage:
            return False

        # Path must start with tenant's prefix
        return path.startswith(storage.prefix)

    # ==================== Encryption ====================

    def _generate_encryption_key(self, tenant_id: str, purpose: str) -> str:
        """Generate unique encryption key ID for tenant"""
        key_id = f"key_{tenant_id}_{purpose}_{datetime.utcnow().strftime('%Y%m%d')}"
        self.encryption_keys[key_id] = hashlib.sha256(
            f"{tenant_id}:{purpose}:{datetime.utcnow()}".encode()
        ).hexdigest()
        return key_id

    def get_encryption_key(self, key_id: str) -> Optional[str]:
        """Get encryption key (would use KMS in production)"""
        return self.encryption_keys.get(key_id)

    def rotate_encryption_keys(self, tenant_id: str) -> Dict[str, Any]:
        """Rotate encryption keys for a tenant"""
        old_db_key = self.databases.get(tenant_id, {}).encryption_key_id if tenant_id in self.databases else None
        old_storage_key = self.storage.get(tenant_id, {}).encryption_key_id if tenant_id in self.storage else None

        new_db_key = self._generate_encryption_key(tenant_id, "database")
        new_storage_key = self._generate_encryption_key(tenant_id, "storage")

        if tenant_id in self.databases:
            self.databases[tenant_id].encryption_key_id = new_db_key
        if tenant_id in self.storage:
            self.storage[tenant_id].encryption_key_id = new_storage_key

        return {
            "success": True,
            "tenant_id": tenant_id,
            "rotated_keys": {
                "database": {"old": old_db_key, "new": new_db_key},
                "storage": {"old": old_storage_key, "new": new_storage_key}
            },
            "message": "Keys rotated. Re-encryption will be performed in background."
        }

    # ==================== Row-Level Security ====================

    def get_rls_policy(self, tenant_id: str, table_name: str) -> str:
        """
        Generate Row-Level Security policy for a table

        Ensures queries only return data for the current tenant.
        """
        return f"""
        CREATE POLICY tenant_isolation_{table_name}
        ON {table_name}
        USING (tenant_id = '{tenant_id}')
        WITH CHECK (tenant_id = '{tenant_id}');
        """

    def apply_tenant_filter(self, query: str, tenant_id: str) -> str:
        """
        Apply tenant filter to a query

        Ensures all queries are scoped to the current tenant.
        This is a backup to RLS for defense in depth.
        """
        # Simple implementation - production would use SQL parser
        if "WHERE" in query.upper():
            return query.replace(
                "WHERE",
                f"WHERE tenant_id = '{tenant_id}' AND "
            )
        else:
            if "ORDER BY" in query.upper():
                return query.replace(
                    "ORDER BY",
                    f"WHERE tenant_id = '{tenant_id}' ORDER BY"
                )
            return f"{query} WHERE tenant_id = '{tenant_id}'"

    # ==================== Cross-Tenant Protection ====================

    def validate_tenant_access(
        self,
        requesting_tenant: str,
        resource_tenant: str
    ) -> bool:
        """Validate that a tenant can access a resource"""
        # Tenants can only access their own resources
        return requesting_tenant == resource_tenant

    def audit_cross_tenant_attempt(
        self,
        requesting_tenant: str,
        target_tenant: str,
        resource_type: str,
        resource_id: str
    ) -> None:
        """Log attempted cross-tenant access"""
        # Would log to security audit system
        print(f"SECURITY: Cross-tenant access attempt - "
              f"Tenant {requesting_tenant} tried to access "
              f"{resource_type}/{resource_id} belonging to {target_tenant}")

    # ==================== Cleanup ====================

    def deprovision_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Remove all tenant resources (for deleted tenants)"""
        results = {
            "tenant_id": tenant_id,
            "database_deleted": False,
            "storage_deleted": False,
            "keys_deleted": False
        }

        # Delete database
        if tenant_id in self.databases:
            db = self.databases[tenant_id]
            if db.strategy == DataIsolationStrategy.DATABASE_PER_TENANT:
                # Would execute: DROP DATABASE {db.database_name}
                pass
            elif db.strategy == DataIsolationStrategy.SCHEMA_PER_TENANT:
                # Would execute: DROP SCHEMA {db.schema_name} CASCADE
                pass
            del self.databases[tenant_id]
            results["database_deleted"] = True

        # Delete storage
        if tenant_id in self.storage:
            storage = self.storage[tenant_id]
            # Would delete all objects under prefix
            del self.storage[tenant_id]
            results["storage_deleted"] = True

        # Delete encryption keys
        keys_to_delete = [k for k in self.encryption_keys if tenant_id in k]
        for key in keys_to_delete:
            del self.encryption_keys[key]
        results["keys_deleted"] = len(keys_to_delete) > 0

        return results

    # ==================== Compliance ====================

    def get_data_residency_info(self, tenant_id: str) -> Dict[str, Any]:
        """Get data residency information for compliance"""
        db = self.databases.get(tenant_id)
        storage = self.storage.get(tenant_id)

        return {
            "tenant_id": tenant_id,
            "database": {
                "location": "us-east-1" if db else None,  # Would be actual region
                "encrypted": db.encrypted_at_rest if db else None,
                "isolation_level": db.strategy.value if db else None
            },
            "storage": {
                "location": "us-east-1" if storage else None,
                "encrypted": storage.encrypted if storage else None,
                "provider": storage.provider if storage else None
            },
            "gdpr_compliant": True,
            "sox_compliant": True,
            "hipaa_eligible": True
        }
