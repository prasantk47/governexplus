"""
AD Group to SAP Role Mapping Engine

Maps Active Directory groups to SAP roles for cross-system provisioning.
Detects group membership changes and generates provisioning actions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of group membership changes."""
    ADDED = "added"
    REMOVED = "removed"


class ProvisioningActionType(Enum):
    """Types of provisioning actions."""
    ASSIGN_ROLE = "assign_role"
    REMOVE_ROLE = "remove_role"


class ProvisioningStatus(Enum):
    """Status of a provisioning action."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ADSAPMapping:
    """Represents a mapping between an AD group and a SAP role."""
    mapping_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    ad_group: str = ""
    sap_role: str = ""
    sap_system: str = "DEFAULT"
    auto_provision: bool = True
    description: str = ""
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "ad_group": self.ad_group,
            "sap_role": self.sap_role,
            "sap_system": self.sap_system,
            "auto_provision": self.auto_provision,
            "description": self.description,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "enabled": self.enabled,
        }


@dataclass
class GroupChange:
    """Represents a detected change in AD group membership."""
    change_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    user_id: str = ""
    ad_group: str = ""
    change_type: ChangeType = ChangeType.ADDED
    detected_at: datetime = field(default_factory=datetime.utcnow)
    mapped_sap_roles: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "user_id": self.user_id,
            "ad_group": self.ad_group,
            "change_type": self.change_type.value,
            "detected_at": self.detected_at.isoformat(),
            "mapped_sap_roles": self.mapped_sap_roles,
        }


@dataclass
class ProvisioningAction:
    """A provisioning action to execute in SAP based on AD group changes."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    user_id: str = ""
    action_type: ProvisioningActionType = ProvisioningActionType.ASSIGN_ROLE
    sap_role: str = ""
    sap_system: str = "DEFAULT"
    source_ad_group: str = ""
    status: ProvisioningStatus = ProvisioningStatus.PENDING
    auto_provision: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "user_id": self.user_id,
            "action_type": self.action_type.value,
            "sap_role": self.sap_role,
            "sap_system": self.sap_system,
            "source_ad_group": self.source_ad_group,
            "status": self.status.value,
            "auto_provision": self.auto_provision,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "error_message": self.error_message,
        }


@dataclass
class SyncResult:
    """Result of syncing a single user."""
    user_id: str = ""
    success: bool = True
    changes_detected: int = 0
    actions_executed: int = 0
    actions_failed: int = 0
    actions_skipped: int = 0
    changes: List[GroupChange] = field(default_factory=list)
    actions: List[ProvisioningAction] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    synced_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "success": self.success,
            "changes_detected": self.changes_detected,
            "actions_executed": self.actions_executed,
            "actions_failed": self.actions_failed,
            "actions_skipped": self.actions_skipped,
            "changes": [c.to_dict() for c in self.changes],
            "actions": [a.to_dict() for a in self.actions],
            "errors": self.errors,
            "synced_at": self.synced_at.isoformat(),
        }


@dataclass
class BulkSyncResult:
    """Result of a bulk sync operation across all users."""
    sync_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    total_users: int = 0
    users_synced: int = 0
    users_failed: int = 0
    total_changes: int = 0
    total_actions_executed: int = 0
    total_actions_failed: int = 0
    user_results: List[SyncResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sync_id": self.sync_id,
            "total_users": self.total_users,
            "users_synced": self.users_synced,
            "users_failed": self.users_failed,
            "total_changes": self.total_changes,
            "total_actions_executed": self.total_actions_executed,
            "total_actions_failed": self.total_actions_failed,
            "user_results": [r.to_dict() for r in self.user_results],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "errors": self.errors,
        }


