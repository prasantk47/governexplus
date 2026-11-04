import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ExclamationTriangleIcon,
  FireIcon,
  ClipboardDocumentCheckIcon,
  LockOpenIcon,
} from '@heroicons/react/24/outline';
import { PageHeader, Card, Button } from '../../components/ui';
import { firefighterApi } from '../../services/api';

interface BreakGlassResult {
  session_id: string;
  ffid: string;
  activated_by: string;
  incident_reference: string;
  expires_at: string;
  controller_id: string;
  requires_retrospective_approval: boolean;
  warning: string;
}

export function BreakGlass() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    ffid: '',
    incident_reference: '',
    reason: '',
    target_system: '',
  });
  const [result, setResult] = useState<BreakGlassResult | null>(null);

  const { data: ffidsData } = useQuery({
    queryKey: ['ffid-registry-bg'],
    queryFn: () => firefighterApi.listFirefighters().then(r => r.data),
  });
  const allFFIDs: any[] = Array.isArray(ffidsData) ? ffidsData : (ffidsData as any)?.firefighter_ids || [];
  const availableFFIDs = allFFIDs.filter(f => f.status === 'active' && !f.in_use);

  const activateMutation = useMutation({
    mutationFn: () => firefighterApi.breakGlass({
      ffid: form.ffid,
      activated_by: localStorage.getItem('userId') || 'admin',
      incident_reference: form.incident_reference,
      reason: form.reason,
      target_system: form.target_system || undefined,
    }),
    onSuccess: (res) => {
      setResult(res.data);
      toast.success('Break-glass session activated — retrospective review required');
      queryClient.invalidateQueries({ queryKey: ['ffid-registry-bg'] });
      queryClient.invalidateQueries({ queryKey: ['firefighterActiveSessions'] });
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.detail || 'Break-glass activation failed');
    },
  });

  const handleActivate = () => {
    if (!form.ffid || !form.incident_reference || !form.reason) {
      toast.error('FFID, incident reference, and reason are all required');
      return;
    }
    if (!confirm('WARNING: This bypasses the normal approval workflow. The session will be flagged for mandatory retrospective review. Proceed?')) {
      return;
    }
    activateMutation.mutate();
  };

  if (result) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Break-Glass Activated"
          subtitle="Emergency session is live — retrospective review is mandatory"
        />
        <Card>
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 mb-5">
            <div className="flex items-center gap-3 mb-3">
              <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
              <span className="text-sm font-semibold text-red-700">{result.warning}</span>
            </div>
          </div>
          <dl className="grid grid-cols-2 gap-4">
            {[
              ['Session ID', result.session_id],
              ['FFID', result.ffid],
              ['Activated By', result.activated_by],
              ['Incident Reference', result.incident_reference],
              ['Expires At', new Date(result.expires_at).toLocaleString()],
              ['Assigned Controller', result.controller_id],
            ].map(([label, value]) => (
              <div key={label as string}>
                <dt className="text-xs text-gray-500">{label}</dt>
                <dd className="text-sm font-medium text-gray-900 mt-0.5 font-mono">{value}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-6 flex gap-3">
            <Button
              onClick={() => { setResult(null); setForm({ ffid: '', incident_reference: '', reason: '', target_system: '' }); }}
            >
              Activate Another
            </Button>
            <Button variant="secondary" href="/privileged-access/sessions">
              View Sessions
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Break-Glass Emergency Access"
        subtitle="Emergency bypass when normal GRC approval is unavailable — requires retrospective review"
      />

      {/* Warning banner */}
      <div className="bg-red-50 border border-red-200 rounded-2xl p-5 flex items-start gap-4">
        <div className="flex-shrink-0 h-10 w-10 rounded-xl bg-red-100 flex items-center justify-center">
          <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-red-700 mb-1">Emergency Use Only</h3>
          <p className="text-sm text-red-600">
            Break-glass bypasses the standard approval workflow. It should ONLY be used when the GRC system is
            unavailable or a critical incident demands immediate access with no time for approval.
            All break-glass sessions are <strong>mandatory retrospective review</strong> items and are
            escalated to the FFID controller and security team automatically.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form */}
        <div className="lg:col-span-2">
          <Card>
            <h2 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <LockOpenIcon className="h-4 w-4 text-red-500" />
              Emergency Activation
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Firefighter ID *</label>
                <select
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500"
                  value={form.ffid}
                  onChange={e => setForm(prev => ({ ...prev, ffid: e.target.value }))}
                >
                  <option value="">Select FFID...</option>
                  {availableFFIDs.map(f => (
                    <option key={f.ffid} value={f.ffid}>
                      {f.ffid} — {f.description} ({f.target_system})
                    </option>
                  ))}
                </select>
                {availableFFIDs.length === 0 && (
                  <p className="text-xs text-orange-600 mt-1">No available FFIDs — all may be in use or no active FFIDs exist.</p>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Incident / Ticket Reference *</label>
                <input
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="INC-2026-04821 or JIRA-1234"
                  value={form.incident_reference}
                  onChange={e => setForm(prev => ({ ...prev, incident_reference: e.target.value }))}
                />
                <p className="text-xs text-gray-400 mt-1">Reference to the incident, change, or ticket that requires this emergency access</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Emergency Justification *</label>
                <textarea
                  rows={4}
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500 resize-none"
                  placeholder="Describe the emergency situation and why normal approval is not possible..."
                  value={form.reason}
                  onChange={e => setForm(prev => ({ ...prev, reason: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Target System (optional)</label>
                <input
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="SAP_PRD"
                  value={form.target_system}
                  onChange={e => setForm(prev => ({ ...prev, target_system: e.target.value }))}
                />
              </div>

              <Button
                onClick={handleActivate}
                disabled={activateMutation.isPending}
                className="w-full bg-red-600 hover:bg-red-700 text-white"
                icon={<FireIcon className="h-4 w-4" />}
              >
                {activateMutation.isPending ? 'Activating...' : 'Activate Break-Glass Session'}
              </Button>
            </div>
          </Card>
        </div>

        {/* Info panel */}
        <div className="space-y-4">
          <Card>
            <h3 className="text-xs font-semibold text-gray-700 uppercase mb-3 flex items-center gap-2">
              <ClipboardDocumentCheckIcon className="h-4 w-4 text-gray-400" />
              What happens next
            </h3>
            <ol className="space-y-3">
              {[
                'Session is activated immediately — no approval required',
                'Controller and security team are notified by email',
                'Session is flagged as BREAK_GLASS in the audit log',
                'Session expires at the FFID maximum duration',
                'Controller must review and approve retrospectively',
                'All activity is captured in the EAM log',
              ].map((step, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                  <span className="flex-shrink-0 h-5 w-5 rounded-full bg-red-100 text-red-700 font-semibold text-xs flex items-center justify-center">{i + 1}</span>
                  {step}
                </li>
              ))}
            </ol>
          </Card>

          <Card>
            <h3 className="text-xs font-semibold text-gray-700 uppercase mb-3">Available FFIDs</h3>
            {availableFFIDs.length === 0 ? (
              <p className="text-xs text-gray-400">No FFIDs currently available</p>
            ) : (
              <div className="space-y-2">
                {availableFFIDs.slice(0, 5).map(f => (
                  <div key={f.ffid} className="text-xs">
                    <span className="font-mono font-semibold text-indigo-700">{f.ffid}</span>
                    <span className="text-gray-500 ml-1">· {f.emergency_function} · {f.region}</span>
                  </div>
                ))}
                {availableFFIDs.length > 5 && (
                  <p className="text-xs text-gray-400">+{availableFFIDs.length - 5} more</p>
                )}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
