# Role Assignment Extractor
# Extracts from SAP AGR_USERS, AGR_DEFINE tables for GOVERNEX+ Firefighter

"""
Role Assignment Extractor for SAP role tables.

Source Tables:
- AGR_USERS: User-role assignments with validity dates
- AGR_DEFINE: Role definitions and metadata

Used by GOVERNEX+ for:
- Privileged role mapping to firefighter IDs
- Session start/end time-bound access
- Auto-revoke at assignment end date
- Role description for audit justification
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .base import BaseExtractor, ExtractionResult
from .connection import SAPRFCConnectionManager
from .config import SAPExtractorConfig

logger = logging.getLogger(__name__)


class RoleExtractor(BaseExtractor):
    """
    Extractor for SAP role assignment data.

    Combines data from AGR_USERS and AGR_DEFINE to provide
    complete role assignment information.
    """

    # AGR_USERS fields
    AGR_USERS_FIELDS = [
        "UNAME",       # User name
        "AGR_NAME",    # Role name
        "FROM_DAT",    # Assignment start date
        "TO_DAT",      # Assignment end date
        "ORG_FLAG",    # Organizational assignment flag
    ]

    # AGR_DEFINE fields
    AGR_DEFINE_FIELDS = [
        "AGR_NAME",    # Role name
        "PARENT_AGR",  # Parent role (for composite roles)
        "CREATE_USR",  # Created by user
        "CREATE_DAT",  # Creation date
    ]

    def __init__(
        self,
        connection_manager: Optional[SAPRFCConnectionManager] = None,
        config: Optional[SAPExtractorConfig] = None
    ):
        super().__init__(connection_manager, config)
        self._role_cache: Dict[str, Dict] = {}

    def extract(
        self,
        username: Optional[str] = None,
        role_pattern: str = "*",
        include_expired: bool = False,
        offset: int = 0,
        limit: int = 1000
    ) -> ExtractionResult:
        """
        Extract role assignments.

        Args:
            username: Filter by specific user (None for all)
            role_pattern: Pattern to filter roles (supports SAP wildcards)
            include_expired: Include expired assignments
            offset: Starting offset for pagination
            limit: Maximum records to return

        Returns:
            ExtractionResult with role assignment data
        """
        start_time = datetime.now()
        errors = []

        try:
            # Build WHERE clauses
            where_clauses = []

            if username:
                where_clauses.append(f"UNAME = '{username}'")

            if role_pattern != "*":
                where_clauses.append(f"AGR_NAME LIKE '{role_pattern}'")

            if not include_expired:
                today = datetime.now().strftime("%Y%m%d")
                where_clauses.append(f"(TO_DAT >= '{today}' OR TO_DAT = '00000000')")

            # Read from AGR_USERS
            raw_data = self._read_table(
                table_name="AGR_USERS",
                fields=self.AGR_USERS_FIELDS,
                where_clauses=where_clauses if where_clauses else None,
                max_rows=limit
            )

            # Transform and enrich with role definitions
            assignments = []
            for row in raw_data:
                assignment = self._transform_assignment(row)

                # Enrich with role definition
                role_def = self._get_role_definition(assignment["role_name"])
                if role_def:
                    assignment["role_definition"] = role_def

                assignments.append(assignment)

            return self._create_result(assignments, "AGR_USERS", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting role assignments: {e}")
            errors.append(str(e))
            return self._create_result([], "AGR_USERS", start_time, errors)

    def get_users_for_role(self, role_name: str) -> List[Dict[str, Any]]:
        """
        Get all users assigned to a specific role.

        Uses PRGN_GET_USERS_FOR_ROLE RFC function.

        Args:
            role_name: Role name to query

        Returns:
            List of user dictionaries
        """
        try:
            result = self._call_rfc(
                "PRGN_GET_USERS_FOR_ROLE",
                ROLE_NAME=role_name
            )

            users = []
            for user_entry in result.get("USERLIST", []):
                users.append({
                    "username": user_entry.get("BNAME", ""),
                    "role_name": role_name,
                })

            return users

        except Exception as e:
            logger.error(f"Error getting users for role {role_name}: {e}")
            raise

    def get_roles_for_user(self, username: str) -> List[Dict[str, Any]]:
        """
        Get all roles assigned to a specific user.

        Uses BAPI_USER_GET_DETAIL RFC function.

        Args:
            username: User ID to query

        Returns:
            List of role assignment dictionaries
        """
        try:
            result = self._call_rfc(
                "BAPI_USER_GET_DETAIL",
                USERNAME=username
            )

            roles = []
            for role in result.get("ACTIVITYGROUPS", []):
                role_data = {
                    "username": username,
                    "role_name": role.get("AGR_NAME", ""),
                    "from_date": self._format_date(role.get("FROM_DAT", "")),
                    "to_date": self._format_date(role.get("TO_DAT", "")),
                    "org_flag": role.get("ORG_FLAG", ""),
                }

                # Enrich with role definition
                role_def = self._get_role_definition(role_data["role_name"])
                if role_def:
                    role_data["role_definition"] = role_def

                roles.append(role_data)

            return roles

        except Exception as e:
            logger.error(f"Error getting roles for user {username}: {e}")
            raise

    def get_privileged_role_assignments(
        self,
        privileged_roles: Optional[List[str]] = None
    ) -> ExtractionResult:
        """
        Extract assignments of privileged/sensitive roles.

        Args:
            privileged_roles: List of role names to check.
                             Defaults to common privileged roles.

        Returns:
            ExtractionResult with privileged role assignments
        """
        start_time = datetime.now()
        errors = []

        # Default privileged roles if not specified
        if privileged_roles is None:
            privileged_roles = [
                "SAP_ALL",
                "SAP_NEW",
                "S_A.ADMIN",
                "S_A.SYSTEM",
                "S_A.DEVELOP",
            ]

        try:
            all_assignments = []

            for role_name in privileged_roles:
                users = self.get_users_for_role(role_name)
                for user in users:
                    user["is_privileged"] = True
                    user["privilege_level"] = self._get_privilege_level(role_name)
                    all_assignments.append(user)

            return self._create_result(all_assignments, "AGR_USERS", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting privileged role assignments: {e}")
            errors.append(str(e))
            return self._create_result([], "AGR_USERS", start_time, errors)

    def get_role_definitions(
        self,
        role_pattern: str = "*",
        limit: int = 1000
    ) -> ExtractionResult:
        """
        Extract role definitions from AGR_DEFINE.

        Args:
            role_pattern: Pattern to filter roles
            limit: Maximum records to return

        Returns:
            ExtractionResult with role definitions
        """
        start_time = datetime.now()
        errors = []

        try:
            where_clauses = []
            if role_pattern != "*":
                where_clauses.append(f"AGR_NAME LIKE '{role_pattern}'")

            raw_data = self._read_table(
                table_name="AGR_DEFINE",
                fields=self.AGR_DEFINE_FIELDS,
                where_clauses=where_clauses if where_clauses else None,
                max_rows=limit
            )

            roles = []
            for row in raw_data:
                role = self._transform_role_definition(row)
                roles.append(role)

            return self._create_result(roles, "AGR_DEFINE", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting role definitions: {e}")
            errors.append(str(e))
            return self._create_result([], "AGR_DEFINE", start_time, errors)

    def _get_role_definition(self, role_name: str) -> Optional[Dict[str, Any]]:
        """
        Get role definition, using cache to avoid repeated lookups.

        Args:
            role_name: Role name to look up

        Returns:
            Role definition dictionary or None
        """
        if role_name in self._role_cache:
            return self._role_cache[role_name]

        try:
            raw_data = self._read_table(
                table_name="AGR_DEFINE",
                fields=self.AGR_DEFINE_FIELDS,
                where_clauses=[f"AGR_NAME = '{role_name}'"],
                max_rows=1
            )

            if raw_data:
                role_def = self._transform_role_definition(raw_data[0])
                self._role_cache[role_name] = role_def
                return role_def

        except Exception as e:
            logger.warning(f"Could not get role definition for {role_name}: {e}")

        return None

    def _transform_assignment(self, raw: Dict[str, str]) -> Dict[str, Any]:
        """Transform raw AGR_USERS record to structured format."""
        from_date = self._format_date(raw.get("FROM_DAT", ""))
        to_date = self._format_date(raw.get("TO_DAT", ""))

        # Calculate assignment status
        today = datetime.now().date()
        is_active = True

        if to_date:
            to_date_obj = datetime.fromisoformat(to_date).date()
            is_active = to_date_obj >= today

        return {
            "username": raw.get("UNAME", ""),
            "role_name": raw.get("AGR_NAME", ""),
            "from_date": from_date,
            "to_date": to_date,
            "org_flag": raw.get("ORG_FLAG", ""),
            "is_active": is_active,
            "is_time_limited": bool(to_date and to_date != "9999-12-31"),
        }

    def _transform_role_definition(self, raw: Dict[str, str]) -> Dict[str, Any]:
        """Transform raw AGR_DEFINE record to structured format."""
        role_name = raw.get("AGR_NAME", "")

        return {
            "role_name": role_name,
            "parent_role": raw.get("PARENT_AGR", ""),
            "created_by": raw.get("CREATE_USR", ""),
            "created_date": self._format_date(raw.get("CREATE_DAT", "")),
            "role_type": self._determine_role_type(role_name, raw.get("PARENT_AGR", "")),
        }

    def _determine_role_type(self, role_name: str, parent_role: str) -> str:
        """Determine role type based on naming and structure."""
        if parent_role:
            return "composite"
        elif role_name.startswith("SAP_"):
            return "standard"
        elif role_name.startswith("Z"):
            return "custom"
        else:
            return "single"

    def _get_privilege_level(self, role_name: str) -> str:
        """Determine privilege level of a role."""
        high_privilege = ["SAP_ALL", "SAP_NEW", "S_A.ADMIN"]
        medium_privilege = ["S_A.SYSTEM", "S_A.DEVELOP"]

        if role_name in high_privilege:
            return "high"
        elif role_name in medium_privilege:
            return "medium"
        else:
            return "standard"
