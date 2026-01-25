"""
SAP System Connector

Provides connectivity to SAP ECC and S/4HANA systems via RFC/BAPI.
Supports user management, role assignment, and authorization queries.

Requires: pyrfc library (SAP NetWeaver RFC SDK)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from enum import Enum
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .base import (
    BaseConnector, ConnectorConfig, OperationResult,
    ConnectorError, AuthenticationError, OperationError,
    ConnectionStatus
)

logger = logging.getLogger(__name__)

# Try to import pyrfc, provide mock if not available
try:
    from pyrfc import Connection, ABAPApplicationError, ABAPRuntimeError, LogonError, CommunicationError
    PYRFC_AVAILABLE = True
except ImportError:
    PYRFC_AVAILABLE = False
    logger.warning("pyrfc not installed. SAP connector will use simulation mode.")


class SAPSystem(Enum):
    """SAP System Types"""
    ECC = "ECC"
    S4HANA = "S4HANA"
    S4HANA_CLOUD = "S4HANA_CLOUD"
    BW = "BW"
    CRM = "CRM"
    SRM = "SRM"


@dataclass
class SAPConfig(ConnectorConfig):
    """SAP-specific configuration"""
    # SAP Connection Parameters
    client: str = "100"  # SAP Client number
    system_number: str = "00"  # SAP System Number
    system_id: str = ""  # SAP System ID (SID)
    sap_router: str = ""  # SAP Router string (if needed)

    # System type
    sap_system_type: SAPSystem = SAPSystem.ECC

    # Language
    language: str = "EN"

    # Pool settings
    pool_size: int = 5

    # Trace/Debug
    trace_level: int = 0  # 0-3, higher = more verbose

    def __post_init__(self):
        self.system_type = "sap"

    def get_connection_params(self) -> Dict[str, str]:
        """Get RFC connection parameters"""
        params = {
            "user": self.username,
            "passwd": self.password,
            "ashost": self.host,
            "sysnr": self.system_number,
            "client": self.client,
            "lang": self.language,
        }

        if self.sap_router:
            params["saprouter"] = self.sap_router

        if self.trace_level > 0:
            params["trace"] = str(self.trace_level)

        return params


class SAPConnectionPool:
    """
    Connection pool for SAP RFC connections.

    Manages a pool of connections for better performance.
    """

    def __init__(self, config: SAPConfig, pool_size: int = 5):
        self.config = config
        self.pool_size = pool_size
        self._pool: List[Any] = []
        self._available: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initialize the connection pool"""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            logger.info(f"Initializing SAP connection pool with {self.pool_size} connections")

            for i in range(self.pool_size):
                try:
                    conn = await self._create_connection()
                    self._pool.append(conn)
                    await self._available.put(conn)
                except Exception as e:
                    logger.error(f"Failed to create pool connection {i}: {e}")

            self._initialized = True
            logger.info(f"SAP connection pool initialized with {len(self._pool)} connections")

    async def _create_connection(self):
        """Create a new RFC connection"""
        if PYRFC_AVAILABLE:
            # Run in thread pool since pyrfc is synchronous
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                conn = await loop.run_in_executor(
                    executor,
                    lambda: Connection(**self.config.get_connection_params())
                )
            return conn
        else:
            # Return mock connection
            return MockSAPConnection(self.config)

    async def acquire(self) -> Any:
        """Acquire a connection from the pool"""
        if not self._initialized:
            await self.initialize()

        try:
            conn = await asyncio.wait_for(self._available.get(), timeout=30)
            return conn
        except asyncio.TimeoutError:
            logger.warning("Connection pool exhausted, creating new connection")
            return await self._create_connection()

    async def release(self, conn: Any):
        """Release a connection back to the pool"""
        await self._available.put(conn)

    async def close_all(self):
        """Close all connections in the pool"""
        async with self._lock:
            for conn in self._pool:
                try:
                    if PYRFC_AVAILABLE and hasattr(conn, 'close'):
                        conn.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")

            self._pool.clear()
            self._initialized = False


