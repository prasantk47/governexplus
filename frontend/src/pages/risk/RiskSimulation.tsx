import { useState } from 'react';
import {
  BeakerIcon,
  UserIcon,
  ShieldExclamationIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ChartBarIcon,
  DocumentMagnifyingGlassIcon,
} from '@heroicons/react/24/outline';

interface SimulationRole {
  id: string;
  name: string;
  system: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  selected: boolean;
}

interface SimulationResult {
  overallRisk: 'low' | 'medium' | 'high' | 'critical';
  riskScore: number;
  sodConflicts: {
    id: string;
    rule: string;
    conflictingRoles: string[];
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
  }[];
  sensitiveAccess: {
    id: string;
    access: string;
    system: string;
    reason: string;
  }[];
  peerComparison: {
    similarUsers: number;
    averageRoles: number;
    percentile: number;
  };
  recommendations: string[];
}

const availableRoles: SimulationRole[] = [
  { id: 'R1', name: 'AP Invoice Processor', system: 'SAP S/4HANA', riskLevel: 'medium', selected: false },
  { id: 'R2', name: 'AP Payment Run', system: 'SAP S/4HANA', riskLevel: 'high', selected: false },
  { id: 'R3', name: 'Vendor Master Maintainer', system: 'SAP S/4HANA', riskLevel: 'high', selected: false },
  { id: 'R4', name: 'GL Posting', system: 'SAP S/4HANA', riskLevel: 'medium', selected: false },
  { id: 'R5', name: 'Purchase Order Creator', system: 'SAP S/4HANA', riskLevel: 'medium', selected: false },
  { id: 'R6', name: 'Goods Receipt Processor', system: 'SAP S/4HANA', riskLevel: 'low', selected: false },
  { id: 'R7', name: 'Financial Report Viewer', system: 'SAP BW', riskLevel: 'low', selected: false },
  { id: 'R8', name: 'User Administrator', system: 'Active Directory', riskLevel: 'critical', selected: false },
  { id: 'R9', name: 'Database Admin', system: 'Oracle', riskLevel: 'critical', selected: false },
  { id: 'R10', name: 'CRM User', system: 'Salesforce', riskLevel: 'low', selected: false },
];

const mockUsers = [
  { id: 'U1', name: 'John Smith', department: 'Finance', currentRoles: 3 },
  { id: 'U2', name: 'Mary Jones', department: 'Procurement', currentRoles: 4 },
  { id: 'U3', name: 'Robert Wilson', department: 'IT', currentRoles: 5 },
  { id: 'U4', name: 'Sarah Brown', department: 'HR', currentRoles: 2 },
];

