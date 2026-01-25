import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeftIcon,
  PlusIcon,
  TrashIcon,
  CheckCircleIcon,
  MagnifyingGlassIcon,
  ShieldExclamationIcon,
  CubeIcon,
  CpuChipIcon,
  LightBulbIcon,
  SparklesIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  UserGroupIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface Permission {
  id: string;
  name: string;
  description: string;
  type: 'transaction' | 'authorization' | 'function';
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
}

interface SodConflict {
  permission1: string;
  permission2: string;
  rule: string;
  riskLevel: 'high' | 'critical';
  confidence?: number;
}

interface MLSuggestion {
  permission: string;
  description: string;
  risk_level: string;
  confidence: number;
  reason: string;
  recommendation_type: string;
}

interface SimilarRole {
  role_name: string;
  similarity_score: number;
  overlap_percentage: number;
  common_permissions: string[];
  current_users: number;
  recommendation: string;
}

interface MLRiskPrediction {
  risk_score: number;
  risk_level: string;
  ml_confidence: number;
  sod_conflicts: Array<{
    rule_name: string;
    risk_level: string;
    ml_confidence: number;
  }>;
  recommendations: Array<{
    type: string;
    priority: string;
    action: string;
    risk_reduction: number;
  }>;
  comparison?: {
    avg_similar_role_risk: number;
    percentile: number;
    trend: string;
  };
}

const availablePermissions: Permission[] = [
  { id: 'P001', name: 'FB01', description: 'Post Document', type: 'transaction', riskLevel: 'medium' },
  { id: 'P002', name: 'FB02', description: 'Change Document', type: 'transaction', riskLevel: 'medium' },
  { id: 'P003', name: 'FK01', description: 'Create Vendor', type: 'transaction', riskLevel: 'high' },
  { id: 'P004', name: 'FK02', description: 'Change Vendor', type: 'transaction', riskLevel: 'medium' },
  { id: 'P005', name: 'F110', description: 'Payment Run', type: 'transaction', riskLevel: 'critical' },
  { id: 'P006', name: 'ME21N', description: 'Create Purchase Order', type: 'transaction', riskLevel: 'medium' },
  { id: 'P007', name: 'ME29N', description: 'Release Purchase Order', type: 'transaction', riskLevel: 'high' },
  { id: 'P008', name: 'MIGO', description: 'Goods Movement', type: 'transaction', riskLevel: 'medium' },
  { id: 'P009', name: 'F_BKPF_BUK', description: 'Company Code Auth', type: 'authorization', riskLevel: 'low' },
  { id: 'P010', name: 'S_TCODE', description: 'Transaction Auth', type: 'authorization', riskLevel: 'low' },
  { id: 'P011', name: 'VA01', description: 'Create Sales Order', type: 'transaction', riskLevel: 'medium' },
  { id: 'P012', name: 'VA02', description: 'Change Sales Order', type: 'transaction', riskLevel: 'medium' },
  { id: 'P013', name: 'VF01', description: 'Create Billing', type: 'transaction', riskLevel: 'high' },
  { id: 'P014', name: 'MIRO', description: 'Enter Invoice', type: 'transaction', riskLevel: 'high' },
  { id: 'P015', name: 'ME22N', description: 'Change Purchase Order', type: 'transaction', riskLevel: 'medium' },
  { id: 'P016', name: 'ME23N', description: 'Display Purchase Order', type: 'transaction', riskLevel: 'low' },
];

const jobFunctions = [
  'AP Clerk',
  'AR Clerk',
  'Procurement Specialist',
  'Buyer',
  'Sales Representative',
  'Warehouse Manager',
  'Financial Analyst',
  'IT Administrator',
];

const riskConfig = {
  low: { color: 'bg-green-100 text-green-800', label: 'Low' },
  medium: { color: 'bg-yellow-100 text-yellow-800', label: 'Medium' },
  high: { color: 'bg-orange-100 text-orange-800', label: 'High' },
  critical: { color: 'bg-red-100 text-red-800', label: 'Critical' },
};

