import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  // ExclamationTriangleIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  FireIcon,
  ClockIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { riskApi, api } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  SearchInput,
  Select,
  Table,
  Badge,
  RiskBadge,
} from '../../components/ui';

interface Violation {
  id: string;
  user: string;
  userId: string;
  department: string;
  type: 'SoD Conflict' | 'Excessive Access' | 'Sensitive Access' | 'Dormant Account';
  rule: string;
  riskLevel: 'critical' | 'high' | 'medium' | 'low';
  detectedDate: string;
  status: 'open' | 'in_review' | 'mitigated' | 'accepted';
  mitigation?: string;
  systems: string[];
}

// Violations are fetched from the API — no hardcoded data

const statusVariant: Record<string, 'danger' | 'info' | 'success' | 'neutral'> = {
  open: 'danger',
  in_review: 'info',
  mitigated: 'success',
  accepted: 'neutral',
};

const statusLabel: Record<string, string> = {
  open: 'Open',
  in_review: 'In Review',
  mitigated: 'Mitigated',
  accepted: 'Accepted',
};

export function RiskViolations() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [selectedViolation, setSelectedViolation] = useState<Violation | null>(null);
  const [mitigatingViolation, setMitigatingViolation] = useState<Violation | null>(null);
  const [mitigationNote, setMitigationNote] = useState('');
  const [mitigationControl, setMitigationControl] = useState('');
  const [mitigationSubmitting, setMitigationSubmitting] = useState(false);

  const { data: violationsData } = useQuery<Violation[]>({
    queryKey: ['risk-violations', statusFilter, riskFilter],
    queryFn: () =>
      riskApi
        .listViolations({
          status: statusFilter !== 'all' ? statusFilter : undefined,
          risk_level: riskFilter !== 'all' ? riskFilter : undefined,
        })
        .then((res) => res.data?.violations || res.data || []),
  });

  const violations: Violation[] = violationsData || [];

  const handleExportReport = () => {
    const headers = ['ID', 'User', 'User ID', 'Department', 'Type', 'Rule', 'Risk Level', 'Status', 'Detected Date', 'Systems', 'Mitigation'];
    const rows = filteredViolations.map(v => [
      v.id, v.user, v.userId, v.department, v.type, v.rule, v.riskLevel, v.status,
      v.detectedDate, v.systems.join('; '), v.mitigation || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `risk_violations_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);

    toast.success(`Exported ${filteredViolations.length} violations to CSV`);
  };

  const filteredViolations = violations.filter((v) => {
    const matchesSearch =
      (v.user ?? '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(v.id).toLowerCase().includes(searchTerm.toLowerCase()) ||
      (v.rule ?? '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || v.status === statusFilter;
    const matchesRisk = riskFilter === 'all' || v.riskLevel === riskFilter;
    const matchesType = typeFilter === 'all' || v.type === typeFilter;
    return matchesSearch && matchesStatus && matchesRisk && matchesType;
  });

  const criticalCount = violations.filter((v) => v.riskLevel === 'critical' && v.status === 'open').length;
  const highCount = violations.filter((v) => v.riskLevel === 'high' && v.status === 'open').length;
  const openCount = violations.filter((v) => v.status === 'open').length;
  const mitigatedCount = violations.filter((v) => v.status === 'mitigated').length;

  const columns = [
    {
      key: 'violation',
      header: 'Violation',
      render: (v: Violation) => (
        <div>
          <div className="text-sm font-medium text-primary-600">{v.id}</div>
          <div className="text-xs text-gray-400 max-w-xs truncate">{v.rule}</div>
        </div>
      ),
    },
    {
      key: 'user',
      header: 'User / Department',
      render: (v: Violation) => (
        <div>
          <div className="text-sm font-medium text-gray-900">{v.user}</div>
          <div className="text-xs text-gray-400">{v.department}</div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (v: Violation) => (
        <span className="text-sm text-gray-600">{v.type}</span>
      ),
    },
    {
      key: 'risk',
      header: 'Risk',
      render: (v: Violation) => <RiskBadge level={v.riskLevel} />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (v: Violation) => (
        <Badge variant={statusVariant[v.status] || 'neutral'} size="sm">
          {statusLabel[v.status] || v.status}
        </Badge>
      ),
    },
    {
      key: 'systems',
      header: 'Systems',
      render: (v: Violation) => (
        <div className="flex flex-wrap gap-1">
          {(v.systems ?? []).map((system) => (
            <Badge key={system} variant="neutral" size="sm">{system}</Badge>
          ))}
        </div>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (v: Violation) => (
        <div className="flex justify-end gap-2">
          <button
            onClick={() => setSelectedViolation(v)}
            className="text-xs font-medium text-primary-600 hover:text-primary-800 transition-colors"
          >
            View
          </button>
          {v.status === 'open' && (
            <button
              onClick={() => { setMitigatingViolation(v); setMitigationNote(''); setMitigationControl(''); }}
              className="text-xs font-medium text-green-600 hover:text-green-800 transition-colors"
            >
              Mitigate
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Violations"
        subtitle="View and manage all active SoD conflicts and access violations"
        actions={
          <Button size="sm" onClick={handleExportReport}>
            Export Report
          </Button>
        }
      />

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <StatCard title="Critical Open" value={criticalCount} icon={ExclamationCircleIcon} iconBgColor="stat-icon-red" iconColor="" />
        <StatCard title="High Open" value={highCount} icon={FireIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Total Open" value={openCount} icon={ClockIcon} iconBgColor="stat-icon-yellow" iconColor="" />
        <StatCard title="Mitigated (30d)" value={mitigatedCount} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col lg:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by user, ID, or rule..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClear={() => setSearchTerm('')}
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Status' },
                { value: 'open', label: 'Open' },
                { value: 'in_review', label: 'In Review' },
                { value: 'mitigated', label: 'Mitigated' },
                { value: 'accepted', label: 'Accepted' },
              ]}
            />
            <Select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Risk' },
                { value: 'critical', label: 'Critical' },
                { value: 'high', label: 'High' },
                { value: 'medium', label: 'Medium' },
                { value: 'low', label: 'Low' },
              ]}
            />
            <Select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Types' },
                { value: 'SoD Conflict', label: 'SoD Conflict' },
                { value: 'Excessive Access', label: 'Excessive Access' },
                { value: 'Sensitive Access', label: 'Sensitive Access' },
                { value: 'Dormant Account', label: 'Dormant Account' },
              ]}
            />
          </div>
        </div>
      </Card>

      {/* Violations Table */}
      <Table
        columns={columns}
        data={filteredViolations}
        emptyMessage="No violations found matching your criteria"
      />

      {/* View Violation Detail Modal */}
      {selectedViolation && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Violation Details</h2>
              <button onClick={() => setSelectedViolation(null)} className="text-gray-400 hover:text-gray-600">
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500">Violation ID</p>
                  <p className="text-sm font-medium text-primary-600">{selectedViolation.id}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Risk Level</p>
                  <RiskBadge level={selectedViolation.riskLevel} />
                </div>
                <div>
                  <p className="text-xs text-gray-500">User</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{selectedViolation.user}</p>
                  <p className="text-xs text-gray-400">{selectedViolation.userId}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Department</p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">{selectedViolation.department}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Type</p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">{selectedViolation.type}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Status</p>
                  <Badge variant={statusVariant[selectedViolation.status] || 'neutral'} size="sm">
                    {statusLabel[selectedViolation.status] || selectedViolation.status}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Detected Date</p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">{selectedViolation.detectedDate}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Systems</p>
                  <div className="flex flex-wrap gap-1 mt-0.5">
                    {(selectedViolation.systems ?? []).map((s) => (
                      <Badge key={s} variant="neutral" size="sm">{s}</Badge>
                    ))}
                  </div>
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-500">Rule</p>
                <p className="text-sm text-gray-700 dark:text-gray-300">{selectedViolation.rule}</p>
              </div>
              {selectedViolation.mitigation && (
                <div>
                  <p className="text-xs text-gray-500">Mitigation</p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">{selectedViolation.mitigation}</p>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 p-5 border-t border-gray-200 dark:border-gray-700">
              {selectedViolation.status === 'open' && (
                <Button size="sm" onClick={() => { setMitigatingViolation(selectedViolation); setSelectedViolation(null); setMitigationNote(''); setMitigationControl(''); }}>
                  Mitigate
                </Button>
              )}
              <Button size="sm" variant="secondary" onClick={() => setSelectedViolation(null)}>Close</Button>
            </div>
          </div>
        </div>
      )}

      {/* Mitigation Modal */}
      {mitigatingViolation && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full mx-4">
            <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Mitigate Violation</h2>
              <button onClick={() => setMitigatingViolation(null)} className="text-gray-400 hover:text-gray-600">
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <p className="text-xs text-gray-500">Violation</p>
                <p className="text-sm font-medium text-primary-600">{mitigatingViolation.id}</p>
                <p className="text-xs text-gray-400">{mitigatingViolation.rule}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Mitigation Control</label>
                <select
                  value={mitigationControl}
                  onChange={(e) => setMitigationControl(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">Select a control...</option>
                  <option value="compensating_control">Compensating Control</option>
                  <option value="monitoring">Continuous Monitoring</option>
                  <option value="exception">Risk Exception</option>
                  <option value="access_removal">Access Removal</option>
                  <option value="role_redesign">Role Redesign</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Justification / Notes</label>
                <textarea
                  value={mitigationNote}
                  onChange={(e) => setMitigationNote(e.target.value)}
                  rows={3}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                  placeholder="Describe the mitigation rationale..."
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 p-5 border-t border-gray-200 dark:border-gray-700">
              <Button size="sm" variant="secondary" onClick={() => setMitigatingViolation(null)}>Cancel</Button>
              <Button
                size="sm"
                disabled={!mitigationControl || mitigationSubmitting}
                onClick={async () => {
                  setMitigationSubmitting(true);
                  try {
                    await api.post('/mitigation/controls', {
                      risk_id: mitigatingViolation.id,
                      control_type: mitigationControl,
                      justification: mitigationNote,
                    });
                    toast.success(`Mitigation applied to ${mitigatingViolation.id}`);
                    setMitigatingViolation(null);
                    queryClient.invalidateQueries({ queryKey: ['risk-violations'] });
                  } catch {
                    toast.error('Failed to apply mitigation. Please try again.');
                  } finally {
                    setMitigationSubmitting(false);
                  }
                }}
              >
                {mitigationSubmitting ? 'Submitting...' : 'Apply Mitigation'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
