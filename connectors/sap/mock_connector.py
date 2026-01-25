"""
SAP Mock Connector

A mock connector for development and testing without actual SAP connectivity.
Simulates SAP system responses for user, role, and authorization data.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random
import logging

from ..base import BaseConnector, ConnectionConfig, ConnectorFactory
from core.rules.models import Entitlement

logger = logging.getLogger(__name__)


class SAPMockConnector(BaseConnector):
    """
    Mock SAP connector for testing and development.

    Provides realistic sample data for:
    - Users with various risk profiles
    - Roles with different authorization levels
    - Entitlements that trigger SoD violations
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._initialize_mock_data()

    def _initialize_mock_data(self):
        """Initialize mock SAP data"""

        # Sample users with different risk profiles
        self.mock_users = {
            'JSMITH': {
                'user_id': 'JSMITH',
                'username': 'JSMITH',
                'full_name': 'John Smith',
                'email': 'john.smith@company.com',
                'department': 'Finance',
                'function': 'Accounts Payable Manager',
                'user_type': 'A',  # Dialog user
                'cost_center': 'CC1000',
                'company_code': '1000',
                'roles': ['Z_AP_MANAGER', 'Z_VENDOR_MAINT', 'Z_PAYMENT_RUN'],
                'profiles': [],
                'valid_from': '20200101',
                'valid_to': '99991231',
                'last_login': datetime.now().strftime('%Y%m%d'),
                'lock_status': 0
            },
            'MBROWN': {
                'user_id': 'MBROWN',
                'username': 'MBROWN',
                'full_name': 'Mary Brown',
                'email': 'mary.brown@company.com',
                'department': 'Procurement',
                'function': 'Procurement Specialist',
                'user_type': 'A',
                'cost_center': 'CC2000',
                'company_code': '1000',
                'roles': ['Z_PURCHASER', 'Z_GR_CLERK'],
                'profiles': [],
                'valid_from': '20210301',
                'valid_to': '99991231',
                'last_login': datetime.now().strftime('%Y%m%d'),
                'lock_status': 0
            },
            'TDAVIS': {
                'user_id': 'TDAVIS',
                'username': 'TDAVIS',
                'full_name': 'Tom Davis',
                'email': 'tom.davis@company.com',
                'department': 'IT',
                'function': 'SAP Basis Admin',
                'user_type': 'A',
                'cost_center': 'CC3000',
                'company_code': '1000',
                'roles': ['Z_BASIS_ADMIN', 'Z_USER_ADMIN'],
                'profiles': ['SAP_ALL'],  # High privilege!
                'valid_from': '20190601',
                'valid_to': '99991231',
                'last_login': datetime.now().strftime('%Y%m%d'),
                'lock_status': 0
            },
            'AWILSON': {
                'user_id': 'AWILSON',
                'username': 'AWILSON',
                'full_name': 'Alice Wilson',
                'email': 'alice.wilson@company.com',
                'department': 'HR',
                'function': 'HR Specialist',
                'user_type': 'A',
                'cost_center': 'CC4000',
                'company_code': '1000',
                'roles': ['Z_HR_SPECIALIST', 'Z_PAYROLL_RUN'],  # Potential SoD!
                'profiles': [],
                'valid_from': '20220101',
                'valid_to': '99991231',
                'last_login': datetime.now().strftime('%Y%m%d'),
                'lock_status': 0
            },
            'FF_EMERGENCY_01': {
                'user_id': 'FF_EMERGENCY_01',
                'username': 'FF_EMERGENCY_01',
                'full_name': 'Firefighter Account 01',
                'email': 'firefighter@company.com',
                'department': 'IT',
                'function': 'Emergency Access',
                'user_type': 'S',  # Service user
                'cost_center': 'CC3000',
                'company_code': '1000',
                'roles': ['Z_FIREFIGHTER_FULL'],
                'profiles': ['SAP_ALL'],
                'valid_from': '20200101',
                'valid_to': '99991231',
                'last_login': '00000000',  # Never logged in
                'lock_status': 64  # Initially locked
            }
        }

        # Mock roles with their authorizations
        self.mock_roles = {
            'Z_AP_MANAGER': {
                'role_name': 'Z_AP_MANAGER',
                'description': 'Accounts Payable Manager Role',
                'transactions': [
                    {'tcode': 'FB60', 'text': 'Enter Incoming Invoices'},
                    {'tcode': 'FBL1N', 'text': 'Vendor Line Items'},
                    {'tcode': 'FK03', 'text': 'Display Vendor'},
                ],
                'authorizations': [
                    {'auth_object': 'F_BKPF_BUK', 'field': 'BUKRS', 'values': ['1000', '2000']},
                    {'auth_object': 'F_BKPF_BUK', 'field': 'ACTVT', 'values': ['01', '02', '03']},
                ]
            },
            'Z_VENDOR_MAINT': {
                'role_name': 'Z_VENDOR_MAINT',
                'description': 'Vendor Master Maintenance',
                'transactions': [
                    {'tcode': 'XK01', 'text': 'Create Vendor (Central)'},
                    {'tcode': 'XK02', 'text': 'Change Vendor (Central)'},
                    {'tcode': 'FK01', 'text': 'Create Vendor'},
                    {'tcode': 'FK02', 'text': 'Change Vendor'},
                ],
                'authorizations': [
                    {'auth_object': 'F_LFA1_BUK', 'field': 'BUKRS', 'values': ['1000']},
                    {'auth_object': 'F_LFA1_BUK', 'field': 'ACTVT', 'values': ['01', '02']},
                ]
            },
            'Z_PAYMENT_RUN': {
                'role_name': 'Z_PAYMENT_RUN',
                'description': 'Payment Execution Role',
                'transactions': [
                    {'tcode': 'F110', 'text': 'Automatic Payment Program'},
                    {'tcode': 'F-53', 'text': 'Post Outgoing Payment'},
                    {'tcode': 'F-58', 'text': 'Payment with Printout'},
                ],
                'authorizations': [
                    {'auth_object': 'F_REGU_BUK', 'field': 'BUKRS', 'values': ['1000']},
                    {'auth_object': 'F_REGU_BUK', 'field': 'ACTVT', 'values': ['01']},
                ]
            },
            'Z_PURCHASER': {
                'role_name': 'Z_PURCHASER',
                'description': 'Purchasing Role',
                'transactions': [
                    {'tcode': 'ME21N', 'text': 'Create Purchase Order'},
                    {'tcode': 'ME22N', 'text': 'Change Purchase Order'},
                    {'tcode': 'ME23N', 'text': 'Display Purchase Order'},
                ],
                'authorizations': [
                    {'auth_object': 'M_BEST_EKO', 'field': 'EKORG', 'values': ['1000']},
                    {'auth_object': 'M_BEST_EKO', 'field': 'ACTVT', 'values': ['01', '02', '03']},
                ]
            },
            'Z_GR_CLERK': {
                'role_name': 'Z_GR_CLERK',
                'description': 'Goods Receipt Clerk',
                'transactions': [
                    {'tcode': 'MIGO', 'text': 'Goods Movement'},
                    {'tcode': 'MB01', 'text': 'Post Goods Receipt for PO'},
                    {'tcode': 'MB03', 'text': 'Display Material Document'},
                ],
                'authorizations': [
                    {'auth_object': 'M_MSEG_WMB', 'field': 'WERKS', 'values': ['1000']},
                    {'auth_object': 'M_MSEG_WMB', 'field': 'ACTVT', 'values': ['01', '03']},
                ]
            },
            'Z_HR_SPECIALIST': {
                'role_name': 'Z_HR_SPECIALIST',
                'description': 'HR Master Data Specialist',
                'transactions': [
                    {'tcode': 'PA30', 'text': 'Maintain HR Master Data'},
                    {'tcode': 'PA20', 'text': 'Display HR Master Data'},
                ],
                'authorizations': [
                    {'auth_object': 'P_ORGIN', 'field': 'INFTY', 'values': ['0001', '0002', '0006', '0009']},
                    {'auth_object': 'P_ORGIN', 'field': 'AUTHC', 'values': ['R', 'W']},
                ]
            },
            'Z_PAYROLL_RUN': {
                'role_name': 'Z_PAYROLL_RUN',
                'description': 'Payroll Processing Role',
                'transactions': [
                    {'tcode': 'PC00_M99_CALC', 'text': 'Payroll Run'},
                    {'tcode': 'PC00_M99_CIPE', 'text': 'Payroll Posting'},
                ],
                'authorizations': [
                    {'auth_object': 'P_PYEVDOC', 'field': 'ACTVT', 'values': ['01', '02']},
                ]
            },
            'Z_BASIS_ADMIN': {
                'role_name': 'Z_BASIS_ADMIN',
                'description': 'Basis Administration',
                'transactions': [
                    {'tcode': 'SM21', 'text': 'System Log'},
                    {'tcode': 'SM37', 'text': 'Job Overview'},
                    {'tcode': 'SE16N', 'text': 'Table Display'},  # Sensitive!
                    {'tcode': 'SE11', 'text': 'Data Dictionary'},
                ],
                'authorizations': [
                    {'auth_object': 'S_TABU_DIS', 'field': 'ACTVT', 'values': ['02', '03']},
                    {'auth_object': 'S_DEVELOP', 'field': 'ACTVT', 'values': ['01', '02', '03']},
                ]
            },
            'Z_USER_ADMIN': {
                'role_name': 'Z_USER_ADMIN',
                'description': 'User Administration',
                'transactions': [
                    {'tcode': 'SU01', 'text': 'User Maintenance'},
                    {'tcode': 'SU10', 'text': 'Mass User Maintenance'},
                    {'tcode': 'PFCG', 'text': 'Role Maintenance'},
                ],
                'authorizations': [
                    {'auth_object': 'S_USER_GRP', 'field': 'ACTVT', 'values': ['01', '02', '03', '05', '22']},
                    {'auth_object': 'S_USER_AGR', 'field': 'ACTVT', 'values': ['01', '02', '22']},
                ]
            },
            'Z_FIREFIGHTER_FULL': {
                'role_name': 'Z_FIREFIGHTER_FULL',
                'description': 'Full Emergency Access Role',
                'transactions': [
                    {'tcode': '*', 'text': 'All Transactions'}
                ],
                'authorizations': [
                    {'auth_object': 'S_TCODE', 'field': 'TCD', 'values': ['*']},
                ]
            }
        }

    def connect(self) -> bool:
        """Simulate connection"""
        self.connected = True
        logger.info(f"Mock SAP connector initialized for {self.config.name}")
        return True

    def disconnect(self) -> bool:
        """Simulate disconnection"""
        self.connected = False
        return True

    def test_connection(self) -> Dict[str, Any]:
        """Return mock connection test results"""
        return {
            "status": "success",
            "system_id": "DEV",
            "database": "HANA",
            "client": self.config.sap_client or "100",
            "host": self.config.host,
            "mode": "MOCK"
        }

    def get_users(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get mock user list"""
        users = []
        for user_id, user_data in self.mock_users.items():
            users.append({
                'user_id': user_data['user_id'],
                'full_name': user_data['full_name'],
                'system': self.config.name
            })
        return users

    def get_user_details(self, user_id: str) -> Dict:
        """Get mock user details"""
        if user_id not in self.mock_users:
            raise ValueError(f"User {user_id} not found")
        return self.mock_users[user_id].copy()

    def get_roles(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get mock role list"""
        roles = []
        for role_name, role_data in self.mock_roles.items():
            roles.append({
                'role_name': role_name,
                'description': role_data['description']
            })
        return roles

    def get_role_details(self, role_id: str) -> Dict:
        """Get mock role details"""
        if role_id not in self.mock_roles:
            raise ValueError(f"Role {role_id} not found")
        return self.mock_roles[role_id].copy()

    def get_user_entitlements(self, user_id: str) -> List[Dict]:
        """Get all entitlements for a mock user"""
        if user_id not in self.mock_users:
            raise ValueError(f"User {user_id} not found")

        user = self.mock_users[user_id]
        entitlements = []

        # Collect entitlements from all user's roles
        for role_name in user.get('roles', []):
            if role_name in self.mock_roles:
                role = self.mock_roles[role_name]

                # Add transaction authorizations
                for tcode in role.get('transactions', []):
                    entitlements.append({
                        'auth_object': 'S_TCODE',
                        'field': 'TCD',
                        'value': tcode['tcode'],
                        'source_role': role_name,
                        'system': self.config.name
                    })

                # Add other authorizations
                for auth in role.get('authorizations', []):
                    for value in auth.get('values', []):
                        entitlements.append({
                            'auth_object': auth['auth_object'],
                            'field': auth.get('field', 'VALUE'),
                            'value': value,
                            'source_role': role_name,
                            'system': self.config.name
                        })

        return entitlements

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

    def check_firefighter_availability(self, firefighter_id: str) -> Dict:
        """Check mock firefighter availability"""
        if firefighter_id not in self.mock_users:
            return {
                'firefighter_id': firefighter_id,
                'available': False,
                'error': 'Firefighter ID not found'
            }

        user = self.mock_users[firefighter_id]
        is_locked = user.get('lock_status', 0) != 0

        return {
            'firefighter_id': firefighter_id,
            'available': not is_locked,
            'is_locked': is_locked,
            'is_valid': True,
            'user_type': user.get('user_type'),
            'last_login': user.get('last_login')
        }

    def unlock_firefighter(self, firefighter_id: str) -> Dict:
        """Unlock mock firefighter"""
        if firefighter_id in self.mock_users:
            self.mock_users[firefighter_id]['lock_status'] = 0
            return {
                'success': True,
                'message': 'User unlocked successfully',
                'firefighter_id': firefighter_id
            }
        return {
            'success': False,
            'message': 'User not found',
            'firefighter_id': firefighter_id
        }

    def lock_firefighter(self, firefighter_id: str) -> Dict:
        """Lock mock firefighter"""
        if firefighter_id in self.mock_users:
            self.mock_users[firefighter_id]['lock_status'] = 64
            return {
                'success': True,
                'message': 'User locked successfully',
                'firefighter_id': firefighter_id
            }
        return {
            'success': False,
            'message': 'User not found',
            'firefighter_id': firefighter_id
        }


# Register with factory
ConnectorFactory.register('sap_mock', SAPMockConnector)
