import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  EnvelopeIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/react/24/outline';
import { smtpConfigApi } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
} from '../../components/ui';

interface SmtpFormData {
  host: string;
  port: number;
  username: string;
  password: string;
  from_email: string;
  from_name: string;
  use_tls: boolean;
  is_enabled: boolean;
}

const PRESET_PROVIDERS = [
  { label: 'Gmail', host: 'smtp.gmail.com', port: 587, use_tls: true },
  { label: 'Outlook / Office 365', host: 'smtp.office365.com', port: 587, use_tls: true },
  { label: 'SendGrid', host: 'smtp.sendgrid.net', port: 587, use_tls: true },
  { label: 'Mailgun', host: 'smtp.mailgun.org', port: 587, use_tls: true },
  { label: 'Amazon SES (US East)', host: 'email-smtp.us-east-1.amazonaws.com', port: 587, use_tls: true },
  { label: 'Custom', host: '', port: 587, use_tls: true },
];

export function SmtpSettings() {
  const queryClient = useQueryClient();
  const [showPassword, setShowPassword] = useState(false);
  const [testEmail, setTestEmail] = useState('');
  const [isTesting, setIsTesting] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  const { data: saved, isLoading } = useQuery({
    queryKey: ['smtp-config'],
    queryFn: () => smtpConfigApi.get().then((r) => r.data),
  });

  const [form, setForm] = useState<SmtpFormData>({
    host: '',
    port: 587,
    username: '',
    password: '',
    from_email: 'noreply@governexplus.com',
    from_name: 'GovernexPlus',
    use_tls: true,
    is_enabled: true,
  });

  // Populate form once data loads (but only if not dirty)
  if (saved && !isDirty && form.host === '' && saved.host) {
    setForm({
      host: saved.host || '',
      port: saved.port || 587,
      username: saved.username || '',
      password: '', // never prefill password
      from_email: saved.from_email || 'noreply@governexplus.com',
      from_name: saved.from_name || 'GovernexPlus',
      use_tls: saved.use_tls ?? true,
      is_enabled: saved.is_enabled ?? true,
    });
  }

  const saveMutation = useMutation({
    mutationFn: (data: SmtpFormData) => smtpConfigApi.save(data),
    onSuccess: () => {
      toast.success('SMTP configuration saved');
      queryClient.invalidateQueries({ queryKey: ['smtp-config'] });
      setIsDirty(false);
    },
    onError: () => toast.error('Failed to save SMTP configuration'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => smtpConfigApi.delete(),
    onSuccess: () => {
      toast.success('SMTP configuration removed');
      queryClient.invalidateQueries({ queryKey: ['smtp-config'] });
      setForm({ host: '', port: 587, username: '', password: '', from_email: 'noreply@governexplus.com', from_name: 'GovernexPlus', use_tls: true, is_enabled: true });
      setIsDirty(false);
    },
    onError: () => toast.error('Failed to remove configuration'),
  });

  const handlePreset = (preset: typeof PRESET_PROVIDERS[0]) => {
    setForm((f) => ({ ...f, host: preset.host, port: preset.port, use_tls: preset.use_tls }));
    setIsDirty(true);
  };

  const handleChange = (field: keyof SmtpFormData, value: string | number | boolean) => {
    setForm((f) => ({ ...f, [field]: value }));
    setIsDirty(true);
  };

  const handleSave = () => {
    if (!form.host || !form.username || !form.password) {
      toast.error('Host, username, and password are required');
      return;
    }
    saveMutation.mutate(form);
  };

  const handleTest = async () => {
    if (!testEmail) { toast.error('Enter a recipient email for the test'); return; }
    setIsTesting(true);
    const toastId = toast.loading('Sending test email...');
    try {
      await smtpConfigApi.test({
        to: testEmail,
        host: form.host || undefined,
        port: form.port || undefined,
        username: form.username || undefined,
        password: form.password || undefined,
        from_email: form.from_email || undefined,
        use_tls: form.use_tls,
      });
      toast.success('Test email sent! Check your inbox.', { id: toastId });
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Test failed';
      toast.error(detail, { id: toastId });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Email (SMTP) Configuration"
        subtitle="Configure the SMTP server used to send notification emails to your users"
      />

      {/* Status banner */}
      {!isLoading && (
        <div className={`flex items-center gap-3 p-4 rounded-xl border ${
          saved?.configured && saved?.is_enabled
            ? 'bg-green-50 border-green-200'
            : 'bg-yellow-50 border-yellow-200'
        }`}>
          {saved?.configured && saved?.is_enabled ? (
            <>
              <CheckCircleIcon className="h-5 w-5 text-green-500 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-green-800">SMTP configured and active</p>
                <p className="text-xs text-green-600">Emails will be sent via {saved.host}</p>
              </div>
            </>
          ) : (
            <>
              <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-yellow-800">No SMTP configured</p>
                <p className="text-xs text-yellow-600">Notifications are logged but not sent. Configure below to enable email delivery.</p>
              </div>
            </>
          )}
        </div>
      )}

      {/* Provider presets */}
      <Card padding="md">
        <p className="text-sm font-medium text-gray-700 mb-3">Quick Setup — Choose Your Provider</p>
        <div className="flex flex-wrap gap-2">
          {PRESET_PROVIDERS.map((p) => (
            <button
              key={p.label}
              onClick={() => handlePreset(p)}
              className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-primary-400 hover:text-primary-700 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>
      </Card>

      {/* Config form */}
      <Card padding="md">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* SMTP Host */}
          <div className="md:col-span-2 flex items-center gap-3">
            <label className="block text-sm font-medium text-gray-700 mb-1">Enable SMTP</label>
            <button
              onClick={() => handleChange('is_enabled', !form.is_enabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                form.is_enabled ? 'bg-primary-600' : 'bg-gray-300'
              }`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                form.is_enabled ? 'translate-x-6' : 'translate-x-1'
              }`} />
            </button>
            <span className="text-xs text-gray-500">{form.is_enabled ? 'Active — emails will be sent' : 'Disabled — emails will be logged only'}</span>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">SMTP Host <span className="text-red-500">*</span></label>
            <input
              type="text"
              value={form.host}
              onChange={(e) => handleChange('host', e.target.value)}
              placeholder="smtp.gmail.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
            <input
              type="number"
              value={form.port}
              onChange={(e) => handleChange('port', parseInt(e.target.value) || 587)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username / Email <span className="text-red-500">*</span></label>
            <input
              type="email"
              value={form.username}
              onChange={(e) => handleChange('username', e.target.value)}
              placeholder="alerts@yourcompany.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password / App Password <span className="text-red-500">*</span></label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={form.password}
                onChange={(e) => handleChange('password', e.target.value)}
                placeholder={saved?.configured ? '••••••••  (leave blank to keep saved)' : 'Enter password'}
                className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showPassword ? <EyeSlashIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From Email</label>
            <input
              type="email"
              value={form.from_email}
              onChange={(e) => handleChange('from_email', e.target.value)}
              placeholder="noreply@yourcompany.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From Name</label>
            <input
              type="text"
              value={form.from_name}
              onChange={(e) => handleChange('from_name', e.target.value)}
              placeholder="GovernexPlus"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleChange('use_tls', !form.use_tls)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                form.use_tls ? 'bg-primary-600' : 'bg-gray-300'
              }`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                form.use_tls ? 'translate-x-6' : 'translate-x-1'
              }`} />
            </button>
            <div>
              <p className="text-sm font-medium text-gray-700">Use STARTTLS</p>
              <p className="text-xs text-gray-500">Recommended for port 587. Disable for port 465 (SSL) or unencrypted.</p>
            </div>
          </div>
        </div>

        <div className="mt-5 flex items-center gap-3 pt-4 border-t border-gray-100">
          <Button
            onClick={handleSave}
            loading={saveMutation.isPending}
            disabled={saveMutation.isPending}
          >
            Save Configuration
          </Button>
          {saved?.configured && (
            <Button
              variant="danger"
              onClick={() => {
                if (confirm('Remove SMTP configuration? Emails will fall back to system defaults.')) {
                  deleteMutation.mutate();
                }
              }}
              loading={deleteMutation.isPending}
            >
              Remove
            </Button>
          )}
        </div>
      </Card>

      {/* Test section */}
      <Card padding="md">
        <div className="flex items-start gap-4">
          <div className="p-2 bg-primary-50 rounded-lg flex-shrink-0">
            <EnvelopeIcon className="h-5 w-5 text-primary-600" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-900">Send Test Email</p>
            <p className="text-xs text-gray-500 mt-0.5">Verify your configuration by sending a test email. Uses the settings in the form above (unsaved changes are included).</p>
            <div className="mt-3 flex items-center gap-3">
              <input
                type="email"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                placeholder="your@email.com"
                className="flex-1 max-w-xs px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <Button
                variant="secondary"
                onClick={handleTest}
                loading={isTesting}
                disabled={isTesting || !form.host}
              >
                Send Test
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Help text */}
      <Card padding="md">
        <p className="text-xs font-medium text-gray-700 mb-2">Setup Tips</p>
        <ul className="space-y-1 text-xs text-gray-500 list-disc list-inside">
          <li><strong>Gmail:</strong> Use an App Password (not your account password). Enable 2FA first, then create an App Password at myaccount.google.com/apppasswords.</li>
          <li><strong>Office 365:</strong> Use your full email as username. May require enabling SMTP AUTH in Exchange admin.</li>
          <li><strong>SendGrid:</strong> Username is <code className="bg-gray-100 px-1 rounded">apikey</code>, password is your SendGrid API key.</li>
          <li><strong>Port 587 + STARTTLS</strong> is the modern standard. Use port 465 + SSL (disable STARTTLS) for legacy servers.</li>
        </ul>
      </Card>
    </div>
  );
}
