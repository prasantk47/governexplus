import { useState, useMemo, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  ArrowLeftIcon,
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  InformationCircleIcon,
  ShieldExclamationIcon,
  PlusCircleIcon,
  PencilSquareIcon,
  TrashIcon,
  LockClosedIcon,
  LockOpenIcon,
  UserPlusIcon,
  ClockIcon,
  CalendarDaysIcon,
  MinusCircleIcon,
  DocumentDuplicateIcon,
  BuildingOfficeIcon,
  ServerStackIcon,
} from '@heroicons/react/24/outline';
import { REQUEST_TYPES, RequestType } from '../../config/roles';
import { provisioningApi, ConnectorStatus } from '../../services/provisioningApi';

interface RequestTypeOption {
  id: RequestType;
  name: string;
  description: string;
  icon: React.ForwardRefExoticComponent<React.SVGProps<SVGSVGElement>>;
  color: string;
}

const requestTypeOptions: RequestTypeOption[] = [
  {
    id: REQUEST_TYPES.NEW_ACCOUNT,
    name: 'New Account',
    description: 'Request a new account in a system with specific roles',
    icon: UserPlusIcon,
    color: 'bg-blue-100 text-blue-600',
  },
  {
    id: REQUEST_TYPES.CHANGE_ACCOUNT,
    name: 'Change Account',
    description: 'Modify roles or permissions on an existing account',
    icon: PencilSquareIcon,
    color: 'bg-yellow-100 text-yellow-600',
  },
  {
    id: REQUEST_TYPES.COPY_USER,
    name: 'Copy User',
    description: 'Create a new account by copying roles from an existing user',
    icon: DocumentDuplicateIcon,
    color: 'bg-purple-100 text-purple-600',
  },
  {
    id: REQUEST_TYPES.REMOVE_ACCOUNT,
    name: 'Remove Account',
    description: 'Delete or deactivate an existing account',
    icon: TrashIcon,
    color: 'bg-red-100 text-red-600',
  },
  {
    id: REQUEST_TYPES.LOCK_ACCOUNT,
    name: 'Lock Account',
    description: 'Temporarily disable an account (can be unlocked later)',
    icon: LockClosedIcon,
    color: 'bg-orange-100 text-orange-600',
  },
  {
    id: REQUEST_TYPES.UNLOCK_ACCOUNT,
    name: 'Unlock Account',
    description: 'Re-enable a previously locked account',
    icon: LockOpenIcon,
    color: 'bg-green-100 text-green-600',
  },
];

interface Role {
  id: string;
  name: string;
  description: string;
  system: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  sodConflicts: string[];
}

interface ExistingUserRole {
  id: string;
  roleId: string;
  roleName: string;
  system: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  assignedDate: string;
  validFrom: string;
  validTo: string | null;
  status: 'active' | 'expiring_soon' | 'expired';
  lastUsed?: string;
}

interface TargetSystem {
  id: string;
  name: string;
  type: string;
  connected: boolean;
}

interface UserProfile {
  userId: string;
  firstName: string;
  lastName: string;
  email: string;
  employeeId: string;
  department: string;
  costCenter: string;
  companyCode: string;
  manager: string;
  jobTitle: string;
  location: string;
}

// Mock users for source user search (Copy User)
const mockUsers = [
  { id: 'john.doe', name: 'John Doe', department: 'Finance', title: 'Senior Accountant' },
  { id: 'jane.smith', name: 'Jane Smith', department: 'Sales', title: 'Sales Manager' },
  { id: 'mike.wilson', name: 'Mike Wilson', department: 'IT', title: 'Developer' },
  { id: 'sarah.johnson', name: 'Sarah Johnson', department: 'HR', title: 'HR Specialist' },
  { id: 'david.brown', name: 'David Brown', department: 'Operations', title: 'Operations Lead' },
];

// Mock existing roles for the current user
const existingUserRoles: Record<string, ExistingUserRole[]> = {
  'john.doe': [
    {
      id: 'EUR-001',
      roleId: 'ROLE-001',
      roleName: 'SAP_MM_BUYER',
      system: 'SAP ECC',
      riskLevel: 'medium',
      assignedDate: '2024-01-15',
      validFrom: '2024-01-15',
      validTo: '2025-01-15',
      status: 'expiring_soon',
      lastUsed: '2025-01-10',
    },
    {
      id: 'EUR-002',
      roleId: 'ROLE-002',
      roleName: 'SAP_FI_AP_CLERK',
      system: 'SAP ECC',
      riskLevel: 'low',
      assignedDate: '2023-06-01',
      validFrom: '2023-06-01',
      validTo: null,
      status: 'active',
      lastUsed: '2025-01-12',
    },
    {
      id: 'EUR-003',
      roleId: 'ROLE-004',
      roleName: 'AWS_DEVELOPER',
      system: 'AWS',
      riskLevel: 'medium',
      assignedDate: '2024-03-20',
      validFrom: '2024-03-20',
      validTo: '2024-09-20',
      status: 'expired',
      lastUsed: '2024-09-15',
    },
  ],
  'jane.smith': [
    {
      id: 'EUR-004',
      roleId: 'ROLE-005',
      roleName: 'SALESFORCE_ADMIN',
      system: 'Salesforce',
      riskLevel: 'high',
      assignedDate: '2024-02-01',
      validFrom: '2024-02-01',
      validTo: null,
      status: 'active',
      lastUsed: '2025-01-14',
    },
    {
      id: 'EUR-005',
      roleId: 'ROLE-006',
      roleName: 'HR_EMPLOYEE_VIEWER',
      system: 'Workday',
      riskLevel: 'low',
      assignedDate: '2023-11-01',
      validFrom: '2023-11-01',
      validTo: '2025-11-01',
      status: 'active',
      lastUsed: '2025-01-08',
    },
  ],
  'current_user': [
    {
      id: 'EUR-006',
      roleId: 'ROLE-002',
      roleName: 'SAP_FI_AP_CLERK',
      system: 'SAP ECC',
      riskLevel: 'low',
      assignedDate: '2024-05-01',
      validFrom: '2024-05-01',
      validTo: null,
      status: 'active',
      lastUsed: '2025-01-15',
    },
    {
      id: 'EUR-007',
      roleId: 'ROLE-006',
      roleName: 'HR_EMPLOYEE_VIEWER',
      system: 'Workday',
      riskLevel: 'low',
      assignedDate: '2024-08-01',
      validFrom: '2024-08-01',
      validTo: '2025-08-01',
      status: 'active',
      lastUsed: '2025-01-10',
    },
  ],
};

