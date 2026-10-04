import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ShieldCheckIcon,
  EyeSlashIcon,
  ClipboardDocumentCheckIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

// ─── Types ────────────────────────────────────────────────────────────────────

type ReportCategory = 'fraud' | 'corruption' | 'safety' | 'harassment' | 'other';

interface IntakeForm {
  category: ReportCategory | '';
  summary: string;
  details: string;
  is_anonymous: boolean;
  email: string;
}

interface SubmitResponse {
  case_reference: string;
  message: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_FORM: IntakeForm = {
  category: '',
  summary: '',
  details: '',
  is_anonymous: true,
  email: '',
};

const CATEGORY_OPTIONS: { value: ReportCategory; label: string; description: string }[] = [
  { value: 'fraud', label: 'Fraud', description: 'Financial fraud, misappropriation of funds' },
  { value: 'corruption', label: 'Corruption', description: 'Bribery, abuse of power, conflict of interest' },
  { value: 'safety', label: 'Safety', description: 'Workplace hazards, health & safety violations' },
  { value: 'harassment', label: 'Harassment', description: 'Workplace bullying, discrimination, harassment' },
  { value: 'other', label: 'Other', description: 'Other ethical concerns or misconduct' },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function WhistleblowerIntake() {
  const [form, setForm] = useState<IntakeForm>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof IntakeForm, string>>>({});
  const [submittedRef, setSubmittedRef] = useState<string | null>(null);
  const [lookupRef, setLookupRef] = useState('');
  const [lookupMode, setLookupMode] = useState(false);
  const [lookupResult, setLookupResult] = useState<{ status: string; updated_at: string } | null>(null);

  // ── Submit Mutation ──

  const submitMutation = useMutation<SubmitResponse, Error, IntakeForm>({
    mutationFn: data =>
      api
        .post('/whistleblower/submit', {
          ...data,
          email: data.is_anonymous ? undefined : data.email,
        })
        .then(r => r.data),
    onSuccess: data => {
      setSubmittedRef(data.case_reference);
    },
    onError: () => toast.error('Submission failed. Please try again.'),
  });

  const lookupMutation = useMutation({
    mutationFn: (ref: string) => api.get(`/whistleblower/status/${ref}`).then(r => r.data),
    onSuccess: data => setLookupResult(data),
    onError: () => toast.error('Reference not found or expired'),
  });

  // ── Handlers ──

  function validate(): boolean {
    const errors: Partial<Record<keyof IntakeForm, string>> = {};
    if (!form.category) errors.category = 'Please select a category';
    if (!form.summary.trim() || form.summary.length < 10) errors.summary = 'Provide at least 10 characters';
    if (!form.details.trim() || form.details.length < 20) errors.details = 'Please provide more detail (at least 20 characters)';
    if (!form.is_anonymous && !form.email.trim()) errors.email = 'Email is required when not anonymous';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    submitMutation.mutate(form);
  }

  function setField<K extends keyof IntakeForm>(key: K, value: IntakeForm[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Submitted State ──

  if (submittedRef) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl p-8 max-w-md w-full text-center space-y-6">
          <div className="flex justify-center">
            <div className="h-16 w-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
              <ClipboardDocumentCheckIcon className="h-9 w-9 text-green-600" />
            </div>
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Report Submitted
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Your report has been securely received. Your reference number is:
            </p>
          </div>
          <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-700 rounded-xl p-5">
            <p className="text-2xl font-mono font-bold text-indigo-600 dark:text-indigo-400 tracking-wider">
              {submittedRef}
            </p>
          </div>
          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 text-left">
            <p className="text-sm font-medium text-amber-800 dark:text-amber-300 mb-1">Important</p>
            <p className="text-sm text-amber-700 dark:text-amber-400">
              Save this reference number. You will need it to check the status of your report. We do not store it linked to your identity.
            </p>
          </div>
          <button
            onClick={() => {
              setForm(EMPTY_FORM);
              setSubmittedRef(null);
            }}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            Submit another report
          </button>
        </div>
      </div>
    );
  }

  // ── Main Form ──

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="h-14 w-14 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-lg">
              <ShieldCheckIcon className="h-8 w-8 text-white" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Confidential Reporting</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 max-w-md mx-auto">
            Report concerns anonymously and securely. All reports are reviewed by an independent compliance team.
          </p>
        </div>

        {/* Toggle Mode */}
        <div className="flex justify-center mb-6 gap-2">
          <button
            onClick={() => setLookupMode(false)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              !lookupMode
                ? 'bg-indigo-600 text-white'
                : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700 border border-gray-200 dark:border-slate-600'
            }`}
          >
            Submit Report
          </button>
          <button
            onClick={() => setLookupMode(true)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
              lookupMode
                ? 'bg-indigo-600 text-white'
                : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700 border border-gray-200 dark:border-slate-600'
            }`}
          >
            <MagnifyingGlassIcon className="h-4 w-4" />
            Check Status
          </button>
        </div>

        {lookupMode ? (
          /* Status Lookup */
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-lg p-8 space-y-5">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Check Report Status</h2>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Reference Number
              </label>
              <input
                type="text"
                value={lookupRef}
                onChange={e => setLookupRef(e.target.value.toUpperCase())}
                className="w-full text-sm font-mono border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 uppercase"
                placeholder="e.g. WB-2026-ABC123"
              />
            </div>
            <button
              onClick={() => lookupRef && lookupMutation.mutate(lookupRef)}
              disabled={!lookupRef || lookupMutation.isPending}
              className="w-full bg-indigo-600 text-white text-sm font-medium py-2.5 px-4 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {lookupMutation.isPending ? 'Looking up...' : 'Check Status'}
            </button>
            {lookupResult && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <p className="text-sm text-green-800 dark:text-green-300">
                  <span className="font-semibold">Status: </span>
                  {lookupResult.status}
                </p>
                <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                  Last updated: {new Date(lookupResult.updated_at).toLocaleString()}
                </p>
              </div>
            )}
          </div>
        ) : (
          /* Submission Form */
          <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-900 rounded-2xl shadow-lg p-8 space-y-6">
            {/* Category */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                Report Category <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {CATEGORY_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setField('category', opt.value)}
                    className={`text-left px-4 py-3 rounded-xl border transition-colors ${
                      form.category === opt.value
                        ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                        : 'border-gray-200 dark:border-slate-600 hover:border-gray-300 dark:hover:border-slate-500 text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    <p className="text-sm font-medium">{opt.label}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{opt.description}</p>
                  </button>
                ))}
              </div>
              {formErrors.category && (
                <p className="text-xs text-red-500 mt-1">{formErrors.category}</p>
              )}
            </div>

            {/* Summary */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Summary <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={form.summary}
                onChange={e => setField('summary', e.target.value)}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Brief description of the concern (e.g. suspected invoice fraud in Accounts Payable)"
              />
              {formErrors.summary && (
                <p className="text-xs text-red-500 mt-1">{formErrors.summary}</p>
              )}
            </div>

            {/* Details */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Details <span className="text-red-500">*</span>
              </label>
              <textarea
                value={form.details}
                onChange={e => setField('details', e.target.value)}
                rows={5}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                placeholder="Provide as much detail as possible: who, what, when, where, how. Include any relevant dates, amounts, or names of people involved."
              />
              {formErrors.details && (
                <p className="text-xs text-red-500 mt-1">{formErrors.details}</p>
              )}
            </div>

            {/* Anonymity Toggle */}
            <div className="border border-gray-200 dark:border-slate-600 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <EyeSlashIcon className="h-5 w-5 text-indigo-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Submit Anonymously
                    </p>
                    <p className="text-xs text-gray-400">
                      {form.is_anonymous
                        ? 'Your identity will not be recorded'
                        : 'Your email will be recorded for follow-up'}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setField('is_anonymous', !form.is_anonymous)}
                  className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none ${
                    form.is_anonymous ? 'bg-indigo-600' : 'bg-gray-200 dark:bg-slate-600'
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ${
                      form.is_anonymous ? 'translate-x-4' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>
              {!form.is_anonymous && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Email Address <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={e => setField('email', e.target.value)}
                    className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="your.email@example.com"
                  />
                  {formErrors.email && (
                    <p className="text-xs text-red-500 mt-1">{formErrors.email}</p>
                  )}
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={submitMutation.isPending}
              className="w-full bg-indigo-600 text-white text-sm font-semibold py-3 px-4 rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              {submitMutation.isPending ? 'Submitting...' : 'Submit Report Securely'}
            </button>

            <p className="text-xs text-center text-gray-400">
              All submissions are encrypted and reviewed by the compliance team. Retaliation against reporters is a serious violation of company policy.
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
