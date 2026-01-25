# User Master Data Extractor
# Extracts from SAP USR02 table for GOVERNEX+ Firefighter

"""
User Master Data Extractor for SAP USR02 table.

Provides extraction of firefighter user data including:
- User ID (BNAME)
- User type (USTYP)
- Validity dates (GLTGV, GLTGB)
- Lock status (UFLAG)
- Last logon (LAST_LOGON)
- Password change date (TRDAT)

Used by GOVERNEX+ for:
- Session binding validation
- User eligibility checks
- Time-bound access control
- Auto-expiry management
- Inactivity monitoring
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from .base import BaseExtractor, ExtractionResult
from .connection import SAPRFCConnectionManager
from .config import SAPExtractorConfig

logger = logging.getLogger(__name__)


class UserMasterExtractor(BaseExtractor):
    """
    Extractor for SAP USR02 (User Master) data.

    Supports both RFC (BAPI_USER_GET_DETAIL) and direct table read
    for different use cases.
    """

    # USR02 fields relevant for firefighter management
    USR02_FIELDS = [
        "BNAME",       # User ID
        "USTYP",       # User type (A=Dialog, B=System, etc.)
        "GLTGV",       # Valid from date
        "GLTGB",       # Valid to date
        "UFLAG",       # Lock status
        "TRDAT",       # Password change date
    ]

    def __init__(
        self,
        connection_manager: Optional[SAPRFCConnectionManager] = None,
        config: Optional[SAPExtractorConfig] = None
    ):
        super().__init__(connection_manager, config)

    def extract(
        self,
        username_pattern: str = "FF_*",
        include_locked: bool = True,
        include_expired: bool = False,
        offset: int = 0,
        limit: int = 1000
    ) -> ExtractionResult:
        """
        Extract user master data for firefighter users.

        Args:
            username_pattern: Pattern to filter users (supports SAP wildcards)
            include_locked: Include locked users in results
            include_expired: Include expired users in results
            offset: Starting offset for pagination
            limit: Maximum records to return

        Returns:
            ExtractionResult with user master data
        """
        start_time = datetime.now()
        errors = []

        try:
            # Build WHERE clauses
            where_clauses = [f"BNAME LIKE '{username_pattern}'"]

            if not include_expired:
                today = datetime.now().strftime("%Y%m%d")
                where_clauses.append(f"GLTGB >= '{today}' OR GLTGB = '00000000'")

            # Read from USR02
            raw_data = self._read_table(
                table_name="USR02",
                fields=self.USR02_FIELDS,
                where_clauses=where_clauses,
                max_rows=limit
            )

            # Transform and enrich data
            users = []
            for row in raw_data:
                user = self._transform_user_record(row)

                # Filter locked users if requested
                if not include_locked and user["lock_status"]["locked"]:
                    continue

                users.append(user)

            return self._create_result(users, "USR02", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting user master data: {e}")
            errors.append(str(e))
            return self._create_result([], "USR02", start_time, errors)

    def get_user_detail(self, username: str) -> Dict[str, Any]:
        """
        Get detailed user information using BAPI.

        More detailed than table read, includes roles and profiles.

        Args:
            username: SAP user ID

        Returns:
            User detail dictionary
        """
        try:
            result = self._call_rfc(
                "BAPI_USER_GET_DETAIL",
                USERNAME=username
            )

            # Check for errors
            for msg in result.get("RETURN", []):
                if msg.get("TYPE") == "E":
                    raise ValueError(f"SAP Error: {msg.get('MESSAGE')}")

            # Extract and transform
            address = result.get("ADDRESS", {})
            logon_data = result.get("LOGONDATA", {})

            return {
                "username": username,
                "user_type": logon_data.get("USTYP", ""),
                "full_name": f"{address.get('FIRSTNAME', '')} {address.get('LASTNAME', '')}".strip(),
                "email": address.get("E_MAIL", ""),
                "department": address.get("DEPARTMENT", ""),
                "valid_from": self._format_date(logon_data.get("GLTGV", "")),
                "valid_to": self._format_date(logon_data.get("GLTGB", "")),
                "lock_status": self._parse_lock_status(logon_data.get("UFLAG", "0")),
                "password_change_date": self._format_date(logon_data.get("TRDAT", "")),
                "roles": [
                    {
                        "role_name": role.get("AGR_NAME"),
                        "from_date": self._format_date(role.get("FROM_DAT", "")),
                        "to_date": self._format_date(role.get("TO_DAT", "")),
                    }
                    for role in result.get("ACTIVITYGROUPS", [])
                ],
                "profiles": [
                    {
                        "profile_name": profile.get("BAESSION"),
                        "profile_text": profile.get("BAPIPTEXT"),
                    }
                    for profile in result.get("PROFILES", [])
                ],
            }

        except Exception as e:
            logger.error(f"Error getting user detail for {username}: {e}")
            raise

    def get_firefighter_status(self, firefighter_id: str) -> Dict[str, Any]:
        """
        Get comprehensive status for a firefighter account.

        Combines user master data with derived metrics.

        Args:
            firefighter_id: Firefighter user ID

        Returns:
            Status dictionary with availability and compliance info
        """
        user = self.get_user_detail(firefighter_id)

        # Calculate derived metrics
        today = datetime.now()

        # Check validity
        is_valid = True
        if user["valid_to"]:
            valid_to_date = datetime.fromisoformat(user["valid_to"])
            is_valid = valid_to_date >= today

        # Calculate inactive days
        inactive_days = None
        if user.get("last_logon"):
            last_logon_date = datetime.fromisoformat(user["last_logon"])
            inactive_days = (today - last_logon_date).days

        # Determine overall availability
        is_locked = user["lock_status"]["locked"]
        available = not is_locked and is_valid

        return {
            "firefighter_id": firefighter_id,
            "available": available,
            "user_type": user["user_type"],
            "is_locked": is_locked,
            "lock_details": user["lock_status"],
            "is_valid": is_valid,
            "valid_from": user["valid_from"],
            "valid_to": user["valid_to"],
            "password_change_date": user["password_change_date"],
            "inactive_days": inactive_days,
            "role_count": len(user.get("roles", [])),
            "roles": user.get("roles", []),
            "compliance": {
                "has_valid_dates": bool(user["valid_from"] and user["valid_to"]),
                "password_compliant": self._check_password_compliance(user),
                "is_dormant": inactive_days and inactive_days > 90,
            }
        }

    def get_inactive_users(
        self,
        days_threshold: int = 90,
        user_pattern: str = "FF_*"
    ) -> ExtractionResult:
        """
        Extract users who haven't logged in recently.

        Args:
            days_threshold: Days of inactivity to flag
            user_pattern: User ID pattern to filter

        Returns:
            ExtractionResult with inactive user records
        """
        start_time = datetime.now()
        errors = []

        try:
            # Calculate cutoff date
            cutoff_date = (datetime.now() - timedelta(days=days_threshold)).strftime("%Y%m%d")

            # Query for inactive users
            # Note: LAST_LOGON may not be directly in USR02 in all SAP versions
            # This may need to be joined with USR02 system-specific logon tracking
            where_clauses = [
                f"BNAME LIKE '{user_pattern}'",
                "USTYP = 'A'",  # Dialog users only
            ]

            raw_data = self._read_table(
                table_name="USR02",
                fields=self.USR02_FIELDS,
                where_clauses=where_clauses,
                max_rows=10000
            )

            # Filter for inactive
            inactive_users = []
            for row in raw_data:
                user = self._transform_user_record(row)

                # Check inactivity (would need LAST_LOGON from proper source)
                # For now, include all and let caller filter
                user["inactive_check"] = {
                    "threshold_days": days_threshold,
                    "cutoff_date": cutoff_date,
                }
                inactive_users.append(user)

            return self._create_result(inactive_users, "USR02", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting inactive users: {e}")
            errors.append(str(e))
            return self._create_result([], "USR02", start_time, errors)

    def _transform_user_record(self, raw: Dict[str, str]) -> Dict[str, Any]:
        """Transform raw USR02 record to structured format."""
        return {
            "username": raw.get("BNAME", ""),
            "user_type": raw.get("USTYP", ""),
            "user_type_text": self._get_user_type_text(raw.get("USTYP", "")),
            "valid_from": self._format_date(raw.get("GLTGV", "")),
            "valid_to": self._format_date(raw.get("GLTGB", "")),
            "lock_status": self._parse_lock_status(raw.get("UFLAG", "0")),
            "password_change_date": self._format_date(raw.get("TRDAT", "")),
        }

    def _get_user_type_text(self, ustyp: str) -> str:
        """Convert SAP user type code to text."""
        user_types = {
            "A": "Dialog",
            "B": "System",
            "C": "Communication",
            "L": "Reference",
            "S": "Service",
        }
        return user_types.get(ustyp, "Unknown")

    def _check_password_compliance(self, user: Dict) -> bool:
        """
        Check if password change is within compliance window.

        Default: Password should be changed within last 90 days.
        """
        if not user.get("password_change_date"):
            return False

        try:
            pwd_date = datetime.fromisoformat(user["password_change_date"])
            days_since_change = (datetime.now() - pwd_date).days
            return days_since_change <= 90
        except:
            return False