const availableRoles: Role[] = [
  {
    id: 'ROLE-001',
    name: 'SAP_MM_BUYER',
    description: 'Procurement buyer role with purchase order creation',
    system: 'SAP ECC',
    riskLevel: 'medium',
    sodConflicts: [],
  },
  {
    id: 'ROLE-002',
    name: 'SAP_FI_AP_CLERK',
    description: 'Accounts payable processing clerk',
    system: 'SAP ECC',
    riskLevel: 'low',
    sodConflicts: [],
  },
  {
    id: 'ROLE-003',
    name: 'SAP_FI_GL_ACCOUNTANT',
    description: 'General ledger accounting and posting',
    system: 'SAP ECC',
    riskLevel: 'high',
    sodConflicts: ['Conflicts with SAP_FI_AP_CLERK - Create/Post GL Entry'],
  },
  {
    id: 'ROLE-004',
    name: 'AWS_DEVELOPER',
    description: 'AWS development access for cloud resources',
    system: 'AWS',
    riskLevel: 'medium',
    sodConflicts: [],
  },
  {
    id: 'ROLE-005',
    name: 'SALESFORCE_ADMIN',
    description: 'Salesforce administrator access',
    system: 'Salesforce',
    riskLevel: 'high',
    sodConflicts: [],
  },
  {
    id: 'ROLE-006',
    name: 'HR_EMPLOYEE_VIEWER',
    description: 'View employee records in Workday',
    system: 'Workday',
    riskLevel: 'low',
    sodConflicts: [],
  },
];

const riskConfig = {
  low: { color: 'bg-green-100 text-green-800', label: 'Low Risk' },
  medium: { color: 'bg-yellow-100 text-yellow-800', label: 'Medium Risk' },
  high: { color: 'bg-orange-100 text-orange-800', label: 'High Risk' },
  critical: { color: 'bg-red-100 text-red-800', label: 'Critical Risk' },
};

// Mock target systems
const defaultTargetSystems: TargetSystem[] = [
  { id: 'sap_ecc', name: 'SAP ECC', type: 'sap', connected: true },
  { id: 'aws_iam', name: 'AWS IAM', type: 'cloud', connected: true },
  { id: 'azure_ad', name: 'Azure AD', type: 'identity', connected: true },
  { id: 'workday', name: 'Workday', type: 'hr', connected: false },
  { id: 'salesforce', name: 'Salesforce', type: 'crm', connected: true },
];

