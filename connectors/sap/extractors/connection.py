# SAP RFC Connection Manager
# Thread-safe connection pooling for GOVERNEX+ extractors

"""
Connection management for SAP RFC extractors.

Features:
- Thread-safe connection pooling
- Automatic reconnection on failure
- Connection health monitoring
- Audit logging of connection events
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from threading import Lock
from queue import Queue, Empty
import logging

from .config import SAPExtractorConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)

# Try to import pyrfc
try:
    from pyrfc import Connection as RFCConnection
    HAS_PYRFC = True
except ImportError:
    HAS_PYRFC = False
    RFCConnection = None
    logger.warning(
        "pyrfc not installed. SAP RFC extractors will use mock mode. "
        "Install SAP NW RFC SDK and pyrfc for production use."
    )


class SAPRFCConnectionManager:
    """
    Thread-safe SAP RFC connection manager with pooling.

    Usage:
        manager = SAPRFCConnectionManager(config)
        with manager.get_connection() as conn:
            result = conn.call("RFC_PING")
    """

    def __init__(self, config: Optional[SAPExtractorConfig] = None):
        """
        Initialize connection manager.

        Args:
            config: SAP connection configuration. Uses DEFAULT_CONFIG if not provided.
        """
        self.config = config or DEFAULT_CONFIG
        self._pool: Queue = Queue(maxsize=self.config.pool_size)
        self._lock = Lock()
        self._created_count = 0
        self._active_count = 0
        self._use_mock = not HAS_PYRFC

        if self._use_mock:
            logger.info("Using mock SAP connection mode")

    def _create_connection(self) -> Any:
        """Create a new RFC connection."""
        if self._use_mock:
            return MockRFCConnection(self.config)

        try:
            params = self.config.to_rfc_params()
            conn = RFCConnection(**params)
            logger.debug(f"Created new RFC connection to {self.config.ashost}")
            return conn
        except Exception as e:
            logger.error(f"Failed to create RFC connection: {e}")
            raise

    def get_connection(self) -> "ConnectionContext":
        """
        Get a connection from the pool.

        Returns a context manager that returns the connection to the pool on exit.
        """
        return ConnectionContext(self)

    def _acquire(self) -> Any:
        """Acquire a connection from the pool or create a new one."""
        # Try to get from pool first
        try:
            conn = self._pool.get_nowait()
            # Validate connection is still alive
            if self._validate_connection(conn):
                with self._lock:
                    self._active_count += 1
                return conn
            else:
                # Connection dead, close and create new
                self._close_connection(conn)
        except Empty:
            pass

        # Create new connection if under limit
        with self._lock:
            if self._created_count < self.config.pool_size:
                self._created_count += 1
                self._active_count += 1
                return self._create_connection()

        # Wait for available connection
        conn = self._pool.get(timeout=self.config.timeout)
        with self._lock:
            self._active_count += 1
        return conn

    def _release(self, conn: Any) -> None:
        """Return a connection to the pool."""
        with self._lock:
            self._active_count -= 1

        if self._validate_connection(conn):
            try:
                self._pool.put_nowait(conn)
            except:
                self._close_connection(conn)
        else:
            self._close_connection(conn)
            with self._lock:
                self._created_count -= 1

    def _validate_connection(self, conn: Any) -> bool:
        """Check if connection is still valid."""
        if self._use_mock:
            return True

        try:
            conn.call("RFC_PING")
            return True
        except:
            return False

    def _close_connection(self, conn: Any) -> None:
        """Close a connection."""
        try:
            if hasattr(conn, "close"):
                conn.close()
        except:
            pass

    def call(self, function_name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute an RFC call using a pooled connection.

        Args:
            function_name: Name of RFC function module
            **kwargs: Function parameters

        Returns:
            RFC function result
        """
        with self.get_connection() as conn:
            return conn.call(function_name, **kwargs)

    def close_all(self) -> None:
        """Close all connections in the pool."""
        while True:
            try:
                conn = self._pool.get_nowait()
                self._close_connection(conn)
            except Empty:
                break

        with self._lock:
            self._created_count = 0
            self._active_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return {
            "pool_size": self.config.pool_size,
            "created_connections": self._created_count,
            "active_connections": self._active_count,
            "pooled_connections": self._pool.qsize(),
            "mock_mode": self._use_mock,
        }