class MockSAPConnection:
    """Mock SAP connection for testing without pyrfc"""

    def __init__(self, config: SAPConfig):
        self.config = config
        self._connected = True

        # Mock user database with full SU01 fields
        self._users = {
            "JSMITH": {
                "USERNAME": "JSMITH",
                "FIRSTNAME": "John",
                "LASTNAME": "Smith",
                "FULLNAME": "John Smith",
                "EMAIL": "jsmith@company.com",
                "DEPARTMENT": "Finance",
                "FUNCTION": "Senior Accountant",
                "BUILDING": "HQ-A",
                "ROOM": "305",
                "FLOOR": "3",
                "TELEPHONE": "+1-555-0101",
                "MOBILE": "+1-555-0102",
                "FAX": "",
                # Logon Tab
                "USER_TYPE": "A",
                "USER_GROUP": "SUPER",
                "VALID_FROM": "20240101",
                "VALID_TO": "99991231",
                "LOCK_STATUS": "",
                "LAST_LOGON": "20250118",
                "SECURITY_POLICY": "DEFAULT",
                # Defaults Tab
                "LANGUAGE": "EN",
                "DECIMAL_NOTATION": "X",  # 1,234.56
                "DATE_FORMAT": "1",  # DD.MM.YYYY
                "TIME_FORMAT": "0",  # 24-hour
                "START_MENU": "SAP_EASY_ACCESS",
                "OUTPUT_DEVICE": "LP01",
                "TIME_ZONE": "EST",
                "COST_CENTER": "1000-FIN",
                # Company Tab
                "COMPANY_CODE": "1000",
                # Parameters
                "PARAMETERS": [
                    {"PARID": "BUK", "PARVA": "1000"},
                    {"PARID": "CAC", "PARVA": "FI"},
                ],
            },
            "MBROWN": {
                "USERNAME": "MBROWN",
                "FIRSTNAME": "Mary",
                "LASTNAME": "Brown",
                "FULLNAME": "Mary Brown",
                "EMAIL": "mbrown@company.com",
                "DEPARTMENT": "Procurement",
                "FUNCTION": "Procurement Manager",
                "BUILDING": "HQ-B",
                "ROOM": "210",
                "FLOOR": "2",
                "TELEPHONE": "+1-555-0201",
                "MOBILE": "+1-555-0202",
                "FAX": "",
                # Logon Tab
                "USER_TYPE": "A",
                "USER_GROUP": "USERS",
                "VALID_FROM": "20240301",
                "VALID_TO": "99991231",
                "LOCK_STATUS": "",
                "LAST_LOGON": "20250119",
                "SECURITY_POLICY": "DEFAULT",
                # Defaults Tab
                "LANGUAGE": "EN",
                "DECIMAL_NOTATION": "X",
                "DATE_FORMAT": "2",  # MM/DD/YYYY
                "TIME_FORMAT": "0",
                "START_MENU": "SAP_EASY_ACCESS",
                "OUTPUT_DEVICE": "LP02",
                "TIME_ZONE": "EST",
                "COST_CENTER": "1000-PROC",
                # Company Tab
                "COMPANY_CODE": "1000",
                # Parameters
                "PARAMETERS": [
                    {"PARID": "BUK", "PARVA": "1000"},
                    {"PARID": "EKO", "PARVA": "1000"},
                ],
            },
        }

        # Mock role database
        self._roles = {
            "SAP_ALL": {"AGR_NAME": "SAP_ALL", "TEXT": "All Authorizations", "TYPE": "S"},
            "Z_FI_DISPLAY": {"AGR_NAME": "Z_FI_DISPLAY", "TEXT": "Finance Display", "TYPE": "C"},
            "Z_FI_POST": {"AGR_NAME": "Z_FI_POST", "TEXT": "Finance Posting", "TYPE": "C"},
            "Z_MM_PO_CREATE": {"AGR_NAME": "Z_MM_PO_CREATE", "TEXT": "Create Purchase Orders", "TYPE": "C"},
            "Z_MM_PO_RELEASE": {"AGR_NAME": "Z_MM_PO_RELEASE", "TEXT": "Release Purchase Orders", "TYPE": "C"},
            "Z_MM_GR_POST": {"AGR_NAME": "Z_MM_GR_POST", "TEXT": "Post Goods Receipt", "TYPE": "C"},
            "Z_MM_VENDOR_MAINT": {"AGR_NAME": "Z_MM_VENDOR_MAINT", "TEXT": "Vendor Master Maintenance", "TYPE": "C"},
        }

        # Mock user-role assignments
        self._user_roles = {
            "JSMITH": [
                {"AGR_NAME": "Z_FI_DISPLAY", "FROM_DAT": "20240101", "TO_DAT": "99991231"},
                {"AGR_NAME": "Z_FI_POST", "FROM_DAT": "20240101", "TO_DAT": "99991231"},
            ],
            "MBROWN": [
                {"AGR_NAME": "Z_MM_PO_CREATE", "FROM_DAT": "20240301", "TO_DAT": "99991231"},
                {"AGR_NAME": "Z_MM_GR_POST", "FROM_DAT": "20240301", "TO_DAT": "99991231"},
            ],
        }

    def call(self, function_name: str, **params) -> Dict:
        """Mock BAPI/RFC call"""
        logger.info(f"Mock SAP call: {function_name} with params: {list(params.keys())}")

        # Simulate different BAPIs
        if function_name == "BAPI_USER_GET_DETAIL":
            return self._bapi_user_get_detail(params.get("USERNAME", ""))

        elif function_name == "BAPI_USER_CREATE1":
            return self._bapi_user_create(params)

        elif function_name == "BAPI_USER_CHANGE":
            return self._bapi_user_change(params)

        elif function_name == "BAPI_USER_DELETE":
            return self._bapi_user_delete(params.get("USERNAME", ""))

        elif function_name == "BAPI_USER_LOCK":
            return self._bapi_user_lock(params.get("USERNAME", ""))

        elif function_name == "BAPI_USER_UNLOCK":
            return self._bapi_user_unlock(params.get("USERNAME", ""))

        elif function_name == "BAPI_USER_ACTGROUPS_ASSIGN":
            return self._bapi_assign_roles(params)

        elif function_name == "BAPI_USER_ACTGROUPS_DELETE":
            return self._bapi_remove_roles(params)

        elif function_name == "BAPI_USER_GETLIST":
            return self._bapi_user_getlist(params)

        elif function_name == "PRGN_ACTIVITY_GROUPS_LIST":
            return self._get_role_list(params)

        elif function_name == "RFC_SYSTEM_INFO":
            return self._get_system_info()

        elif function_name == "BAPI_TRANSACTION_COMMIT":
            return {"RETURN": []}

        else:
            return {"RETURN": [{"TYPE": "E", "MESSAGE": f"Unknown function: {function_name}"}]}

    def _bapi_user_get_detail(self, username: str) -> Dict:
        """Return full SU01 user details matching real SAP structure."""
        if username in self._users:
            user = self._users[username]
            roles = self._user_roles.get(username, [])
            return {
                # Address Tab
                "ADDRESS": {
                    "FIRSTNAME": user.get("FIRSTNAME", ""),
                    "LASTNAME": user.get("LASTNAME", ""),
                    "FULLNAME": user.get("FULLNAME", ""),
                    "E_MAIL": user.get("EMAIL", ""),
                    "DEPARTMENT": user.get("DEPARTMENT", ""),
                    "FUNCTION": user.get("FUNCTION", ""),
                    "BUILDING": user.get("BUILDING", ""),
                    "ROOM_NO_P": user.get("ROOM", ""),
                    "FLOOR_P": user.get("FLOOR", ""),
                    "TEL1_NUMBR": user.get("TELEPHONE", ""),
                    "MOB_NUMBER": user.get("MOBILE", ""),
                    "FAX_NUMBER": user.get("FAX", ""),
                },
                # Logon Tab
                "LOGONDATA": {
                    "GLTGV": user.get("VALID_FROM", ""),
                    "GLTGB": user.get("VALID_TO", ""),
                    "USTYP": user.get("USER_TYPE", "A"),
                    "CLASS": user.get("USER_GROUP", ""),
                    "UFLAG": 64 if user.get("LOCK_STATUS") == "L" else 0,
                    "TRDAT": user.get("LAST_LOGON", ""),
                    "LTIME": "120000",
                    "PWDSTATE": "0",
                    "SECURITY_POLICY": user.get("SECURITY_POLICY", ""),
                },
                # Defaults Tab
                "DEFAULTS": {
                    "LANGU": user.get("LANGUAGE", "EN"),
                    "DCPFM": user.get("DECIMAL_NOTATION", ""),
                    "DATFM": user.get("DATE_FORMAT", ""),
                    "TIMEFM": user.get("TIME_FORMAT", ""),
                    "START_MENU": user.get("START_MENU", ""),
                    "SPLD": user.get("OUTPUT_DEVICE", ""),
                    "TZONE": user.get("TIME_ZONE", ""),
                    "KOSTL": user.get("COST_CENTER", ""),
                },
                # Company Tab
                "COMPANY": {
                    "COMPANY": user.get("COMPANY_CODE", ""),
                },
                # Parameters Tab
                "PARAMETER": user.get("PARAMETERS", []),
                # Roles
                "ACTIVITYGROUPS": roles,
                # Profiles (empty for mock)
                "PROFILES": [],
                "RETURN": []
            }
        else:
            return {"RETURN": [{"TYPE": "E", "ID": "01", "NUMBER": "124", "MESSAGE": f"User {username} does not exist"}]}

    def _bapi_user_create(self, params: Dict) -> Dict:
        """Create user with full SU01 fields."""
        username = params.get("USERNAME", "")
        if username in self._users:
            return {"RETURN": [{"TYPE": "E", "MESSAGE": f"User {username} already exists"}]}

        address = params.get("ADDRESS", {})
        logondata = params.get("LOGONDATA", {})
        defaults = params.get("DEFAULTS", {})
        company = params.get("COMPANY", {})
        parameters = params.get("PARAMETER", [])

        self._users[username] = {
            "USERNAME": username,
            # Address Tab
            "FIRSTNAME": address.get("FIRSTNAME", ""),
            "LASTNAME": address.get("LASTNAME", ""),
            "FULLNAME": address.get("FULLNAME", ""),
            "EMAIL": address.get("E_MAIL", ""),
            "DEPARTMENT": address.get("DEPARTMENT", ""),
            "FUNCTION": address.get("FUNCTION", ""),
            "BUILDING": address.get("BUILDING", ""),
            "ROOM": address.get("ROOM_NO_P", ""),
            "FLOOR": address.get("FLOOR_P", ""),
            "TELEPHONE": address.get("TEL1_NUMBR", ""),
            "MOBILE": address.get("MOB_NUMBER", ""),
            "FAX": address.get("FAX_NUMBER", ""),
            # Logon Tab
            "USER_TYPE": logondata.get("USTYP", "A"),
            "USER_GROUP": logondata.get("CLASS", "USERS"),
            "VALID_FROM": logondata.get("GLTGV", datetime.now().strftime("%Y%m%d")),
            "VALID_TO": logondata.get("GLTGB", "99991231"),
            "LOCK_STATUS": "",
            "LAST_LOGON": "",
            "SECURITY_POLICY": "DEFAULT",
            # Defaults Tab
            "LANGUAGE": defaults.get("LANGU", "EN"),
            "DECIMAL_NOTATION": defaults.get("DCPFM", ""),
            "DATE_FORMAT": defaults.get("DATFM", ""),
            "TIME_FORMAT": defaults.get("TIMEFM", ""),
            "START_MENU": defaults.get("START_MENU", ""),
            "OUTPUT_DEVICE": defaults.get("SPLD", ""),
            "TIME_ZONE": defaults.get("TZONE", ""),
            "COST_CENTER": defaults.get("KOSTL", ""),
            # Company Tab
            "COMPANY_CODE": company.get("COMPANY", ""),
            # Parameters Tab
            "PARAMETERS": parameters,
        }
        self._user_roles[username] = []

        return {"RETURN": [{"TYPE": "S", "MESSAGE": f"User {username} created successfully"}]}

    def _bapi_user_change(self, params: Dict) -> Dict:
        """Update user with full SU01 field support."""
        username = params.get("USERNAME", "")
        if username not in self._users:
            return {"RETURN": [{"TYPE": "E", "MESSAGE": f"User {username} does not exist"}]}

        user = self._users[username]

        # Update ADDRESS fields if provided
        if "ADDRESS" in params and "ADDRESSX" in params:
            address = params["ADDRESS"]
            addressx = params["ADDRESSX"]
            field_map = {
                "FIRSTNAME": "FIRSTNAME",
                "LASTNAME": "LASTNAME",
                "FULLNAME": "FULLNAME",
                "E_MAIL": "EMAIL",
                "DEPARTMENT": "DEPARTMENT",
                "FUNCTION": "FUNCTION",
                "BUILDING": "BUILDING",
                "ROOM_NO_P": "ROOM",
                "FLOOR_P": "FLOOR",
                "TEL1_NUMBR": "TELEPHONE",
                "MOB_NUMBER": "MOBILE",
                "FAX_NUMBER": "FAX",
            }
            for sap_field, user_field in field_map.items():
                if addressx.get(sap_field) == "X":
                    user[user_field] = address.get(sap_field, user.get(user_field, ""))

        # Update LOGONDATA fields if provided
        if "LOGONDATA" in params and "LOGONDATAX" in params:
            logondata = params["LOGONDATA"]
            logondatax = params["LOGONDATAX"]
            if logondatax.get("USTYP") == "X":
                user["USER_TYPE"] = logondata.get("USTYP", user.get("USER_TYPE", "A"))
            if logondatax.get("CLASS") == "X":
                user["USER_GROUP"] = logondata.get("CLASS", user.get("USER_GROUP", ""))
            if logondatax.get("GLTGV") == "X":
                user["VALID_FROM"] = logondata.get("GLTGV", user.get("VALID_FROM", ""))
            if logondatax.get("GLTGB") == "X":
                user["VALID_TO"] = logondata.get("GLTGB", user.get("VALID_TO", ""))

        # Update DEFAULTS fields if provided
        if "DEFAULTS" in params and "DEFAULTSX" in params:
            defaults = params["DEFAULTS"]
            defaultsx = params["DEFAULTSX"]
            defaults_map = {
                "LANGU": "LANGUAGE",
                "DCPFM": "DECIMAL_NOTATION",
                "DATFM": "DATE_FORMAT",
                "TIMEFM": "TIME_FORMAT",
                "START_MENU": "START_MENU",
                "SPLD": "OUTPUT_DEVICE",
                "TZONE": "TIME_ZONE",
                "KOSTL": "COST_CENTER",
            }
            for sap_field, user_field in defaults_map.items():
                if defaultsx.get(sap_field) == "X":
                    user[user_field] = defaults.get(sap_field, user.get(user_field, ""))

        # Update COMPANY if provided
        if "COMPANY" in params and "COMPANYX" in params:
            company = params["COMPANY"]
            companyx = params["COMPANYX"]
            if companyx.get("COMPANY") == "X":
                user["COMPANY_CODE"] = company.get("COMPANY", user.get("COMPANY_CODE", ""))

        return {"RETURN": [{"TYPE": "S", "MESSAGE": f"User {username} updated successfully"}]}

    def _bapi_user_delete(self, username: str) -> Dict:
        if username not in self._users:
            return {"RETURN": [{"TYPE": "E", "MESSAGE": f"User {username} does not exist"}]}

        del self._users[username]
        if username in self._user_roles:
            del self._user_roles[username]

        return {"RETURN": [{"TYPE": "S", "MESSAGE": f"User {username} deleted successfully"}]}

    def _bapi_user_lock(self, username: str) -> Dict:
        if username not in self._users:
            return {"RETURN": [{"TYPE": "E", "MESSAGE": f"User {username} does not exist"}]}

        self._users[username]["LOCK_STATUS"] = "L"
        return {"RETURN": [{"TYPE": "S", "MESSAGE": f"User {username} locked successfully"}]}

    def _bapi_user_unlock(self, username: str) -> Dict:
        if username not in self._users:
            return {"RETURN": [{"TYPE": "E", "MESSAGE": f"User {username} does not exist"}]}

        self._users[username]["LOCK_STATUS"] = ""
        return {"RETURN": [{"TYPE": "S", "MESSAGE": f"User {username} unlocked successfully"}]}

    def _bapi_assign_roles(self, params: Dict) -> Dict:
        username = params.get("USERNAME", "")
        if username not in self._users:
            return {"RETURN": [{"TYPE": "E", "MESSAGE": f"User {username} does not exist"}]}

        roles = params.get("ACTIVITYGROUPS", [])
        if username not in self._user_roles:
            self._user_roles[username] = []

        for role in roles:
            role_name = role.get("AGR_NAME", "")
            if role_name and role_name not in [r["AGR_NAME"] for r in self._user_roles[username]]:
                self._user_roles[username].append({
                    "AGR_NAME": role_name,
                    "FROM_DAT": role.get("FROM_DAT", datetime.now().strftime("%Y%m%d")),
                    "TO_DAT": role.get("TO_DAT", "99991231")
                })

        return {"RETURN": [{"TYPE": "S", "MESSAGE": f"Roles assigned to {username} successfully"}]}

    def _bapi_remove_roles(self, params: Dict) -> Dict:
        username = params.get("USERNAME", "")
        if username not in self._users:
            return {"RETURN": [{"TYPE": "E", "MESSAGE": f"User {username} does not exist"}]}

        roles_to_remove = params.get("ACTIVITYGROUPS", [])
        role_names = [r.get("AGR_NAME") for r in roles_to_remove]

        if username in self._user_roles:
            self._user_roles[username] = [
                r for r in self._user_roles[username]
                if r["AGR_NAME"] not in role_names
            ]

        return {"RETURN": [{"TYPE": "S", "MESSAGE": f"Roles removed from {username} successfully"}]}

    def _bapi_user_getlist(self, params: Dict) -> Dict:
        users = []
        for username, user in self._users.items():
            users.append({
                "USERNAME": username,
                "FIRSTNAME": user["FIRSTNAME"],
                "LASTNAME": user["LASTNAME"],
            })

        return {
            "USERLIST": users,
            "RETURN": []
        }

    def _get_role_list(self, params: Dict) -> Dict:
        roles = []
        for role_name, role in self._roles.items():
            roles.append({
                "AGR_NAME": role_name,
                "TEXT": role["TEXT"],
                "AGR_TYPE": role["TYPE"]
            })

        return {
            "ACTIVITY_GROUPS": roles,
            "RETURN": []
        }

    def _get_system_info(self) -> Dict:
        return {
            "RFCSI_EXPORT": {
                "RFCHOST": self.config.host,
                "RFCSYSID": self.config.system_id or "DEV",
                "RFCDBSYS": "ORACLE",
                "RFCDBHOST": self.config.host,
                "RFCDATABS": "DEV",
                "RFCMACH": "Linux",
                "RFCKERNREL": "753",
                "RFCPROTO": "011",
            }
        }

    def close(self):
        """Close the mock connection"""
        self._connected = False