export function RiskSimulation() {
  const [selectedUser, setSelectedUser] = useState<string>('');
  const [roles, setRoles] = useState<SimulationRole[]>(availableRoles);
  const [searchTerm, setSearchTerm] = useState('');
  const [isSimulating, setIsSimulating] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);

  const selectedRoles = roles.filter((r) => r.selected);
  const filteredRoles = roles.filter(
    (r) =>
      r.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.system.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const toggleRole = (id: string) => {
    setRoles(roles.map((r) => (r.id === id ? { ...r, selected: !r.selected } : r)));
    setResult(null); // Clear previous results
  };

  const runSimulation = async () => {
    setIsSimulating(true);
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Mock simulation result
    const hasHighRiskRoles = selectedRoles.some((r) => r.riskLevel === 'high' || r.riskLevel === 'critical');
    const hasSodConflict = selectedRoles.some((r) => r.id === 'R1') && selectedRoles.some((r) => r.id === 'R2');
    const hasVendorSodConflict = selectedRoles.some((r) => r.id === 'R3') && selectedRoles.some((r) => r.id === 'R2');

    const conflicts = [];
    if (hasSodConflict) {
      conflicts.push({
        id: 'SOD-001',
        rule: 'AP Processing & Payment Execution',
        conflictingRoles: ['AP Invoice Processor', 'AP Payment Run'],
        severity: 'critical' as const,
        description: 'User can create invoices and execute payments, creating fraud risk',
      });
    }
    if (hasVendorSodConflict) {
      conflicts.push({
        id: 'SOD-002',
        rule: 'Vendor Maintenance & Payment Execution',
        conflictingRoles: ['Vendor Master Maintainer', 'AP Payment Run'],
        severity: 'high' as const,
        description: 'User can create vendors and pay them, enabling ghost vendor fraud',
      });
    }

    setResult({
      overallRisk: conflicts.length > 0 ? 'critical' : hasHighRiskRoles ? 'high' : 'medium',
      riskScore: conflicts.length > 0 ? 85 : hasHighRiskRoles ? 65 : 35,
      sodConflicts: conflicts,
      sensitiveAccess: selectedRoles
        .filter((r) => r.riskLevel === 'high' || r.riskLevel === 'critical')
        .map((r) => ({
          id: r.id,
          access: r.name,
          system: r.system,
          reason: r.riskLevel === 'critical' ? 'Administrative privileges' : 'Financial transaction access',
        })),
      peerComparison: {
        similarUsers: 45,
        averageRoles: 4,
        percentile: selectedRoles.length > 4 ? 85 : 50,
      },
      recommendations: [
        ...(conflicts.length > 0
          ? ['Remove one of the conflicting roles to eliminate SoD violation']
          : []),
        ...(hasHighRiskRoles
          ? ['Consider implementing compensating controls for high-risk access']
          : []),
        selectedRoles.length > 5
          ? 'Review if all requested roles are necessary - consider least privilege'
          : 'Role count is within acceptable limits',
      ],
    });

    setIsSimulating(false);
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-green-100 text-green-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Risk Simulation</h1>
        <p className="text-sm text-gray-500">
          Simulate access changes before provisioning to identify potential risks
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel - Configuration */}
        <div className="lg:col-span-2 space-y-6">
          {/* User Selection */}
          <div className="bg-white shadow rounded-lg">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <UserIcon className="h-5 w-5 text-gray-400" />
                Select User
              </h2>
            </div>
            <div className="p-6">
              <select
                value={selectedUser}
                onChange={(e) => setSelectedUser(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">Select a user to simulate...</option>
                {mockUsers.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.name} ({user.department}) - {user.currentRoles} current roles
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Role Selection */}
          <div className="bg-white shadow rounded-lg">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <ShieldExclamationIcon className="h-5 w-5 text-gray-400" />
                  Select Roles to Add
                </h2>
                <span className="text-sm text-gray-500">{selectedRoles.length} selected</span>
              </div>
            </div>
            <div className="p-6">
              <input
                type="text"
                placeholder="Search roles..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 mb-4 focus:ring-primary-500 focus:border-primary-500"
              />
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {filteredRoles.map((role) => (
                  <div
                    key={role.id}
                    onClick={() => toggleRole(role.id)}
                    className={`flex items-center justify-between p-3 rounded-lg cursor-pointer border-2 transition-all ${
                      role.selected
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={role.selected}
                        onChange={() => toggleRole(role.id)}
                        className="h-4 w-4 rounded border-gray-300 text-primary-600"
                      />
                      <div>
                        <div className="text-sm font-medium text-gray-900">{role.name}</div>
                        <div className="text-xs text-gray-500">{role.system}</div>
                      </div>
                    </div>
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getRiskColor(role.riskLevel)}`}>
                      {role.riskLevel}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
              <button
                onClick={runSimulation}
                disabled={selectedRoles.length === 0 || isSimulating}
                className="w-full px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isSimulating ? (
                  <>
                    <ArrowPathIcon className="h-5 w-5 animate-spin" />
                    Running Simulation...
                  </>
                ) : (
                  <>
                    <BeakerIcon className="h-5 w-5" />
                    Run Simulation
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right Panel - Results */}
        <div className="space-y-6">
          {!result && !isSimulating && (
            <div className="bg-white shadow rounded-lg p-6 text-center">
              <DocumentMagnifyingGlassIcon className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-sm font-medium text-gray-900 mb-1">No Simulation Yet</h3>
              <p className="text-xs text-gray-500">
                Select roles and run a simulation to see risk analysis
              </p>
            </div>
          )}

          {isSimulating && (
            <div className="bg-white shadow rounded-lg p-6 text-center">
              <ArrowPathIcon className="h-12 w-12 text-primary-600 mx-auto mb-4 animate-spin" />
              <h3 className="text-sm font-medium text-gray-900 mb-1">Analyzing...</h3>
              <p className="text-xs text-gray-500">Running SoD checks and risk calculations</p>
            </div>
          )}

          {result && (
            <>
              {/* Risk Score */}
              <div className="bg-white shadow rounded-lg p-6">
                <h3 className="text-sm font-medium text-gray-700 mb-4">Overall Risk Assessment</h3>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-16 w-16 rounded-full flex items-center justify-center text-2xl font-bold ${
                        result.riskScore >= 70 ? 'bg-red-100 text-red-700' :
                        result.riskScore >= 50 ? 'bg-orange-100 text-orange-700' :
                        result.riskScore >= 30 ? 'bg-yellow-100 text-yellow-700' :
                        'bg-green-100 text-green-700'
                      }`}
                    >
                      {result.riskScore}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">Risk Score</p>
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getRiskColor(result.overallRisk)}`}>
                        {result.overallRisk.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      result.riskScore >= 70 ? 'bg-red-500' :
                      result.riskScore >= 50 ? 'bg-orange-500' :
                      result.riskScore >= 30 ? 'bg-yellow-500' :
                      'bg-green-500'
                    }`}
                    style={{ width: `${result.riskScore}%` }}
                  />
                </div>
              </div>

              {/* SoD Conflicts */}
              <div className="bg-white shadow rounded-lg p-6">
                <h3 className="text-sm font-medium text-gray-700 mb-4 flex items-center gap-2">
                  <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
                  SoD Conflicts ({result.sodConflicts.length})
                </h3>
                {result.sodConflicts.length === 0 ? (
                  <div className="flex items-center gap-2 text-green-600 text-sm">
                    <CheckCircleIcon className="h-5 w-5" />
                    No SoD conflicts detected
                  </div>
                ) : (
                  <div className="space-y-3">
                    {result.sodConflicts.map((conflict) => (
                      <div key={conflict.id} className="bg-red-50 border border-red-200 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-red-800">{conflict.rule}</span>
                          <span className={`text-xs px-1.5 py-0.5 rounded ${getRiskColor(conflict.severity)}`}>
                            {conflict.severity}
                          </span>
                        </div>
                        <p className="text-xs text-red-600 mb-2">{conflict.description}</p>
                        <div className="flex flex-wrap gap-1">
                          {conflict.conflictingRoles.map((role, i) => (
                            <span key={i} className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                              {role}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Sensitive Access */}
              {result.sensitiveAccess.length > 0 && (
                <div className="bg-white shadow rounded-lg p-6">
                  <h3 className="text-sm font-medium text-gray-700 mb-4 flex items-center gap-2">
                    <ShieldExclamationIcon className="h-5 w-5 text-orange-500" />
                    Sensitive Access ({result.sensitiveAccess.length})
                  </h3>
                  <div className="space-y-2">
                    {result.sensitiveAccess.map((item) => (
                      <div key={item.id} className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                        <div className="text-sm font-medium text-orange-800">{item.access}</div>
                        <div className="text-xs text-orange-600">{item.system} - {item.reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Peer Comparison */}
              <div className="bg-white shadow rounded-lg p-6">
                <h3 className="text-sm font-medium text-gray-700 mb-4 flex items-center gap-2">
                  <ChartBarIcon className="h-5 w-5 text-blue-500" />
                  Peer Comparison
                </h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Similar users analyzed:</span>
                    <span className="font-medium">{result.peerComparison.similarUsers}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Average roles per user:</span>
                    <span className="font-medium">{result.peerComparison.averageRoles}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Your percentile:</span>
                    <span className={`font-medium ${result.peerComparison.percentile > 75 ? 'text-orange-600' : 'text-green-600'}`}>
                      {result.peerComparison.percentile}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              <div className="bg-white shadow rounded-lg p-6">
                <h3 className="text-sm font-medium text-gray-700 mb-4">Recommendations</h3>
                <div className="space-y-2">
                  {result.recommendations.map((rec, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      <CheckCircleIcon className="h-5 w-5 text-primary-500 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-600">{rec}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
