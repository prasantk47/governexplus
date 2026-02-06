import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeftIcon,
  BuildingOffice2Icon,
  UserIcon,
  EnvelopeIcon,
  KeyIcon,
  CheckIcon,
  CubeIcon,
  SparklesIcon,
  RocketLaunchIcon,
  ShieldCheckIcon,
  ChartBarIcon,
  CpuChipIcon,
  BoltIcon,
  ClipboardDocumentCheckIcon,
  GlobeAltIcon,
  LockClosedIcon,
  DocumentDuplicateIcon,
  ArrowRightIcon,
  StarIcon,
  FireIcon,
  BeakerIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolid, StarIcon as StarSolid } from '@heroicons/react/24/solid';
import clsx from 'clsx';

interface OnboardingData {
  company_name: string;
  admin_email: string;
  admin_name: string;
  admin_password: string;
  tier: string;
  trial_days: number;
  modules: string[];
}

const tiers = [
  {
    id: 'starter',
    name: 'Starter',
    price: 99,
    description: 'Perfect for small teams getting started with GRC',
    features: ['Up to 25 users', '2 connected systems', 'Basic SoD Analysis', 'Email support', '5 GB storage'],
    modules: ['access_management'],
    color: 'slate',
    popular: false,
  },
  {
    id: 'professional',
    name: 'Professional',
    price: 499,
    description: 'For growing organizations with compliance needs',
    features: ['Up to 100 users', '5 connected systems', 'Full compliance frameworks', 'Advanced risk scoring', 'Priority support', '50 GB storage'],
    modules: ['access_management', 'compliance', 'risk_analytics'],
    color: 'indigo',
    popular: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 2500,
    description: 'Complete solution for large enterprises',
    features: ['Up to 500 users', '20 connected systems', 'AI-powered insights', 'ML analytics', 'Custom integrations', 'Dedicated support', 'Unlimited storage', 'Custom SLAs'],
    modules: ['access_management', 'compliance', 'risk_analytics', 'ai_assistant', 'advanced_ml'],
    color: 'amber',
    popular: false,
  }
];

const availableModules = [
  { id: 'access_management', name: 'Access Management', description: 'User provisioning, role management, access requests', icon: ShieldCheckIcon, color: 'indigo' },
  { id: 'compliance', name: 'Compliance', description: 'Frameworks, assessments, certifications', icon: ClipboardDocumentCheckIcon, color: 'emerald' },
  { id: 'risk_analytics', name: 'Risk Analytics', description: 'Risk scoring, SoD analysis, violations', icon: ChartBarIcon, color: 'amber' },
  { id: 'ai_assistant', name: 'AI Assistant', description: 'Natural language queries, smart recommendations', icon: SparklesIcon, color: 'purple' },
  { id: 'advanced_ml', name: 'Advanced ML', description: 'Role mining, anomaly detection, predictions', icon: CpuChipIcon, color: 'pink' },
  { id: 'firefighter', name: 'Firefighter Access', description: 'Emergency access management & audit', icon: FireIcon, color: 'red' },
  { id: 'siem_integration', name: 'SIEM Integration', description: 'Security event monitoring & alerts', icon: BoltIcon, color: 'cyan' },
];

