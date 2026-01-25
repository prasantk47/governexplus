"""
Rule Transport System

Version-controlled rule management with import/export, Git integration,
environment promotion, and change tracking.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from datetime import datetime
import json
import hashlib
import uuid


class TransportStatus(Enum):
    """Transport request status"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPORTED = "imported"
    RELEASED = "released"
    CANCELLED = "cancelled"


class RuleObjectType(Enum):
    """Types of objects that can be transported"""
    SOD_RULE = "sod_rule"
    SENSITIVE_ACCESS_RULE = "sensitive_access_rule"
    BUSINESS_FUNCTION = "business_function"
    RISK_RULE = "risk_rule"
    WORKFLOW = "workflow"
    MITIGATION_CONTROL = "mitigation_control"
    RULESET = "ruleset"


class Environment(Enum):
    """Target environments"""
    DEVELOPMENT = "development"
    QUALITY = "quality"
    PRODUCTION = "production"


@dataclass
class TransportObject:
    """Object included in a transport"""
    object_id: str
    object_type: RuleObjectType
    object_name: str
    version: int
    content_hash: str
    content: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)  # Other object IDs
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TransportRequest:
    """Transport request for moving rules between environments"""
    transport_id: str
    tenant_id: str
    name: str
    description: str

    # Source and target
    source_environment: Environment
    target_environment: Environment

    # Objects
    objects: List[TransportObject] = field(default_factory=list)

    # Status
    status: TransportStatus = TransportStatus.DRAFT

    # Approval
    requires_approval: bool = True
    approver_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_comments: str = ""

    # Execution
    imported_at: Optional[datetime] = None
    import_log: List[str] = field(default_factory=list)

    # Metadata
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RuleVersion:
    """Version history for a rule"""
    version_id: str
    object_id: str
    object_type: RuleObjectType
    version_number: int
    content: Dict[str, Any]
    content_hash: str
    change_description: str
    created_by: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Comparison
    previous_version_id: Optional[str] = None
    changes: Dict[str, Any] = field(default_factory=dict)