class SAPConnector(BaseConnector):
    """
    SAP System Connector

    Provides full connectivity to SAP ECC/S4HANA systems via RFC.
    Supports all user management and authorization operations.
    """

    def __init__(self, config: SAPConfig):
        super().__init__(config)
        self.sap_config = config
        self._pool: Optional[SAPConnectionPool] = None
        self._executor = ThreadPoolExecutor(max_workers=config.pool_size)

    async def _do_connect(self):
        """Establish SAP RFC connection"""
        self._pool = SAPConnectionPool(self.sap_config, self.sap_config.pool_size)
        await self._pool.initialize()

        # Test connection
        conn = await self._pool.acquire()
        try:
            result = await self._call_rfc(conn, "RFC_SYSTEM_INFO")
            logger.info(f"Connected to SAP system: {result.get('RFCSI_EXPORT', {}).get('RFCSYSID', 'Unknown')}")
        finally:
            await self._pool.release(conn)

    async def _do_disconnect(self):
        """Disconnect from SAP"""
        if self._pool:
            await self._pool.close_all()
            self._pool = None

    async def _do_test_connection(self) -> Dict:
        """Test SAP connection"""
        conn = await self._pool.acquire()
        try:
            result = await self._call_rfc(conn, "RFC_SYSTEM_INFO")
            sys_info = result.get("RFCSI_EXPORT", {})
            return {
                "system_id": sys_info.get("RFCSYSID", ""),
                "host": sys_info.get("RFCHOST", ""),
                "database": sys_info.get("RFCDBSYS", ""),
                "kernel_release": sys_info.get("RFCKERNREL", ""),
                "status": "connected"
            }
        finally:
            await self._pool.release(conn)

    async def _do_execute(self, operation: str, **params) -> Dict:
        """Execute SAP operation"""
        operation_map = {
            "get_user": self._get_user,
            "create_user": self._create_user,
            "update_user": self._update_user,
            "delete_user": self._delete_user,
            "lock_user": self._lock_user,
            "unlock_user": self._unlock_user,
            "reset_password": self._reset_password,
            "assign_role": self._assign_role,
            "remove_role": self._remove_role,
            "get_user_roles": self._get_user_roles,
            "list_users": self._list_users,
            "list_roles": self._list_roles,
        }

        handler = operation_map.get(operation)
        if not handler:
            raise OperationError(f"Unknown operation: {operation}", operation)

        return await handler(**params)

    async def _call_rfc(self, conn, function_name: str, **params) -> Dict:
        """Call an RFC function module"""
        loop = asyncio.get_event_loop()

        def _call():
            return conn.call(function_name, **params)

        result = await loop.run_in_executor(self._executor, _call)
        self._check_return(result, function_name)
        return result

    def _check_return(self, result: Dict, operation: str):
        """Check BAPI return for errors"""
        returns = result.get("RETURN", [])
        if isinstance(returns, dict):
            returns = [returns]

        for ret in returns:
            if ret.get("TYPE") in ("E", "A"):  # Error or Abort
                raise OperationError(
                    ret.get("MESSAGE", "Unknown error"),
                    operation,
                    {"return": ret}
                )

    async def _commit(self, conn):
        """Commit BAPI transaction"""
        await self._call_rfc(conn, "BAPI_TRANSACTION_COMMIT", WAIT="X")

    # =========================================================================
    # User Management Operations
    # =========================================================================

    async def _get_user(self, user_id: str) -> Dict:
        """
        Get user details from SAP (full SU01 data).

        Returns all tabs: Address, Logon, Defaults, Parameters, Company, Roles.
        """
        conn = await self._pool.acquire()
        try:
            result = await self._call_rfc(conn, "BAPI_USER_GET_DETAIL", USERNAME=user_id)

            # Extract all structure data
            address = result.get("ADDRESS", {})
            logondata = result.get("LOGONDATA", {})
            defaults = result.get("DEFAULTS", {})
            company = result.get("COMPANY", {})
            uclass = result.get("UCLASS", {})  # User Group info
            roles = result.get("ACTIVITYGROUPS", [])
            profiles = result.get("PROFILES", [])
            parameter = result.get("PARAMETER", [])  # User parameters

            # Map user type codes
            user_type_map = {
                "A": "Dialog",
                "B": "System",
                "C": "Communication",
                "L": "Reference",
                "S": "Service",
            }

            return {
                "user_id": user_id,
                # === Address Tab ===
                "first_name": address.get("FIRSTNAME", ""),
                "last_name": address.get("LASTNAME", ""),
                "full_name": address.get("FULLNAME", ""),
                "email": address.get("E_MAIL", ""),
                "department": address.get("DEPARTMENT", ""),
                "function": address.get("FUNCTION", ""),
                "building": address.get("BUILDING", ""),
                "room": address.get("ROOM_NO_P", ""),
                "floor": address.get("FLOOR_P", ""),
                "telephone": address.get("TEL1_NUMBR", ""),
                "mobile": address.get("MOB_NUMBER", ""),
                "fax": address.get("FAX_NUMBER", ""),

                # === Logon Tab ===
                "user_type": logondata.get("USTYP", "A"),
                "user_type_text": user_type_map.get(logondata.get("USTYP", "A"), "Dialog"),
                "user_group": logondata.get("CLASS", ""),  # User Group (SUPER, USERS, etc.)
                "valid_from": logondata.get("GLTGV", ""),
                "valid_to": logondata.get("GLTGB", ""),
                "lock_status": logondata.get("UFLAG", 0),
                "is_locked": int(logondata.get("UFLAG", 0)) > 0,
                "last_logon_date": logondata.get("TRDAT", ""),
                "last_logon_time": logondata.get("LTIME", ""),
                "password_status": logondata.get("PWDSTATE", ""),
                "security_policy": logondata.get("SECURITY_POLICY", ""),

                # === Defaults Tab ===
                "language": defaults.get("LANGU", "EN"),
                "logon_language": defaults.get("LANGU", "EN"),
                "decimal_notation": defaults.get("DCPFM", ""),
                "date_format": defaults.get("DATFM", ""),
                "time_format": defaults.get("TIMEFM", ""),
                "start_menu": defaults.get("START_MENU", ""),
                "output_device": defaults.get("SPLD", ""),  # Spool device (printer)
                "print_immed": defaults.get("SPLG", ""),
                "delete_after_print": defaults.get("SPDA", ""),
                "time_zone": defaults.get("TZONE", ""),
                "cost_center": defaults.get("KOSTL", ""),

                # === Parameters Tab ===
                "parameters": [
                    {
                        "parameter_id": p.get("PARID", ""),
                        "parameter_value": p.get("PARVA", ""),
                    }
                    for p in parameter
                ],

                # === Company Tab ===
                "company_code": company.get("COMPANY", ""),

                # === Roles ===
                "roles": [
                    {
                        "role_name": r.get("AGR_NAME", ""),
                        "from_date": r.get("FROM_DAT", ""),
                        "to_date": r.get("TO_DAT", ""),
                        "org_flag": r.get("ORG_FLAG", ""),
                    }
                    for r in roles
                ],

                # === Profiles ===
                "profiles": [
                    {
                        "profile_name": p.get("BAESSION", ""),
                        "profile_text": p.get("BAPIPTEXT", ""),
                    }
                    for p in profiles
                ],
            }
        finally:
            await self._pool.release(conn)

    async def _create_user(self, user_data: Dict) -> Dict:
        """
        Create a new user in SAP (SU01).

        Supports all SU01 tabs:
        - Address: name, email, department, phone, etc.
        - Logon: user type, user group, validity dates
        - Defaults: language, date format, output device, cost center
        - Parameters: user-specific parameters
        - Company: company code assignment

        Args:
            user_data: Dict with user attributes matching SU01 fields
        """
        conn = await self._pool.acquire()
        try:
            # === ADDRESS structure (Address Tab) ===
            address = {
                "FIRSTNAME": user_data.get("first_name", ""),
                "LASTNAME": user_data.get("last_name", ""),
                "FULLNAME": user_data.get("full_name", ""),
                "E_MAIL": user_data.get("email", ""),
                "DEPARTMENT": user_data.get("department", ""),
                "FUNCTION": user_data.get("function", ""),
                "BUILDING": user_data.get("building", ""),
                "ROOM_NO_P": user_data.get("room", ""),
                "FLOOR_P": user_data.get("floor", ""),
                "TEL1_NUMBR": user_data.get("telephone", ""),
                "MOB_NUMBER": user_data.get("mobile", ""),
                "FAX_NUMBER": user_data.get("fax", ""),
            }

            # === LOGONDATA structure (Logon Tab) ===
            # User Types: A=Dialog, B=System, C=Communication, L=Reference, S=Service
            logondata = {
                "GLTGV": user_data.get("valid_from", datetime.now().strftime("%Y%m%d")),
                "GLTGB": user_data.get("valid_to", "99991231"),
                "USTYP": user_data.get("user_type", "A"),
                "CLASS": user_data.get("user_group", ""),  # User Group (e.g., SUPER, USERS, LIMITED)
            }

            # === DEFAULTS structure (Defaults Tab) ===
            defaults = {
                "LANGU": user_data.get("language", "EN"),
                "DCPFM": user_data.get("decimal_notation", ""),  # Decimal format
                "DATFM": user_data.get("date_format", ""),  # Date format (1=DD.MM.YYYY, 2=MM/DD/YYYY, etc.)
                "TIMEFM": user_data.get("time_format", ""),  # Time format
                "START_MENU": user_data.get("start_menu", ""),  # Initial transaction/menu
                "SPLD": user_data.get("output_device", ""),  # Output device (printer)
                "TZONE": user_data.get("time_zone", ""),  # Time zone
                "KOSTL": user_data.get("cost_center", ""),  # Cost center
            }

            # === COMPANY structure (Company Tab) ===
            company = {}
            if user_data.get("company_code"):
                company["COMPANY"] = user_data.get("company_code")

            # === PASSWORD structure ===
            password = {
                "BAPIPWD": user_data.get("initial_password", "Init1234!")
            }

            # === PARAMETER table (Parameters Tab) ===
            parameters = []
            for param in user_data.get("parameters", []):
                if param.get("parameter_id") and param.get("parameter_value"):
                    parameters.append({
                        "PARID": param["parameter_id"],
                        "PARVA": param["parameter_value"],
                    })

            # Build RFC call parameters
            rfc_params = {
                "USERNAME": user_data.get("user_id", ""),
                "ADDRESS": address,
                "LOGONDATA": logondata,
                "DEFAULTS": defaults,
                "PASSWORD": password,
            }

            # Add optional structures only if they have data
            if company:
                rfc_params["COMPANY"] = company
            if parameters:
                rfc_params["PARAMETER"] = parameters

            result = await self._call_rfc(conn, "BAPI_USER_CREATE1", **rfc_params)

            await self._commit(conn)

            return {
                "user_id": user_data.get("user_id"),
                "created": True,
                "message": f"User {user_data.get('user_id')} created successfully",
                "details": {
                    "user_type": user_data.get("user_type", "A"),
                    "user_group": user_data.get("user_group", ""),
                    "valid_from": user_data.get("valid_from"),
                    "valid_to": user_data.get("valid_to"),
                }
            }
        finally:
            await self._pool.release(conn)

    async def _update_user(self, user_id: str, user_data: Dict) -> Dict:
        """
        Update user details in SAP (SU01).

        Supports updating all SU01 tabs:
        - Address: name, email, department, phone, etc.
        - Logon: user type, user group, validity dates
        - Defaults: language, date format, output device, cost center
        - Parameters: user-specific parameters
        """
        conn = await self._pool.acquire()
        try:
            # === ADDRESS structure and change flags ===
            address = {}
            addressx = {}

            address_fields = {
                "first_name": "FIRSTNAME",
                "last_name": "LASTNAME",
                "full_name": "FULLNAME",
                "email": "E_MAIL",
                "department": "DEPARTMENT",
                "function": "FUNCTION",
                "building": "BUILDING",
                "room": "ROOM_NO_P",
                "floor": "FLOOR_P",
                "telephone": "TEL1_NUMBR",
                "mobile": "MOB_NUMBER",
                "fax": "FAX_NUMBER",
            }

            for py_field, sap_field in address_fields.items():
                if py_field in user_data:
                    address[sap_field] = user_data[py_field]
                    addressx[sap_field] = "X"

            # === LOGONDATA structure and change flags ===
            logondata = {}
            logondatax = {}

            logon_fields = {
                "user_type": "USTYP",
                "user_group": "CLASS",
                "valid_from": "GLTGV",
                "valid_to": "GLTGB",
            }

            for py_field, sap_field in logon_fields.items():
                if py_field in user_data:
                    logondata[sap_field] = user_data[py_field]
                    logondatax[sap_field] = "X"

            # === DEFAULTS structure and change flags ===
            defaults = {}
            defaultsx = {}

            defaults_fields = {
                "language": "LANGU",
                "logon_language": "LANGU",
                "decimal_notation": "DCPFM",
                "date_format": "DATFM",
                "time_format": "TIMEFM",
                "start_menu": "START_MENU",
                "output_device": "SPLD",
                "time_zone": "TZONE",
                "cost_center": "KOSTL",
            }

            for py_field, sap_field in defaults_fields.items():
                if py_field in user_data:
                    defaults[sap_field] = user_data[py_field]
                    defaultsx[sap_field] = "X"

            # === COMPANY structure ===
            company = {}
            companyx = {}
            if "company_code" in user_data:
                company["COMPANY"] = user_data["company_code"]
                companyx["COMPANY"] = "X"

            # Build RFC call parameters
            rfc_params = {"USERNAME": user_id}

            if address:
                rfc_params["ADDRESS"] = address
                rfc_params["ADDRESSX"] = addressx
            if logondata:
                rfc_params["LOGONDATA"] = logondata
                rfc_params["LOGONDATAX"] = logondatax
            if defaults:
                rfc_params["DEFAULTS"] = defaults
                rfc_params["DEFAULTSX"] = defaultsx
            if company:
                rfc_params["COMPANY"] = company
                rfc_params["COMPANYX"] = companyx

            result = await self._call_rfc(conn, "BAPI_USER_CHANGE", **rfc_params)

            await self._commit(conn)

            return {
                "user_id": user_id,
                "updated": True,
                "message": f"User {user_id} updated successfully",
                "fields_updated": list(user_data.keys())
            }
        finally:
            await self._pool.release(conn)

    async def _delete_user(self, user_id: str) -> Dict:
        """Delete user from SAP"""
        conn = await self._pool.acquire()
        try:
            result = await self._call_rfc(
                conn,
                "BAPI_USER_DELETE",
                USERNAME=user_id,
            )

            await self._commit(conn)

            return {
                "user_id": user_id,
                "deleted": True,
                "message": f"User {user_id} deleted successfully"
            }
        finally:
            await self._pool.release(conn)

    async def _lock_user(self, user_id: str) -> Dict:
        """Lock user account in SAP"""
        conn = await self._pool.acquire()
        try:
            result = await self._call_rfc(
                conn,
                "BAPI_USER_LOCK",
                USERNAME=user_id,
            )

            await self._commit(conn)

            return {
                "user_id": user_id,
                "locked": True,
                "message": f"User {user_id} locked successfully"
            }
        finally:
            await self._pool.release(conn)

    async def _unlock_user(self, user_id: str) -> Dict:
        """Unlock user account in SAP"""
        conn = await self._pool.acquire()
        try:
            result = await self._call_rfc(
                conn,
                "BAPI_USER_UNLOCK",
                USERNAME=user_id,
            )

            await self._commit(conn)

            return {
                "user_id": user_id,
                "unlocked": True,
                "message": f"User {user_id} unlocked successfully"
            }
        finally:
            await self._pool.release(conn)

    async def _reset_password(self, user_id: str, new_password: str) -> Dict:
        """Reset user password in SAP"""
        conn = await self._pool.acquire()
        try:
            password = {
                "BAPIPWD": new_password
            }
            passwordx = {
                "BAPIPWD": "X"
            }

            result = await self._call_rfc(
                conn,
                "BAPI_USER_CHANGE",
                USERNAME=user_id,
                PASSWORD=password,
                PASSWORDX=passwordx,
            )

            await self._commit(conn)

            return {
                "user_id": user_id,
                "password_reset": True,
                "message": f"Password reset for user {user_id}"
            }
        finally:
            await self._pool.release(conn)

    async def _assign_role(self, user_id: str, role_name: str, valid_from: Optional[datetime] = None, valid_to: Optional[datetime] = None) -> Dict:
        """Assign a role to a user in SAP (PFCG)"""
        conn = await self._pool.acquire()
        try:
            # Prepare ACTIVITYGROUPS table
            from_date = valid_from.strftime("%Y%m%d") if valid_from else datetime.now().strftime("%Y%m%d")
            to_date = valid_to.strftime("%Y%m%d") if valid_to else "99991231"

            roles = [{
                "AGR_NAME": role_name,
                "FROM_DAT": from_date,
                "TO_DAT": to_date,
            }]

            result = await self._call_rfc(
                conn,
                "BAPI_USER_ACTGROUPS_ASSIGN",
                USERNAME=user_id,
                ACTIVITYGROUPS=roles,
            )

            await self._commit(conn)

            return {
                "user_id": user_id,
                "role_name": role_name,
                "assigned": True,
                "valid_from": from_date,
                "valid_to": to_date,
                "message": f"Role {role_name} assigned to user {user_id}"
            }
        finally:
            await self._pool.release(conn)

    async def _remove_role(self, user_id: str, role_name: str) -> Dict:
        """Remove a role from a user in SAP"""
        conn = await self._pool.acquire()
        try:
            roles = [{"AGR_NAME": role_name}]

            result = await self._call_rfc(
                conn,
                "BAPI_USER_ACTGROUPS_DELETE",
                USERNAME=user_id,
                ACTIVITYGROUPS=roles,
            )

            await self._commit(conn)

            return {
                "user_id": user_id,
                "role_name": role_name,
                "removed": True,
                "message": f"Role {role_name} removed from user {user_id}"
            }
        finally:
            await self._pool.release(conn)

    async def _get_user_roles(self, user_id: str) -> Dict:
        """Get all roles assigned to a user"""
        user_data = await self._get_user(user_id)
        return {
            "user_id": user_id,
            "roles": user_data.get("roles", [])
        }

    async def _list_users(self, filters: Optional[Dict] = None) -> Dict:
        """List users in SAP"""
        conn = await self._pool.acquire()
        try:
            params = {}
            if filters:
                if "username_pattern" in filters:
                    params["USERNAME"] = filters["username_pattern"]

            result = await self._call_rfc(conn, "BAPI_USER_GETLIST", **params)

            users = []
            for user in result.get("USERLIST", []):
                users.append({
                    "user_id": user.get("USERNAME", ""),
                    "first_name": user.get("FIRSTNAME", ""),
                    "last_name": user.get("LASTNAME", ""),
                })

            return {
                "users": users,
                "count": len(users)
            }
        finally:
            await self._pool.release(conn)

    async def _list_roles(self, filters: Optional[Dict] = None) -> Dict:
        """List roles in SAP"""
        conn = await self._pool.acquire()
        try:
            params = {}
            if filters:
                if "role_pattern" in filters:
                    params["ROLE"] = filters["role_pattern"]

            result = await self._call_rfc(conn, "PRGN_ACTIVITY_GROUPS_LIST", **params)

            roles = []
            for role in result.get("ACTIVITY_GROUPS", []):
                roles.append({
                    "role_name": role.get("AGR_NAME", ""),
                    "description": role.get("TEXT", ""),
                    "type": role.get("AGR_TYPE", ""),
                })

            return {
                "roles": roles,
                "count": len(roles)
            }
        finally:
            await self._pool.release(conn)
