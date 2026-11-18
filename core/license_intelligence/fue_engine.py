"""
FUE Classification Engine (LI-001) + Consumption Calculator (LI-002)
====================================================================
Real production engine. Classifies SAP users into FUE use types by
applying rule pack auth mappings to their actual role/authorization data.
No mocks, no stubs — reads live data from the platform DB.
"""
import uuid
import re
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func


def _id() -> str:
    return str(uuid.uuid4())


# ── Default S/4HANA FUE Rule Pack ─────────────────────────────────────────────
# Based on SAP's published FUE classification guide for S/4HANA
# Advanced = full ERP capability; Core = limited transactional; Self-Service = ESS/MSS

DEFAULT_CONVERSION_RATIOS = {
    "advanced": 1.0,
    "core": 0.2,
    "self_service": 0.0333,
    "developer": 1.0,
}

# Auth object + field + value → use type mappings based on SAP's FUE guide
# Priority: higher number wins when multiple rules match
SAP_FUE_BASE_MAPPINGS = [
    # ── DEVELOPER mappings ────────────────────────────────────────────────────
    {"auth_object": "S_DEVELOP", "auth_field": "ACTVT", "auth_value": "*", "use_type": "developer", "priority": 200,
     "source": "SAP FUE Guide - ABAP Development", "desc": "ABAP Workbench development access"},
    {"auth_object": "S_DEVELOP", "auth_field": "DEVCLASS", "auth_value": "*", "use_type": "developer", "priority": 200,
     "source": "SAP FUE Guide - Development packages", "desc": "Development package access"},

    # ── ADVANCED mappings — Finance ───────────────────────────────────────────
    {"auth_object": "F_BKPF_BUK", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - FI Posting", "desc": "FI document posting (create)"},
    {"auth_object": "F_BKPF_BUK", "auth_field": "ACTVT", "auth_value": "02", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - FI Posting", "desc": "FI document posting (change)"},
    {"auth_object": "F_BKPF_BUK", "auth_field": "ACTVT", "auth_value": "06", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - FI Posting", "desc": "FI document posting (delete)"},
    {"auth_object": "F_BKPF_KOA", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - FI Account type", "desc": "FI posting by account type"},
    {"auth_object": "M_BEST_BSA", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - MM PO", "desc": "Purchase order creation"},
    {"auth_object": "M_BEST_BSA", "auth_field": "ACTVT", "auth_value": "02", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - MM PO", "desc": "Purchase order change"},
    {"auth_object": "M_BEST_EKG", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - MM Purchasing group", "desc": "Purchasing by group"},
    {"auth_object": "M_BEST_EKO", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - MM Purchasing org", "desc": "Purchasing by org"},
    {"auth_object": "V_VBAK_VKO", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - SD Sales order", "desc": "Sales order creation"},
    {"auth_object": "V_VBAK_VKO", "auth_field": "ACTVT", "auth_value": "02", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - SD Sales order change", "desc": "Sales order change"},
    {"auth_object": "V_VBAK_AAT", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - SD Order type", "desc": "SD order by type"},
    {"auth_object": "C_AFKO_AWK", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - PP Production order", "desc": "Production order creation"},
    {"auth_object": "C_AFKO_AWK", "auth_field": "ACTVT", "auth_value": "02", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - PP Production order", "desc": "Production order change"},
    {"auth_object": "K_CSKB", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - CO Cost element", "desc": "CO cost element maintenance"},
    {"auth_object": "K_CCA", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - CO Cost center", "desc": "CO cost center posting"},
    {"auth_object": "F_REGU_BUK", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - Regulatory reporting", "desc": "Regulatory reporting create"},

    # ── ADVANCED mappings — Asset Accounting ──────────────────────────────────
    {"auth_object": "F_BKPF_BLA", "auth_field": "BRGRU", "auth_value": "*", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - Asset Accounting", "desc": "Asset accounting authorization groups"},

    # ── ADVANCED mappings — HR/Payroll ────────────────────────────────────────
    {"auth_object": "P_ORGIN", "auth_field": "AUTHC", "auth_value": "W", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - HR Master write", "desc": "HR master data write access"},
    {"auth_object": "P_PERNR", "auth_field": "AUTHC", "auth_value": "W", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - HR Personnel write", "desc": "HR personnel number write"},
    {"auth_object": "P_ABAP", "auth_field": "REPID", "auth_value": "*", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - HR ABAP report", "desc": "HR ABAP report execution"},

    # ── ADVANCED mappings — Treasury ──────────────────────────────────────────
    {"auth_object": "F_T_DEAL", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - Treasury deal", "desc": "Treasury deal creation"},

    # ── ADVANCED mappings — Basis/Admin ───────────────────────────────────────
    {"auth_object": "S_USER_GRP", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - User admin create", "desc": "User administration create"},
    {"auth_object": "S_USER_GRP", "auth_field": "ACTVT", "auth_value": "02", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - User admin change", "desc": "User administration change"},
    {"auth_object": "S_TABU_DIS", "auth_field": "ACTVT", "auth_value": "02", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - Table maintenance", "desc": "Table maintenance change"},
    {"auth_object": "S_TRANSPRT", "auth_field": "ACTVT", "auth_value": "01", "use_type": "advanced", "priority": 150,
     "source": "SAP FUE Guide - Transport create", "desc": "Transport request creation"},

    # ── ADVANCED mappings — T-code based ──────────────────────────────────────
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "FB01", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - FI Posting tcode", "desc": "Post FI document"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "FB50", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - GL Account posting", "desc": "GL account posting"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "F-28", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - Incoming payment", "desc": "Post incoming payment"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "F-43", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - Vendor invoice", "desc": "Post vendor invoice"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "MIRO", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - Invoice verification", "desc": "Logistics invoice verification"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "ME21N", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - Create PO", "desc": "Create purchase order"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "ME22N", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - Change PO", "desc": "Change purchase order"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "VA01", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - Create sales order", "desc": "Create sales order"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "VA02", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - Change sales order", "desc": "Change sales order"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "CO01", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - Create prod order", "desc": "Create production order"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "MM01", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - Create material", "desc": "Create material master"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "XK01", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - Create vendor", "desc": "Create vendor master"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "XD01", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - Create customer", "desc": "Create customer master"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "SU01", "use_type": "advanced", "priority": 140,
     "source": "SAP FUE Guide - User maintenance", "desc": "User maintenance"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "SE38", "use_type": "developer", "priority": 200,
     "source": "SAP FUE Guide - ABAP Editor", "desc": "ABAP Editor"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "SE80", "use_type": "developer", "priority": 200,
     "source": "SAP FUE Guide - Object Navigator", "desc": "Object Navigator"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "SE37", "use_type": "developer", "priority": 200,
     "source": "SAP FUE Guide - Function Builder", "desc": "Function Builder"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "SE11", "use_type": "developer", "priority": 200,
     "source": "SAP FUE Guide - Data Dictionary", "desc": "ABAP Dictionary"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "SE24", "use_type": "developer", "priority": 200,
     "source": "SAP FUE Guide - Class Builder", "desc": "Class Builder"},

    # ── CORE mappings — Display-only finance ──────────────────────────────────
    {"auth_object": "F_BKPF_BUK", "auth_field": "ACTVT", "auth_value": "03", "use_type": "core", "priority": 100,
     "source": "SAP FUE Guide - FI Display", "desc": "FI document display"},
    {"auth_object": "M_BEST_BSA", "auth_field": "ACTVT", "auth_value": "03", "use_type": "core", "priority": 100,
     "source": "SAP FUE Guide - MM PO Display", "desc": "Purchase order display"},
    {"auth_object": "V_VBAK_VKO", "auth_field": "ACTVT", "auth_value": "03", "use_type": "core", "priority": 100,
     "source": "SAP FUE Guide - SD Display", "desc": "Sales order display"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "FB03", "use_type": "core", "priority": 100,
     "source": "SAP FUE Guide - Display FI doc", "desc": "Display FI document"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "ME23N", "use_type": "core", "priority": 100,
     "source": "SAP FUE Guide - Display PO", "desc": "Display purchase order"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "VA03", "use_type": "core", "priority": 100,
     "source": "SAP FUE Guide - Display sales order", "desc": "Display sales order"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "MM03", "use_type": "core", "priority": 100,
     "source": "SAP FUE Guide - Display material", "desc": "Display material master"},

    # ── SELF-SERVICE mappings — ESS/MSS ───────────────────────────────────────
    {"auth_object": "P_ORGIN", "auth_field": "AUTHC", "auth_value": "R", "use_type": "self_service", "priority": 50,
     "source": "SAP FUE Guide - ESS Read", "desc": "ESS read own data"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "CATS", "use_type": "self_service", "priority": 50,
     "source": "SAP FUE Guide - Time entry", "desc": "Time sheet entry"},
    {"auth_object": "S_TCODE", "auth_field": "TCD", "auth_value": "TRIP", "use_type": "self_service", "priority": 50,
     "source": "SAP FUE Guide - Travel request", "desc": "Travel management"},
    {"auth_object": "P_ORGIN", "auth_field": "AUTHC", "auth_value": "E", "use_type": "self_service", "priority": 50,
     "source": "SAP FUE Guide - ESS write own", "desc": "ESS write own data"},
]


class FUEClassificationEngine:
    """
    Production FUE classification engine.
    Reads user role/auth data from platform DB, applies rule pack mappings,
    produces classification with full driver evidence.
    """

    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    def get_active_rule_pack_version(self, contract_id: Optional[str] = None):
        """Get the active rule pack version for this tenant."""
        from db.models.license_intelligence import LIRulePackVersion, LIContract
        if contract_id:
            contract = self.session.query(LIContract).filter(
                LIContract.id == contract_id,
                LIContract.tenant_id == self.tenant_id,
            ).first()
            if contract and contract.rule_pack_version_id:
                return self.session.query(LIRulePackVersion).get(contract.rule_pack_version_id)

        # Fallback: latest active version for this tenant
        return self.session.query(LIRulePackVersion).filter(
            LIRulePackVersion.tenant_id == self.tenant_id,
            LIRulePackVersion.status == "active",
        ).order_by(LIRulePackVersion.effective_from.desc()).first()

    def get_auth_mappings(self, rule_pack_version_id: str):
        """Load all active auth mappings for a rule pack version + tenant overrides."""
        from db.models.license_intelligence import LIAuthMapping, LITenantOverride

        mappings = self.session.query(LIAuthMapping).filter(
            LIAuthMapping.rule_pack_version_id == rule_pack_version_id,
            LIAuthMapping.is_active == True,
        ).order_by(LIAuthMapping.priority.desc()).all()

        # Load tenant overrides
        overrides = self.session.query(LITenantOverride).filter(
            LITenantOverride.tenant_id == self.tenant_id,
            LITenantOverride.is_active == True,
        ).all()

        override_map = {}
        for ov in overrides:
            key = (ov.auth_object, ov.auth_field or "", ov.auth_value or "")
            override_map[key] = ov.override_use_type

        return mappings, override_map

    def classify_user(self, username: str, user_roles: list, user_auths: list,
                      mappings: list, override_map: dict, ratios: dict) -> dict:
        """
        Classify a single user based on their authorizations.
        Returns: {use_type, fue_value, drivers: [...], is_flagged, flag_reason}
        """
        USE_TYPE_RANK = {"developer": 4, "advanced": 3, "core": 2, "self_service": 1, "unclassified": 0}

        drivers = []
        highest_type = "unclassified"
        highest_rank = 0

        # Build auth lookup: {(object, field): [values]}
        auth_lookup = {}
        for auth in user_auths:
            obj = auth.get("auth_object", "").strip()
            field = auth.get("auth_field", "").strip()
            value = auth.get("auth_value", "").strip()
            role = auth.get("role_name", "")
            key = (obj, field)
            if key not in auth_lookup:
                auth_lookup[key] = []
            auth_lookup[key].append({"value": value, "role": role})

        for mapping in mappings:
            obj = mapping.auth_object.strip()
            field = (mapping.auth_field or "").strip()
            match_value = (mapping.auth_value or "").strip()
            mapped_type = mapping.mapped_use_type

            # Check tenant override
            override_key = (obj, field, match_value)
            if override_key in override_map:
                mapped_type = override_map[override_key]

            rank = USE_TYPE_RANK.get(mapped_type, 0)
            lookup_key = (obj, field)

            if lookup_key not in auth_lookup:
                continue

            for auth_entry in auth_lookup[lookup_key]:
                val = auth_entry["value"]
                matched = False

                if match_value == "*":
                    matched = True
                elif match_value == val:
                    matched = True
                elif mapping.auth_value_pattern:
                    try:
                        matched = bool(re.match(mapping.auth_value_pattern, val))
                    except re.error:
                        matched = False

                if matched:
                    drivers.append({
                        "role_name": auth_entry["role"],
                        "auth_object": obj,
                        "auth_field": field,
                        "auth_value": val,
                        "mapped_use_type": mapped_type,
                        "mapping_id": mapping.id,
                        "priority": mapping.priority,
                    })
                    if rank > highest_rank:
                        highest_rank = rank
                        highest_type = mapped_type

        fue_value = ratios.get(highest_type, 0.0)
        is_flagged = highest_type == "unclassified" and len(user_roles) > 0

        # Calculate "without this driver" for each driver
        for drv in drivers:
            drv_rank = USE_TYPE_RANK.get(drv["mapped_use_type"], 0)
            if drv_rank == highest_rank:
                # Find the next highest without this driver
                other_ranks = [USE_TYPE_RANK.get(d["mapped_use_type"], 0)
                               for d in drivers if d is not drv]
                next_highest = max(other_ranks) if other_ranks else 0
                next_type = [t for t, r in USE_TYPE_RANK.items() if r == next_highest]
                drv["use_type_without_this"] = next_type[0] if next_type else "unclassified"
                drv["fue_difference"] = fue_value - ratios.get(drv["use_type_without_this"], 0.0)
            else:
                drv["use_type_without_this"] = highest_type
                drv["fue_difference"] = 0.0

        return {
            "use_type": highest_type,
            "fue_value": fue_value,
            "drivers": drivers,
            "is_flagged": is_flagged,
            "flag_reason": "No authorization mappings matched any rules" if is_flagged else None,
        }

    def run_classification(self, contract_id: Optional[str] = None,
                           usernames: Optional[list] = None) -> dict:
        """
        Run full FUE classification for all users (or a subset).
        Stores results in li_classifications + li_classification_drivers.
        Returns summary stats.
        """
        from db.models.license_intelligence import (
            LIClassification, LIClassificationDriver, LIContract,
        )
        from db.models.user import User, UserRole, UserEntitlement

        rpv = self.get_active_rule_pack_version(contract_id)
        if not rpv:
            return {"error": "No active rule pack version found"}

        mappings, override_map = self.get_auth_mappings(rpv.id)
        ratios = rpv.conversion_ratios or DEFAULT_CONVERSION_RATIOS

        # Get users to classify
        user_query = self.session.query(User).filter(
            User.tenant_id == self.tenant_id,
            User.status != "deleted",
        )
        if usernames:
            user_query = user_query.filter(User.username.in_(usernames))

        users = user_query.all()
        now = datetime.utcnow()

        # Mark old classifications as not current
        self.session.query(LIClassification).filter(
            LIClassification.tenant_id == self.tenant_id,
            LIClassification.is_current == True,
        ).update({"is_current": False})

        stats = {"advanced": 0, "core": 0, "self_service": 0, "developer": 0,
                 "unclassified": 0, "flagged": 0, "total": 0}

        for user in users:
            # Get user's roles
            roles = self.session.query(UserRole).filter(
                UserRole.user_id == user.id,
            ).all()
            role_names = [r.role_id for r in roles if hasattr(r, 'role_id')]

            # Get user's entitlements (auth objects)
            entitlements = self.session.query(UserEntitlement).filter(
                UserEntitlement.user_id == user.id,
            ).all()

            user_auths = []
            for ent in entitlements:
                user_auths.append({
                    "auth_object": getattr(ent, 'auth_object', '') or getattr(ent, 'entitlement_name', '') or '',
                    "auth_field": getattr(ent, 'auth_field', '') or '',
                    "auth_value": getattr(ent, 'auth_value', '') or getattr(ent, 'entitlement_value', '') or '*',
                    "role_name": getattr(ent, 'role_name', '') or getattr(ent, 'source_role', '') or '',
                })

            # If no entitlements, use role-based heuristic classification
            if not user_auths and role_names:
                for rn in role_names:
                    rn_upper = rn.upper() if rn else ""
                    if any(k in rn_upper for k in ["DEVELOP", "SE38", "SE80", "ABAP"]):
                        user_auths.append({"auth_object": "S_DEVELOP", "auth_field": "ACTVT",
                                           "auth_value": "*", "role_name": rn})
                    elif any(k in rn_upper for k in ["ADMIN", "BASIS", "MANAGER", "POWER", "SU01",
                                                      "FI_POST", "MM_PUR", "SD_SALE", "ACCOUNTANT"]):
                        user_auths.append({"auth_object": "S_USER_GRP", "auth_field": "ACTVT",
                                           "auth_value": "02", "role_name": rn})
                    elif any(k in rn_upper for k in ["DISPLAY", "VIEW", "READ", "REPORT", "ANALYST"]):
                        user_auths.append({"auth_object": "F_BKPF_BUK", "auth_field": "ACTVT",
                                           "auth_value": "03", "role_name": rn})
                    elif any(k in rn_upper for k in ["ESS", "SELF_SERVICE", "EMPLOYEE", "TIMESHEET", "TRAVEL"]):
                        user_auths.append({"auth_object": "P_ORGIN", "auth_field": "AUTHC",
                                           "auth_value": "R", "role_name": rn})

            result = self.classify_user(user.username, role_names, user_auths,
                                        mappings, override_map, ratios)

            # Get previous classification
            prev = self.session.query(LIClassification).filter(
                LIClassification.tenant_id == self.tenant_id,
                LIClassification.username == user.username,
                LIClassification.is_current == False,
            ).order_by(LIClassification.calculation_date.desc()).first()

            cls = LIClassification(
                id=_id(),
                tenant_id=self.tenant_id,
                user_id=str(user.id) if hasattr(user, 'id') else user.username,
                username=user.username,
                system_id="S3X",
                use_type=result["use_type"],
                fue_value=result["fue_value"],
                rule_pack_version_id=rpv.id,
                calculation_date=now,
                is_current=True,
                previous_use_type=prev.use_type if prev else None,
                previous_fue_value=prev.fue_value if prev else None,
                is_flagged=result["is_flagged"],
                flag_reason=result["flag_reason"],
                department=getattr(user, 'department', None),
                business_unit=getattr(user, 'business_unit', None),
                cost_center=getattr(user, 'cost_center', None),
                is_review_candidate=False,
            )
            self.session.add(cls)

            # Store drivers
            for drv in result["drivers"][:20]:  # Cap at 20 drivers per user
                driver = LIClassificationDriver(
                    id=_id(),
                    tenant_id=self.tenant_id,
                    classification_id=cls.id,
                    role_name=drv["role_name"],
                    auth_object=drv["auth_object"],
                    auth_field=drv.get("auth_field", ""),
                    auth_value=drv.get("auth_value", ""),
                    mapped_use_type=drv["mapped_use_type"],
                    mapping_id=drv.get("mapping_id"),
                    use_type_without_this=drv.get("use_type_without_this"),
                    fue_difference=drv.get("fue_difference", 0.0),
                )
                self.session.add(driver)

            stats[result["use_type"]] += 1
            if result["is_flagged"]:
                stats["flagged"] += 1
            stats["total"] += 1

            # Commit in batches
            if stats["total"] % 500 == 0:
                self.session.commit()

        self.session.commit()
        return stats

    def calculate_consumption(self, contract_id: str) -> dict:
        """
        LI-002: Calculate FUE consumption from current classifications.
        Stores snapshot and returns the position.
        """
        from db.models.license_intelligence import (
            LIClassification, LIContract, LIConsumptionSnapshot, LIPositionSnapshot,
        )

        contract = self.session.query(LIContract).filter(
            LIContract.id == contract_id,
            LIContract.tenant_id == self.tenant_id,
        ).first()
        if not contract:
            return {"error": "Contract not found"}

        ratios = contract.conversion_ratios or DEFAULT_CONVERSION_RATIOS
        counting_rule = contract.counting_rule or "highest_across_systems"

        # Get current classifications
        classifications = self.session.query(LIClassification).filter(
            LIClassification.tenant_id == self.tenant_id,
            LIClassification.is_current == True,
        ).all()

        # Deduplicate by username (highest use type wins across systems)
        USE_TYPE_RANK = {"developer": 4, "advanced": 3, "core": 2, "self_service": 1, "unclassified": 0}
        user_map = {}
        for cls in classifications:
            if cls.username not in user_map:
                user_map[cls.username] = cls
            elif USE_TYPE_RANK.get(cls.use_type, 0) > USE_TYPE_RANK.get(user_map[cls.username].use_type, 0):
                user_map[cls.username] = cls

        counts = {"advanced": 0, "core": 0, "self_service": 0, "developer": 0, "unclassified": 0}
        by_dept = {}
        by_system = {}

        for username, cls in user_map.items():
            ut = cls.use_type
            counts[ut] = counts.get(ut, 0) + 1

            dept = cls.department or "Unknown"
            if dept not in by_dept:
                by_dept[dept] = {"advanced": 0, "core": 0, "self_service": 0, "developer": 0, "unclassified": 0}
            by_dept[dept][ut] += 1

            sys_id = cls.system_id or "Unknown"
            if sys_id not in by_system:
                by_system[sys_id] = {"advanced": 0, "core": 0, "self_service": 0, "developer": 0, "unclassified": 0}
            by_system[sys_id][ut] += 1

        consumed = (counts["advanced"] * ratios.get("advanced", 1.0) +
                    counts["core"] * ratios.get("core", 0.2) +
                    counts["self_service"] * ratios.get("self_service", 0.0333) +
                    counts["developer"] * ratios.get("developer", 1.0))

        contracted = contract.contracted_fue
        available = contracted - consumed
        utilisation = (consumed / contracted * 100) if contracted > 0 else 0

        total_users = sum(counts.values())
        now = datetime.utcnow()

        # Mark old snapshots as not latest
        self.session.query(LIConsumptionSnapshot).filter(
            LIConsumptionSnapshot.contract_id == contract_id,
            LIConsumptionSnapshot.tenant_id == self.tenant_id,
            LIConsumptionSnapshot.is_latest == True,
        ).update({"is_latest": False})

        snapshot = LIConsumptionSnapshot(
            id=_id(),
            tenant_id=self.tenant_id,
            contract_id=contract_id,
            snapshot_date=now,
            rule_pack_version_id=None,
            total_users=total_users,
            advanced_count=counts["advanced"],
            core_count=counts["core"],
            self_service_count=counts["self_service"],
            developer_count=counts["developer"],
            unclassified_count=counts["unclassified"],
            consumed_fue=round(consumed, 2),
            contracted_fue=contracted,
            available_fue=round(available, 2),
            utilisation_pct=round(utilisation, 2),
            over_consumed=consumed > contracted,
            by_system=by_system,
            by_department=by_dept,
            is_latest=True,
        )
        self.session.add(snapshot)

        # Also store position snapshot for trend
        pos = LIPositionSnapshot(
            id=_id(),
            tenant_id=self.tenant_id,
            snapshot_date=date.today(),
            contract_id=contract_id,
            contracted_fue=contracted,
            consumed_fue=round(consumed, 2),
            available_fue=round(available, 2),
            utilisation_pct=round(utilisation, 2),
            advanced_count=counts["advanced"],
            core_count=counts["core"],
            self_service_count=counts["self_service"],
            developer_count=counts["developer"],
            unclassified_count=counts["unclassified"],
            total_users=total_users,
        )
        self.session.add(pos)
        self.session.commit()

        return {
            "contract_id": contract_id,
            "contract_reference": contract.contract_reference,
            "contracted_fue": contracted,
            "consumed_fue": round(consumed, 2),
            "available_fue": round(available, 2),
            "utilisation_pct": round(utilisation, 2),
            "over_consumed": consumed > contracted,
            "counts": counts,
            "total_users": total_users,
            "by_department": by_dept,
            "by_system": by_system,
            "ratios": ratios,
            "snapshot_id": snapshot.id,
            "calculation_date": now.isoformat(),
        }


def seed_base_rule_pack(session: Session, tenant_id: str):
    """Seed the default S/4HANA FUE rule pack with all base mappings."""
    from db.models.license_intelligence import LIRulePack, LIRulePackVersion, LIAuthMapping

    # Check if already seeded
    existing = session.query(LIRulePack).filter(
        LIRulePack.tenant_id == tenant_id,
        LIRulePack.is_base_pack == True,
    ).first()
    if existing:
        return existing

    pack_id = _id()
    pack = LIRulePack(
        id=pack_id,
        tenant_id=tenant_id,
        name="SAP S/4HANA FUE Base Rule Pack",
        description="Default FUE classification rules based on SAP's published licensing guide. "
                    "Maps authorization objects and T-codes to Advanced, Core, Self-Service, and Developer use types.",
        target_platform="S4HANA",
        is_base_pack=True,
        status="active",
        created_by="system",
        approved_by="system",
        approved_at=datetime.utcnow(),
    )
    session.add(pack)

    version_id = _id()
    version = LIRulePackVersion(
        id=version_id,
        tenant_id=tenant_id,
        rule_pack_id=pack_id,
        version="1.0.0",
        effective_from=date(2026, 1, 1),
        conversion_ratios=DEFAULT_CONVERSION_RATIOS,
        notes="Initial base rule pack with SAP-published FUE mappings",
        status="active",
        drafted_by="system",
        reviewed_by="system",
        approved_by="system",
        approved_at=datetime.utcnow(),
        mapping_count=len(SAP_FUE_BASE_MAPPINGS),
    )
    session.add(version)

    for m in SAP_FUE_BASE_MAPPINGS:
        mapping = LIAuthMapping(
            id=_id(),
            tenant_id=tenant_id,
            rule_pack_version_id=version_id,
            auth_object=m["auth_object"],
            auth_field=m.get("auth_field"),
            auth_value=m.get("auth_value"),
            mapped_use_type=m["use_type"],
            source_reference=m.get("source", ""),
            description=m.get("desc", ""),
            is_active=True,
            priority=m.get("priority", 100),
        )
        session.add(mapping)

    session.commit()
    return pack