class ConnectionContext:
    """Context manager for connection acquisition/release."""

    def __init__(self, manager: SAPRFCConnectionManager):
        self.manager = manager
        self.conn = None

    def __enter__(self) -> Any:
        self.conn = self.manager._acquire()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.conn:
            self.manager._release(self.conn)
        return False


class MockRFCConnection:
    """
    Mock RFC connection for testing and development.

    Simulates SAP RFC calls with realistic sample data.
    """

    def __init__(self, config: SAPExtractorConfig):
        self.config = config
        self._connected = True

    def call(self, function_name: str, **kwargs) -> Dict[str, Any]:
        """Simulate RFC function call."""
        logger.debug(f"Mock RFC call: {function_name}({kwargs})")

        # Route to mock handlers
        handlers = {
            "RFC_PING": self._mock_ping,
            "RFC_SYSTEM_INFO": self._mock_system_info,
            "RFC_READ_TABLE": self._mock_read_table,
            "BAPI_USER_GET_DETAIL": self._mock_user_detail,
            "BAPI_USER_GETLIST": self._mock_user_list,
            "BAPI_USER_LOCK": self._mock_user_lock,
            "BAPI_USER_UNLOCK": self._mock_user_unlock,
            "PRGN_GET_USERS_FOR_ROLE": self._mock_users_for_role,
            "PRGN_GET_AUTH_VALUES_FOR_ROLE": self._mock_auth_values,
            "RSAU_READ_LOG": self._mock_audit_log,
        }

        handler = handlers.get(function_name, self._mock_default)
        return handler(**kwargs)

    def close(self) -> None:
        """Close mock connection."""
        self._connected = False

    def _mock_ping(self, **kwargs) -> Dict:
        return {}

    def _mock_system_info(self, **kwargs) -> Dict:
        return {
            "RFCSI_EXPORT": {
                "RFCSYSID": "DEV",
                "RFCDBSYS": "HANA",
                "RFCHOST": "sapdev01",
                "RFCOPSYS": "Linux",
            }
        }

    def _mock_read_table(self, **kwargs) -> Dict:
        """Mock RFC_READ_TABLE for various SAP tables."""
        table = kwargs.get("QUERY_TABLE", "")
        fields = kwargs.get("FIELDS", [])
        options = kwargs.get("OPTIONS", [])

        # Return mock data based on table
        if table == "USR02":
            return self._mock_usr02_data(fields, options)
        elif table == "AGR_USERS":
            return self._mock_agr_users_data(fields, options)
        elif table == "AGR_DEFINE":
            return self._mock_agr_define_data(fields, options)
        elif table == "AGR_1251":
            return self._mock_agr_1251_data(fields, options)
        elif table == "CDHDR":
            return self._mock_cdhdr_data(fields, options)
        elif table == "CDPOS":
            return self._mock_cdpos_data(fields, options)
        elif table == "STAD":
            return self._mock_stad_data(fields, options)

        return {"DATA": [], "FIELDS": fields}

    def _mock_usr02_data(self, fields, options) -> Dict:
        """Mock USR02 (User Master) data."""
        return {
            "DATA": [
                {"WA": "FF_FIN_01|A|20240101|99991231|0|20240115|20240110"},
                {"WA": "FF_HR_01|A|20240101|99991231|64|20240110|20240105"},
                {"WA": "FF_MM_01|A|20240101|99991231|0|20240112|20240108"},
            ],
            "FIELDS": [
                {"FIELDNAME": "BNAME"},
                {"FIELDNAME": "USTYP"},
                {"FIELDNAME": "GLTGV"},
                {"FIELDNAME": "GLTGB"},
                {"FIELDNAME": "UFLAG"},
                {"FIELDNAME": "LAST_LOGON"},
                {"FIELDNAME": "TRDAT"},
            ]
        }

    def _mock_agr_users_data(self, fields, options) -> Dict:
        """Mock AGR_USERS (Role Assignment) data."""
        return {
            "DATA": [
                {"WA": "FF_FIN_01|SAP_ALL|20240101|99991231|"},
                {"WA": "FF_FIN_01|Z_FF_FINANCE|20240101|99991231|"},
                {"WA": "FF_HR_01|SAP_ALL|20240101|99991231|"},
            ],
            "FIELDS": [
                {"FIELDNAME": "UNAME"},
                {"FIELDNAME": "AGR_NAME"},
                {"FIELDNAME": "FROM_DAT"},
                {"FIELDNAME": "TO_DAT"},
                {"FIELDNAME": "ORG_FLAG"},
            ]
        }

    def _mock_agr_define_data(self, fields, options) -> Dict:
        """Mock AGR_DEFINE (Role Definition) data."""
        return {
            "DATA": [
                {"WA": "SAP_ALL|SAP_ALL|S|"},
                {"WA": "Z_FF_FINANCE|Z_FF_FINANCE|S|Firefighter Finance Role"},
                {"WA": "Z_FF_HR|Z_FF_HR|S|Firefighter HR Role"},
            ],
            "FIELDS": [
                {"FIELDNAME": "AGR_NAME"},
                {"FIELDNAME": "AGR_TITLE"},
                {"FIELDNAME": "AGR_TYPE"},
                {"FIELDNAME": "AGR_TEXT"},
            ]
        }

    def _mock_agr_1251_data(self, fields, options) -> Dict:
        """Mock AGR_1251 (Authorization Content) data."""
        return {
            "DATA": [
                {"WA": "SAP_ALL|S_TCODE|TCD|*|"},
                {"WA": "SAP_ALL|S_TABU_DIS|ACTVT|03|"},
                {"WA": "Z_FF_FINANCE|S_TCODE|TCD|FB01|"},
                {"WA": "Z_FF_FINANCE|S_TCODE|TCD|FB02|"},
                {"WA": "Z_FF_FINANCE|F_BKPF_BUK|BUKRS|1000|"},
            ],
            "FIELDS": [
                {"FIELDNAME": "AGR_NAME"},
                {"FIELDNAME": "OBJECT"},
                {"FIELDNAME": "FIELD"},
                {"FIELDNAME": "LOW"},
                {"FIELDNAME": "HIGH"},
            ]
        }

    def _mock_cdhdr_data(self, fields, options) -> Dict:
        """Mock CDHDR (Change Document Header) data."""
        return {
            "DATA": [
                {"WA": "USER|FF_HR_01|FF_FIN_01|20240115|120530|0000001234"},
                {"WA": "ROLE|Z_FF_TEST|FF_FIN_01|20240115|143022|0000001235"},
            ],
            "FIELDS": [
                {"FIELDNAME": "OBJECTCLAS"},
                {"FIELDNAME": "OBJECTID"},
                {"FIELDNAME": "USERNAME"},
                {"FIELDNAME": "UDATE"},
                {"FIELDNAME": "UTIME"},
                {"FIELDNAME": "CHANGENR"},
            ]
        }

    def _mock_cdpos_data(self, fields, options) -> Dict:
        """Mock CDPOS (Change Document Items) data."""
        return {
            "DATA": [
                {"WA": "0000001234|USLOCK|0|64"},
                {"WA": "0000001235|AGR_TEXT|Old Text|New Description"},
            ],
            "FIELDS": [
                {"FIELDNAME": "CHANGENR"},
                {"FIELDNAME": "FNAME"},
                {"FIELDNAME": "VALUE_OLD"},
                {"FIELDNAME": "VALUE_NEW"},
            ]
        }

    def _mock_stad_data(self, fields, options) -> Dict:
        """Mock STAD (Transaction Usage) data."""
        return {
            "DATA": [
                {"WA": "FF_FIN_01|FB01|SAPMF05A|20240115|100523|1250|"},
                {"WA": "FF_FIN_01|FB02|SAPMF05A|20240115|100845|980|"},
                {"WA": "FF_FIN_01|SE16|RSE16000|20240115|101230|450|"},
                {"WA": "FF_FIN_01|SU01|SAPMSUU0|20240115|102015|2100|"},
            ],
            "FIELDS": [
                {"FIELDNAME": "UNAME"},
                {"FIELDNAME": "TCODE"},
                {"FIELDNAME": "REPORT"},
                {"FIELDNAME": "DATUM"},
                {"FIELDNAME": "UZEIT"},
                {"FIELDNAME": "DURATION"},
                {"FIELDNAME": "RFC_CALL"},
            ]
        }

    def _mock_user_detail(self, **kwargs) -> Dict:
        """Mock BAPI_USER_GET_DETAIL."""
        username = kwargs.get("USERNAME", "")
        return {
            "ADDRESS": {
                "FIRSTNAME": "Firefighter",
                "LASTNAME": username,
                "E_MAIL": f"{username.lower()}@example.com",
                "DEPARTMENT": "IT Security",
            },
            "LOGONDATA": {
                "USTYP": "A",
                "GLTGV": "20240101",
                "GLTGB": "99991231",
                "UFLAG": "0" if "FIN" in username else "64",
                "TRDAT": "20240115",
            },
            "ACTIVITYGROUPS": [
                {"AGR_NAME": "SAP_ALL", "FROM_DAT": "20240101", "TO_DAT": "99991231"},
            ],
            "PROFILES": [],
            "RETURN": [],
        }

    def _mock_user_list(self, **kwargs) -> Dict:
        """Mock BAPI_USER_GETLIST."""
        return {
            "USERLIST": [
                {"USERNAME": "FF_FIN_01", "FULLNAME": "Firefighter Finance 01"},
                {"USERNAME": "FF_HR_01", "FULLNAME": "Firefighter HR 01"},
                {"USERNAME": "FF_MM_01", "FULLNAME": "Firefighter MM 01"},
            ]
        }

    def _mock_user_lock(self, **kwargs) -> Dict:
        return {"RETURN": [{"TYPE": "S", "MESSAGE": "User locked"}]}

    def _mock_user_unlock(self, **kwargs) -> Dict:
        return {"RETURN": [{"TYPE": "S", "MESSAGE": "User unlocked"}]}

    def _mock_users_for_role(self, **kwargs) -> Dict:
        """Mock PRGN_GET_USERS_FOR_ROLE."""
        return {
            "USERLIST": [
                {"BNAME": "FF_FIN_01"},
                {"BNAME": "FF_HR_01"},
            ]
        }

    def _mock_auth_values(self, **kwargs) -> Dict:
        """Mock PRGN_GET_AUTH_VALUES_FOR_ROLE."""
        return {
            "AUTH_VALUES": [
                {"OBJECT": "S_TCODE", "FIELD": "TCD", "LOW": "*"},
                {"OBJECT": "S_TABU_DIS", "FIELD": "ACTVT", "LOW": "03"},
            ]
        }

    def _mock_audit_log(self, **kwargs) -> Dict:
        """Mock RSAU_READ_LOG (Security Audit Log)."""
        return {
            "LOG_DATA": [
                {
                    "USER": "FF_FIN_01",
                    "AUDIT_CLASS": "LOGON",
                    "EVENT": "AU1",
                    "DATE": "20240115",
                    "TIME": "100000",
                    "TERMINAL": "192.168.1.100",
                    "MESSAGE": "Logon successful",
                },
                {
                    "USER": "FF_FIN_01",
                    "AUDIT_CLASS": "LOGOFF",
                    "EVENT": "AU2",
                    "DATE": "20240115",
                    "TIME": "140000",
                    "TERMINAL": "192.168.1.100",
                    "MESSAGE": "Logoff",
                },
            ]
        }

    def _mock_default(self, **kwargs) -> Dict:
        """Default mock handler for unknown functions."""
        logger.warning(f"No mock handler for RFC function, returning empty result")
        return {}
