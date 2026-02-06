import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  ArrowLeftIcon,
  FireIcon,
  ClockIcon,
  ShieldExclamationIcon,
  InformationCircleIcon,
  PlusIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  Card,
  Button,
  Badge,
  Select,
  Input,
  Textarea,
  RiskBadge,
} from '../../components/ui';

interface FirefighterId {
  id: string;
  name: string;
  description: string;
  system: string;
  riskLevel: 'high' | 'critical';
  maxDuration: string;
  available: boolean;
  requiresApproval: boolean;
}

interface ReasonCode {
  code: string;
  label: string;
  description: string;
  requires_ticket: boolean;
  requires_justification: boolean;
  default_priority: string;
  max_duration_hours: number;
  approval_chain: string[];
  sla_minutes: number;
  auto_approve_eligible: boolean;
  controller_review_sla_hours: number;
}

const firefighterIds: FirefighterId[] = [
  { id: 'FF_EMERGENCY_SAP_01', name: 'SAP Emergency Admin', description: 'Emergency administrative access to SAP ECC Production', system: 'SAP ECC', riskLevel: 'critical', maxDuration: '4 hours', available: true, requiresApproval: true },
  { id: 'FF_EMERGENCY_SAP_02', name: 'SAP Basis Emergency', description: 'Emergency Basis access for system maintenance', system: 'SAP ECC', riskLevel: 'critical', maxDuration: '2 hours', available: true, requiresApproval: true },
  { id: 'FF_ADMIN_AWS', name: 'AWS Production Admin', description: 'Emergency admin access to AWS production resources', system: 'AWS', riskLevel: 'critical', maxDuration: '2 hours', available: false, requiresApproval: true },
  { id: 'FF_ADMIN_DB', name: 'Database Admin', description: 'Emergency DBA access to production databases', system: 'Oracle DB', riskLevel: 'high', maxDuration: '4 hours', available: true, requiresApproval: true },
  { id: 'FF_HR_ADMIN', name: 'HR Emergency Admin', description: 'Emergency access to HR systems for critical updates', system: 'Workday', riskLevel: 'high', maxDuration: '2 hours', available: true, requiresApproval: false },
  { id: 'FF_NETWORK_ADMIN', name: 'Network Emergency', description: 'Emergency network administration access', system: 'Network Infrastructure', riskLevel: 'critical', maxDuration: '1 hour', available: true, requiresApproval: true },
];

const priorityVariant: Record<string, 'neutral' | 'info' | 'warning' | 'danger'> = {
  low: 'neutral',
  medium: 'info',
  high: 'warning',
  critical: 'danger',
};

