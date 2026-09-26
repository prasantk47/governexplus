"""
Migration Copilot — ECC → S/4HANA Role Migration with SoD Validation
Maps old roles to new, validates SoD, generates migration plan + test cases.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from sqlalchemy.orm import Session

from db.models.user import Role, UserRole, User


class MigrationCopilot:
    """AI-assisted role migration from ECC to S/4HANA."""

    # Known ECC→S/4HANA tcode mappings (subset — extensible)
    TCODE_MAP = {
        # FI
        "FB01": "FB01", "FB02": "FB02", "FB03": "FB03",
        "FB60": "FB60", "FB65": "FB65", "FB70": "FB70",
        "F-28": "F-28", "F-32": "F-32", "F110": "F110",
        "FK01": "BP", "FK02": "BP", "FK03": "BP",  # Vendor → BP
        "XK01": "BP", "XK02": "BP", "XK03": "BP",
        "FD01": "BP", "FD02": "BP", "FD03": "BP",  # Customer → BP
        "XD01": "BP", "XD02": "BP", "XD03": "BP",
        # MM
        "ME21N": "ME21N", "ME22N": "ME22N", "ME23N": "ME23N",
        "MIGO": "MIGO", "MIRO": "MIRO",
        "MM01": "MM01", "MM02": "MM02", "MM03": "MM03",
        "MB01": "MIGO", "MB1A": "MIGO", "MB1B": "MIGO", "MB1C": "MIGO",
        # SD
        "VA01": "VA01", "VA02": "VA02", "VA03": "VA03",
        "VL01N": "VL01N", "VL02N": "VL02N",
        "VF01": "VF01", "VF02": "VF02",
        # Replaced in S/4
        "F-43": "FB60", "F-44": "FB65",
        "MK01": "BP", "MK02": "BP",
        "MRBR": "MRBR_S4",
    }

    # Tcodes removed/deprecated in S/4HANA
    DEPRECATED = {"LSMW", "SE16", "SE16N", "SM30", "SM31", "SCAT", "CATT"}

    # Fiori apps replacing tcodes
    FIORI_MAP = {
        "BP": {"app": "F0842A", "name": "Manage Business Partner"},
        "FB60": {"app": "F0859", "name": "Post Supplier Invoices"},
        "ME21N": {"app": "F1943", "name": "Create Purchase Order"},
        "VA01": {"app": "F5765", "name": "Create Sales Order"},
        "MIGO": {"app": "F3893", "name": "Post Goods Receipt"},
    }

    def __init__(self, tenant_id: str, db: Session):
        self.tenant_id = tenant_id
        self.db = db

    def analyze_migration_impact(self) -> dict:
        """Analyze full migration impact for all roles."""
        roles = self.db.query(Role).filter_by(tenant_id=self.tenant_id, is_active=True).all()

        results = {
            "analysis_id": f"MIG-{uuid.uuid4().hex[:8].upper()}",
            "generated_at": datetime.utcnow().isoformat(),
            "total_roles": len(roles),
            "roles_requiring_changes": 0,
            "roles_no_change": 0,
            "deprecated_tcode_usage": 0,
            "bp_migration_needed": 0,
            "fiori_opportunities": 0,
            "role_mappings": [],
        }

        for role in roles:
            mapping = self._map_role(role)
            if mapping["changes_required"]:
                results["roles_requiring_changes"] += 1
            else:
                results["roles_no_change"] += 1
            if mapping["deprecated_tcodes"]:
                results["deprecated_tcode_usage"] += 1
            if mapping["bp_consolidation"]:
                results["bp_migration_needed"] += 1
            if mapping["fiori_apps"]:
                results["fiori_opportunities"] += 1
            results["role_mappings"].append(mapping)

        results["summary"] = (
            f"Of {len(roles)} roles, {results['roles_requiring_changes']} require changes for S/4HANA. "
            f"{results['bp_migration_needed']} need Business Partner migration. "
            f"{results['deprecated_tcode_usage']} use deprecated transactions. "
            f"{results['fiori_opportunities']} have Fiori app alternatives."
        )
        return results

    def _map_role(self, role: Role) -> dict:
        """Map a single role from ECC to S/4HANA."""
        from db.models.user import UserEntitlement, UserRole as UR
        user_roles = self.db.query(UR).filter_by(
            tenant_id=self.tenant_id, role_id=role.id, is_active=True
        ).limit(1).all()

        tcodes = []
        if user_roles:
            ents = self.db.query(UserEntitlement).filter(
                UserEntitlement.user_id == user_roles[0].user_id,
                UserEntitlement.source_role == role.role_id,
                UserEntitlement.auth_object == "S_TCODE"
            ).all()
            tcodes = [e.auth_value for e in ents]

        mapped = []
        deprecated = []
        bp_needed = False
        fiori = []
        changes = []

        for tc in tcodes:
            tc_upper = tc.upper()
            if tc_upper in self.DEPRECATED:
                deprecated.append(tc_upper)
                changes.append(f"Remove deprecated tcode {tc_upper}")
            elif tc_upper in self.TCODE_MAP:
                new_tc = self.TCODE_MAP[tc_upper]
                if new_tc != tc_upper:
                    mapped.append({"old": tc_upper, "new": new_tc})
                    changes.append(f"Replace {tc_upper} → {new_tc}")
                    if new_tc == "BP":
                        bp_needed = True
                if new_tc in self.FIORI_MAP:
                    fiori.append(self.FIORI_MAP[new_tc])

        return {
            "role_id": role.role_id,
            "role_name": role.role_name,
            "original_tcodes": tcodes,
            "tcode_mappings": mapped,
            "deprecated_tcodes": deprecated,
            "bp_consolidation": bp_needed,
            "fiori_apps": fiori,
            "changes_required": bool(mapped or deprecated),
            "change_count": len(changes),
            "changes": changes,
            "migration_steps": self._generate_migration_steps(role, mapped, deprecated, bp_needed),
            "test_cases": self._generate_test_cases(role, mapped, deprecated),
        }

    def migrate_role(self, role_id: str) -> dict:
        """Generate detailed migration plan for a single role."""
        role = self.db.query(Role).filter_by(
            tenant_id=self.tenant_id, role_id=role_id
        ).first()
        if not role:
            return {"error": "Role not found"}

        mapping = self._map_role(role)

        # Get affected users
        user_roles = self.db.query(UserRole).filter_by(
            tenant_id=self.tenant_id, role_id=role.id, is_active=True
        ).all()
        user_ids = [ur.user_id for ur in user_roles]
        users = self.db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []

        mapping["affected_users"] = [
            {"user_id": u.user_id, "full_name": u.full_name, "department": u.department}
            for u in users
        ]
        mapping["affected_user_count"] = len(users)
        mapping["proposed_new_role_name"] = f"{role.role_id}_S4" if mapping["changes_required"] else role.role_id
        mapping["validation"] = {
            "pre_migration": [
                "Export current role authorizations",
                "Document current user assignments",
                "Run SoD analysis on current role",
                "Backup role configuration",
            ],
            "post_migration": [
                "Run SoD analysis on migrated role",
                "Compare authorization scope (before/after)",
                "Validate business process execution",
                "Verify Fiori app access where applicable",
                f"Test with {min(3, len(users))} representative users",
            ],
        }
        return mapping

    def _generate_migration_steps(self, role, mapped, deprecated, bp_needed) -> list:
        steps = []
        if mapped:
            steps.append(f"Update {len(mapped)} transaction code mappings")
        if deprecated:
            steps.append(f"Remove {len(deprecated)} deprecated transactions")
        if bp_needed:
            steps.append("Add BP (Business Partner) authorization and remove legacy vendor/customer tcodes")
        steps.append("Run SoD check on migrated role")
        steps.append("Test business process execution")
        steps.append("Reassign users to migrated role")
        return steps

    def _generate_test_cases(self, role, mapped, deprecated) -> list:
        cases = [f"Verify role {role.role_id} loads without errors in S/4HANA"]
        for m in mapped[:5]:
            cases.append(f"Verify {m['new']} works as replacement for {m['old']}")
        for d in deprecated[:3]:
            cases.append(f"Verify {d} is no longer accessible")
        cases.append("Execute end-to-end business process test")
        return cases

    def generate_migration_report(self) -> dict:
        """Executive migration readiness report."""
        analysis = self.analyze_migration_impact()
        total = analysis["total_roles"]
        changes = analysis["roles_requiring_changes"]

        readiness = round((analysis["roles_no_change"] / max(total, 1)) * 100)

        return {
            "title": "S/4HANA Migration Readiness Report",
            "generated_at": datetime.utcnow().isoformat(),
            "readiness_score": readiness,
            "total_roles": total,
            "roles_ready": analysis["roles_no_change"],
            "roles_need_work": changes,
            "bp_migration_count": analysis["bp_migration_needed"],
            "deprecated_usage_count": analysis["deprecated_tcode_usage"],
            "fiori_opportunity_count": analysis["fiori_opportunities"],
            "summary": analysis["summary"],
            "effort_estimate": {
                "low_effort": analysis["roles_no_change"],
                "medium_effort": changes - analysis["bp_migration_needed"],
                "high_effort": analysis["bp_migration_needed"],
            },
            "recommended_sequence": [
                {"phase": 1, "action": f"Migrate {analysis['roles_no_change']} roles with no changes", "effort": "Low"},
                {"phase": 2, "action": f"Update {changes - analysis['bp_migration_needed']} roles with tcode mappings", "effort": "Medium"},
                {"phase": 3, "action": f"Migrate {analysis['bp_migration_needed']} roles requiring BP consolidation", "effort": "High"},
            ],
        }