export function NewAccessRequest() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [requestType, setRequestType] = useState<RequestType | null>(null);
  const [requestForOther, setRequestForOther] = useState(false);
  const [targetUser, setTargetUser] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRoles, setSelectedRoles] = useState<Role[]>([]);
  const [rolesToRemove, setRolesToRemove] = useState<ExistingUserRole[]>([]);
  const [justification, setJustification] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [isTemporary, setIsTemporary] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // New Account / Copy User profile fields
  const [userProfile, setUserProfile] = useState<UserProfile>({
    userId: '',
    firstName: '',
    lastName: '',
    email: '',
    employeeId: '',
    department: '',
    costCenter: '',
    companyCode: '',
    manager: '',
    jobTitle: '',
    location: '',
  });

  // Copy User specific state
  const [sourceUser, setSourceUser] = useState('');
  const [sourceUserSearch, setSourceUserSearch] = useState('');
  const [showSourceUserDropdown, setShowSourceUserDropdown] = useState(false);
  const [sourceUserRoles, setSourceUserRoles] = useState<ExistingUserRole[]>([]);
  const [selectedSystemsToCopy, setSelectedSystemsToCopy] = useState<string[]>([]);

  // Target systems for provisioning
  const [targetSystems, setTargetSystems] = useState<TargetSystem[]>(defaultTargetSystems);
  const [selectedTargetSystems, setSelectedTargetSystems] = useState<string[]>([]);
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([]);

  // Lock/Unlock specific
  const [lockReason, setLockReason] = useState('');
  const [lockDuration, setLockDuration] = useState('');

  // Remove Account specific
  const [removeAction, setRemoveAction] = useState<'lock' | 'disable' | 'delete'>('lock');

  const selectedRequestType = requestTypeOptions.find((r) => r.id === requestType);
  const needsRoleSelection = requestType === REQUEST_TYPES.NEW_ACCOUNT || requestType === REQUEST_TYPES.CHANGE_ACCOUNT;
  const isCopyUser = requestType === REQUEST_TYPES.COPY_USER;
  const isNewAccount = requestType === REQUEST_TYPES.NEW_ACCOUNT;
  const isChangeAccount = requestType === REQUEST_TYPES.CHANGE_ACCOUNT;
  const isRemoveAccount = requestType === REQUEST_TYPES.REMOVE_ACCOUNT;
  const isLockAccount = requestType === REQUEST_TYPES.LOCK_ACCOUNT;
  const isUnlockAccount = requestType === REQUEST_TYPES.UNLOCK_ACCOUNT;

  // Calculate total steps based on request type
  const getTotalSteps = () => {
    if (isNewAccount) return 5; // Type -> Profile -> Systems -> Roles -> Review
    if (isCopyUser) return 5; // Type -> Profile -> Source User -> Systems -> Review
    if (isChangeAccount) return 4; // Type -> Roles -> Justification -> Review
    return 3; // Type -> Justification -> Review
  };

  const totalSteps = getTotalSteps();

  // Load connectors from API
  useEffect(() => {
    const loadConnectors = async () => {
      try {
        const response = await provisioningApi.listConnectors();
        if (response.connectors && response.connectors.length > 0) {
          setConnectors(response.connectors);
          // Map connectors to target systems
          const systems: TargetSystem[] = response.connectors.map((c) => ({
            id: c.connector_id,
            name: c.name,
            type: c.system_type,
            connected: c.is_connected,
          }));
          setTargetSystems(systems);
        }
      } catch (error) {
        console.log('Using default target systems');
      }
    };
    loadConnectors();
  }, []);

  // Get existing roles for the user
  const userRolesKey = requestForOther ? targetUser.toLowerCase().replace(/\s+/g, '.') : 'current_user';
  const currentUserRoles = useMemo(() => {
    return existingUserRoles[userRolesKey] || existingUserRoles['current_user'] || [];
  }, [userRolesKey]);

  // Source user search filter
  const filteredUsers = useMemo(() => {
    if (!sourceUserSearch) return mockUsers;
    return mockUsers.filter(
      (u) =>
        u.name.toLowerCase().includes(sourceUserSearch.toLowerCase()) ||
        u.id.toLowerCase().includes(sourceUserSearch.toLowerCase()) ||
        u.department.toLowerCase().includes(sourceUserSearch.toLowerCase())
    );
  }, [sourceUserSearch]);

  // Load source user roles when selected
  useEffect(() => {
    if (sourceUser) {
      const roles = existingUserRoles[sourceUser] || [];
      setSourceUserRoles(roles);
      // Get unique systems from source user roles
      const systems = [...new Set(roles.map((r) => r.system))];
      setSelectedSystemsToCopy(systems);
    }
  }, [sourceUser]);

  const getStatusBadge = (status: ExistingUserRole['status']) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'expiring_soon':
        return 'bg-yellow-100 text-yellow-800';
      case 'expired':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusLabel = (status: ExistingUserRole['status']) => {
    switch (status) {
      case 'active':
        return 'Active';
      case 'expiring_soon':
        return 'Expiring Soon';
      case 'expired':
        return 'Expired';
      default:
        return status;
    }
  };

  const toggleRoleRemoval = (role: ExistingUserRole) => {
    if (rolesToRemove.find((r) => r.id === role.id)) {
      setRolesToRemove(rolesToRemove.filter((r) => r.id !== role.id));
    } else {
      setRolesToRemove([...rolesToRemove, role]);
    }
  };

  const filteredRoles = availableRoles.filter(
    (role) =>
      role.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      role.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      role.system.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const toggleRole = (role: Role) => {
    if (selectedRoles.find((r) => r.id === role.id)) {
      setSelectedRoles(selectedRoles.filter((r) => r.id !== role.id));
    } else {
      setSelectedRoles([...selectedRoles, role]);
    }
  };

  const toggleTargetSystem = (systemId: string) => {
    if (selectedTargetSystems.includes(systemId)) {
      setSelectedTargetSystems(selectedTargetSystems.filter((s) => s !== systemId));
    } else {
      setSelectedTargetSystems([...selectedTargetSystems, systemId]);
    }
  };

  const hasConflicts = selectedRoles.some((r) => r.sodConflicts.length > 0);
  const highestRisk = selectedRoles.reduce((highest, role) => {
    const riskOrder = { low: 1, medium: 2, high: 3, critical: 4 };
    return riskOrder[role.riskLevel] > riskOrder[highest] ? role.riskLevel : highest;
  }, 'low' as 'low' | 'medium' | 'high' | 'critical');

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      // Call provisioning API based on request type
      if (isNewAccount || isCopyUser) {
        await provisioningApi.provisionUser(
          {
            user_id: userProfile.userId,
            first_name: userProfile.firstName,
            last_name: userProfile.lastName,
            email: userProfile.email,
            department: userProfile.department,
            job_title: userProfile.jobTitle,
            manager_id: userProfile.manager,
          },
          selectedTargetSystems,
          isCopyUser ? 'copy_user' : 'manual',
          isCopyUser ? sourceUser : ''
        );
      } else if (isChangeAccount) {
        if (selectedRoles.length > 0) {
          await provisioningApi.assignRoles(
            requestForOther ? targetUser : 'current_user',
            selectedRoles.map((r) => ({
              system: r.system,
              role_name: r.name,
              valid_from: startDate || undefined,
              valid_to: isTemporary ? endDate : undefined,
            })),
            'access_request'
          );
        }
        if (rolesToRemove.length > 0) {
          await provisioningApi.revokeRoles(
            requestForOther ? targetUser : 'current_user',
            rolesToRemove.map((r) => ({
              system: r.system,
              role_name: r.roleName,
            })),
            'access_request'
          );
        }
      } else if (isRemoveAccount || isLockAccount) {
        await provisioningApi.deprovisionUser(
          requestForOther ? targetUser : 'current_user',
          selectedTargetSystems,
          removeAction,
          isLockAccount ? 'lock_request' : 'remove_request'
        );
      }

      toast.success('Access request submitted successfully!');
      navigate('/access-requests');
    } catch (error) {
      // Request submitted but provisioning deferred until approval
      toast.success('Request submitted for approval. Provisioning will occur after approval.');
      navigate('/access-requests');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStepLabel = (s: number) => {
    if (s === 1) return 'Request Type';

    if (isNewAccount) {
      if (s === 2) return 'User Profile';
      if (s === 3) return 'Target Systems';
      if (s === 4) return 'Select Roles';
      if (s === 5) return 'Review & Submit';
    }

    if (isCopyUser) {
      if (s === 2) return 'New User Profile';
      if (s === 3) return 'Source User';
      if (s === 4) return 'Select Systems';
      if (s === 5) return 'Review & Submit';
    }

    if (isChangeAccount) {
      if (s === 2) return 'Select Roles';
      if (s === 3) return 'Justification';
      if (s === 4) return 'Review & Submit';
    }

    // Lock/Unlock/Remove
    if (s === 2) return 'Details';
    if (s === 3) return 'Review & Submit';

    return '';
  };

  const canProceedFromStep = (currentStep: number) => {
    if (currentStep === 1) {
      return requestType && (!requestForOther || targetUser);
    }

    if (isNewAccount) {
      if (currentStep === 2) {
        return userProfile.userId && userProfile.firstName && userProfile.lastName && userProfile.email;
      }
      if (currentStep === 3) return selectedTargetSystems.length > 0;
      if (currentStep === 4) return selectedRoles.length > 0;
    }

    if (isCopyUser) {
      if (currentStep === 2) {
        return userProfile.userId && userProfile.firstName && userProfile.lastName && userProfile.email;
      }
      if (currentStep === 3) return sourceUser !== '';
      if (currentStep === 4) return selectedSystemsToCopy.length > 0;
    }

    if (isChangeAccount) {
      if (currentStep === 2) return selectedRoles.length > 0 || rolesToRemove.length > 0;
      if (currentStep === 3) return justification.length >= 20;
    }

    // Lock/Unlock/Remove
    if (currentStep === 2) {
      if (isRemoveAccount) return selectedTargetSystems.length > 0 && justification.length >= 20;
      if (isLockAccount) return selectedTargetSystems.length > 0 && lockReason && justification.length >= 20;
      if (isUnlockAccount) return selectedTargetSystems.length > 0 && justification.length >= 20;
    }

    return true;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Link
            to="/access-requests"
            className="mr-4 p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="page-title">New Access Request</h1>
            <p className="page-subtitle">
              {selectedRequestType
                ? `${selectedRequestType.name}${requestForOther ? ` for ${targetUser}` : ''}`
                : 'Select request type and submit for approval'}
            </p>
          </div>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="bg-white shadow rounded-lg p-4">
        <div className="flex items-center justify-between">
          {Array.from({ length: totalSteps }, (_, i) => i + 1).map((s) => (
            <div key={s} className="flex items-center">
              <div
                className={`flex items-center justify-center w-7 h-7 rounded-full text-xs ${
                  step >= s ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-500'
                }`}
              >
                {s}
              </div>
              <span
                className={`ml-2 text-xs font-medium ${step >= s ? 'text-primary-600' : 'text-gray-500'}`}
              >
                {getStepLabel(s)}
              </span>
              {s < totalSteps && (
                <div className={`mx-3 h-0.5 w-12 ${step > s ? 'bg-primary-600' : 'bg-gray-200'}`} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step 1: Request Type Selection */}
      {step === 1 && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Select Request Type</h2>
            <p className="mt-1 text-sm text-gray-500">
              Choose what type of access request you want to submit
            </p>
          </div>

          <div className="p-6 space-y-4">
            {/* Request for self or other */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center mb-3">
                <input
                  type="checkbox"
                  id="requestForOther"
                  checked={requestForOther}
                  onChange={(e) => setRequestForOther(e.target.checked)}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label htmlFor="requestForOther" className="ml-2 text-sm font-medium text-gray-700">
                  Request for another user
                </label>
              </div>
              {requestForOther && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Target User</label>
                  <input
                    type="text"
                    placeholder="Enter username or search..."
                    value={targetUser}
                    onChange={(e) => setTargetUser(e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              )}
            </div>

            {/* Request Type Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {requestTypeOptions.map((type) => {
                const Icon = type.icon;
                const isSelected = requestType === type.id;

                return (
                  <div
                    key={type.id}
                    onClick={() => setRequestType(type.id)}
                    className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                      isSelected
                        ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-200'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <div className={`p-2 rounded-lg ${type.color}`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <h3 className="font-medium text-gray-900">{type.name}</h3>
                    </div>
                    <p className="text-xs text-gray-500">{type.description}</p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end">
            <button
              onClick={() => setStep(2)}
              disabled={!canProceedFromStep(1)}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {/* Step 2 for New Account / Copy User: User Profile */}
      {step === 2 && (isNewAccount || isCopyUser) && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              {isCopyUser ? 'New User Profile' : 'User Profile Information'}
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Enter the details for the new user account
            </p>
          </div>

          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Basic Info */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  User ID / Username *
                </label>
                <input
                  type="text"
                  value={userProfile.userId}
                  onChange={(e) => setUserProfile({ ...userProfile, userId: e.target.value })}
                  placeholder="e.g., john.doe"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Employee ID
                </label>
                <input
                  type="text"
                  value={userProfile.employeeId}
                  onChange={(e) => setUserProfile({ ...userProfile, employeeId: e.target.value })}
                  placeholder="e.g., EMP001"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  First Name *
                </label>
                <input
                  type="text"
                  value={userProfile.firstName}
                  onChange={(e) => setUserProfile({ ...userProfile, firstName: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Last Name *
                </label>
                <input
                  type="text"
                  value={userProfile.lastName}
                  onChange={(e) => setUserProfile({ ...userProfile, lastName: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address *
                </label>
                <input
                  type="email"
                  value={userProfile.email}
                  onChange={(e) => setUserProfile({ ...userProfile, email: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Job Title
                </label>
                <input
                  type="text"
                  value={userProfile.jobTitle}
                  onChange={(e) => setUserProfile({ ...userProfile, jobTitle: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Department
                </label>
                <select
                  value={userProfile.department}
                  onChange={(e) => setUserProfile({ ...userProfile, department: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">Select Department</option>
                  <option value="Finance">Finance</option>
                  <option value="IT">IT</option>
                  <option value="HR">Human Resources</option>
                  <option value="Sales">Sales</option>
                  <option value="Operations">Operations</option>
                  <option value="Marketing">Marketing</option>
                  <option value="Legal">Legal</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Manager
                </label>
                <input
                  type="text"
                  value={userProfile.manager}
                  onChange={(e) => setUserProfile({ ...userProfile, manager: e.target.value })}
                  placeholder="Manager's user ID"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Cost Center
                </label>
                <input
                  type="text"
                  value={userProfile.costCenter}
                  onChange={(e) => setUserProfile({ ...userProfile, costCenter: e.target.value })}
                  placeholder="e.g., CC1001"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Company Code
                </label>
                <input
                  type="text"
                  value={userProfile.companyCode}
                  onChange={(e) => setUserProfile({ ...userProfile, companyCode: e.target.value })}
                  placeholder="e.g., 1000"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Location
                </label>
                <input
                  type="text"
                  value={userProfile.location}
                  onChange={(e) => setUserProfile({ ...userProfile, location: e.target.value })}
                  placeholder="e.g., New York"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            </div>
          </div>

          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep(3)}
              disabled={!canProceedFromStep(2)}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {/* Step 3 for New Account: Target Systems */}
      {step === 3 && isNewAccount && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Select Target Systems</h2>
            <p className="mt-1 text-sm text-gray-500">
              Choose which systems to create the user account in
            </p>
          </div>

          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {targetSystems.map((system) => {
                const isSelected = selectedTargetSystems.includes(system.id);

                return (
                  <div
                    key={system.id}
                    onClick={() => toggleTargetSystem(system.id)}
                    className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                      isSelected
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    } ${!system.connected ? 'opacity-50' : ''}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                            isSelected ? 'border-primary-600 bg-primary-600' : 'border-gray-300'
                          }`}
                        >
                          {isSelected && <CheckCircleIcon className="h-4 w-4 text-white" />}
                        </div>
                        <div>
                          <ServerStackIcon className="h-5 w-5 text-gray-400" />
                        </div>
                        <div>
                          <span className="text-sm font-medium text-gray-900">{system.name}</span>
                          <span className="ml-2 text-xs text-gray-500">({system.type})</span>
                        </div>
                      </div>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          system.connected
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {system.connected ? 'Connected' : 'Disconnected'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {selectedTargetSystems.length > 0 && (
              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <span className="text-sm text-blue-800">
                  {selectedTargetSystems.length} system(s) selected for account creation
                </span>
              </div>
            )}
          </div>

          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            <button
              onClick={() => setStep(2)}
              className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep(4)}
              disabled={!canProceedFromStep(3)}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {/* Step 3 for Copy User: Source User Selection */}
      {step === 3 && isCopyUser && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Select Source User</h2>
            <p className="mt-1 text-sm text-gray-500">
              Choose an existing user to copy roles from
            </p>
          </div>

          <div className="p-6">
            {/* Source User Search */}
            <div className="relative mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search for Source User
              </label>
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by name, user ID, or department..."
                  value={sourceUserSearch}
                  onChange={(e) => {
                    setSourceUserSearch(e.target.value);
                    setShowSourceUserDropdown(true);
                  }}
                  onFocus={() => setShowSourceUserDropdown(true)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              {/* Dropdown */}
              {showSourceUserDropdown && (
                <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-auto">
                  {filteredUsers.map((user) => (
                    <div
                      key={user.id}
                      onClick={() => {
                        setSourceUser(user.id);
                        setSourceUserSearch(user.name);
                        setShowSourceUserDropdown(false);
                      }}
                      className={`p-3 cursor-pointer hover:bg-gray-50 ${
                        sourceUser === user.id ? 'bg-primary-50' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-sm font-medium text-gray-900">{user.name}</span>
                          <span className="ml-2 text-xs text-gray-500">({user.id})</span>
                        </div>
                        <div className="text-right">
                          <span className="text-xs text-gray-500">{user.department}</span>
                          <span className="block text-xs text-gray-400">{user.title}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Source User Roles Preview */}
            {sourceUser && sourceUserRoles.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                  <DocumentDuplicateIcon className="h-4 w-4 mr-2 text-purple-500" />
                  Roles to Copy from {sourceUserSearch}
                </h3>
                <div className="bg-purple-50 rounded-lg border border-purple-200 overflow-hidden">
                  <table className="min-w-full divide-y divide-purple-200">
                    <thead className="bg-purple-100">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-purple-700 uppercase">
                          Role
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-purple-700 uppercase">
                          System
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-purple-700 uppercase">
                          Risk
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-purple-700 uppercase">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-purple-100">
                      {sourceUserRoles.map((role) => {
                        const riskInfo = riskConfig[role.riskLevel];
                        return (
                          <tr key={role.id}>
                            <td className="px-4 py-3 text-sm font-medium text-gray-900">
                              {role.roleName}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500">{role.system}</td>
                            <td className="px-4 py-3">
                              <span
                                className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${riskInfo.color}`}
                              >
                                {riskInfo.label}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadge(
                                  role.status
                                )}`}
                              >
                                {getStatusLabel(role.status)}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  {sourceUserRoles.length} role(s) will be copied to the new user
                </p>
              </div>
            )}
          </div>

          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            <button
              onClick={() => setStep(2)}
              className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep(4)}
              disabled={!canProceedFromStep(3)}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {/* Step 4 for Copy User: Select Systems to Copy */}
      {step === 4 && isCopyUser && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Select Systems to Copy</h2>
            <p className="mt-1 text-sm text-gray-500">
              Choose which system roles to copy from the source user
            </p>
          </div>

          <div className="p-6">
            {/* Group roles by system */}
            {(() => {
              const systemGroups = sourceUserRoles.reduce((acc, role) => {
                if (!acc[role.system]) {
                  acc[role.system] = [];
                }
                acc[role.system].push(role);
                return acc;
              }, {} as Record<string, ExistingUserRole[]>);

              return (
                <div className="space-y-4">
                  {Object.entries(systemGroups).map(([system, roles]) => {
                    const isSelected = selectedSystemsToCopy.includes(system);

                    return (
                      <div
                        key={system}
                        className={`border-2 rounded-lg overflow-hidden transition-all ${
                          isSelected ? 'border-purple-500' : 'border-gray-200'
                        }`}
                      >
                        <div
                          onClick={() => {
                            if (isSelected) {
                              setSelectedSystemsToCopy(
                                selectedSystemsToCopy.filter((s) => s !== system)
                              );
                            } else {
                              setSelectedSystemsToCopy([...selectedSystemsToCopy, system]);
                            }
                          }}
                          className={`p-4 cursor-pointer flex items-center justify-between ${
                            isSelected ? 'bg-purple-50' : 'bg-gray-50'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div
                              className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                                isSelected
                                  ? 'border-purple-600 bg-purple-600'
                                  : 'border-gray-300'
                              }`}
                            >
                              {isSelected && <CheckCircleIcon className="h-4 w-4 text-white" />}
                            </div>
                            <BuildingOfficeIcon className="h-5 w-5 text-gray-400" />
                            <span className="text-sm font-medium text-gray-900">{system}</span>
                          </div>
                          <span className="text-xs text-gray-500">{roles.length} role(s)</span>
                        </div>
                        {isSelected && (
                          <div className="p-3 bg-white border-t border-purple-200">
                            <div className="space-y-2">
                              {roles.map((role) => {
                                const riskInfo = riskConfig[role.riskLevel];
                                return (
                                  <div
                                    key={role.id}
                                    className="flex items-center justify-between text-sm"
                                  >
                                    <span className="text-gray-700">{role.roleName}</span>
                                    <span
                                      className={`px-2 py-0.5 rounded text-xs font-medium ${riskInfo.color}`}
                                    >
                                      {riskInfo.label}
                                    </span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })()}

            {selectedSystemsToCopy.length > 0 && (
              <div className="mt-4 p-3 bg-purple-50 border border-purple-200 rounded-lg">
                <span className="text-sm text-purple-800">
                  Copying roles from {selectedSystemsToCopy.length} system(s)
                </span>
              </div>
            )}
          </div>

          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            <button
              onClick={() => setStep(3)}
              className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep(5)}
              disabled={!canProceedFromStep(4)}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {/* Step 2 for Change Account: Select Roles */}
      {step === 2 && isChangeAccount && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Modify Roles</h2>
            <p className="mt-1 text-sm text-gray-500">
              Review existing roles and select new roles to add or roles to remove
            </p>
          </div>

          <div className="p-6">
            {/* Existing Roles Section */}
            {currentUserRoles.length > 0 && (
              <div className="mb-8">
                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                  <ClockIcon className="h-4 w-4 mr-2 text-gray-500" />
                  Current Assigned Roles
                </h3>
                <div className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Role
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          System
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Validity
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Last Used
                        </th>
                        <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Remove
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {currentUserRoles.map((role) => {
                        const isMarkedForRemoval = rolesToRemove.find((r) => r.id === role.id);
                        const riskInfo = riskConfig[role.riskLevel];
                        return (
                          <tr
                            key={role.id}
                            className={isMarkedForRemoval ? 'bg-red-50' : 'hover:bg-gray-50'}
                          >
                            <td className="px-4 py-3">
                              <div className="flex items-center">
                                <div>
                                  <div
                                    className={`text-sm font-medium ${
                                      isMarkedForRemoval
                                        ? 'text-red-600 line-through'
                                        : 'text-gray-900'
                                    }`}
                                  >
                                    {role.roleName}
                                  </div>
                                  <span
                                    className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${riskInfo.color}`}
                                  >
                                    {riskInfo.label}
                                  </span>
                                </div>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500">{role.system}</td>
                            <td className="px-4 py-3">
                              <div className="flex items-center text-xs text-gray-500">
                                <CalendarDaysIcon className="h-3.5 w-3.5 mr-1 text-gray-400" />
                                <span>
                                  {role.validFrom}
                                  <span className="mx-1">→</span>
                                  {role.validTo || 'Permanent'}
                                </span>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadge(
                                  role.status
                                )}`}
                              >
                                {getStatusLabel(role.status)}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-xs text-gray-500">
                              {role.lastUsed || 'Never'}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <button
                                onClick={() => toggleRoleRemoval(role)}
                                className={`p-1 rounded transition-colors ${
                                  isMarkedForRemoval
                                    ? 'text-red-600 bg-red-100 hover:bg-red-200'
                                    : 'text-gray-400 hover:text-red-600 hover:bg-red-50'
                                }`}
                                title={
                                  isMarkedForRemoval
                                    ? 'Click to keep this role'
                                    : 'Click to remove this role'
                                }
                              >
                                <MinusCircleIcon className="h-5 w-5" />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Roles to Remove Summary */}
                {rolesToRemove.length > 0 && (
                  <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-red-800">
                        {rolesToRemove.length} role(s) marked for removal
                      </span>
                      <button
                        onClick={() => setRolesToRemove([])}
                        className="text-sm text-red-600 hover:text-red-800"
                      >
                        Clear all
                      </button>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {rolesToRemove.map((role) => (
                        <span
                          key={role.id}
                          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800"
                        >
                          {role.roleName}
                          <button
                            onClick={() => toggleRoleRemoval(role)}
                            className="ml-1 text-red-600 hover:text-red-800"
                          >
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Add New Roles Section */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                <PlusCircleIcon className="h-4 w-4 mr-2 text-gray-500" />
                Add New Roles
              </h3>

              {/* Search */}
              <div className="relative mb-4">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search roles by name, description, or system..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              {/* Selected Roles Summary */}
              {selectedRoles.length > 0 && (
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-blue-800">
                      {selectedRoles.length} new role(s) to add
                    </span>
                    <button
                      onClick={() => setSelectedRoles([])}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      Clear all
                    </button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {selectedRoles.map((role) => (
                      <span
                        key={role.id}
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                      >
                        {role.name}
                        <button
                          onClick={() => toggleRole(role)}
                          className="ml-1 text-blue-600 hover:text-blue-800"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Role List */}
            <div className="space-y-3">
              {filteredRoles.map((role) => {
                const isSelected = selectedRoles.find((r) => r.id === role.id);
                const riskInfo = riskConfig[role.riskLevel];

                return (
                  <div
                    key={role.id}
                    onClick={() => toggleRole(role)}
                    className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                      isSelected
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start">
                        <div
                          className={`mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center ${
                            isSelected ? 'border-primary-600 bg-primary-600' : 'border-gray-300'
                          }`}
                        >
                          {isSelected && <CheckCircleIcon className="h-4 w-4 text-white" />}
                        </div>
                        <div className="ml-3">
                          <div className="flex items-center">
                            <span className="text-sm font-medium text-gray-900">{role.name}</span>
                            <span className="ml-2 inline-flex px-2 py-0.5 rounded bg-gray-100 text-xs text-gray-600">
                              {role.system}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-gray-500">{role.description}</p>
                          {role.sodConflicts.length > 0 && (
                            <div className="mt-2 flex items-center text-xs text-orange-600">
                              <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
                              {role.sodConflicts[0]}
                            </div>
                          )}
                        </div>
                      </div>
                      <span
                        className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${riskInfo.color}`}
                      >
                        {riskInfo.label}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep(3)}
              disabled={!canProceedFromStep(2)}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {/* Step 4 for New Account: Select Roles */}
      {step === 4 && isNewAccount && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Select Initial Roles</h2>
            <p className="mt-1 text-sm text-gray-500">
              Choose the roles to assign to the new account
            </p>
          </div>

          <div className="p-6">
            {/* Search */}
            <div className="relative mb-4">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search roles by name, description, or system..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            {/* Filter by selected systems */}
            {selectedTargetSystems.length > 0 && (
              <div className="mb-4 p-3 bg-gray-50 border border-gray-200 rounded-lg">
                <span className="text-xs text-gray-600">
                  Showing roles for: {selectedTargetSystems.map(s =>
                    targetSystems.find(ts => ts.id === s)?.name
                  ).join(', ')}
                </span>
              </div>
            )}

            {/* Selected Roles Summary */}
            {selectedRoles.length > 0 && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-blue-800">
                    {selectedRoles.length} role(s) selected
                  </span>
                  <button
                    onClick={() => setSelectedRoles([])}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    Clear all
                  </button>
                </div>
              </div>
            )}

            {/* Role List */}
            <div className="space-y-3">
              {filteredRoles.map((role) => {
                const isSelected = selectedRoles.find((r) => r.id === role.id);
                const riskInfo = riskConfig[role.riskLevel];

                return (
                  <div
                    key={role.id}
                    onClick={() => toggleRole(role)}
                    className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                      isSelected
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start">
                        <div
                          className={`mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center ${
                            isSelected ? 'border-primary-600 bg-primary-600' : 'border-gray-300'
                          }`}
                        >
                          {isSelected && <CheckCircleIcon className="h-4 w-4 text-white" />}
                        </div>
                        <div className="ml-3">
                          <div className="flex items-center">
                            <span className="text-sm font-medium text-gray-900">{role.name}</span>
                            <span className="ml-2 inline-flex px-2 py-0.5 rounded bg-gray-100 text-xs text-gray-600">
                              {role.system}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-gray-500">{role.description}</p>
                          {role.sodConflicts.length > 0 && (
                            <div className="mt-2 flex items-center text-xs text-orange-600">
                              <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
                              {role.sodConflicts[0]}
                            </div>
                          )}
                        </div>
                      </div>
                      <span
                        className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${riskInfo.color}`}
                      >
                        {riskInfo.label}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            <button
              onClick={() => setStep(3)}
              className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep(5)}
              disabled={!canProceedFromStep(4)}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {/* Step 2 for Lock/Unlock/Remove: Details */}
      {step === 2 && (isLockAccount || isUnlockAccount || isRemoveAccount) && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              {isLockAccount ? 'Lock Account Details' : isUnlockAccount ? 'Unlock Account Details' : 'Remove Account Details'}
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Provide the details for this operation
            </p>
          </div>

          <div className="p-6 space-y-6">
            {/* Target Systems Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Select Target Systems *
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {targetSystems.map((system) => {
                  const isSelected = selectedTargetSystems.includes(system.id);

                  return (
                    <div
                      key={system.id}
                      onClick={() => toggleTargetSystem(system.id)}
                      className={`p-3 border-2 rounded-lg cursor-pointer transition-all ${
                        isSelected
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-4 h-4 rounded border-2 flex items-center justify-center ${
                            isSelected ? 'border-primary-600 bg-primary-600' : 'border-gray-300'
                          }`}
                        >
                          {isSelected && <CheckCircleIcon className="h-3 w-3 text-white" />}
                        </div>
                        <span className="text-sm font-medium text-gray-900">{system.name}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Lock-specific fields */}
            {isLockAccount && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Lock Reason *
                  </label>
                  <select
                    value={lockReason}
                    onChange={(e) => setLockReason(e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="">Select reason...</option>
                    <option value="leave">Extended Leave</option>
                    <option value="security">Security Investigation</option>
                    <option value="termination_pending">Termination Pending</option>
                    <option value="compliance">Compliance Requirement</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Lock Duration
                  </label>
                  <select
                    value={lockDuration}
                    onChange={(e) => setLockDuration(e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="">Indefinite (until unlocked)</option>
                    <option value="7">7 days</option>
                    <option value="14">14 days</option>
                    <option value="30">30 days</option>
                    <option value="90">90 days</option>
                  </select>
                </div>
              </>
            )}

            {/* Remove-specific fields */}
            {isRemoveAccount && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Removal Action *
                </label>
                <div className="space-y-3">
                  <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                    <input
                      type="radio"
                      name="removeAction"
                      value="lock"
                      checked={removeAction === 'lock'}
                      onChange={() => setRemoveAction('lock')}
                      className="h-4 w-4 text-primary-600"
                    />
                    <div className="ml-3">
                      <span className="text-sm font-medium text-gray-900">Lock Account</span>
                      <p className="text-xs text-gray-500">Disable login but retain account data</p>
                    </div>
                  </label>
                  <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                    <input
                      type="radio"
                      name="removeAction"
                      value="disable"
                      checked={removeAction === 'disable'}
                      onChange={() => setRemoveAction('disable')}
                      className="h-4 w-4 text-primary-600"
                    />
                    <div className="ml-3">
                      <span className="text-sm font-medium text-gray-900">Disable Account</span>
                      <p className="text-xs text-gray-500">Mark account as inactive, can be reactivated</p>
                    </div>
                  </label>
                  <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                    <input
                      type="radio"
                      name="removeAction"
                      value="delete"
                      checked={removeAction === 'delete'}
                      onChange={() => setRemoveAction('delete')}
                      className="h-4 w-4 text-red-600"
                    />
                    <div className="ml-3">
                      <span className="text-sm font-medium text-red-700">Delete Account</span>
                      <p className="text-xs text-red-500">Permanently remove account (cannot be undone)</p>
                    </div>
                  </label>
                </div>
              </div>
            )}

            {/* Justification */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Business Justification *
              </label>
              <textarea
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                rows={4}
                placeholder="Explain the reason for this request..."
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Minimum 20 characters required.
              </p>
            </div>
          </div>

          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep(3)}
              disabled={!canProceedFromStep(2)}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {/* Step 3 for Change Account: Justification */}
      {step === 3 && isChangeAccount && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Business Justification</h2>
            <p className="mt-1 text-sm text-gray-500">
              Provide a business reason for this access request
            </p>
          </div>

          <div className="p-6 space-y-6">
            {/* Risk Warning */}
            {(hasConflicts || highestRisk === 'high' || highestRisk === 'critical') && (
              <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
                <div className="flex items-start">
                  <ShieldExclamationIcon className="h-5 w-5 text-orange-600 mt-0.5" />
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-orange-800">Elevated Risk Request</h3>
                    <p className="mt-1 text-sm text-orange-700">
                      This request includes high-risk roles or potential SoD conflicts. Additional
                      approval may be required.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Justification */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Business Justification *
              </label>
              <textarea
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                rows={4}
                placeholder="Explain why you need this access and how it will be used for business purposes..."
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Minimum 20 characters. Be specific about the business need.
              </p>
            </div>

            {/* Temporary Access */}
            <div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="temporary"
                  checked={isTemporary}
                  onChange={(e) => setIsTemporary(e.target.checked)}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label htmlFor="temporary" className="ml-2 text-sm text-gray-700">
                  This is a temporary access request
                </label>
              </div>
            </div>

            {/* Date Range */}
            {isTemporary && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Start Date
                  </label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    End Date
                  </label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            <button
              onClick={() => setStep(2)}
              className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep(4)}
              disabled={!canProceedFromStep(3)}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {/* Final Review Step */}
      {((step === 5 && (isNewAccount || isCopyUser)) ||
        (step === 4 && isChangeAccount) ||
        (step === 3 && (isLockAccount || isUnlockAccount || isRemoveAccount))) && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Review & Submit</h2>
            <p className="mt-1 text-sm text-gray-500">Review your request before submitting</p>
          </div>

          <div className="p-6 space-y-6">
            {/* Request Type */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Request Type</h3>
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                {selectedRequestType && (
                  <>
                    <div className={`p-2 rounded-lg ${selectedRequestType.color}`}>
                      <selectedRequestType.icon className="h-4 w-4" />
                    </div>
                    <div>
                      <span className="text-sm font-medium text-gray-900">
                        {selectedRequestType.name}
                      </span>
                      {requestForOther && (
                        <span className="ml-2 text-xs text-gray-500">for {targetUser}</span>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* User Profile (New Account / Copy User) */}
            {(isNewAccount || isCopyUser) && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3">New User Profile</h3>
                <div className="grid grid-cols-2 gap-3 p-3 bg-gray-50 rounded-lg text-sm">
                  <div>
                    <span className="text-gray-500">User ID:</span>
                    <span className="ml-2 text-gray-900">{userProfile.userId}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Name:</span>
                    <span className="ml-2 text-gray-900">
                      {userProfile.firstName} {userProfile.lastName}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Email:</span>
                    <span className="ml-2 text-gray-900">{userProfile.email}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Department:</span>
                    <span className="ml-2 text-gray-900">{userProfile.department || 'N/A'}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Source User (Copy User) */}
            {isCopyUser && sourceUser && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                  <DocumentDuplicateIcon className="h-4 w-4 mr-2 text-purple-500" />
                  Copying Roles From
                </h3>
                <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
                  <span className="text-sm font-medium text-purple-800">{sourceUserSearch}</span>
                  <span className="ml-2 text-xs text-purple-600">
                    ({sourceUserRoles.filter(r => selectedSystemsToCopy.includes(r.system)).length} roles from {selectedSystemsToCopy.length} system(s))
                  </span>
                </div>
              </div>
            )}

            {/* Target Systems (New Account / Lock / Unlock / Remove) */}
            {(isNewAccount || isLockAccount || isUnlockAccount || isRemoveAccount) &&
              selectedTargetSystems.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-3">Target Systems</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedTargetSystems.map((systemId) => {
                      const system = targetSystems.find((s) => s.id === systemId);
                      return (
                        <span
                          key={systemId}
                          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                        >
                          <ServerStackIcon className="h-3 w-3 mr-1" />
                          {system?.name || systemId}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

            {/* Roles to Remove (Change Account) */}
            {isChangeAccount && rolesToRemove.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                  <MinusCircleIcon className="h-4 w-4 mr-2 text-red-500" />
                  Roles to Remove
                </h3>
                <div className="space-y-2">
                  {rolesToRemove.map((role) => {
                    const riskInfo = riskConfig[role.riskLevel];
                    return (
                      <div
                        key={role.id}
                        className="flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-lg"
                      >
                        <div>
                          <span className="text-sm font-medium text-red-700 line-through">
                            {role.roleName}
                          </span>
                          <span className="ml-2 text-xs text-red-500">({role.system})</span>
                        </div>
                        <span
                          className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${riskInfo.color}`}
                        >
                          {riskInfo.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Roles to Add (New/Change Account) */}
            {(isNewAccount || isChangeAccount) && selectedRoles.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                  <PlusCircleIcon className="h-4 w-4 mr-2 text-green-500" />
                  {isChangeAccount ? 'Roles to Add' : 'Requested Roles'}
                </h3>
                <div className="space-y-2">
                  {selectedRoles.map((role) => {
                    const riskInfo = riskConfig[role.riskLevel];
                    return (
                      <div
                        key={role.id}
                        className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg"
                      >
                        <div>
                          <span className="text-sm font-medium text-gray-900">{role.name}</span>
                          <span className="ml-2 text-xs text-gray-500">({role.system})</span>
                        </div>
                        <span
                          className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${riskInfo.color}`}
                        >
                          {riskInfo.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Remove Action */}
            {isRemoveAccount && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Removal Action</h3>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <span
                    className={`text-sm font-medium ${
                      removeAction === 'delete' ? 'text-red-700' : 'text-gray-900'
                    }`}
                  >
                    {removeAction === 'lock'
                      ? 'Lock Account'
                      : removeAction === 'disable'
                      ? 'Disable Account'
                      : 'Delete Account (Permanent)'}
                  </span>
                </div>
              </div>
            )}

            {/* Lock Details */}
            {isLockAccount && lockReason && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Lock Details</h3>
                <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg text-sm">
                  <div>
                    <span className="text-orange-700">Reason:</span>
                    <span className="ml-2 text-orange-900 capitalize">{lockReason.replace('_', ' ')}</span>
                  </div>
                  {lockDuration && (
                    <div className="mt-1">
                      <span className="text-orange-700">Duration:</span>
                      <span className="ml-2 text-orange-900">{lockDuration} days</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Justification */}
            {justification && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Business Justification</h3>
                <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">{justification}</p>
              </div>
            )}

            {/* Duration (Change Account with temporary) */}
            {isChangeAccount && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Access Duration</h3>
                <p className="text-sm text-gray-600">
                  {isTemporary ? `Temporary: ${startDate} to ${endDate}` : 'Permanent (until revoked)'}
                </p>
              </div>
            )}

            {/* Approval Info */}
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start">
                <InformationCircleIcon className="h-5 w-5 text-blue-600 mt-0.5" />
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">Approval Workflow</h3>
                  <p className="mt-1 text-sm text-blue-700">
                    This request will be sent to your manager for approval.
                    {(hasConflicts || highestRisk === 'high' || highestRisk === 'critical') &&
                      ' Additional security review may be required due to elevated risk.'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            <button
              onClick={() => {
                if (isNewAccount || isCopyUser) setStep(4);
                else if (isChangeAccount) setStep(3);
                else setStep(2);
              }}
              className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-400"
            >
              {isSubmitting ? 'Submitting...' : 'Submit Request'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