class ADSAPMappingEngine:
    """
    Maps Active Directory groups to SAP roles for cross-system provisioning.

    Supports:
    - Configurable AD group to SAP role mappings
    - Automatic detection of group membership changes
    - Generation of provisioning/deprovisioning actions
    - Single-user and bulk sync operations
    - Audit trail of all mapping changes
    """

    def __init__(self, db_session=None):
        self._db_session = db_session
        self._mappings: Dict[str, List[ADSAPMapping]] = {}
        self._user_group_cache: Dict[str, Set[str]] = {}
        self._sync_history: List[BulkSyncResult] = []
        self._load_default_mappings()

    def _load_default_mappings(self):
        """Load default AD group to SAP role mappings."""
        defaults = [
            ("Finance_AP", "Z_AP_USER", "DEFAULT", "Accounts Payable user role"),
            ("Finance_AR", "Z_AR_USER", "DEFAULT", "Accounts Receivable user role"),
            ("Finance_GL", "Z_GL_USER", "DEFAULT", "General Ledger user role"),
            ("Finance_Managers", "Z_FI_MANAGER", "DEFAULT", "Finance manager role"),
            ("SAP_MM", "Z_MM_USER", "DEFAULT", "Materials Management user role"),
            ("SAP_MM_Managers", "Z_MM_MANAGER", "DEFAULT", "MM manager role"),
            ("SAP_SD", "Z_SD_USER", "DEFAULT", "Sales & Distribution user role"),
            ("SAP_SD_Managers", "Z_SD_MANAGER", "DEFAULT", "SD manager role"),
            ("SAP_FICO", "Z_FICO_USER", "DEFAULT", "FI/CO user role"),
            ("SAP_HR", "Z_HR_USER", "DEFAULT", "Human Resources user role"),
            ("SAP_HR_Managers", "Z_HR_MANAGER", "DEFAULT", "HR manager role"),
            ("SAP_PP", "Z_PP_USER", "DEFAULT", "Production Planning user role"),
            ("SAP_QM", "Z_QM_USER", "DEFAULT", "Quality Management user role"),
            ("SAP_WM", "Z_WM_USER", "DEFAULT", "Warehouse Management user role"),
            ("SAP_Basis", "Z_BASIS_ADMIN", "DEFAULT", "Basis administration role"),
            ("SAP_Security", "Z_SECURITY_ADMIN", "DEFAULT", "Security administration role"),
            ("SAP_Developers", "Z_DEVELOPER", "DEFAULT", "ABAP developer role"),
            ("SAP_Transport", "Z_TRANSPORT_ADMIN", "DEFAULT", "Transport management role"),
            ("SAP_Reporting", "Z_REPORT_USER", "DEFAULT", "Reporting and analytics role"),
            ("SAP_GRC_Users", "Z_GRC_USER", "DEFAULT", "GRC platform access role"),
            ("SAP_Auditors", "Z_AUDITOR", "DEFAULT", "Audit and compliance role"),
        ]

        for ad_group, sap_role, sap_system, description in defaults:
            mapping = ADSAPMapping(
                ad_group=ad_group,
                sap_role=sap_role,
                sap_system=sap_system,
                description=description,
                auto_provision=True,
                enabled=True,
            )
            if ad_group not in self._mappings:
                self._mappings[ad_group] = []
            self._mappings[ad_group].append(mapping)

        logger.info(
            "Loaded %d default AD-SAP mappings",
            sum(len(v) for v in self._mappings.values()),
        )

    # ---- Core Mapping Operations ----

    def add_mapping(
        self,
        ad_group: str,
        sap_role: str,
        sap_system: str = "DEFAULT",
        auto_provision: bool = True,
        description: str = "",
        created_by: str = "admin",
    ) -> ADSAPMapping:
        """Add a new AD group to SAP role mapping."""
        existing = self._mappings.get(ad_group, [])
        for m in existing:
            if m.sap_role == sap_role and m.sap_system == sap_system:
                raise ValueError(
                    f"Mapping already exists: {ad_group} -> {sap_role} on {sap_system}"
                )

        mapping = ADSAPMapping(
            ad_group=ad_group,
            sap_role=sap_role,
            sap_system=sap_system,
            auto_provision=auto_provision,
            description=description,
            created_by=created_by,
            enabled=True,
        )

        if ad_group not in self._mappings:
            self._mappings[ad_group] = []
        self._mappings[ad_group].append(mapping)

        logger.info("Added mapping: %s -> %s (%s)", ad_group, sap_role, sap_system)
        return mapping

    def remove_mapping(
        self, ad_group: str, sap_role: str, sap_system: str = "DEFAULT"
    ) -> bool:
        """Remove a mapping between an AD group and SAP role."""
        mappings = self._mappings.get(ad_group, [])
        for i, m in enumerate(mappings):
            if m.sap_role == sap_role and m.sap_system == sap_system:
                mappings.pop(i)
                if not mappings:
                    del self._mappings[ad_group]
                logger.info("Removed mapping: %s -> %s (%s)", ad_group, sap_role, sap_system)
                return True
        return False

    def remove_mapping_by_id(self, mapping_id: str) -> bool:
        """Remove a mapping by its unique ID."""
        for ad_group, mappings in list(self._mappings.items()):
            for i, m in enumerate(mappings):
                if m.mapping_id == mapping_id:
                    mappings.pop(i)
                    if not mappings:
                        del self._mappings[ad_group]
                    logger.info("Removed mapping %s: %s -> %s", mapping_id, m.ad_group, m.sap_role)
                    return True
        return False

    def get_mapping_by_id(self, mapping_id: str) -> Optional[ADSAPMapping]:
        """Get a mapping by its unique ID."""
        for mappings in self._mappings.values():
            for m in mappings:
                if m.mapping_id == mapping_id:
                    return m
        return None

    def get_mappings_for_group(self, ad_group: str) -> List[ADSAPMapping]:
        """Get all SAP role mappings for a given AD group."""
        return [m for m in self._mappings.get(ad_group, []) if m.enabled]

    def get_mappings_for_role(self, sap_role: str) -> List[ADSAPMapping]:
        """Get all AD group mappings that map to a given SAP role."""
        result = []
        for mappings in self._mappings.values():
            for m in mappings:
                if m.sap_role == sap_role and m.enabled:
                    result.append(m)
        return result

    def get_all_mappings(self) -> List[ADSAPMapping]:
        """Get all configured mappings."""
        result = []
        for mappings in self._mappings.values():
            result.extend(mappings)
        return sorted(result, key=lambda m: (m.ad_group, m.sap_role))

    def update_mapping(self, mapping_id: str, **kwargs) -> Optional[ADSAPMapping]:
        """Update an existing mapping properties."""
        mapping = self.get_mapping_by_id(mapping_id)
        if not mapping:
            return None

        allowed_fields = {"auto_provision", "description", "priority", "enabled", "sap_system"}
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(mapping, key, value)
        mapping.updated_at = datetime.utcnow()
        logger.info("Updated mapping %s", mapping_id)
        return mapping

    # ---- Change Detection ----

    def detect_group_changes(
        self,
        user_id: str,
        current_groups: Set[str],
        previous_groups: Optional[Set[str]] = None,
    ) -> List[GroupChange]:
        """Detect changes in AD group membership for a user."""
        if previous_groups is None:
            previous_groups = self._user_group_cache.get(user_id, set())

        added_groups = current_groups - previous_groups
        removed_groups = previous_groups - current_groups
        changes: List[GroupChange] = []

        for group in sorted(added_groups):
            mapped_roles = [m.sap_role for m in self.get_mappings_for_group(group)]
            if mapped_roles:
                changes.append(GroupChange(
                    user_id=user_id,
                    ad_group=group,
                    change_type=ChangeType.ADDED,
                    mapped_sap_roles=mapped_roles,
                ))

        for group in sorted(removed_groups):
            mapped_roles = [m.sap_role for m in self.get_mappings_for_group(group)]
            if mapped_roles:
                changes.append(GroupChange(
                    user_id=user_id,
                    ad_group=group,
                    change_type=ChangeType.REMOVED,
                    mapped_sap_roles=mapped_roles,
                ))

        self._user_group_cache[user_id] = current_groups.copy()

        if changes:
            logger.info(
                "Detected %d group changes for user %s (added=%d, removed=%d)",
                len(changes), user_id, len(added_groups), len(removed_groups),
            )
        return changes

    def generate_provisioning_actions(
        self, changes: List[GroupChange]
    ) -> List[ProvisioningAction]:
        """Generate provisioning actions from detected group changes."""
        actions: List[ProvisioningAction] = []

        for change in changes:
            mappings = self.get_mappings_for_group(change.ad_group)
            for mapping in mappings:
                action_type = (
                    ProvisioningActionType.ASSIGN_ROLE
                    if change.change_type == ChangeType.ADDED
                    else ProvisioningActionType.REMOVE_ROLE
                )
                action = ProvisioningAction(
                    user_id=change.user_id,
                    action_type=action_type,
                    sap_role=mapping.sap_role,
                    sap_system=mapping.sap_system,
                    source_ad_group=change.ad_group,
                    auto_provision=mapping.auto_provision,
                    status=(
                        ProvisioningStatus.PENDING
                        if mapping.auto_provision
                        else ProvisioningStatus.SKIPPED
                    ),
                )
                actions.append(action)

        logger.info("Generated %d provisioning actions from %d changes", len(actions), len(changes))
        return actions

    # ---- Sync Operations ----

    def sync_user(self, user_id: str, ad_connector=None, sap_connector=None) -> SyncResult:
        """Sync a single user AD group memberships to SAP roles."""
        result = SyncResult(user_id=user_id)

        try:
            if ad_connector:
                try:
                    current_groups = set(ad_connector.get_user_groups(user_id))
                except Exception as e:
                    result.success = False
                    result.errors.append(f"Failed to get AD groups: {str(e)}")
                    return result
            else:
                current_groups = self._user_group_cache.get(user_id, set())

            changes = self.detect_group_changes(user_id, current_groups)
            result.changes = changes
            result.changes_detected = len(changes)

            if not changes:
                return result

            actions = self.generate_provisioning_actions(changes)
            result.actions = actions

            for action in actions:
                if action.status == ProvisioningStatus.SKIPPED:
                    result.actions_skipped += 1
                    continue

                if sap_connector:
                    try:
                        action.status = ProvisioningStatus.IN_PROGRESS
                        if action.action_type == ProvisioningActionType.ASSIGN_ROLE:
                            sap_connector.assign_role(
                                user_id=user_id,
                                role=action.sap_role,
                                system=action.sap_system,
                            )
                        else:
                            sap_connector.remove_role(
                                user_id=user_id,
                                role=action.sap_role,
                                system=action.sap_system,
                            )
                        action.status = ProvisioningStatus.COMPLETED
                        action.executed_at = datetime.utcnow()
                        result.actions_executed += 1
                    except Exception as e:
                        action.status = ProvisioningStatus.FAILED
                        action.error_message = str(e)
                        result.actions_failed += 1
                        result.errors.append(
                            f"Failed to {action.action_type.value} {action.sap_role}: {str(e)}"
                        )
                else:
                    result.actions_skipped += 1

            result.success = result.actions_failed == 0

        except Exception as e:
            result.success = False
            result.errors.append(f"Sync failed: {str(e)}")
            logger.error("Sync failed for user %s: %s", user_id, str(e))

        return result

    def bulk_sync(
        self, ad_connector=None, sap_connector=None, user_ids: Optional[List[str]] = None
    ) -> BulkSyncResult:
        """Sync AD group memberships to SAP roles for multiple users."""
        bulk_result = BulkSyncResult()

        if user_ids is None:
            if ad_connector:
                try:
                    user_ids = ad_connector.list_users()
                except Exception as e:
                    bulk_result.errors.append(f"Failed to list AD users: {str(e)}")
                    bulk_result.completed_at = datetime.utcnow()
                    return bulk_result
            else:
                user_ids = list(self._user_group_cache.keys())

        bulk_result.total_users = len(user_ids)

        for user_id in user_ids:
            try:
                user_result = self.sync_user(user_id, ad_connector, sap_connector)
                bulk_result.user_results.append(user_result)

                if user_result.success:
                    bulk_result.users_synced += 1
                else:
                    bulk_result.users_failed += 1

                bulk_result.total_changes += user_result.changes_detected
                bulk_result.total_actions_executed += user_result.actions_executed
                bulk_result.total_actions_failed += user_result.actions_failed

            except Exception as e:
                bulk_result.users_failed += 1
                bulk_result.errors.append(f"User {user_id}: {str(e)}")

        bulk_result.completed_at = datetime.utcnow()
        self._sync_history.append(bulk_result)

        logger.info(
            "Bulk sync completed: %d synced, %d failed, %d changes, %d actions",
            bulk_result.users_synced, bulk_result.users_failed,
            bulk_result.total_changes, bulk_result.total_actions_executed,
        )
        return bulk_result

    def get_sync_history(self, limit: int = 10) -> List[BulkSyncResult]:
        """Get recent bulk sync results."""
        return self._sync_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics about configured mappings."""
        all_mappings = self.get_all_mappings()
        enabled = [m for m in all_mappings if m.enabled]
        auto = [m for m in enabled if m.auto_provision]
        ad_groups = set(m.ad_group for m in all_mappings)
        sap_roles = set(m.sap_role for m in all_mappings)

        return {
            "total_mappings": len(all_mappings),
            "enabled_mappings": len(enabled),
            "auto_provision_mappings": len(auto),
            "unique_ad_groups": len(ad_groups),
            "unique_sap_roles": len(sap_roles),
            "cached_users": len(self._user_group_cache),
            "sync_history_count": len(self._sync_history),
        }