export function RoleDesigner() {
  const { roleId } = useParams();
  const isEditing = !!roleId;

  const [roleName, setRoleName] = useState(isEditing ? 'SAP_MM_BUYER' : '');
  const [roleDescription, setRoleDescription] = useState(
    isEditing ? 'Procurement buyer role with purchase order creation' : ''
  );
  const [roleSystem, setRoleSystem] = useState(isEditing ? 'SAP ECC' : '');
  const [roleType, setRoleType] = useState<'business' | 'technical' | 'composite'>('business');
  const [selectedPermissions, setSelectedPermissions] = useState<Permission[]>(
    isEditing
      ? [availablePermissions[5], availablePermissions[6], availablePermissions[7]]
      : []
  );
  const [searchTerm, setSearchTerm] = useState('');
  const [showSimulation, setShowSimulation] = useState(false);

  // ML States
  const [selectedJobFunction, setSelectedJobFunction] = useState<string>('');
  const [mlSuggestions, setMlSuggestions] = useState<MLSuggestion[]>([]);
  const [similarRoles, setSimilarRoles] = useState<SimilarRole[]>([]);
  const [mlRiskPrediction, setMlRiskPrediction] = useState<MLRiskPrediction | null>(null);
  const [isLoadingML, setIsLoadingML] = useState(false);
  const [showMLPanel, setShowMLPanel] = useState(true);
  const [mlTab, setMlTab] = useState<'suggestions' | 'similar' | 'optimize'>('suggestions');

  const filteredPermissions = availablePermissions.filter(
    (p) =>
      !selectedPermissions.find((sp) => sp.id === p.id) &&
      (p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Simulated SoD conflicts with ML confidence
  const sodConflicts: SodConflict[] = [];
  if (
    selectedPermissions.find((p) => p.name === 'ME21N') &&
    selectedPermissions.find((p) => p.name === 'ME29N')
  ) {
    sodConflicts.push({
      permission1: 'ME21N',
      permission2: 'ME29N',
      rule: 'Create PO / Release PO',
      riskLevel: 'high',
      confidence: 0.95,
    });
  }
  if (
    selectedPermissions.find((p) => p.name === 'FK01') &&
    selectedPermissions.find((p) => p.name === 'F110')
  ) {
    sodConflicts.push({
      permission1: 'FK01',
      permission2: 'F110',
      rule: 'Create Vendor / Execute Payment',
      riskLevel: 'critical',
      confidence: 0.98,
    });
  }
  if (
    selectedPermissions.find((p) => p.name === 'ME21N') &&
    selectedPermissions.find((p) => p.name === 'MIRO')
  ) {
    sodConflicts.push({
      permission1: 'ME21N',
      permission2: 'MIRO',
      rule: 'Create PO / Enter Invoice',
      riskLevel: 'high',
      confidence: 0.92,
    });
  }

  const addPermission = (permission: Permission) => {
    setSelectedPermissions([...selectedPermissions, permission]);
  };

  const removePermission = (permissionId: string) => {
    setSelectedPermissions(selectedPermissions.filter((p) => p.id !== permissionId));
  };

  const addPermissionByName = (permName: string) => {
    const perm = availablePermissions.find(p => p.name === permName);
    if (perm && !selectedPermissions.find(sp => sp.id === perm.id)) {
      setSelectedPermissions([...selectedPermissions, perm]);
    }
  };

  const calculateRiskScore = () => {
    if (selectedPermissions.length === 0) return 0;
    const riskValues = { low: 10, medium: 30, high: 60, critical: 100 };
    const totalRisk = selectedPermissions.reduce(
      (acc, p) => acc + riskValues[p.riskLevel],
      0
    );
    const baseScore = Math.min(totalRisk / selectedPermissions.length, 100);
    const conflictPenalty = sodConflicts.length * 15;
    return Math.min(Math.round(baseScore + conflictPenalty), 100);
  };

  const riskScore = mlRiskPrediction?.risk_score ?? calculateRiskScore();

  // Fetch ML suggestions when job function changes
  useEffect(() => {
    if (selectedJobFunction) {
      fetchMLSuggestions();
    }
  }, [selectedJobFunction]);

  // Fetch similar roles and risk prediction when permissions change
  useEffect(() => {
    if (selectedPermissions.length > 0) {
      fetchSimilarRoles();
      fetchRiskPrediction();
    } else {
      setSimilarRoles([]);
      setMlRiskPrediction(null);
    }
  }, [selectedPermissions]);

  const fetchMLSuggestions = async () => {
    setIsLoadingML(true);
    try {
      const response = await fetch('/api/ml/role-design/suggest-permissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_function: selectedJobFunction,
          current_permissions: selectedPermissions.map(p => p.name),
          system: roleSystem || 'SAP ECC'
        })
      });
      if (response.ok) {
        const data = await response.json();
        setMlSuggestions(data.suggestions || []);
      }
    } catch (error) {
      // Use mock data on error
      setMlSuggestions(getMockSuggestions(selectedJobFunction));
    }
    setIsLoadingML(false);
  };

  const fetchSimilarRoles = async () => {
    if (selectedPermissions.length === 0) return;
    try {
      const perms = selectedPermissions.map(p => p.name).join(',');
      const response = await fetch(`/api/ml/role-design/similar-roles?permissions=${perms}&limit=5`);
      if (response.ok) {
        const data = await response.json();
        setSimilarRoles(data.similar_roles || []);
      }
    } catch (error) {
      // Use mock data on error
      setSimilarRoles(getMockSimilarRoles(selectedPermissions));
    }
  };

  const fetchRiskPrediction = async () => {
    if (selectedPermissions.length === 0) return;
    try {
      const response = await fetch('/api/ml/role-design/predict-risk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role_name: roleName || 'NEW_ROLE',
          permissions: selectedPermissions.map(p => p.name),
          system: roleSystem || 'SAP ECC'
        })
      });
      if (response.ok) {
        const data = await response.json();
        setMlRiskPrediction(data);
      }
    } catch (error) {
      // Use calculated risk on error
      setMlRiskPrediction(null);
    }
  };

  // Mock data generators for offline/development
  const getMockSuggestions = (jobFunc: string): MLSuggestion[] => {
    const suggestions: Record<string, MLSuggestion[]> = {
      'Buyer': [
        { permission: 'ME21N', description: 'Create Purchase Order', risk_level: 'medium', confidence: 0.95, reason: 'Core permission for Buyer', recommendation_type: 'core' },
        { permission: 'ME22N', description: 'Change Purchase Order', risk_level: 'medium', confidence: 0.93, reason: 'Core permission for Buyer', recommendation_type: 'core' },
        { permission: 'ME23N', description: 'Display Purchase Order', risk_level: 'low', confidence: 0.91, reason: 'Core permission for Buyer', recommendation_type: 'core' },
        { permission: 'ME29N', description: 'Release Purchase Order', risk_level: 'high', confidence: 0.88, reason: 'Core permission for Buyer', recommendation_type: 'core' },
        { permission: 'MIGO', description: 'Goods Movement', risk_level: 'medium', confidence: 0.78, reason: 'Commonly used by Buyers', recommendation_type: 'recommended' },
      ],
      'AP Clerk': [
        { permission: 'FB01', description: 'Post Document', risk_level: 'medium', confidence: 0.96, reason: 'Core permission for AP Clerk', recommendation_type: 'core' },
        { permission: 'FB02', description: 'Change Document', risk_level: 'medium', confidence: 0.94, reason: 'Core permission for AP Clerk', recommendation_type: 'core' },
        { permission: 'MIRO', description: 'Enter Invoice', risk_level: 'high', confidence: 0.92, reason: 'Core permission for AP Clerk', recommendation_type: 'core' },
        { permission: 'F110', description: 'Payment Run', risk_level: 'critical', confidence: 0.89, reason: 'Core permission for AP Clerk', recommendation_type: 'core' },
      ],
      'Sales Representative': [
        { permission: 'VA01', description: 'Create Sales Order', risk_level: 'medium', confidence: 0.97, reason: 'Core permission for Sales', recommendation_type: 'core' },
        { permission: 'VA02', description: 'Change Sales Order', risk_level: 'medium', confidence: 0.95, reason: 'Core permission for Sales', recommendation_type: 'core' },
        { permission: 'VF01', description: 'Create Billing', risk_level: 'high', confidence: 0.82, reason: 'Commonly used by Sales', recommendation_type: 'recommended' },
      ],
    };
    return suggestions[jobFunc] || [];
  };

  const getMockSimilarRoles = (perms: Permission[]): SimilarRole[] => {
    const permNames = perms.map(p => p.name);
    const roles: SimilarRole[] = [];

    if (permNames.some(p => ['ME21N', 'ME22N', 'ME29N'].includes(p))) {
      roles.push({
        role_name: 'SAP_MM_BUYER',
        similarity_score: 0.85,
        overlap_percentage: 80,
        common_permissions: permNames.filter(p => ['ME21N', 'ME22N', 'ME23N', 'ME29N'].includes(p)),
        current_users: 62,
        recommendation: 'Consider consolidating'
      });
    }
    if (permNames.some(p => ['FB01', 'FB02', 'F110'].includes(p))) {
      roles.push({
        role_name: 'SAP_FI_AP_CLERK',
        similarity_score: 0.72,
        overlap_percentage: 65,
        common_permissions: permNames.filter(p => ['FB01', 'FB02', 'F110', 'MIRO'].includes(p)),
        current_users: 45,
        recommendation: 'Reference for design'
      });
    }
    return roles;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Link
            to="/roles"
            className="mr-4 p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {isEditing ? 'Edit Role' : 'Create New Role'}
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              {isEditing ? `Editing: ${roleId}` : 'Design a new role with ML-powered insights'}
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowMLPanel(!showMLPanel)}
            className={clsx(
              'px-4 py-2 border rounded-md text-sm font-medium flex items-center gap-2',
              showMLPanel
                ? 'border-primary-500 text-primary-700 bg-primary-50'
                : 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'
            )}
          >
            <CpuChipIcon className="h-4 w-4" />
            {showMLPanel ? 'Hide ML Assistant' : 'Show ML Assistant'}
          </button>
          <button
            onClick={() => setShowSimulation(!showSimulation)}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            {showSimulation ? 'Hide' : 'Run'} Risk Simulation
          </button>
          <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm font-medium">
            Save Role
          </button>
        </div>
      </div>

      <div className={clsx('grid gap-6', showMLPanel ? 'grid-cols-1 lg:grid-cols-4' : 'grid-cols-1 lg:grid-cols-3')}>
        {/* Role Details */}
        <div className={clsx(showMLPanel ? 'lg:col-span-2' : 'lg:col-span-2', 'space-y-6')}>
          {/* Basic Info */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Role Details</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Role Name *
                </label>
                <input
                  type="text"
                  value={roleName}
                  onChange={(e) => setRoleName(e.target.value)}
                  placeholder="e.g., SAP_FI_AP_CLERK"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  System *
                </label>
                <select
                  value={roleSystem}
                  onChange={(e) => setRoleSystem(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">Select System</option>
                  <option value="SAP ECC">SAP ECC</option>
                  <option value="SAP S/4HANA">SAP S/4HANA</option>
                  <option value="AWS">AWS</option>
                  <option value="Azure AD">Azure AD</option>
                  <option value="Workday">Workday</option>
                  <option value="Salesforce">Salesforce</option>
                </select>
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  value={roleDescription}
                  onChange={(e) => setRoleDescription(e.target.value)}
                  rows={2}
                  placeholder="Describe the purpose of this role..."
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Role Type
                </label>
                <select
                  value={roleType}
                  onChange={(e) => setRoleType(e.target.value as any)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="business">Business Role</option>
                  <option value="technical">Technical Role</option>
                  <option value="composite">Composite Role</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <span className="flex items-center gap-1">
                    <SparklesIcon className="h-4 w-4 text-primary-500" />
                    Job Function (ML)
                  </span>
                </label>
                <select
                  value={selectedJobFunction}
                  onChange={(e) => setSelectedJobFunction(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">Select for ML suggestions</option>
                  {jobFunctions.map(func => (
                    <option key={func} value={func}>{func}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Permission Assignment */}
          <div className="bg-white shadow rounded-lg">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Permissions</h2>
              <p className="mt-1 text-sm text-gray-500">
                Add permissions to this role
              </p>
            </div>

            {/* Selected Permissions */}
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                Assigned Permissions ({selectedPermissions.length})
              </h3>
              {selectedPermissions.length > 0 ? (
                <div className="space-y-2">
                  {selectedPermissions.map((permission) => {
                    const riskInfo = riskConfig[permission.riskLevel];
                    const hasConflict = sodConflicts.some(
                      c => c.permission1 === permission.name || c.permission2 === permission.name
                    );
                    return (
                      <div
                        key={permission.id}
                        className={clsx(
                          'flex items-center justify-between p-3 rounded-lg',
                          hasConflict ? 'bg-red-50 border border-red-200' : 'bg-gray-50'
                        )}
                      >
                        <div className="flex items-center">
                          <CubeIcon className={clsx('h-5 w-5 mr-3', hasConflict ? 'text-red-400' : 'text-gray-400')} />
                          <div>
                            <span className="text-sm font-medium text-gray-900">
                              {permission.name}
                            </span>
                            <span className="ml-2 text-sm text-gray-500">
                              - {permission.description}
                            </span>
                            {hasConflict && (
                              <span className="ml-2 text-xs text-red-600">
                                (SoD Conflict)
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span
                            className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${riskInfo.color}`}
                          >
                            {riskInfo.label}
                          </span>
                          <button
                            onClick={() => removePermission(permission.id)}
                            className="text-red-500 hover:text-red-700"
                          >
                            <TrashIcon className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-gray-500 text-center py-4">
                  No permissions assigned. Add permissions from the list below or use ML suggestions.
                </p>
              )}
            </div>

            {/* Available Permissions */}
            <div className="p-6">
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                Available Permissions
              </h3>
              <div className="relative mb-4">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search permissions..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              <div className="max-h-64 overflow-y-auto space-y-2">
                {filteredPermissions.map((permission) => {
                  const riskInfo = riskConfig[permission.riskLevel];
                  return (
                    <div
                      key={permission.id}
                      className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
                    >
                      <div className="flex items-center">
                        <div>
                          <span className="text-sm font-medium text-gray-900">
                            {permission.name}
                          </span>
                          <span className="ml-2 text-sm text-gray-500">
                            - {permission.description}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${riskInfo.color}`}
                        >
                          {riskInfo.label}
                        </span>
                        <button
                          onClick={() => addPermission(permission)}
                          className="text-primary-600 hover:text-primary-700"
                        >
                          <PlusIcon className="h-5 w-5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* ML Assistant Panel */}
        {showMLPanel && (
          <div className="space-y-6">
            <div className="bg-gradient-to-br from-primary-500 to-indigo-600 rounded-lg p-4 text-white">
              <div className="flex items-center gap-2 mb-2">
                <CpuChipIcon className="h-5 w-5" />
                <h3 className="font-medium">ML Role Assistant</h3>
              </div>
              <p className="text-xs opacity-90">
                AI-powered suggestions for optimal role design
              </p>
            </div>

            {/* ML Tabs */}
            <div className="bg-white shadow rounded-lg">
              <div className="border-b border-gray-200">
                <nav className="flex -mb-px">
                  <button
                    onClick={() => setMlTab('suggestions')}
                    className={clsx(
                      'flex-1 py-3 px-4 text-center text-xs font-medium border-b-2',
                      mlTab === 'suggestions'
                        ? 'border-primary-500 text-primary-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    )}
                  >
                    <LightBulbIcon className="h-4 w-4 mx-auto mb-1" />
                    Suggestions
                  </button>
                  <button
                    onClick={() => setMlTab('similar')}
                    className={clsx(
                      'flex-1 py-3 px-4 text-center text-xs font-medium border-b-2',
                      mlTab === 'similar'
                        ? 'border-primary-500 text-primary-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    )}
                  >
                    <UserGroupIcon className="h-4 w-4 mx-auto mb-1" />
                    Similar Roles
                  </button>
                  <button
                    onClick={() => setMlTab('optimize')}
                    className={clsx(
                      'flex-1 py-3 px-4 text-center text-xs font-medium border-b-2',
                      mlTab === 'optimize'
                        ? 'border-primary-500 text-primary-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    )}
                  >
                    <AdjustmentsHorizontalIcon className="h-4 w-4 mx-auto mb-1" />
                    Optimize
                  </button>
                </nav>
              </div>

              <div className="p-4">
                {mlTab === 'suggestions' && (
                  <div className="space-y-3">
                    {!selectedJobFunction ? (
                      <div className="text-center py-6 text-gray-500">
                        <SparklesIcon className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">Select a job function above to get ML-powered permission suggestions</p>
                      </div>
                    ) : isLoadingML ? (
                      <div className="text-center py-6">
                        <ArrowPathIcon className="h-6 w-6 mx-auto mb-2 animate-spin text-primary-500" />
                        <p className="text-sm text-gray-500">Analyzing permissions...</p>
                      </div>
                    ) : mlSuggestions.length > 0 ? (
                      <>
                        <p className="text-xs text-gray-500 mb-2">
                          Recommended for {selectedJobFunction}:
                        </p>
                        {mlSuggestions.map((suggestion, idx) => (
                          <div
                            key={idx}
                            className="p-3 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-medium text-gray-900">
                                    {suggestion.permission}
                                  </span>
                                  <span className={clsx(
                                    'px-1.5 py-0.5 text-xs rounded',
                                    suggestion.recommendation_type === 'core'
                                      ? 'bg-primary-100 text-primary-700'
                                      : 'bg-gray-100 text-gray-600'
                                  )}>
                                    {suggestion.recommendation_type}
                                  </span>
                                </div>
                                <p className="text-xs text-gray-500 mt-1">
                                  {suggestion.description}
                                </p>
                                <div className="flex items-center gap-3 mt-2 text-xs">
                                  <span className={clsx(
                                    'px-1.5 py-0.5 rounded',
                                    riskConfig[suggestion.risk_level as keyof typeof riskConfig]?.color || 'bg-gray-100'
                                  )}>
                                    {suggestion.risk_level}
                                  </span>
                                  <span className="text-gray-500">
                                    {Math.round(suggestion.confidence * 100)}% confidence
                                  </span>
                                </div>
                              </div>
                              <button
                                onClick={() => addPermissionByName(suggestion.permission)}
                                className="ml-2 p-1 text-primary-600 hover:bg-primary-100 rounded"
                                disabled={selectedPermissions.some(p => p.name === suggestion.permission)}
                              >
                                <PlusIcon className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                        <button
                          onClick={fetchMLSuggestions}
                          className="w-full mt-2 py-2 text-xs text-primary-600 hover:text-primary-700 flex items-center justify-center gap-1"
                        >
                          <ArrowPathIcon className="h-3 w-3" />
                          Refresh suggestions
                        </button>
                      </>
                    ) : (
                      <div className="text-center py-6 text-gray-500">
                        <p className="text-sm">No suggestions available</p>
                      </div>
                    )}
                  </div>
                )}

                {mlTab === 'similar' && (
                  <div className="space-y-3">
                    {similarRoles.length > 0 ? (
                      <>
                        <p className="text-xs text-gray-500 mb-2">
                          Roles with similar permissions:
                        </p>
                        {similarRoles.map((role, idx) => (
                          <div key={idx} className="p-3 border border-gray-200 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-sm font-medium text-gray-900">
                                {role.role_name}
                              </span>
                              <span className={clsx(
                                'text-xs px-2 py-0.5 rounded',
                                role.similarity_score > 0.7
                                  ? 'bg-green-100 text-green-700'
                                  : role.similarity_score > 0.4
                                  ? 'bg-yellow-100 text-yellow-700'
                                  : 'bg-gray-100 text-gray-600'
                              )}>
                                {Math.round(role.similarity_score * 100)}% match
                              </span>
                            </div>
                            <div className="text-xs text-gray-500 space-y-1">
                              <p>{role.current_users} users assigned</p>
                              <p>Common: {role.common_permissions.join(', ')}</p>
                            </div>
                            <p className={clsx(
                              'text-xs mt-2 font-medium',
                              role.recommendation === 'Consider consolidating'
                                ? 'text-primary-600'
                                : 'text-gray-500'
                            )}>
                              {role.recommendation}
                            </p>
                          </div>
                        ))}
                      </>
                    ) : (
                      <div className="text-center py-6 text-gray-500">
                        <UserGroupIcon className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">Add permissions to find similar roles</p>
                      </div>
                    )}
                  </div>
                )}

                {mlTab === 'optimize' && (
                  <div className="space-y-3">
                    {mlRiskPrediction?.recommendations && mlRiskPrediction.recommendations.length > 0 ? (
                      <>
                        <p className="text-xs text-gray-500 mb-2">
                          ML recommendations to reduce risk:
                        </p>
                        {mlRiskPrediction.recommendations.map((rec, idx) => (
                          <div key={idx} className={clsx(
                            'p-3 rounded-lg border',
                            rec.priority === 'high'
                              ? 'border-red-200 bg-red-50'
                              : 'border-yellow-200 bg-yellow-50'
                          )}>
                            <div className="flex items-start gap-2">
                              <ExclamationTriangleIcon className={clsx(
                                'h-4 w-4 mt-0.5',
                                rec.priority === 'high' ? 'text-red-500' : 'text-yellow-500'
                              )} />
                              <div className="flex-1">
                                <p className="text-sm text-gray-900">{rec.action}</p>
                                <p className="text-xs text-gray-500 mt-1">
                                  Risk reduction: -{rec.risk_reduction} points
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </>
                    ) : selectedPermissions.length > 0 ? (
                      <div className="text-center py-6 text-green-600">
                        <CheckCircleIcon className="h-8 w-8 mx-auto mb-2" />
                        <p className="text-sm font-medium">Role is well optimized</p>
                        <p className="text-xs text-gray-500 mt-1">No major issues detected</p>
                      </div>
                    ) : (
                      <div className="text-center py-6 text-gray-500">
                        <AdjustmentsHorizontalIcon className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">Add permissions to get optimization insights</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Sidebar - Risk Analysis */}
        <div className="space-y-6">
          {/* ML Risk Score */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-gray-900">Role Risk Score</h3>
              {mlRiskPrediction && (
                <span className="text-xs text-primary-600 flex items-center gap-1">
                  <CpuChipIcon className="h-3 w-3" />
                  ML Powered
                </span>
              )}
            </div>
            <div className="flex items-center justify-center">
              <div className="relative w-32 h-32">
                <svg className="w-full h-full" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" strokeWidth="10" />
                  <circle
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke={riskScore > 70 ? '#ef4444' : riskScore > 40 ? '#f59e0b' : '#22c55e'}
                    strokeWidth="10"
                    strokeDasharray={`${riskScore * 2.83} ${100 * 2.83}`}
                    strokeLinecap="round"
                    transform="rotate(-90 50 50)"
                  />
                  <text x="50" y="50" textAnchor="middle" dy="0.3em" className="text-2xl font-bold" fill="#111827">
                    {Math.round(riskScore)}
                  </text>
                </svg>
              </div>
            </div>
            <div className="mt-4 text-center">
              <span
                className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${
                  riskScore > 70
                    ? 'bg-red-100 text-red-800'
                    : riskScore > 40
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-green-100 text-green-800'
                }`}
              >
                {riskScore > 70 ? 'High Risk' : riskScore > 40 ? 'Medium Risk' : 'Low Risk'}
              </span>
              {mlRiskPrediction && (
                <p className="text-xs text-gray-500 mt-2">
                  {Math.round(mlRiskPrediction.ml_confidence * 100)}% ML confidence
                </p>
              )}
            </div>
          </div>

          {/* SoD Conflicts */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-gray-900">SoD Conflicts</h3>
              <span className="text-xs text-primary-600 flex items-center gap-1">
                <CpuChipIcon className="h-3 w-3" />
                ML Detection
              </span>
            </div>
            {sodConflicts.length > 0 ? (
              <div className="space-y-3">
                {sodConflicts.map((conflict, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg border ${
                      conflict.riskLevel === 'critical'
                        ? 'bg-red-50 border-red-200'
                        : 'bg-orange-50 border-orange-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <ShieldExclamationIcon
                          className={`h-5 w-5 ${
                            conflict.riskLevel === 'critical' ? 'text-red-600' : 'text-orange-600'
                          }`}
                        />
                        <span
                          className={`ml-2 text-sm font-medium ${
                            conflict.riskLevel === 'critical' ? 'text-red-800' : 'text-orange-800'
                          }`}
                        >
                          {conflict.rule}
                        </span>
                      </div>
                      {conflict.confidence && (
                        <span className="text-xs text-gray-500">
                          {Math.round(conflict.confidence * 100)}%
                        </span>
                      )}
                    </div>
                    <p
                      className={`mt-1 text-xs ${
                        conflict.riskLevel === 'critical' ? 'text-red-700' : 'text-orange-700'
                      }`}
                    >
                      {conflict.permission1} + {conflict.permission2}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4">
                <CheckCircleIcon className="mx-auto h-8 w-8 text-green-500" />
                <p className="mt-2 text-sm text-gray-500">No SoD conflicts detected</p>
              </div>
            )}
          </div>

          {/* Simulation Results */}
          {showSimulation && (
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-sm font-medium text-gray-900 mb-4">Risk Simulation</h3>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Users Affected</span>
                  <span className="font-medium text-gray-900">{isEditing ? '45' : '0'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">New Violations</span>
                  <span className="font-medium text-red-600">{sodConflicts.length * 45}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Compliance Impact</span>
                  <span
                    className={`font-medium ${
                      sodConflicts.length > 0 ? 'text-orange-600' : 'text-green-600'
                    }`}
                  >
                    {sodConflicts.length > 0 ? 'Review Required' : 'Compliant'}
                  </span>
                </div>
                {mlRiskPrediction && (
                  <>
                    <div className="border-t border-gray-200 pt-3 mt-3">
                      <p className="text-xs text-gray-500 mb-2">ML Insights:</p>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">Peer Comparison</span>
                        <span className="font-medium text-gray-900">
                          {mlRiskPrediction.comparison?.trend === 'above_average' ? 'Higher risk' :
                           mlRiskPrediction.comparison?.trend === 'below_average' ? 'Lower risk' : 'Average'}
                        </span>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