class RuleTransportSystem:
    """
    Rule Transport System

    Provides:
    1. Rule versioning and history
    2. Transport requests for environment promotion
    3. Import/Export with dependency resolution
    4. Approval workflow for production changes
    5. Rollback capabilities
    """

    def __init__(self):
        # Rule versions by object ID
        self.versions: Dict[str, List[RuleVersion]] = {}

        # Current version by object ID
        self.current_versions: Dict[str, RuleVersion] = {}

        # Transport requests
        self.transports: Dict[str, TransportRequest] = {}

        # Environment data (simulated)
        self.environments: Dict[Environment, Dict[str, Any]] = {
            Environment.DEVELOPMENT: {},
            Environment.QUALITY: {},
            Environment.PRODUCTION: {}
        }

    # ==================== Versioning ====================

    def create_version(
        self,
        object_id: str,
        object_type: RuleObjectType,
        content: Dict[str, Any],
        change_description: str,
        created_by: str
    ) -> RuleVersion:
        """Create a new version of a rule"""
        # Calculate content hash
        content_hash = self._calculate_hash(content)

        # Get previous version info
        prev_version = self.current_versions.get(object_id)
        version_number = (prev_version.version_number + 1) if prev_version else 1
        prev_version_id = prev_version.version_id if prev_version else None

        # Calculate changes
        changes = {}
        if prev_version:
            changes = self._calculate_diff(prev_version.content, content)

        # Create version
        version = RuleVersion(
            version_id=f"VER_{object_id}_{version_number}",
            object_id=object_id,
            object_type=object_type,
            version_number=version_number,
            content=content,
            content_hash=content_hash,
            change_description=change_description,
            created_by=created_by,
            previous_version_id=prev_version_id,
            changes=changes
        )

        # Store
        if object_id not in self.versions:
            self.versions[object_id] = []
        self.versions[object_id].append(version)
        self.current_versions[object_id] = version

        return version

    def get_version_history(
        self,
        object_id: str,
        limit: int = 50
    ) -> List[RuleVersion]:
        """Get version history for an object"""
        versions = self.versions.get(object_id, [])
        return sorted(versions, key=lambda v: v.version_number, reverse=True)[:limit]

    def get_version(self, version_id: str) -> Optional[RuleVersion]:
        """Get a specific version"""
        for versions in self.versions.values():
            for version in versions:
                if version.version_id == version_id:
                    return version
        return None

    def rollback_to_version(
        self,
        object_id: str,
        version_id: str,
        rolled_back_by: str
    ) -> RuleVersion:
        """Rollback to a previous version"""
        target_version = self.get_version(version_id)
        if not target_version or target_version.object_id != object_id:
            raise ValueError(f"Version not found: {version_id}")

        # Create a new version with the old content
        return self.create_version(
            object_id=object_id,
            object_type=target_version.object_type,
            content=target_version.content,
            change_description=f"Rollback to version {target_version.version_number}",
            created_by=rolled_back_by
        )

    def compare_versions(
        self,
        version_id_1: str,
        version_id_2: str
    ) -> Dict[str, Any]:
        """Compare two versions"""
        v1 = self.get_version(version_id_1)
        v2 = self.get_version(version_id_2)

        if not v1 or not v2:
            return {"error": "Version not found"}

        return {
            "version_1": {
                "version_id": v1.version_id,
                "version_number": v1.version_number,
                "created_at": v1.created_at.isoformat()
            },
            "version_2": {
                "version_id": v2.version_id,
                "version_number": v2.version_number,
                "created_at": v2.created_at.isoformat()
            },
            "differences": self._calculate_diff(v1.content, v2.content)
        }

    # ==================== Transport Requests ====================

    def create_transport(
        self,
        tenant_id: str,
        name: str,
        description: str,
        source_environment: Environment,
        target_environment: Environment,
        created_by: str
    ) -> TransportRequest:
        """Create a new transport request"""
        transport_id = f"TR_{tenant_id}_{uuid.uuid4().hex[:8]}"

        # Determine if approval required (always for production)
        requires_approval = target_environment == Environment.PRODUCTION

        transport = TransportRequest(
            transport_id=transport_id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            source_environment=source_environment,
            target_environment=target_environment,
            requires_approval=requires_approval,
            created_by=created_by
        )

        self.transports[transport_id] = transport
        return transport

    def add_object_to_transport(
        self,
        transport_id: str,
        object_id: str,
        include_dependencies: bool = True
    ) -> TransportRequest:
        """Add an object to a transport request"""
        transport = self.transports.get(transport_id)
        if not transport:
            raise ValueError(f"Transport not found: {transport_id}")

        if transport.status != TransportStatus.DRAFT:
            raise ValueError("Cannot modify submitted transport")

        # Get current version
        version = self.current_versions.get(object_id)
        if not version:
            raise ValueError(f"Object not found: {object_id}")

        # Create transport object
        transport_object = TransportObject(
            object_id=version.object_id,
            object_type=version.object_type,
            object_name=version.content.get("name", object_id),
            version=version.version_number,
            content_hash=version.content_hash,
            content=version.content
        )

        # Check if already added
        existing_ids = {obj.object_id for obj in transport.objects}
        if object_id not in existing_ids:
            transport.objects.append(transport_object)

        # Add dependencies
        if include_dependencies:
            dependencies = version.content.get("dependencies", [])
            for dep_id in dependencies:
                if dep_id not in existing_ids:
                    self.add_object_to_transport(transport_id, dep_id, True)

        transport.updated_at = datetime.utcnow()
        return transport

    def remove_object_from_transport(
        self,
        transport_id: str,
        object_id: str
    ) -> TransportRequest:
        """Remove an object from a transport request"""
        transport = self.transports.get(transport_id)
        if not transport:
            raise ValueError(f"Transport not found: {transport_id}")

        if transport.status != TransportStatus.DRAFT:
            raise ValueError("Cannot modify submitted transport")

        transport.objects = [obj for obj in transport.objects if obj.object_id != object_id]
        transport.updated_at = datetime.utcnow()
        return transport

    def submit_transport(self, transport_id: str) -> TransportRequest:
        """Submit a transport request for approval"""
        transport = self.transports.get(transport_id)
        if not transport:
            raise ValueError(f"Transport not found: {transport_id}")

        if not transport.objects:
            raise ValueError("Transport has no objects")

        if transport.status != TransportStatus.DRAFT:
            raise ValueError("Transport already submitted")

        transport.status = TransportStatus.SUBMITTED
        transport.updated_at = datetime.utcnow()
        return transport

    def approve_transport(
        self,
        transport_id: str,
        approver_id: str,
        comments: str = ""
    ) -> TransportRequest:
        """Approve a transport request"""
        transport = self.transports.get(transport_id)
        if not transport:
            raise ValueError(f"Transport not found: {transport_id}")

        if transport.status != TransportStatus.SUBMITTED:
            raise ValueError("Transport not pending approval")

        transport.status = TransportStatus.APPROVED
        transport.approver_id = approver_id
        transport.approved_at = datetime.utcnow()
        transport.approval_comments = comments
        transport.updated_at = datetime.utcnow()
        return transport

    def reject_transport(
        self,
        transport_id: str,
        approver_id: str,
        comments: str
    ) -> TransportRequest:
        """Reject a transport request"""
        transport = self.transports.get(transport_id)
        if not transport:
            raise ValueError(f"Transport not found: {transport_id}")

        if transport.status != TransportStatus.SUBMITTED:
            raise ValueError("Transport not pending approval")

        transport.status = TransportStatus.REJECTED
        transport.approver_id = approver_id
        transport.approval_comments = comments
        transport.updated_at = datetime.utcnow()
        return transport

    def execute_transport(self, transport_id: str) -> Dict[str, Any]:
        """Execute (import) a transport into target environment"""
        transport = self.transports.get(transport_id)
        if not transport:
            raise ValueError(f"Transport not found: {transport_id}")

        if transport.requires_approval and transport.status != TransportStatus.APPROVED:
            raise ValueError("Transport not approved")

        if not transport.requires_approval and transport.status not in [TransportStatus.DRAFT, TransportStatus.SUBMITTED]:
            raise ValueError("Invalid transport status")

        import_log = []
        imported_count = 0
        errors = []

        # Import each object
        for obj in transport.objects:
            try:
                # In production, this would write to the target environment's database
                env_data = self.environments.get(transport.target_environment, {})
                env_data[obj.object_id] = {
                    "type": obj.object_type.value,
                    "name": obj.object_name,
                    "version": obj.version,
                    "content": obj.content,
                    "imported_at": datetime.utcnow().isoformat(),
                    "transport_id": transport_id
                }

                import_log.append(f"Imported {obj.object_type.value}: {obj.object_name} (v{obj.version})")
                imported_count += 1

            except Exception as e:
                errors.append(f"Failed to import {obj.object_name}: {str(e)}")
                import_log.append(f"ERROR: Failed to import {obj.object_name}: {str(e)}")

        # Update transport status
        transport.status = TransportStatus.IMPORTED
        transport.imported_at = datetime.utcnow()
        transport.import_log = import_log
        transport.updated_at = datetime.utcnow()

        return {
            "transport_id": transport_id,
            "status": "imported" if not errors else "partial",
            "imported_count": imported_count,
            "error_count": len(errors),
            "errors": errors,
            "log": import_log
        }

    # ==================== Export/Import ====================

    def export_ruleset(
        self,
        object_ids: List[str],
        include_dependencies: bool = True,
        include_history: bool = False
    ) -> Dict[str, Any]:
        """Export rules to a portable format"""
        export_data = {
            "export_version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "objects": [],
            "dependencies": []
        }

        all_ids = set(object_ids)
        processed_ids: Set[str] = set()

        # Collect objects and dependencies
        while all_ids - processed_ids:
            current_id = (all_ids - processed_ids).pop()
            processed_ids.add(current_id)

            version = self.current_versions.get(current_id)
            if not version:
                continue

            obj_export = {
                "object_id": version.object_id,
                "object_type": version.object_type.value,
                "version": version.version_number,
                "content": version.content,
                "content_hash": version.content_hash
            }

            if include_history:
                obj_export["history"] = [
                    {
                        "version": v.version_number,
                        "change_description": v.change_description,
                        "created_by": v.created_by,
                        "created_at": v.created_at.isoformat()
                    }
                    for v in self.get_version_history(current_id)
                ]

            export_data["objects"].append(obj_export)

            # Add dependencies
            if include_dependencies:
                deps = version.content.get("dependencies", [])
                for dep_id in deps:
                    all_ids.add(dep_id)
                    if dep_id not in [d["from"] for d in export_data["dependencies"]]:
                        export_data["dependencies"].append({
                            "from": current_id,
                            "to": dep_id
                        })

        return export_data

    def import_ruleset(
        self,
        export_data: Dict[str, Any],
        imported_by: str,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """Import rules from exported data"""
        results = {
            "imported": [],
            "skipped": [],
            "errors": []
        }

        # Sort by dependencies (simple topological sort)
        dep_graph = {obj["object_id"]: [] for obj in export_data["objects"]}
        for dep in export_data.get("dependencies", []):
            if dep["from"] in dep_graph:
                dep_graph[dep["from"]].append(dep["to"])

        # Import in dependency order
        imported_ids: Set[str] = set()
        for obj_data in export_data["objects"]:
            object_id = obj_data["object_id"]

            # Check dependencies
            deps = dep_graph.get(object_id, [])
            missing_deps = [d for d in deps if d not in imported_ids and d not in self.current_versions]
            if missing_deps:
                results["errors"].append({
                    "object_id": object_id,
                    "error": f"Missing dependencies: {missing_deps}"
                })
                continue

            # Check if exists
            if object_id in self.current_versions and not overwrite:
                results["skipped"].append({
                    "object_id": object_id,
                    "reason": "Already exists (use overwrite=true)"
                })
                continue

            try:
                # Create version
                self.create_version(
                    object_id=object_id,
                    object_type=RuleObjectType(obj_data["object_type"]),
                    content=obj_data["content"],
                    change_description=f"Imported from export",
                    created_by=imported_by
                )

                results["imported"].append(object_id)
                imported_ids.add(object_id)

            except Exception as e:
                results["errors"].append({
                    "object_id": object_id,
                    "error": str(e)
                })

        return results

    # ==================== Utilities ====================

    def _calculate_hash(self, content: Dict[str, Any]) -> str:
        """Calculate hash of content"""
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def _calculate_diff(
        self,
        old_content: Dict[str, Any],
        new_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate differences between two versions"""
        diff = {
            "added": {},
            "removed": {},
            "modified": {}
        }

        old_keys = set(old_content.keys())
        new_keys = set(new_content.keys())

        # Added keys
        for key in new_keys - old_keys:
            diff["added"][key] = new_content[key]

        # Removed keys
        for key in old_keys - new_keys:
            diff["removed"][key] = old_content[key]

        # Modified keys
        for key in old_keys & new_keys:
            if old_content[key] != new_content[key]:
                diff["modified"][key] = {
                    "old": old_content[key],
                    "new": new_content[key]
                }

        return diff

    def get_transport_history(
        self,
        tenant_id: str,
        status: TransportStatus = None,
        limit: int = 50
    ) -> List[TransportRequest]:
        """Get transport history for a tenant"""
        transports = [t for t in self.transports.values() if t.tenant_id == tenant_id]

        if status:
            transports = [t for t in transports if t.status == status]

        return sorted(transports, key=lambda t: t.created_at, reverse=True)[:limit]


# Singleton instance
rule_transport = RuleTransportSystem()