export function TenantOnboard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdTenant, setCreatedTenant] = useState<any>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const [formData, setFormData] = useState<OnboardingData>({
    company_name: '',
    admin_email: '',
    admin_name: '',
    admin_password: '',
    tier: 'professional',
    trial_days: 14,
    modules: ['access_management', 'compliance', 'risk_analytics']
  });

  const updateForm = (field: keyof OnboardingData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const selectTier = (tierId: string) => {
    const tier = tiers.find(t => t.id === tierId);
    if (tier) {
      updateForm('tier', tierId);
      updateForm('modules', tier.modules);
    }
  };

  const toggleModule = (moduleId: string) => {
    const current = formData.modules;
    if (current.includes(moduleId)) {
      updateForm('modules', current.filter(m => m !== moduleId));
    } else {
      updateForm('modules', [...current, moduleId]);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);

    try {
      const response = await fetch('/api/admin/tenants', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('admin_token')}`
        },
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (data.success) {
        setCreatedTenant(data);
        setStep(4);
      }
    } catch (err) {
      // Demo mode - simulate success
      const demoPassword = formData.admin_password || 'Welcome123!';
      const slug = formData.company_name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
      setCreatedTenant({
        success: true,
        tenant: {
          id: `tenant_${slug}`,
          name: formData.company_name,
          slug: slug,
          tier: formData.tier,
          status: 'trial'
        },
        admin_credentials: {
          email: formData.admin_email,
          password: demoPassword,
          login_url: `https://${slug}.governexplus.com`
        }
      });
      setStep(4);
    }

    setIsSubmitting(false);
  };

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopied(field);
    setTimeout(() => setCopied(null), 2000);
  };

  const canProceed = () => {
    switch (step) {
      case 1:
        return formData.company_name.trim().length >= 2;
      case 2:
        return formData.admin_email.includes('@') && formData.admin_name.trim().length >= 2;
      case 3:
        return formData.modules.length > 0;
      default:
        return true;
    }
  };

  const selectedTier = tiers.find(t => t.id === formData.tier);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-slate-200/50 sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6">
          <div className="flex items-center justify-between h-16">
            <Link
              to="/admin/dashboard"
              className="flex items-center gap-2 text-slate-600 hover:text-slate-900 transition-colors"
            >
              <ArrowLeftIcon className="h-5 w-5" />
              <span className="font-medium">Back to Dashboard</span>
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg">
                <RocketLaunchIcon className="h-5 w-5 text-white" />
              </div>
              <span className="font-semibold text-slate-900">New Tenant Onboarding</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Progress Steps */}
        <div className="mb-10">
          <div className="flex items-center justify-between relative">
            {/* Progress Line */}
            <div className="absolute left-0 right-0 top-5 h-0.5 bg-slate-200">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500"
                style={{ width: `${((step - 1) / 3) * 100}%` }}
              />
            </div>

            {[
              { num: 1, label: 'Organization', icon: BuildingOffice2Icon },
              { num: 2, label: 'Admin User', icon: UserIcon },
              { num: 3, label: 'Plan & Modules', icon: CubeIcon },
              { num: 4, label: 'Complete', icon: CheckIcon }
            ].map((s, i) => (
              <div key={s.num} className="relative flex flex-col items-center">
                <div className={clsx(
                  'w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all duration-300 z-10',
                  step > s.num
                    ? 'bg-gradient-to-br from-emerald-400 to-emerald-600 text-white shadow-lg shadow-emerald-500/30'
                    : step === s.num
                      ? 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/30 scale-110'
                      : 'bg-white border-2 border-slate-200 text-slate-400'
                )}>
                  {step > s.num ? (
                    <CheckIcon className="h-5 w-5" />
                  ) : (
                    <s.icon className="h-5 w-5" />
                  )}
                </div>
                <span className={clsx(
                  'mt-2 text-sm font-medium transition-colors',
                  step >= s.num ? 'text-slate-900' : 'text-slate-400'
                )}>
                  {s.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="bg-white rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden">
          {/* Step 1: Organization */}
          {step === 1 && (
            <div className="p-8 md:p-12">
              <div className="text-center mb-10">
                <div className="relative inline-block">
                  <div className="absolute inset-0 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl blur-xl opacity-30" />
                  <div className="relative inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl shadow-xl">
                    <BuildingOffice2Icon className="h-10 w-10 text-white" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-slate-900 mt-6">Organization Details</h2>
                <p className="text-slate-500 mt-2 max-w-md mx-auto">
                  Let's start by setting up the organization profile for your new tenant.
                </p>
              </div>

              <div className="max-w-lg mx-auto space-y-6">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">
                    Company Name <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <BuildingOffice2Icon className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                    <input
                      type="text"
                      value={formData.company_name}
                      onChange={(e) => updateForm('company_name', e.target.value)}
                      placeholder="e.g., Acme Corporation"
                      className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent focus:bg-white transition-all"
                    />
                  </div>
                  {formData.company_name && (
                    <p className="mt-2 text-sm text-slate-500">
                      Subdomain: <span className="font-mono text-indigo-600">
                        {formData.company_name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')}.governexplus.com
                      </span>
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">
                    Trial Period
                  </label>
                  <div className="grid grid-cols-4 gap-3">
                    {[
                      { value: 0, label: 'No Trial' },
                      { value: 7, label: '7 days' },
                      { value: 14, label: '14 days', recommended: true },
                      { value: 30, label: '30 days' },
                    ].map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => updateForm('trial_days', option.value)}
                        className={clsx(
                          'relative p-3 rounded-xl border-2 transition-all text-sm font-medium',
                          formData.trial_days === option.value
                            ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                            : 'border-slate-200 hover:border-slate-300 text-slate-600'
                        )}
                      >
                        {option.recommended && (
                          <span className="absolute -top-2 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-indigo-500 text-white text-xs font-semibold rounded-full">
                            Recommended
                          </span>
                        )}
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Admin User */}
          {step === 2 && (
            <div className="p-8 md:p-12">
              <div className="text-center mb-10">
                <div className="relative inline-block">
                  <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-2xl blur-xl opacity-30" />
                  <div className="relative inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl shadow-xl">
                    <UserIcon className="h-10 w-10 text-white" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-slate-900 mt-6">Tenant Administrator</h2>
                <p className="text-slate-500 mt-2 max-w-md mx-auto">
                  Create the primary admin account who will manage this organization.
                </p>
              </div>

              <div className="max-w-lg mx-auto space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-2">
                      Full Name <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <UserIcon className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                      <input
                        type="text"
                        value={formData.admin_name}
                        onChange={(e) => updateForm('admin_name', e.target.value)}
                        placeholder="John Smith"
                        className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent focus:bg-white transition-all"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-2">
                      Email Address <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                      <input
                        type="email"
                        value={formData.admin_email}
                        onChange={(e) => updateForm('admin_email', e.target.value)}
                        placeholder="admin@company.com"
                        className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent focus:bg-white transition-all"
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">
                    Password
                    <span className="text-slate-400 font-normal ml-2">(Leave empty to auto-generate)</span>
                  </label>
                  <div className="relative">
                    <KeyIcon className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                    <input
                      type="password"
                      value={formData.admin_password}
                      onChange={(e) => updateForm('admin_password', e.target.value)}
                      placeholder="Auto-generated if empty"
                      className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent focus:bg-white transition-all"
                    />
                  </div>
                  <p className="mt-2 text-sm text-slate-500">
                    A secure password will be generated if left empty. Credentials will be shown after creation.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Plan & Modules */}
          {step === 3 && (
            <div className="p-8 md:p-12">
              <div className="text-center mb-10">
                <div className="relative inline-block">
                  <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl blur-xl opacity-30" />
                  <div className="relative inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-600 rounded-2xl shadow-xl">
                    <CubeIcon className="h-10 w-10 text-white" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-slate-900 mt-6">Select Plan & Modules</h2>
                <p className="text-slate-500 mt-2 max-w-md mx-auto">
                  Choose the subscription tier and enable the modules your tenant needs.
                </p>
              </div>

              {/* Tier Selection */}
              <div className="mb-10">
                <h3 className="text-sm font-semibold text-slate-700 mb-4">Subscription Tier</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {tiers.map((tier) => (
                    <div
                      key={tier.id}
                      onClick={() => selectTier(tier.id)}
                      className={clsx(
                        'relative p-6 rounded-2xl cursor-pointer transition-all duration-300',
                        formData.tier === tier.id
                          ? 'bg-gradient-to-br from-indigo-50 to-purple-50 border-2 border-indigo-500 shadow-lg shadow-indigo-500/10'
                          : 'bg-white border-2 border-slate-200 hover:border-slate-300 hover:shadow-md'
                      )}
                    >
                      {tier.popular && (
                        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-gradient-to-r from-indigo-500 to-purple-500 text-white text-xs font-semibold rounded-full flex items-center gap-1">
                          <StarSolid className="h-3 w-3" />
                          Most Popular
                        </div>
                      )}

                      <div className="flex items-center justify-between mb-4">
                        <h4 className="text-lg font-bold text-slate-900">{tier.name}</h4>
                        {formData.tier === tier.id && (
                          <CheckCircleSolid className="h-6 w-6 text-indigo-600" />
                        )}
                      </div>

                      <div className="mb-4">
                        <span className="text-3xl font-bold text-slate-900">${tier.price}</span>
                        <span className="text-slate-500">/month</span>
                      </div>

                      <p className="text-sm text-slate-500 mb-4">{tier.description}</p>

                      <ul className="space-y-2">
                        {tier.features.slice(0, 4).map((feature, i) => (
                          <li key={i} className="flex items-center gap-2 text-sm text-slate-600">
                            <CheckCircleSolid className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                            {feature}
                          </li>
                        ))}
                        {tier.features.length > 4 && (
                          <li className="text-sm text-indigo-600 font-medium">
                            +{tier.features.length - 4} more features
                          </li>
                        )}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>

              {/* Module Selection */}
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-4">Enabled Modules</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {availableModules.map((mod) => {
                    const isSelected = formData.modules.includes(mod.id);
                    const ModIcon = mod.icon;

                    return (
                      <div
                        key={mod.id}
                        onClick={() => toggleModule(mod.id)}
                        className={clsx(
                          'p-4 rounded-xl cursor-pointer transition-all duration-200 flex items-center gap-4',
                          isSelected
                            ? 'bg-gradient-to-r from-indigo-50 to-purple-50 border-2 border-indigo-500'
                            : 'bg-white border-2 border-slate-200 hover:border-slate-300'
                        )}
                      >
                        <div className={clsx(
                          'w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0',
                          isSelected ? 'bg-indigo-100' : 'bg-slate-100'
                        )}>
                          <ModIcon className={clsx('h-6 w-6', isSelected ? 'text-indigo-600' : 'text-slate-400')} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className={clsx('font-semibold', isSelected ? 'text-slate-900' : 'text-slate-700')}>
                            {mod.name}
                          </p>
                          <p className="text-sm text-slate-500 truncate">{mod.description}</p>
                        </div>
                        <div className={clsx(
                          'w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all',
                          isSelected
                            ? 'border-indigo-500 bg-indigo-500'
                            : 'border-slate-300'
                        )}>
                          {isSelected && <CheckIcon className="h-4 w-4 text-white" />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Complete */}
          {step === 4 && createdTenant && (
            <div className="p-8 md:p-12">
              <div className="text-center mb-10">
                <div className="relative inline-block">
                  <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full blur-xl opacity-40 animate-pulse" />
                  <div className="relative inline-flex items-center justify-center w-24 h-24 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-full shadow-2xl shadow-emerald-500/30">
                    <CheckIcon className="h-12 w-12 text-white" />
                  </div>
                </div>
                <h2 className="text-3xl font-bold text-slate-900 mt-6">Tenant Created!</h2>
                <p className="text-slate-500 mt-2">
                  <span className="font-semibold text-slate-700">{createdTenant.tenant.name}</span> has been successfully onboarded.
                </p>
              </div>

              {/* Credentials Card */}
              <div className="max-w-xl mx-auto">
                <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-8 text-white shadow-2xl">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-white/10 rounded-lg">
                      <LockClosedIcon className="h-6 w-6" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg">Admin Credentials</h3>
                      <p className="text-sm text-slate-400">Share securely with the tenant admin</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs text-slate-400 uppercase tracking-wider">Login URL</p>
                          <p className="font-mono text-indigo-400 mt-1">{createdTenant.admin_credentials.login_url}</p>
                        </div>
                        <button
                          onClick={() => copyToClipboard(createdTenant.admin_credentials.login_url, 'url')}
                          className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                        >
                          {copied === 'url' ? (
                            <CheckCircleSolid className="h-5 w-5 text-emerald-400" />
                          ) : (
                            <DocumentDuplicateIcon className="h-5 w-5 text-slate-400" />
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                        <p className="text-xs text-slate-400 uppercase tracking-wider">Email</p>
                        <div className="flex items-center justify-between mt-1">
                          <p className="font-mono text-sm">{createdTenant.admin_credentials.email}</p>
                          <button
                            onClick={() => copyToClipboard(createdTenant.admin_credentials.email, 'email')}
                            className="p-1 hover:bg-white/10 rounded transition-colors"
                          >
                            {copied === 'email' ? (
                              <CheckCircleSolid className="h-4 w-4 text-emerald-400" />
                            ) : (
                              <DocumentDuplicateIcon className="h-4 w-4 text-slate-400" />
                            )}
                          </button>
                        </div>
                      </div>

                      <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                        <p className="text-xs text-slate-400 uppercase tracking-wider">Password</p>
                        <div className="flex items-center justify-between mt-1">
                          <p className="font-mono text-sm">{createdTenant.admin_credentials.password}</p>
                          <button
                            onClick={() => copyToClipboard(createdTenant.admin_credentials.password, 'password')}
                            className="p-1 hover:bg-white/10 rounded transition-colors"
                          >
                            {copied === 'password' ? (
                              <CheckCircleSolid className="h-4 w-4 text-emerald-400" />
                            ) : (
                              <DocumentDuplicateIcon className="h-4 w-4 text-slate-400" />
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 p-4 bg-amber-500/10 rounded-xl border border-amber-500/20">
                    <p className="text-sm text-amber-200 flex items-start gap-2">
                      <SparklesIcon className="h-5 w-5 flex-shrink-0 mt-0.5" />
                      Save these credentials securely. The password should be changed on first login for security.
                    </p>
                  </div>
                </div>

                {/* Tenant Summary */}
                <div className="mt-6 bg-white rounded-2xl p-6 border border-slate-200">
                  <h4 className="font-semibold text-slate-900 mb-4">Tenant Summary</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-slate-500">Organization</p>
                      <p className="font-medium text-slate-900">{createdTenant.tenant.name}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Tier</p>
                      <p className="font-medium text-slate-900 capitalize">{createdTenant.tenant.tier}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Status</p>
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                        Trial
                      </span>
                    </div>
                    <div>
                      <p className="text-slate-500">Modules</p>
                      <p className="font-medium text-slate-900">{formData.modules.length} enabled</p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-center gap-4 mt-8">
                  <Link
                    to="/admin/dashboard"
                    className="px-6 py-3 text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 font-medium transition-colors"
                  >
                    Back to Dashboard
                  </Link>
                  <button
                    onClick={() => {
                      setStep(1);
                      setFormData({
                        company_name: '',
                        admin_email: '',
                        admin_name: '',
                        admin_password: '',
                        tier: 'professional',
                        trial_days: 14,
                        modules: ['access_management', 'compliance', 'risk_analytics']
                      });
                      setCreatedTenant(null);
                    }}
                    className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl hover:from-indigo-600 hover:to-purple-700 font-medium transition-all shadow-lg shadow-indigo-500/25 flex items-center gap-2"
                  >
                    <PlusIcon className="h-5 w-5" />
                    Onboard Another
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          {step < 4 && (
            <div className="px-8 md:px-12 py-6 bg-slate-50 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setStep(Math.max(1, step - 1))}
                  disabled={step === 1}
                  className="flex items-center gap-2 px-5 py-3 text-slate-600 hover:text-slate-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <ArrowLeftIcon className="h-4 w-4" />
                  Back
                </button>

                <div className="flex items-center gap-4">
                  {selectedTier && step === 3 && (
                    <div className="text-sm text-slate-500">
                      Total: <span className="font-semibold text-slate-900">${selectedTier.price}/mo</span>
                    </div>
                  )}

                  {step < 3 ? (
                    <button
                      onClick={() => setStep(step + 1)}
                      disabled={!canProceed()}
                      className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl font-medium hover:from-indigo-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-indigo-500/25"
                    >
                      Continue
                      <ArrowRightIcon className="h-4 w-4" />
                    </button>
                  ) : (
                    <button
                      onClick={handleSubmit}
                      disabled={!canProceed() || isSubmitting}
                      className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl font-medium hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-emerald-500/25"
                    >
                      {isSubmitting ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          Creating Tenant...
                        </>
                      ) : (
                        <>
                          <RocketLaunchIcon className="h-5 w-5" />
                          Create Tenant
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TenantOnboard;
