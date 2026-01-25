# Authorization Content Extractor
# Extracts from SAP AGR_1251 table for GOVERNEX+ Firefighter

"""
Authorization Content Extractor for SAP AGR_1251 table.

Source Table: AGR_1251
Fields:
- AGR_NAME: Role name
- OBJECT: Authorization object (e.g., S_TCODE, S_TABU_DIS)
- FIELD: Authorization field
- LOW: Field value (lower bound)
- HIGH: Upper value (for ranges)

Used by GOVERNEX+ for:
- Sensitive access detection during firefighter sessions
- Audit justification (what privileges were granted)
- SoD (Segregation of Duties) analysis
- Risk scoring of firefighter activities
"""

from typing import List, Optional, Dict, Any, Set
from datetime import datetime
import logging

from .base import BaseExtractor, ExtractionResult
from .connection import SAPRFCConnectionManager
from .config import SAPExtractorConfig, TRACKED_AUTH_OBJECTS, RESTRICTED_TCODES

logger = logging.getLogger(__name__)


class AuthorizationExtractor(BaseExtractor):
    """
    Extractor for SAP authorization content (AGR_1251).

    Provides deep analysis of what privileges a role grants.
    """

    # AGR_1251 fields
    AGR_1251_FIELDS = [
        "AGR_NAME",    # Role name
        "OBJECT",      # Authorization object
        "FIELD",       # Authorization field
        "LOW",         # Field value (or range start)
        "HIGH",        # Range end value
    ]

    def __init__(
        self,
        connection_manager: Optional[SAPRFCConnectionManager] = None,
        config: Optional[SAPExtractorConfig] = None
    ):
        super().__init__(connection_manager, config)

    def extract(
        self,
        role_name: Optional[str] = None,
        auth_object: Optional[str] = None,
        offset: int = 0,
        limit: int = 10000
    ) -> ExtractionResult:
        """
        Extract authorization content from AGR_1251.

        Args:
            role_name: Filter by specific role
            auth_object: Filter by authorization object
            offset: Starting offset for pagination
            limit: Maximum records to return

        Returns:
            ExtractionResult with authorization content
        """
        start_time = datetime.now()
        errors = []

        try:
            # Build WHERE clauses
            where_clauses = []

            if role_name:
                where_clauses.append(f"AGR_NAME = '{role_name}'")

            if auth_object:
                where_clauses.append(f"OBJECT = '{auth_object}'")

            # Read from AGR_1251
            raw_data = self._read_table(
                table_name="AGR_1251",
                fields=self.AGR_1251_FIELDS,
                where_clauses=where_clauses if where_clauses else None,
                max_rows=limit
            )

            # Transform data
            authorizations = []
            for row in raw_data:
                auth = self._transform_authorization(row)
                authorizations.append(auth)

            return self._create_result(authorizations, "AGR_1251", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting authorization content: {e}")
            errors.append(str(e))
            return self._create_result([], "AGR_1251", start_time, errors)

    def get_role_authorizations(self, role_name: str) -> Dict[str, Any]:
        """
        Get complete authorization profile for a role.

        Uses PRGN_GET_AUTH_VALUES_FOR_ROLE RFC function.

        Args:
            role_name: Role to analyze

        Returns:
            Dictionary with structured authorization data
        """
        try:
            result = self._call_rfc(
                "PRGN_GET_AUTH_VALUES_FOR_ROLE",
                ROLE_NAME=role_name
            )

            auth_values = result.get("AUTH_VALUES", [])

            # Group by authorization object
            by_object: Dict[str, List] = {}
            for auth in auth_values:
                obj = auth.get("OBJECT", "")
                if obj not in by_object:
                    by_object[obj] = []
                by_object[obj].append({
                    "field": auth.get("FIELD", ""),
                    "value": auth.get("LOW", ""),
                    "high": auth.get("HIGH", ""),
                })

            # Analyze for sensitive authorizations
            sensitive_auth = self._analyze_sensitive_authorizations(by_object)

            return {
                "role_name": role_name,
                "authorization_count": len(auth_values),
                "object_count": len(by_object),
                "authorizations_by_object": by_object,
                "sensitive_authorizations": sensitive_auth,
                "risk_indicators": self._calculate_risk_indicators(by_object),
            }

        except Exception as e:
            logger.error(f"Error getting role authorizations for {role_name}: {e}")
            raise

    def get_sensitive_authorizations(
        self,
        role_names: List[str]
    ) -> ExtractionResult:
        """
        Extract only sensitive/restricted authorizations for given roles.

        Args:
            role_names: List of roles to analyze

        Returns:
            ExtractionResult with sensitive authorizations only
        """
        start_time = datetime.now()
        errors = []

        try:
            sensitive_auths = []

            for role_name in role_names:
                # Get authorizations for this role
                result = self.extract(role_name=role_name)

                for auth in result.data:
                    # Check if this is a sensitive authorization
                    if self._is_sensitive_authorization(auth):
                        auth["role_name"] = role_name
                        auth["sensitivity_reason"] = self._get_sensitivity_reason(auth)
                        sensitive_auths.append(auth)

            return self._create_result(sensitive_auths, "AGR_1251", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting sensitive authorizations: {e}")
            errors.append(str(e))
            return self._create_result([], "AGR_1251", start_time, errors)

    def get_tcode_authorizations(
        self,
        role_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get all transaction codes authorized for a role.

        Args:
            role_name: Role to analyze

        Returns:
            List of authorized transaction codes
        """
        try:
            result = self.extract(role_name=role_name, auth_object="S_TCODE")

            tcodes = []
            for auth in result.data:
                if auth["field"] == "TCD":
                    tcode_entry = {
                        "tcode": auth["value"],
                        "is_range": bool(auth.get("high_value")),
                        "is_restricted": auth["value"] in RESTRICTED_TCODES,
                    }

                    if auth.get("high_value"):
                        tcode_entry["range_end"] = auth["high_value"]

                    tcodes.append(tcode_entry)

            return tcodes

        except Exception as e:
            logger.error(f"Error getting tcode authorizations for {role_name}: {e}")
            raise

    def analyze_firefighter_role(
        self,
        role_name: str
    ) -> Dict[str, Any]:
        """
        Comprehensive analysis of a firefighter role.

        Provides detailed breakdown suitable for audit.

        Args:
            role_name: Firefighter role to analyze

        Returns:
            Comprehensive analysis dictionary
        """
        try:
            # Get all authorizations
            auth_profile = self.get_role_authorizations(role_name)

            # Get transaction codes
            tcodes = self.get_tcode_authorizations(role_name)

            # Identify restricted tcodes
            restricted_tcodes = [t for t in tcodes if t["is_restricted"]]

            # Calculate risk score
            risk_score = self._calculate_role_risk_score(auth_profile, tcodes)

            return {
                "role_name": role_name,
                "analysis_timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_authorizations": auth_profile["authorization_count"],
                    "authorization_objects": auth_profile["object_count"],
                    "transaction_codes": len(tcodes),
                    "restricted_tcodes": len(restricted_tcodes),
                    "risk_score": risk_score,
                },
                "transaction_codes": {
                    "all": tcodes,
                    "restricted": restricted_tcodes,
                    "wildcard_count": len([t for t in tcodes if t["tcode"] == "*"]),
                },
                "sensitive_authorizations": auth_profile["sensitive_authorizations"],
                "risk_indicators": auth_profile["risk_indicators"],
                "audit_flags": self._generate_audit_flags(auth_profile, tcodes),
            }

        except Exception as e:
            logger.error(f"Error analyzing firefighter role {role_name}: {e}")
            raise

    def _transform_authorization(self, raw: Dict[str, str]) -> Dict[str, Any]:
        """Transform raw AGR_1251 record to structured format."""
        return {
            "role_name": raw.get("AGR_NAME", ""),
            "object": raw.get("OBJECT", ""),
            "field": raw.get("FIELD", ""),
            "value": raw.get("LOW", ""),
            "high_value": raw.get("HIGH", "") or None,
            "is_wildcard": raw.get("LOW", "") == "*",
            "is_range": bool(raw.get("HIGH", "")),
        }

    def _is_sensitive_authorization(self, auth: Dict) -> bool:
        """Check if an authorization is considered sensitive."""
        obj = auth.get("object", "")
        value = auth.get("value", "")

        # Check tracked auth objects
        if obj in TRACKED_AUTH_OBJECTS:
            return True

        # Check for wildcard in sensitive objects
        if auth.get("is_wildcard") and obj in ["S_TCODE", "S_TABU_DIS", "S_RFC"]:
            return True

        # Check for restricted tcodes
        if obj == "S_TCODE" and value in RESTRICTED_TCODES:
            return True

        return False

    def _get_sensitivity_reason(self, auth: Dict) -> str:
        """Get reason why an authorization is flagged as sensitive."""
        obj = auth.get("object", "")
        value = auth.get("value", "")

        reasons = []

        if obj in TRACKED_AUTH_OBJECTS:
            reasons.append(f"Tracked authorization object: {obj}")

        if auth.get("is_wildcard"):
            reasons.append("Wildcard (*) authorization")

        if obj == "S_TCODE" and value in RESTRICTED_TCODES:
            reasons.append(f"Restricted transaction code: {value}")

        if obj == "S_TABU_DIS":
            reasons.append("Direct table access authorization")

        if obj == "S_DEVELOP":
            reasons.append("Development authorization")

        return "; ".join(reasons) if reasons else "Sensitive authorization object"

    def _analyze_sensitive_authorizations(
        self,
        by_object: Dict[str, List]
    ) -> List[Dict]:
        """Analyze authorizations for sensitive entries."""
        sensitive = []

        for obj, auths in by_object.items():
            if obj in TRACKED_AUTH_OBJECTS:
                for auth in auths:
                    sensitive.append({
                        "object": obj,
                        "field": auth.get("field", ""),
                        "value": auth.get("value", ""),
                        "reason": f"Tracked object: {obj}",
                    })

            # Check for wildcards
            for auth in auths:
                if auth.get("value") == "*":
                    sensitive.append({
                        "object": obj,
                        "field": auth.get("field", ""),
                        "value": "*",
                        "reason": "Wildcard authorization",
                    })

        return sensitive

    def _calculate_risk_indicators(self, by_object: Dict[str, List]) -> Dict[str, Any]:
        """Calculate risk indicators from authorization profile."""
        indicators = {
            "has_sap_all_equivalent": False,
            "has_development_access": False,
            "has_user_admin": False,
            "has_table_access": False,
            "has_transport_access": False,
            "wildcard_count": 0,
        }

        # Count wildcards
        for auths in by_object.values():
            indicators["wildcard_count"] += len([a for a in auths if a.get("value") == "*"])

        # Check for SAP_ALL equivalent (S_TCODE with *)
        if "S_TCODE" in by_object:
            for auth in by_object["S_TCODE"]:
                if auth.get("value") == "*":
                    indicators["has_sap_all_equivalent"] = True

        # Check for development access
        if "S_DEVELOP" in by_object:
            indicators["has_development_access"] = True

        # Check for user admin
        if "S_USER_GRP" in by_object:
            indicators["has_user_admin"] = True

        # Check for table access
        if "S_TABU_DIS" in by_object:
            indicators["has_table_access"] = True

        # Check for transport access
        if "S_TRANSPRT" in by_object or "S_CTS_ADMI" in by_object:
            indicators["has_transport_access"] = True

        return indicators

    def _calculate_role_risk_score(
        self,
        auth_profile: Dict,
        tcodes: List[Dict]
    ) -> int:
        """Calculate risk score (0-100) for a role."""
        score = 0
        indicators = auth_profile.get("risk_indicators", {})

        # High risk indicators
        if indicators.get("has_sap_all_equivalent"):
            score += 40

        if indicators.get("has_development_access"):
            score += 20

        if indicators.get("has_user_admin"):
            score += 15

        if indicators.get("has_table_access"):
            score += 10

        if indicators.get("has_transport_access"):
            score += 10

        # Wildcard penalty
        wildcard_count = indicators.get("wildcard_count", 0)
        score += min(wildcard_count * 2, 20)

        # Restricted tcode penalty
        restricted_count = len([t for t in tcodes if t.get("is_restricted")])
        score += min(restricted_count * 3, 15)

        return min(score, 100)

    def _generate_audit_flags(
        self,
        auth_profile: Dict,
        tcodes: List[Dict]
    ) -> List[str]:
        """Generate audit flags for the role."""
        flags = []
        indicators = auth_profile.get("risk_indicators", {})

        if indicators.get("has_sap_all_equivalent"):
            flags.append("CRITICAL: Has SAP_ALL equivalent access (S_TCODE = *)")

        if indicators.get("has_development_access"):
            flags.append("HIGH: Has development authorization (S_DEVELOP)")

        if indicators.get("has_user_admin"):
            flags.append("HIGH: Has user administration access (S_USER_GRP)")

        if indicators.get("has_table_access"):
            flags.append("MEDIUM: Has direct table access (S_TABU_DIS)")

        restricted_tcodes = [t["tcode"] for t in tcodes if t.get("is_restricted")]
        if restricted_tcodes:
            flags.append(f"MEDIUM: Has restricted transactions: {', '.join(restricted_tcodes[:5])}")

        if indicators.get("wildcard_count", 0) > 5:
            flags.append(f"MEDIUM: High number of wildcard authorizations ({indicators['wildcard_count']})")

        return flags
