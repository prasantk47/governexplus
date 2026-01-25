"""
SAP RFC Connector

Connects to SAP systems via RFC (Remote Function Call) using pyrfc library.
Requires SAP NW RFC SDK to be installed on the system.

Key capabilities:
- User and role management
- Authorization data extraction
- Transaction usage monitoring
- Emergency access provisioning
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from ..base import BaseConnector, ConnectionConfig, ConnectionType, ConnectorFactory
from core.rules.models import Entitlement

logger = logging.getLogger(__name__)

# Try to import pyrfc, handle if not installed
try:
    from pyrfc import Connection as RFCConnection
    HAS_PYRFC = True
except ImportError:
    HAS_PYRFC = False
    logger.warning("pyrfc not installed. SAP RFC connection will not be available. "
                   "Install SAP NW RFC SDK and pyrfc for full functionality.")


class SAPRFCConnector(BaseConnector):
    """
    SAP RFC Connector for direct system access.

    This connector uses pyrfc to make RFC calls to SAP systems.
    It can extract user data, roles, authorizations, and manage
    emergency (firefighter) access.
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)

        if not HAS_PYRFC:
            raise ImportError(
                "pyrfc library is not installed. "
                "Please install SAP NW RFC SDK and pyrfc package."
            )

        self.rfc_params = {
            'ashost': config.host,
            'sysnr': config.sap_sysnr or '00',
            'client': config.sap_client or '100',
            'user': config.username,
            'passwd': config.password,
            'lang': config.sap_language or 'EN'
        }

        # Add optional parameters
        if config.extra_params.get('saprouter'):
            self.rfc_params['saprouter'] = config.extra_params['saprouter']
        if config.extra_params.get('mshost'):
            # Message server for load balancing
            self.rfc_params['mshost'] = config.extra_params['mshost']
            self.rfc_params['group'] = config.extra_params.get('group', 'PUBLIC')

    def connect(self) -> bool:
        """Establish RFC connection to SAP"""
        try:
            self.connection = RFCConnection(**self.rfc_params)
            self.connected = True
            logger.info(f"Connected to SAP system {self.config.host}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SAP: {e}")
            self.connected = False
            raise

    def disconnect(self) -> bool:
        """Close RFC connection"""
        try:
            if self.connection:
                self.connection.close()
            self.connected = False
            return True
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            return False

    def test_connection(self) -> Dict[str, Any]:
        """Test SAP connection by calling RFC_PING"""
        if not self.connected:
            self.connect()

        try:
            # Simple ping to verify connection
            self.connection.call('RFC_PING')

            # Get system info
            system_info = self.connection.call('RFC_SYSTEM_INFO')

            return {
                "status": "success",
                "system_id": system_info.get('RFCSI_EXPORT', {}).get('RFCSYSID', 'Unknown'),
                "database": system_info.get('RFCSI_EXPORT', {}).get('RFCDBSYS', 'Unknown'),
                "client": self.rfc_params['client'],
                "host": self.config.host
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def get_users(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get list of users from SAP.

        Args:
            filters: Optional dict with keys like 'username_pattern', 'user_type', etc.
        """
        if not self.connected:
            self.connect()

        users = []
        filters = filters or {}

        try:
            # Use BAPI to get user list
            username_pattern = filters.get('username_pattern', '*')

            result = self.connection.call(
                'BAPI_USER_GETLIST',
                MAX_ROWS=filters.get('max_rows', 1000),
                SELECTION_RANGE=[{
                    'PARAMETER': 'USERNAME',
                    'SIGN': 'I',
                    'OPTION': 'CP',
                    'LOW': username_pattern
                }]
            )

            for user_entry in result.get('USERLIST', []):
                users.append({
                    'user_id': user_entry.get('USERNAME'),
                    'full_name': user_entry.get('FULLNAME', ''),
                    'system': self.config.name
                })

            return users

        except Exception as e:
            logger.error(f"Error getting users: {e}")
            raise

    def get_user_details(self, user_id: str) -> Dict:
        """Get detailed user information from SAP"""
        if not self.connected:
            self.connect()

        try:
            result = self.connection.call(
                'BAPI_USER_GET_DETAIL',
                USERNAME=user_id,
                CACHE_RESULTS='X'
            )

            # Check for errors
            if result.get('RETURN', []):
                for msg in result['RETURN']:
                    if msg.get('TYPE') == 'E':
                        raise ValueError(f"SAP Error: {msg.get('MESSAGE')}")

            # Extract user details
            address = result.get('ADDRESS', {})
            logon_data = result.get('LOGONDATA', {})
            defaults = result.get('DEFAULTS', {})

            # Get roles
            roles = [
                {
                    'role_name': role.get('AGR_NAME'),
                    'from_date': role.get('FROM_DAT'),
                    'to_date': role.get('TO_DAT'),
                    'org_flag': role.get('ORG_FLAG')
                }
                for role in result.get('ACTIVITYGROUPS', [])
            ]

            # Get profiles
            profiles = [
                {
                    'profile_name': profile.get('BAESSION'),
                    'profile_text': profile.get('BAPIPTEXT')
                }
                for profile in result.get('PROFILES', [])
            ]

            return {
                'user_id': user_id,
                'username': user_id,
                'full_name': f"{address.get('FIRSTNAME', '')} {address.get('LASTNAME', '')}".strip(),
                'email': address.get('E_MAIL', ''),
                'department': address.get('DEPARTMENT', ''),
                'function': address.get('FUNCTION', ''),
                'user_type': logon_data.get('USTYP', ''),
                'valid_from': logon_data.get('GLTGV'),
                'valid_to': logon_data.get('GLTGB'),
                'last_login': logon_data.get('TRDAT'),
                'lock_status': logon_data.get('UFLAG', 0),
                'roles': roles,
                'profiles': profiles,
                'cost_center': defaults.get('KOSTL', ''),
                'company_code': defaults.get('BUKRS', '')
            }

        except Exception as e:
            logger.error(f"Error getting user details for {user_id}: {e}")
            raise

    def get_roles(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get list of roles from SAP"""
        if not self.connected:
            self.connect()

        try:
            filters = filters or {}
            role_pattern = filters.get('role_pattern', '*')

            # Read from AGR_DEFINE table
            result = self.connection.call(
                'RFC_READ_TABLE',
                QUERY_TABLE='AGR_DEFINE',
                DELIMITER='|',
                OPTIONS=[{
                    'TEXT': f"AGR_NAME LIKE '{role_pattern}'"
                }],
                FIELDS=[
                    {'FIELDNAME': 'AGR_NAME'},
                    {'FIELDNAME': 'PARENT_AGR'},
                    {'FIELDNAME': 'CREATE_USR'},
                    {'FIELDNAME': 'CREATE_DAT'}
                ],
                ROWCOUNT=filters.get('max_rows', 1000)
            )

            roles = []
            for row in result.get('DATA', []):
                values = row.get('WA', '').split('|')
                if len(values) >= 4:
                    roles.append({
                        'role_name': values[0].strip(),
                        'parent_role': values[1].strip(),
                        'created_by': values[2].strip(),
                        'created_date': values[3].strip()
                    })

            return roles

        except Exception as e:
            logger.error(f"Error getting roles: {e}")
            raise

    def get_role_details(self, role_id: str) -> Dict:
        """Get detailed role information including transactions and authorizations"""
        if not self.connected:
            self.connect()

        try:
            # Get role menu (transactions)
            menu_result = self.connection.call(
                'PRGN_GET_MENU_FROM_ROLE',
                ROLE_NAME=role_id
            )

            transactions = []
            for menu_item in menu_result.get('MENU', []):
                if menu_item.get('ITEM_TYPE') == 'T':  # Transaction
                    transactions.append({
                        'tcode': menu_item.get('ITEM_ID'),
                        'text': menu_item.get('ITEM_TEXT')
                    })

            # Get authorization data
            auth_result = self.connection.call(
                'PRGN_GET_AUTHORIZATIONS',
                ROLE_NAME=role_id
            )

            authorizations = []
            for auth in auth_result.get('AUTHORIZATIONS', []):
                authorizations.append({
                    'auth_object': auth.get('OBJECT'),
                    'field': auth.get('AUTH'),
                    'values': auth.get('VALUE', [])
                })

            # Get role text
            text_result = self.connection.call(
                'RFC_READ_TABLE',
                QUERY_TABLE='AGR_TEXTS',
                DELIMITER='|',
                OPTIONS=[{
                    'TEXT': f"AGR_NAME = '{role_id}' AND SPRAS = 'E'"
                }],
                FIELDS=[
                    {'FIELDNAME': 'TEXT'}
                ]
            )

            description = ''
            if text_result.get('DATA'):
                description = text_result['DATA'][0].get('WA', '').strip()

            return {
                'role_name': role_id,
                'description': description,
                'transactions': transactions,
                'authorizations': authorizations,
                'transaction_count': len(transactions),
                'auth_object_count': len(set(a['auth_object'] for a in authorizations))
            }

        except Exception as e:
            logger.error(f"Error getting role details for {role_id}: {e}")
            raise

    def get_user_entitlements(self, user_id: str) -> List[Dict]:
        """
        Get all entitlements (authorizations) for a user.

        This aggregates authorizations from all roles and profiles.
        Returns list of Entitlement-compatible dicts.
        """
        if not self.connected:
            self.connect()

        try:
            entitlements = []

            # Get user's roles first
            user_details = self.get_user_details(user_id)

            # For each role, get authorizations
            for role in user_details.get('roles', []):
                role_name = role.get('role_name')

                try:
                    role_details = self.get_role_details(role_name)

                    # Add transaction authorizations
                    for tcode in role_details.get('transactions', []):
                        entitlements.append({
                            'auth_object': 'S_TCODE',
                            'field': 'TCD',
                            'value': tcode['tcode'],
                            'source_role': role_name,
                            'system': self.config.name
                        })

                    # Add other authorizations
                    for auth in role_details.get('authorizations', []):
                        for value in auth.get('values', [auth.get('field')]):
                            entitlements.append({
                                'auth_object': auth['auth_object'],
                                'field': auth.get('field', 'VALUE'),
                                'value': value,
                                'source_role': role_name,
                                'system': self.config.name
                            })

                except Exception as role_error:
                    logger.warning(f"Could not get details for role {role_name}: {role_error}")

            return entitlements

        except Exception as e:
            logger.error(f"Error getting entitlements for {user_id}: {e}")
            raise

    def get_user_entitlements_as_objects(self, user_id: str) -> List[Entitlement]:
        """Get entitlements as Entitlement objects for rule engine"""
        raw_entitlements = self.get_user_entitlements(user_id)

        return [
            Entitlement(
                auth_object=e['auth_object'],
                field=e['field'],
                value=e['value'],
                system=e.get('system', 'SAP'),
                attributes={'source_role': e.get('source_role')}
            )
            for e in raw_entitlements
        ]

    # ==========================================================================
    # Firefighter / Emergency Access Methods
    # ==========================================================================

    def check_firefighter_availability(self, firefighter_id: str) -> Dict:
        """Check if a firefighter ID is available for use"""
        if not self.connected:
            self.connect()

        try:
            # Get firefighter user status
            user_details = self.get_user_details(firefighter_id)

            # Check lock status
            is_locked = user_details.get('lock_status', 0) != 0
            is_valid = True

            # Check validity dates
            valid_to = user_details.get('valid_to')
            if valid_to and valid_to != '00000000':
                try:
                    valid_date = datetime.strptime(valid_to, '%Y%m%d')
                    is_valid = valid_date >= datetime.now()
                except ValueError:
                    pass

            return {
                'firefighter_id': firefighter_id,
                'available': not is_locked and is_valid,
                'is_locked': is_locked,
                'is_valid': is_valid,
                'user_type': user_details.get('user_type'),
                'last_login': user_details.get('last_login')
            }

        except Exception as e:
            logger.error(f"Error checking firefighter {firefighter_id}: {e}")
            return {
                'firefighter_id': firefighter_id,
                'available': False,
                'error': str(e)
            }

    def unlock_firefighter(self, firefighter_id: str) -> Dict:
        """Unlock a firefighter ID for use"""
        if not self.connected:
            self.connect()

        try:
            result = self.connection.call(
                'BAPI_USER_UNLOCK',
                USERNAME=firefighter_id
            )

            # Check return
            success = True
            message = "User unlocked successfully"

            for msg in result.get('RETURN', []):
                if msg.get('TYPE') == 'E':
                    success = False
                    message = msg.get('MESSAGE')

            return {
                'success': success,
                'message': message,
                'firefighter_id': firefighter_id
            }

        except Exception as e:
            logger.error(f"Error unlocking firefighter {firefighter_id}: {e}")
            raise

    def lock_firefighter(self, firefighter_id: str) -> Dict:
        """Lock a firefighter ID after use"""
        if not self.connected:
            self.connect()

        try:
            result = self.connection.call(
                'BAPI_USER_LOCK',
                USERNAME=firefighter_id
            )

            success = True
            message = "User locked successfully"

            for msg in result.get('RETURN', []):
                if msg.get('TYPE') == 'E':
                    success = False
                    message = msg.get('MESSAGE')

            return {
                'success': success,
                'message': message,
                'firefighter_id': firefighter_id
            }

        except Exception as e:
            logger.error(f"Error locking firefighter {firefighter_id}: {e}")
            raise

    def set_temporary_password(self, user_id: str, password: str) -> Dict:
        """Set temporary password for firefighter access"""
        if not self.connected:
            self.connect()

        try:
            result = self.connection.call(
                'BAPI_USER_CHANGE',
                USERNAME=user_id,
                PASSWORD={'BAPIPWD': password},
                PASSWORDX={'BAPIPWD': 'X'}
            )

            success = True
            message = "Password changed successfully"

            for msg in result.get('RETURN', []):
                if msg.get('TYPE') == 'E':
                    success = False
                    message = msg.get('MESSAGE')

            return {
                'success': success,
                'message': message
            }

        except Exception as e:
            logger.error(f"Error setting password for {user_id}: {e}")
            raise

    def get_transaction_usage(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get transaction usage history for a user (from SM21/STAD logs)"""
        if not self.connected:
            self.connect()

        try:
            # This would typically query STAD or custom logging tables
            # The exact implementation depends on available FMs and custom Z* functions

            from_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            to_date = datetime.now().strftime('%Y%m%d')

            # Example: reading from a usage log table
            # In practice, you might need a custom FM or read from CDHDR/CDPOS
            result = self.connection.call(
                'RFC_READ_TABLE',
                QUERY_TABLE='TSTCT',  # Transaction texts - just as example
                DELIMITER='|',
                ROWCOUNT=100
            )

            # Parse and return
            # This is simplified - real implementation would use actual log tables

            return []  # Placeholder

        except Exception as e:
            logger.error(f"Error getting transaction usage: {e}")
            return []


# Register with factory
ConnectorFactory.register('sap_rfc', SAPRFCConnector)