export function FirefighterRequest() {
  const navigate = useNavigate();
  const [selectedFF, setSelectedFF] = useState<FirefighterId | null>(null);
  const [reasonCodes, setReasonCodes] = useState<ReasonCode[]>([]);
  const [selectedReasonCode, setSelectedReasonCode] = useState<ReasonCode | null>(null);
  const [reason, setReason] = useState('');
  const [businessJustification, setBusinessJustification] = useState('');
  const [plannedActions, setPlannedActions] = useState<string[]>([]);
  const [newAction, setNewAction] = useState('');
  const [duration, setDuration] = useState('60');
  const [ticketNumber, setTicketNumber] = useState('');
  const [acknowledged, setAcknowledged] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const fetchReasonCodes = async () => {
      try {
        const response = await api.get('/firefighter/reason-codes');
        setReasonCodes(response.data.reason_codes);
      } catch (error) {
        console.warn('Failed to fetch reason codes, using defaults');
        setReasonCodes([
          { code: 'prod_incident', label: 'Production Incident', description: 'Resolution of active production incident', requires_ticket: true, requires_justification: true, default_priority: 'critical', max_duration_hours: 4, approval_chain: ['ff_owner', 'it_manager'], sla_minutes: 15, auto_approve_eligible: false, controller_review_sla_hours: 24 },
          { code: 'change_management', label: 'Change Management', description: 'Implementation of pre-approved change', requires_ticket: true, requires_justification: false, default_priority: 'medium', max_duration_hours: 8, approval_chain: ['ff_owner'], sla_minutes: 60, auto_approve_eligible: true, controller_review_sla_hours: 48 },
          { code: 'audit_request', label: 'Audit Request', description: 'Access for audit verification', requires_ticket: true, requires_justification: true, default_priority: 'medium', max_duration_hours: 4, approval_chain: ['ff_owner', 'compliance_manager'], sla_minutes: 30, auto_approve_eligible: false, controller_review_sla_hours: 24 },
          { code: 'security_incident', label: 'Security Incident', description: 'Response to security event', requires_ticket: true, requires_justification: true, default_priority: 'critical', max_duration_hours: 4, approval_chain: ['security_manager', 'ciso'], sla_minutes: 10, auto_approve_eligible: false, controller_review_sla_hours: 8 },
          { code: 'data_correction', label: 'Data Correction', description: 'Critical data fix', requires_ticket: true, requires_justification: true, default_priority: 'high', max_duration_hours: 2, approval_chain: ['ff_owner', 'data_owner'], sla_minutes: 30, auto_approve_eligible: false, controller_review_sla_hours: 24 },
          { code: 'month_end', label: 'Month/Quarter/Year End', description: 'Period-end closing activities', requires_ticket: false, requires_justification: true, default_priority: 'high', max_duration_hours: 6, approval_chain: ['ff_owner', 'finance_manager'], sla_minutes: 30, auto_approve_eligible: true, controller_review_sla_hours: 48 },
          { code: 'system_maintenance', label: 'System Maintenance', description: 'System maintenance activity', requires_ticket: true, requires_justification: false, default_priority: 'medium', max_duration_hours: 8, approval_chain: ['ff_owner', 'it_manager'], sla_minutes: 60, auto_approve_eligible: true, controller_review_sla_hours: 72 },
          { code: 'disaster_recovery', label: 'Disaster Recovery', description: 'DR/BCP execution', requires_ticket: true, requires_justification: true, default_priority: 'critical', max_duration_hours: 8, approval_chain: ['ff_owner'], sla_minutes: 5, auto_approve_eligible: false, controller_review_sla_hours: 24 },
          { code: 'other', label: 'Other', description: 'Other reason - requires detailed justification', requires_ticket: true, requires_justification: true, default_priority: 'low', max_duration_hours: 2, approval_chain: ['ff_owner', 'security_manager'], sla_minutes: 120, auto_approve_eligible: false, controller_review_sla_hours: 24 },
        ]);
      }
    };
    fetchReasonCodes();
  }, []);

  const getDurationOptions = () => {
    const maxHours = selectedReasonCode?.max_duration_hours || 8;
    const options = [];
    if (maxHours >= 0.5) options.push({ value: '30', label: '30 minutes' });
    if (maxHours >= 1) options.push({ value: '60', label: '1 hour' });
    if (maxHours >= 2) options.push({ value: '120', label: '2 hours' });
    if (maxHours >= 4) options.push({ value: '240', label: '4 hours' });
    if (maxHours >= 6) options.push({ value: '360', label: '6 hours' });
    if (maxHours >= 8) options.push({ value: '480', label: '8 hours' });
    return options;
  };

  const addPlannedAction = () => {
    if (newAction.trim()) {
      setPlannedActions([...plannedActions, newAction.trim()]);
      setNewAction('');
    }
  };

  const removePlannedAction = (index: number) => {
    setPlannedActions(plannedActions.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!selectedFF || !selectedReasonCode || !acknowledged || isSubmitting) return;
    if (selectedReasonCode.requires_ticket && !ticketNumber) {
      toast.error('This reason code requires a ticket reference.');
      return;
    }
    if (selectedReasonCode.requires_justification && !businessJustification) {
      toast.error('This reason code requires a business justification.');
      return;
    }

    setIsSubmitting(true);
    try {
      const userInfo = { user_id: 'CURRENT_USER', name: 'Current User', email: 'user@company.com' };
      await api.post('/firefighter/requests', {
        requester_user_id: userInfo.user_id,
        requester_name: userInfo.name,
        requester_email: userInfo.email,
        target_system: selectedFF.system,
        firefighter_id: selectedFF.id,
        reason_code: selectedReasonCode.code,
        reason: reason,
        business_justification: businessJustification,
        planned_actions: plannedActions,
        duration_hours: parseInt(duration) / 60,
        ticket_reference: ticketNumber || undefined,
      });

      if (selectedFF.requiresApproval) {
        toast.success(`Emergency access requested for ${selectedFF.name}. Awaiting approval (SLA: ${selectedReasonCode.sla_minutes} min).`);
      } else {
        toast.success(`Emergency access for ${selectedFF.name} will be granted shortly.`);
      }
      navigate('/firefighter');
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Failed to submit emergency access request. Please try again.';
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const canSubmit = selectedFF && selectedReasonCode && acknowledged &&
    (!selectedReasonCode.requires_ticket || ticketNumber) &&
    (!selectedReasonCode.requires_justification || businessJustification);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center">
        <Link
          to="/firefighter"
          className="mr-4 p-2 text-gray-400 hover:text-gray-600 rounded-xl hover:bg-white/50 transition-colors"
        >
          <ArrowLeftIcon className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-xl font-semibold text-gray-900 tracking-tight">Request Emergency Access</h1>
          <p className="mt-1 text-sm text-gray-500">
            Request firefighter/emergency privileged access
          </p>
        </div>
      </div>

      {/* Warning Banner */}
      <div className="p-4 bg-red-50/80 border border-red-200/60 rounded-xl backdrop-blur-sm">
        <div className="flex items-start">
          <ShieldExclamationIcon className="h-6 w-6 text-red-600 mt-0.5" />
          <div className="ml-3">
            <h3 className="text-sm font-semibold text-red-800">Emergency Access Only</h3>
            <p className="mt-1 text-sm text-red-700">
              Firefighter access is for emergency situations only. All actions will be logged
              and audited. Misuse of emergency access is a policy violation.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Firefighter ID Selection */}
        <div className="lg:col-span-2">
          <Card>
            <div className="px-6 py-4 border-b border-white/20">
              <h2 className="text-sm font-semibold text-gray-900">Select Firefighter ID</h2>
              <p className="mt-1 text-xs text-gray-500">Choose the emergency access profile you need</p>
            </div>
            <div className="p-6 space-y-3">
              {firefighterIds.map((ff) => {
                const isSelected = selectedFF?.id === ff.id;
                return (
                  <div
                    key={ff.id}
                    onClick={() => ff.available && setSelectedFF(ff)}
                    className={`p-4 border rounded-xl transition-all duration-200 ${
                      !ff.available
                        ? 'bg-gray-50/50 border-gray-200/50 cursor-not-allowed opacity-60'
                        : isSelected
                        ? 'border-orange-400 bg-orange-50/50 cursor-pointer shadow-sm'
                        : 'border-white/40 bg-white/30 hover:border-gray-300 hover:bg-white/50 cursor-pointer'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start">
                        <div
                          className={`mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                            isSelected ? 'border-orange-600 bg-orange-600' : 'border-gray-300'
                          }`}
                        >
                          {isSelected && <div className="w-2 h-2 bg-white rounded-full" />}
                        </div>
                        <div className="ml-3">
                          <div className="flex items-center">
                            <FireIcon className="h-4 w-4 text-orange-500 mr-1" />
                            <span className="text-sm font-medium text-gray-900">{ff.name}</span>
                            <span className="ml-2 text-xs text-gray-500">({ff.id})</span>
                          </div>
                          <p className="mt-1 text-sm text-gray-500">{ff.description}</p>
                          <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
                            <span className="flex items-center">
                              <ClockIcon className="h-3 w-3 mr-1" />
                              Max: {ff.maxDuration}
                            </span>
                            <Badge variant="neutral" size="sm">{ff.system}</Badge>
                            {!ff.available && <Badge variant="danger" size="sm">In Use</Badge>}
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <RiskBadge level={ff.riskLevel} />
                        {ff.requiresApproval && (
                          <span className="text-xs text-gray-500">Requires Approval</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        {/* Request Details */}
        <div className="space-y-6">
          <Card padding="lg">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Reason Code *</h3>
            <Select
              value={selectedReasonCode?.code || ''}
              onChange={(e) => {
                const code = reasonCodes.find(rc => rc.code === e.target.value);
                setSelectedReasonCode(code || null);
                if (code && parseInt(duration) / 60 > code.max_duration_hours) {
                  setDuration(String(code.max_duration_hours * 60));
                }
              }}
              options={[
                { value: '', label: 'Select a reason code...' },
                ...reasonCodes.map((rc) => ({ value: rc.code, label: rc.label })),
              ]}
            />
            {selectedReasonCode && (
              <div className="mt-3 p-3 bg-white/40 backdrop-blur-sm rounded-xl text-xs">
                <p className="text-gray-600 mb-2">{selectedReasonCode.description}</p>
                <div className="flex flex-wrap gap-2">
                  <Badge variant={priorityVariant[selectedReasonCode.default_priority] || 'neutral'} size="sm">
                    {selectedReasonCode.default_priority.toUpperCase()} Priority
                  </Badge>
                  <Badge variant="neutral" size="sm">Max {selectedReasonCode.max_duration_hours}h</Badge>
                  <Badge variant="info" size="sm">SLA: {selectedReasonCode.sla_minutes} min</Badge>
                  {selectedReasonCode.requires_ticket && (
                    <Badge variant="warning" size="sm">Ticket Required</Badge>
                  )}
                  {selectedReasonCode.auto_approve_eligible && (
                    <Badge variant="success" size="sm">Auto-approve Eligible</Badge>
                  )}
                </div>
              </div>
            )}
          </Card>

          <Card padding="lg">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Access Duration</h3>
            <Select
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              options={getDurationOptions()}
            />
            <p className="mt-2 text-xs text-gray-500">Session will auto-terminate after this duration</p>
          </Card>

          <Card padding="lg">
            <h3 className="text-sm font-medium text-gray-900 mb-3">
              Incident/Change Ticket {selectedReasonCode?.requires_ticket ? '*' : ''}
            </h3>
            <Input
              value={ticketNumber}
              onChange={(e) => setTicketNumber(e.target.value)}
              placeholder="e.g., INC0012345"
            />
            <p className="mt-2 text-xs text-gray-500">
              {selectedReasonCode?.requires_ticket ? 'Required for this reason code' : 'Optional: Link to related ticket'}
            </p>
          </Card>

          {selectedReasonCode?.requires_justification && (
            <Card padding="lg">
              <h3 className="text-sm font-medium text-gray-900 mb-3">Business Justification *</h3>
              <Textarea
                value={businessJustification}
                onChange={(e) => setBusinessJustification(e.target.value)}
                rows={3}
                placeholder="Explain why this access is necessary..."
              />
            </Card>
          )}

          <Card padding="lg">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Additional Details</h3>
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              placeholder="Any additional details about the access needed..."
            />
          </Card>

          <Card padding="lg">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Planned Actions</h3>
            <p className="text-xs text-gray-500 mb-3">
              List the specific actions you plan to perform during this session
            </p>
            <div className="flex gap-2 mb-3">
              <Input
                value={newAction}
                onChange={(e) => setNewAction(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addPlannedAction()}
                placeholder="e.g., Run PA30 for employee update"
              />
              <button
                onClick={addPlannedAction}
                type="button"
                className="px-3 py-2 bg-white/50 backdrop-blur-sm text-gray-700 rounded-xl border border-white/40 hover:bg-white/70 transition-colors"
              >
                <PlusIcon className="h-5 w-5" />
              </button>
            </div>
            {plannedActions.length > 0 && (
              <ul className="space-y-2">
                {plannedActions.map((action, index) => (
                  <li key={index} className="flex items-center justify-between p-2 bg-white/40 backdrop-blur-sm rounded-xl">
                    <span className="text-sm text-gray-700">{action}</span>
                    <button onClick={() => removePlannedAction(index)} className="text-gray-400 hover:text-red-500 transition-colors">
                      <XMarkIcon className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card padding="lg">
            <div className="flex items-start">
              <input
                type="checkbox"
                id="acknowledge"
                checked={acknowledged}
                onChange={(e) => setAcknowledged(e.target.checked)}
                className="mt-1 h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded"
              />
              <label htmlFor="acknowledge" className="ml-2 text-sm text-gray-700">
                I acknowledge that this is for emergency use only and all my actions
                will be logged and audited. I understand misuse is a policy violation.
              </label>
            </div>
          </Card>

          <Button
            fullWidth
            onClick={handleSubmit}
            disabled={!canSubmit || isSubmitting}
            icon={<FireIcon className="h-5 w-5" />}
            loading={isSubmitting}
          >
            Request Emergency Access
          </Button>

          <div className="p-4 bg-blue-50/80 border border-blue-200/60 rounded-xl backdrop-blur-sm">
            <div className="flex items-start">
              <InformationCircleIcon className="h-5 w-5 text-blue-600 mt-0.5" />
              <div className="ml-2 text-xs text-blue-700">
                {selectedReasonCode ? (
                  <>
                    <p className="font-medium mb-1">Approval Process:</p>
                    <ul className="list-disc list-inside space-y-1">
                      <li>Approval chain: {selectedReasonCode.approval_chain.join(' \u2192 ')}</li>
                      <li>Approval SLA: {selectedReasonCode.sla_minutes} minutes</li>
                      <li>Post-session review: {selectedReasonCode.controller_review_sla_hours} hours</li>
                    </ul>
                  </>
                ) : (
                  <p>Select a reason code to see approval requirements.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
