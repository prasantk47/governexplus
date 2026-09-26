"""
SAP Role Redesign Copilot
Analyzes role landscape → identifies problems → proposes solutions → generates migration plan.

Input: roles, user-role assignments, authorizations, usage data, SoD rules
Output: consolidation proposals, cleanup recommendations, redesigned roles, migration steps
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
from sqlalchemy.orm import Session

from db.models.user import Role, UserRole, User, UserEntitlement


class RoleRedesignCopilot:
    def __init__(self, tenant_id: str, db: Session):
        self.tenant_id = tenant_id
        self.db = db

    # ── Analysis Phase ──────────────────────────────────────────────────

    def analyze_landscape(self) -> dict:
        """Full landscape analysis — the entry point.
        Returns comprehensive intelligence report."""
        roles = self.db.query(Role).filter_by(tenant_id=self.tenant_id, is_active=True).all()
        user_roles = self.db.query(UserRole).filter_by(tenant_id=self.tenant_id, is_active=True).all()
        users = self.db.query(User).filter_by(tenant_id=self.tenant_id).all()

        # Build lookup maps
        role_map = {r.id: r for r in roles}
        role_users: Dict[int, list] = defaultdict(list)   # role pk -> [user pks]
        user_role_map: Dict[int, list] = defaultdict(list) # user pk -> [role pks]
        for ur in user_roles:
            role_users[ur.role_id].append(ur.user_id)
            user_role_map[ur.user_id].append(ur.role_id)

        # Run all analyses
        unused = self._find_unused_roles(roles, role_users)
        duplicates = self._find_duplicate_roles(roles)
        similar = self._find_similar_roles(roles)
        high_risk = self._find_high_risk_roles(roles)
        overprovisioned = self._find_overprovisioned_users(users, user_role_map, role_map)
        consolidation = self._propose_consolidation(similar, role_users, role_map)

        return {
            "analysis_id": f"RRA-{uuid.uuid4().hex[:8].upper()}",
            "generated_at": datetime.utcnow().isoformat(),
            "landscape": {
                "total_roles": len(roles),
                "total_users": len(users),
                "total_assignments": len(user_roles),
                "role_types": dict(Counter(r.role_type for r in roles)),
            },
            "findings": {
                "unused_roles": {"count": len(unused), "roles": unused[:50]},
                "duplicate_roles": {"count": len(duplicates), "pairs": duplicates[:50]},
                "similar_roles": {"count": len(similar), "pairs": similar[:50]},
                "high_risk_roles": {"count": len(high_risk), "roles": high_risk[:50]},
                "overprovisioned_users": {"count": len(overprovisioned), "users": overprovisioned[:20]},
            },
            "recommendations": {
                "consolidation_proposals": consolidation[:20],
                "estimated_role_reduction": len(unused) + sum(
                    1 for c in consolidation if c.get("merge_count", 0) > 1
                ),
                "estimated_risk_reduction_pct": min(30, len(high_risk) * 2),
            },
        }

    def _find_unused_roles(self, roles: list, role_users: dict) -> list:
        """Roles with 0 user assignments."""
        unused = []
        for r in roles:
            if r.id not in role_users or len(role_users[r.id]) == 0:
                unused.append({
                    "role_id": r.role_id,
                    "role_name": r.role_name,
                    "role_type": r.role_type,
                    "recommendation": "Delete or archive — no users assigned",
                })
        return unused

    def _find_duplicate_roles(self, roles: list) -> list:
        """Roles with identical names (case-insensitive) or descriptions."""
        seen_names: Dict[str, list] = defaultdict(list)
        for r in roles:
            key = (r.role_name or "").strip().lower()
            if key:
                seen_names[key].append(r)

        duplicates = []
        for name, group in seen_names.items():
            if len(group) > 1:
                duplicates.append({
                    "name": name,
                    "roles": [
                        {
                            "role_id": r.role_id,
                            "role_name": r.role_name,
                            "user_count": r.user_count or 0,
                        }
                        for r in group
                    ],
                    "recommendation": f"Consolidate {len(group)} duplicate roles into one",
                })
        return duplicates

    def _find_similar_roles(self, roles: list) -> list:
        """Roles with similar names (prefix-similarity heuristic)."""
        similar = []
        role_list = sorted(roles, key=lambda r: r.role_name or "")
        for i in range(len(role_list)):
            for j in range(i + 1, min(i + 10, len(role_list))):
                a, b = role_list[i], role_list[j]
                name_a = (a.role_name or "").lower()
                name_b = (b.role_name or "").lower()
                # Simple prefix similarity
                common_prefix = 0
                for ca, cb in zip(name_a, name_b):
                    if ca == cb:
                        common_prefix += 1
                    else:
                        break
                min_len = min(len(name_a), len(name_b))
                if min_len > 5 and common_prefix / min_len > 0.7 and name_a != name_b:
                    similar.append({
                        "role_a": {"role_id": a.role_id, "role_name": a.role_name},
                        "role_b": {"role_id": b.role_id, "role_name": b.role_name},
                        "similarity": round(common_prefix / min_len * 100),
                        "recommendation": "Review for potential consolidation",
                    })
        return similar

    def _find_high_risk_roles(self, roles: list) -> list:
        """Roles marked as high/critical risk or sensitive."""
        return [
            {
                "role_id": r.role_id,
                "role_name": r.role_name,
                "risk_level": r.risk_level,
                "is_sensitive": r.is_sensitive,
                "user_count": r.user_count or 0,
                "recommendation": "Review user assignments and consider restricting",
            }
            for r in roles
            if r.risk_level in ("high", "critical") or r.is_sensitive
        ]

    def _find_overprovisioned_users(
        self,
        users: list,
        user_role_map: dict,
        role_map: dict,
        threshold: int = 10,
    ) -> list:
        """Users with excessive role count."""
        overprovisioned = []
        for u in users:
            count = len(user_role_map.get(u.id, []))
            if count > threshold:
                roles = [
                    role_map[rid].role_name
                    for rid in user_role_map[u.id]
                    if rid in role_map
                ]
                overprovisioned.append({
                    "user_id": u.user_id,
                    "full_name": u.full_name,
                    "role_count": count,
                    "department": u.department,
                    "roles": roles[:20],
                    "recommendation": (
                        f"Review {count} role assignments — above threshold of {threshold}"
                    ),
                })
        return sorted(overprovisioned, key=lambda x: x["role_count"], reverse=True)

    def _propose_consolidation(
        self,
        similar_pairs: list,
        role_users: dict,
        role_map: dict,
    ) -> list:
        """Group similar roles into consolidation proposals."""
        proposals = []
        seen: set = set()
        for pair in similar_pairs:
            a_id = pair["role_a"]["role_id"]
            b_id = pair["role_b"]["role_id"]
            if a_id in seen or b_id in seen:
                continue
            seen.add(a_id)
            seen.add(b_id)

            # Resolve DB PKs from role_map (role_map is keyed by pk integer)
            # role_users keys are DB PKs; pair role_ids are business role_ids
            # Look up PKs for a and b from role_map
            a_pk = next(
                (pk for pk, r in role_map.items() if r.role_id == a_id), None
            )
            b_pk = next(
                (pk for pk, r in role_map.items() if r.role_id == b_id), None
            )
            a_users = len(role_users.get(a_pk, [])) if a_pk else 0
            b_users = len(role_users.get(b_pk, [])) if b_pk else 0

            keep = pair["role_a"] if a_users >= b_users else pair["role_b"]
            merge = pair["role_b"] if a_users >= b_users else pair["role_a"]

            proposals.append({
                "proposal_id": f"CRP-{uuid.uuid4().hex[:6].upper()}",
                "action": "consolidate",
                "keep_role": keep,
                "merge_roles": [merge],
                "merge_count": 2,
                "affected_users": a_users + b_users,
                "similarity": pair["similarity"],
                "steps": [
                    f"Compare authorizations of {keep['role_id']} and {merge['role_id']}",
                    f"Merge unique authorizations into {keep['role_id']}",
                    f"Reassign users from {merge['role_id']} to {keep['role_id']}",
                    f"Run SoD check on merged role",
                    f"Deactivate {merge['role_id']}",
                    "Validate user access post-migration",
                ],
            })
        return proposals

    # ── Redesign Phase ──────────────────────────────────────────────────

    def propose_role_split(self, role_id: str) -> dict:
        """Propose splitting a role with SoD conflicts into clean roles."""
        role = (
            self.db.query(Role)
            .filter_by(tenant_id=self.tenant_id, role_id=role_id)
            .first()
        )
        if not role:
            return {"error": "Role not found"}

        # Get user assignments for this role
        user_roles = (
            self.db.query(UserRole)
            .filter_by(tenant_id=self.tenant_id, role_id=role.id, is_active=True)
            .all()
        )

        user_ids = [ur.user_id for ur in user_roles]
        entitlements: list = []
        if user_ids:
            entitlements = (
                self.db.query(UserEntitlement)
                .filter(
                    UserEntitlement.user_id.in_(user_ids),
                    UserEntitlement.source_role == role_id,
                    UserEntitlement.auth_object == "S_TCODE",
                )
                .all()
            )

        tcodes = list({e.auth_value for e in entitlements})

        # Categorize tcodes by business function
        categories = self._categorize_tcodes(tcodes)

        # Propose split roles
        new_roles = []
        for cat_name, cat_tcodes in categories.items():
            new_roles.append({
                "proposed_role_name": f"{role.role_name}_{cat_name.upper()}",
                "function": cat_name,
                "tcodes": cat_tcodes,
                "tcode_count": len(cat_tcodes),
            })

        return {
            "original_role": {"role_id": role.role_id, "role_name": role.role_name},
            "original_tcodes": tcodes,
            "proposed_split": new_roles,
            "split_count": len(new_roles),
            "reason": (
                "Separate conflicting business functions to eliminate SoD violations"
            ),
            "migration_steps": [
                f"Create {len(new_roles)} new roles based on proposal",
                "Run SoD check on each new role individually",
                f"Reassign {len(user_ids)} users to appropriate new roles",
                f"Deactivate original role {role.role_id}",
                "Run post-migration SoD analysis on all affected users",
            ],
            "test_cases": [
                "Verify each new role has no internal SoD conflicts",
                "Verify user access unchanged (union of new roles = original)",
                "Verify no new cross-role SoD introduced",
                "Validate business process execution for each affected user",
            ],
        }

    def _categorize_tcodes(self, tcodes: list) -> dict:
        """Categorize tcodes by business function."""
        categories: Dict[str, list] = {
            "master_data": [],
            "documents": [],
            "reporting": [],
            "config": [],
            "other": [],
        }
        for tc in tcodes:
            tc_upper = tc.upper()
            if any(tc_upper.startswith(p) for p in ["XK", "FK", "MK", "XD", "FD", "BP"]):
                categories["master_data"].append(tc)
            elif any(
                tc_upper.startswith(p)
                for p in ["FB", "F-", "FV", "MR", "MI", "MB", "ME2"]
            ):
                categories["documents"].append(tc)
            elif any(tc_upper.startswith(p) for p in ["S_", "SA", "SE", "SM", "SU", "SP"]):
                categories["config"].append(tc)
            elif any(
                tc_upper.startswith(p) for p in ["FA", "FS", "FK1", "FBL", "KS", "ME2"]
            ):
                categories["reporting"].append(tc)
            else:
                categories["other"].append(tc)
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

    # ── Intelligence Report ─────────────────────────────────────────────

    def generate_executive_summary(self, analysis: dict) -> dict:
        """Generate executive-level summary from analysis."""
        findings = analysis.get("findings", {})
        landscape = analysis.get("landscape", {})
        recommendations = analysis.get("recommendations", {})

        total_roles = landscape.get("total_roles", 0)
        unused = findings.get("unused_roles", {}).get("count", 0)
        duplicates = findings.get("duplicate_roles", {}).get("count", 0)
        high_risk = findings.get("high_risk_roles", {}).get("count", 0)
        reduction = recommendations.get("estimated_role_reduction", 0)

        health_score = max(0, 100 - (unused * 2) - (duplicates * 3) - (high_risk * 5))
        health_score = min(100, health_score)

        return {
            "title": "Role Landscape Intelligence Report",
            "generated_at": datetime.utcnow().isoformat(),
            "health_score": health_score,
            "summary": (
                f"Your role landscape has {total_roles} active roles. "
                f"We identified {unused} unused roles, {duplicates} duplicate groups, "
                f"and {high_risk} high-risk roles. "
                f"Estimated {reduction} roles can be eliminated through consolidation and cleanup, "
                f"reducing complexity by {round(reduction / max(total_roles, 1) * 100)}%."
            ),
            "key_metrics": {
                "total_roles": total_roles,
                "unused_roles": unused,
                "duplicate_groups": duplicates,
                "high_risk_roles": high_risk,
                "estimated_reduction": reduction,
                "reduction_pct": round(reduction / max(total_roles, 1) * 100),
            },
            "priority_actions": [
                {
                    "priority": 1,
                    "action": f"Delete/archive {unused} unused roles",
                    "effort": "Low",
                    "impact": "Medium",
                },
                {
                    "priority": 2,
                    "action": f"Consolidate {duplicates} duplicate role groups",
                    "effort": "Medium",
                    "impact": "High",
                },
                {
                    "priority": 3,
                    "action": f"Review {high_risk} high-risk role assignments",
                    "effort": "Medium",
                    "impact": "Critical",
                },
            ],
        }
