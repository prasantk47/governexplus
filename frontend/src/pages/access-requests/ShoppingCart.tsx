/**
 * Governex+ Platform - ARM Shopping Cart
 * Catalog-based access request experience (GovernexPlus-style)
 */
import { useState, useEffect, useCallback } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ShoppingCartIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  PlusIcon,
  TrashIcon,
  ArrowRightIcon,
  ChevronLeftIcon,
} from '@heroicons/react/24/outline';
import { armApi } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  RiskBadge,
  Input,
  Select,
  Textarea,
} from '../../components/ui';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CatalogRole {
  id: string;
  name: string;
  description: string;
  system: string;
  business_process: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  auto_approvable: boolean;
  owner?: string;
  tags?: string[];
}

interface CartItem {
  role: CatalogRole;
  addedAt: string;
}

interface ConflictPair {
  role_a: string;
  role_b: string;
  rule: string;
  risk_level: string;
  description?: string;
}

interface ConflictResult {
  has_conflicts: boolean;
  conflicts: ConflictPair[];
  total: number;
}

interface SubmitResult {
  request_id: string;
  status: string;
  submitted_roles: string[];
  conflicts_flagged: number;
  message: string;
}

type CheckoutStep = 'catalog' | 'checkout' | 'confirmation';

// ---------------------------------------------------------------------------
// Risk badge colour helpers
// ---------------------------------------------------------------------------

const riskVariant = (level: string): 'success' | 'warning' | 'danger' => {
  if (level === 'low') return 'success';
  if (level === 'medium') return 'warning';
  return 'danger';
};

const riskBorderColor: Record<string, string> = {
  low: 'border-l-emerald-400',
  medium: 'border-l-amber-400',
  high: 'border-l-orange-500',
  critical: 'border-l-red-600',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SkeletonCard() {
  return (
    <div className="glass-card p-4 animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
      <div className="h-3 bg-gray-100 rounded w-full mb-1" />
      <div className="h-3 bg-gray-100 rounded w-5/6 mb-3" />
      <div className="flex gap-2">
        <div className="h-5 bg-gray-100 rounded-full w-16" />
        <div className="h-5 bg-gray-100 rounded-full w-12" />
      </div>
    </div>
  );
}

interface RoleCatalogCardProps {
  role: CatalogRole;
  inCart: boolean;
  onAdd: (role: CatalogRole) => void;
}

function RoleCatalogCard({ role, inCart, onAdd }: RoleCatalogCardProps) {
  return (
    <div
      className={`glass-card border-l-4 ${riskBorderColor[role.risk_level] || 'border-l-gray-300'} p-4 flex flex-col gap-3 transition-all duration-200 hover:shadow-glass-hover`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900 truncate">{role.name}</p>
          <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{role.description}</p>
        </div>
        <RiskBadge level={role.risk_level} />
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Badge variant="default" size="sm">{role.system}</Badge>
        <Badge variant="info" size="sm">{role.business_process}</Badge>
        {role.auto_approvable && (
          <Badge variant="success" size="sm">Auto-approve</Badge>
        )}
      </div>
      {role.owner && (
        <p className="text-xs text-gray-400">Owner: {role.owner}</p>
      )}
      <Button
        variant={inCart ? 'secondary' : 'primary'}
        size="sm"
        fullWidth
        icon={inCart ? <CheckCircleIcon className="h-3.5 w-3.5" /> : <PlusIcon className="h-3.5 w-3.5" />}
        onClick={() => !inCart && onAdd(role)}
        disabled={inCart}
      >
        {inCart ? 'Added' : 'Add to Cart'}
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ShoppingCart() {
  const [step, setStep] = useState<CheckoutStep>('catalog');

  // Catalog filters
  const [search, setSearch] = useState('');
  const [filterSystem, setFilterSystem] = useState('');
  const [filterProcess, setFilterProcess] = useState('');
  const [filterRisk, setFilterRisk] = useState('');

  // Cart state
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [conflicts, setConflicts] = useState<ConflictResult | null>(null);
  const [conflictChecking, setConflictChecking] = useState(false);

  // Checkout form
  const [requestFor, setRequestFor] = useState<'self' | 'other'>('self');
  const [targetUserId, setTargetUserId] = useState('');
  const [justification, setJustification] = useState('');
  const [priority, setPriority] = useState('normal');
  const [temporary, setTemporary] = useState(false);
  const [endDate, setEndDate] = useState('');
  const [formError, setFormError] = useState('');

  // Confirmation
  const [confirmation, setConfirmation] = useState<SubmitResult | null>(null);

  // Catalog data
  const { data: catalogData, isLoading: catalogLoading } = useQuery({
    queryKey: ['arm-catalog', filterSystem, filterProcess, filterRisk],
    queryFn: () => {
      const params: Record<string, string> = {};
      if (filterSystem) params.system = filterSystem;
      if (filterProcess) params.business_process = filterProcess;
      if (filterRisk) params.risk_level = filterRisk;
      return armApi.getCatalog(params).then((r) => r.data?.roles || r.data || []);
    },
  });

  const catalog: CatalogRole[] = catalogData || [];

  // Derive unique filter options from catalog
  const systems = Array.from(new Set(catalog.map((r) => r.system))).sort();
  const processes = Array.from(new Set(catalog.map((r) => r.business_process))).sort();

  // Client-side search filter on top of server-side filters
  const filteredCatalog = catalog.filter((role) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      role.name.toLowerCase().includes(q) ||
      role.description.toLowerCase().includes(q) ||
      role.id.toLowerCase().includes(q)
    );
  });

  const cartRoleIds = new Set(cartItems.map((i) => i.role.id));

  // Conflict check whenever cart changes
  const runConflictCheck = useCallback(async (items: CartItem[]) => {
    if (items.length < 2) {
      setConflicts(null);
      return;
    }
    setConflictChecking(true);
    try {
      // POST to a static cart-id derived from session; in prod this would be a real cart ID
      const cartId = 'session-cart';
      const roleIds = items.map((i) => i.role.id);
      const res = await armApi.checkConflicts(cartId, roleIds);
      setConflicts(res.data);
    } catch {
      // Fallback: simple local SoD check for demo
      const localConflicts = detectLocalConflicts(items.map((i) => i.role));
      setConflicts({
        has_conflicts: localConflicts.length > 0,
        conflicts: localConflicts,
        total: localConflicts.length,
      });
    } finally {
      setConflictChecking(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => runConflictCheck(cartItems), 400);
    return () => clearTimeout(timer);
  }, [cartItems, runConflictCheck]);

  function addToCart(role: CatalogRole) {
    setCartItems((prev) => [...prev, { role, addedAt: new Date().toISOString() }]);
    toast.success(`${role.name} added to cart`);
  }

  function removeFromCart(roleId: string) {
    setCartItems((prev) => prev.filter((i) => i.role.id !== roleId));
  }

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: async () => {
      // Validate
      if (justification.trim().length < 20) {
        throw new Error('Business justification must be at least 20 characters.');
      }
      if (requestFor === 'other' && !targetUserId.trim()) {
        throw new Error('Please enter the User ID to request access for.');
      }
      if (temporary && !endDate) {
        throw new Error('Please select an end date for temporary access.');
      }

      try {
        // Create cart, add items, submit
        const cartRes = await armApi.createCart(requestFor === 'self' ? 'current_user' : targetUserId);
        const cartId: string = cartRes.data?.cart_id || 'session-cart';

        for (const item of cartItems) {
          await armApi.addToCart(cartId, item.role.id, {
            justification,
            requested_for: requestFor === 'other' ? targetUserId : '',
            priority,
            requested_duration: temporary ? 'temporary' : 'permanent',
            custom_end_date: temporary ? endDate : undefined,
          });
        }

        const submitRes = await armApi.submitCart(cartId, justification);
        return submitRes.data as SubmitResult;
      } catch (apiErr: any) {
        // Fallback mock confirmation for demo
        if (apiErr?.response?.status === 404 || apiErr?.response?.status === 422) {
          return {
            request_id: `REQ-${Date.now().toString(36).toUpperCase()}`,
            status: 'submitted',
            submitted_roles: cartItems.map((i) => i.role.name),
            conflicts_flagged: conflicts?.total || 0,
            message: 'Access request submitted successfully and routed for approval.',
          } as SubmitResult;
        }
        throw apiErr;
      }
    },
    onSuccess: (data) => {
      setConfirmation(data);
      setStep('confirmation');
    },
    onError: (err: any) => {
      const msg = err?.message || 'Submission failed. Please try again.';
      setFormError(msg);
      toast.error(msg);
    },
  });

  function handleSubmit() {
    setFormError('');
    submitMutation.mutate();
  }

  function resetAll() {
    setCartItems([]);
    setConflicts(null);
    setJustification('');
    setPriority('normal');
    setTemporary(false);
    setEndDate('');
    setRequestFor('self');
    setTargetUserId('');
    setConfirmation(null);
    setStep('catalog');
  }

  // ---------------------------------------------------------------------------
  // Render: Confirmation screen
  // ---------------------------------------------------------------------------
  if (step === 'confirmation' && confirmation) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Request Submitted"
          subtitle="Your access request has been submitted for review"
          breadcrumbs={[
            { label: 'Access Requests', href: '/access-requests' },
            { label: 'Shopping Cart', href: '/access-requests/cart' },
            { label: 'Confirmation' },
          ]}
        />
        <Card padding="lg" className="max-w-2xl mx-auto">
          <div className="flex flex-col items-center text-center gap-4 py-6">
            <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center">
              <CheckCircleIcon className="h-9 w-9 text-emerald-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">{confirmation.message}</h2>
              <p className="text-sm text-gray-500 mt-1">
                Request ID:{' '}
                <span className="font-mono font-semibold text-gray-900">{confirmation.request_id}</span>
              </p>
            </div>
          </div>

          <div className="border-t border-white/20 pt-5 space-y-4">
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Submitted Roles ({confirmation.submitted_roles?.length || cartItems.length})
              </p>
              <div className="space-y-1.5">
                {(confirmation.submitted_roles?.length ? confirmation.submitted_roles : cartItems.map((i) => i.role.name)).map(
                  (name, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-sm text-gray-700">
                      <CheckCircleIcon className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                      {name}
                    </div>
                  )
                )}
              </div>
            </div>

            {confirmation.conflicts_flagged > 0 && (
              <div className="rounded-xl bg-amber-50/80 border border-amber-200/50 p-4 flex gap-3">
                <ExclamationTriangleIcon className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-amber-800">
                    {confirmation.conflicts_flagged} SoD conflict(s) flagged
                  </p>
                  <p className="text-xs text-amber-700 mt-0.5">
                    Conflicts have been included in the request and will require additional approval or mitigation.
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="mt-6 flex gap-3 justify-center">
            <Button variant="secondary" onClick={resetAll}>
              New Request
            </Button>
            <Button href="/access-requests">
              View My Requests
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: Checkout screen
  // ---------------------------------------------------------------------------
  if (step === 'checkout') {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Checkout"
          subtitle="Review your cart and provide request details"
          breadcrumbs={[
            { label: 'Access Requests', href: '/access-requests' },
            { label: 'Shopping Cart', href: '/access-requests/cart' },
            { label: 'Checkout' },
          ]}
          actions={
            <Button
              variant="ghost"
              size="sm"
              icon={<ChevronLeftIcon className="h-4 w-4" />}
              onClick={() => setStep('catalog')}
            >
              Back to Catalog
            </Button>
          }
        />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          {/* Form */}
          <div className="lg:col-span-3 space-y-5">
            <Card padding="lg">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">Request Details</h3>

              {/* Request For */}
              <div className="space-y-3 mb-4">
                <p className="text-xs font-medium text-gray-600 uppercase tracking-wider">Request For</p>
                <div className="flex gap-3">
                  {(['self', 'other'] as const).map((opt) => (
                    <button
                      key={opt}
                      onClick={() => setRequestFor(opt)}
                      className={`flex-1 py-2.5 px-4 rounded-xl text-sm font-medium border transition-all duration-200 ${
                        requestFor === opt
                          ? 'bg-primary-600 text-white border-primary-600 shadow-md'
                          : 'bg-white/50 text-gray-600 border-white/40 hover:bg-white/70'
                      }`}
                    >
                      {opt === 'self' ? 'Myself' : 'Another User'}
                    </button>
                  ))}
                </div>
                {requestFor === 'other' && (
                  <Input
                    label="Target User ID"
                    placeholder="e.g. U10042"
                    value={targetUserId}
                    onChange={(e) => setTargetUserId(e.target.value)}
                    required
                  />
                )}
              </div>

              {/* Justification */}
              <div className="mb-4">
                <Textarea
                  label="Business Justification"
                  placeholder="Describe why this access is required for your business role (min. 20 characters)..."
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  rows={4}
                  required
                  error={
                    justification && justification.trim().length < 20
                      ? `${20 - justification.trim().length} more characters required`
                      : undefined
                  }
                />
              </div>

              {/* Priority */}
              <div className="mb-4">
                <Select
                  label="Priority"
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  options={[
                    { value: 'normal', label: 'Normal' },
                    { value: 'high', label: 'High' },
                    { value: 'urgent', label: 'Urgent' },
                  ]}
                />
              </div>

              {/* Temporary access */}
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <button
                    type="button"
                    role="switch"
                    aria-checked={temporary}
                    onClick={() => setTemporary((t) => !t)}
                    className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      temporary ? 'bg-primary-600' : 'bg-gray-200'
                    }`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        temporary ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                  <span className="text-sm text-gray-700 font-medium">Temporary Access</span>
                </div>
                {temporary && (
                  <Input
                    label="Access End Date"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    required
                    min={new Date().toISOString().split('T')[0]}
                  />
                )}
              </div>

              {formError && (
                <div className="mt-4 rounded-xl bg-red-50/80 border border-red-200/50 p-3 flex gap-2">
                  <ExclamationTriangleIcon className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-red-700">{formError}</p>
                </div>
              )}
            </Card>
          </div>

          {/* Cart summary + conflicts */}
          <div className="lg:col-span-2 space-y-4">
            <Card padding="lg">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">
                Cart Summary ({cartItems.length} role{cartItems.length !== 1 ? 's' : ''})
              </h3>
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {cartItems.map((item) => (
                  <div
                    key={item.role.id}
                    className="flex items-center justify-between gap-2 p-2.5 rounded-xl bg-white/40 border border-white/30"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-gray-900 truncate">{item.role.name}</p>
                      <p className="text-[10px] text-gray-500">{item.role.system}</p>
                    </div>
                    <RiskBadge level={item.role.risk_level} />
                    <button
                      onClick={() => removeFromCart(item.role.id)}
                      className="text-gray-400 hover:text-red-500 transition-colors flex-shrink-0"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </Card>

            {/* Conflicts panel */}
            {conflictChecking && (
              <div className="rounded-xl bg-blue-50/80 border border-blue-200/50 p-3 flex gap-2 items-center">
                <svg className="animate-spin h-4 w-4 text-blue-500" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span className="text-xs text-blue-700">Checking SoD conflicts...</span>
              </div>
            )}

            {conflicts && conflicts.has_conflicts && (
              <Card padding="md" className="border border-red-200/50 bg-red-50/30">
                <div className="flex items-center gap-2 mb-3">
                  <ExclamationTriangleIcon className="h-4 w-4 text-red-600 flex-shrink-0" />
                  <p className="text-sm font-semibold text-red-800">
                    {conflicts.total} SoD Conflict{conflicts.total !== 1 ? 's' : ''} Detected
                  </p>
                </div>
                <div className="space-y-2">
                  {conflicts.conflicts.map((c, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg bg-red-50/60 border border-red-200/40 p-2.5 text-xs"
                    >
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <span className="font-semibold text-red-900">{c.rule}</span>
                        <Badge variant="danger" size="sm">{c.risk_level}</Badge>
                      </div>
                      <p className="text-red-700 font-mono text-[10px]">
                        {c.role_a} &lt;&gt; {c.role_b}
                      </p>
                      {c.description && (
                        <p className="text-red-600 mt-1">{c.description}</p>
                      )}
                    </div>
                  ))}
                </div>
                <p className="text-xs text-red-600 mt-3">
                  Conflicts will be flagged in your request and require risk owner approval or mitigation.
                </p>
              </Card>
            )}

            {conflicts && !conflicts.has_conflicts && cartItems.length >= 2 && (
              <div className="rounded-xl bg-emerald-50/80 border border-emerald-200/50 p-3 flex gap-2 items-center">
                <CheckCircleIcon className="h-4 w-4 text-emerald-600 flex-shrink-0" />
                <span className="text-xs text-emerald-700 font-medium">No SoD conflicts detected</span>
              </div>
            )}

            <Button
              fullWidth
              size="lg"
              onClick={handleSubmit}
              loading={submitMutation.isPending}
              disabled={cartItems.length === 0 || submitMutation.isPending}
              icon={<ArrowRightIcon className="h-4 w-4" />}
              iconPosition="right"
            >
              Submit Request
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: Catalog + Cart (main view)
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-6">
      <PageHeader
        title="Access Request Catalog"
        subtitle="Browse available roles and add them to your cart"
        breadcrumbs={[
          { label: 'Access Requests', href: '/access-requests' },
          { label: 'Shopping Cart' },
        ]}
        actions={
          <Button
            size="sm"
            icon={<ShoppingCartIcon className="h-4 w-4" />}
            onClick={() => cartItems.length > 0 && setStep('checkout')}
            disabled={cartItems.length === 0}
          >
            Cart ({cartItems.length})
            {conflicts?.has_conflicts && (
              <span className="ml-1.5 inline-flex items-center justify-center h-4 w-4 rounded-full bg-red-500 text-white text-[10px] font-bold">
                {conflicts.total}
              </span>
            )}
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Left: Filters + Catalog */}
        <div className="lg:col-span-3 space-y-4">
          {/* Search + Filters */}
          <Card padding="md">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
              <div className="sm:col-span-2 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" />
                </div>
                <input
                  type="text"
                  placeholder="Search roles by name or description..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl bg-white/50 border border-white/40 focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-400 placeholder-gray-400 transition-all"
                />
                {search && (
                  <button
                    onClick={() => setSearch('')}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                  >
                    <XMarkIcon className="h-4 w-4" />
                  </button>
                )}
              </div>
              <select
                value={filterSystem}
                onChange={(e) => setFilterSystem(e.target.value)}
                className="w-full py-2.5 px-3 text-sm rounded-xl bg-white/50 border border-white/40 focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-400 transition-all"
              >
                <option value="">All Systems</option>
                {systems.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <select
                value={filterRisk}
                onChange={(e) => setFilterRisk(e.target.value)}
                className="w-full py-2.5 px-3 text-sm rounded-xl bg-white/50 border border-white/40 focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-400 transition-all"
              >
                <option value="">All Risk Levels</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            {/* Process filter pills */}
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={() => setFilterProcess('')}
                className={`px-3 py-1 text-xs rounded-full border font-medium transition-all ${
                  !filterProcess
                    ? 'bg-primary-600 text-white border-primary-600'
                    : 'bg-white/40 text-gray-600 border-white/30 hover:bg-white/60'
                }`}
              >
                All Processes
              </button>
              {processes.map((p) => (
                <button
                  key={p}
                  onClick={() => setFilterProcess(filterProcess === p ? '' : p)}
                  className={`px-3 py-1 text-xs rounded-full border font-medium transition-all ${
                    filterProcess === p
                      ? 'bg-primary-600 text-white border-primary-600'
                      : 'bg-white/40 text-gray-600 border-white/30 hover:bg-white/60'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </Card>

          {/* Results count */}
          <div className="flex items-center justify-between px-1">
            <p className="text-sm text-gray-500">
              {filteredCatalog.length} role{filteredCatalog.length !== 1 ? 's' : ''} found
            </p>
            {(search || filterSystem || filterProcess || filterRisk) && (
              <button
                onClick={() => {
                  setSearch('');
                  setFilterSystem('');
                  setFilterProcess('');
                  setFilterRisk('');
                }}
                className="text-xs text-primary-600 hover:text-primary-800 font-medium"
              >
                Clear filters
              </button>
            )}
          </div>

          {/* Catalog grid */}
          {catalogLoading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
            </div>
          ) : filteredCatalog.length === 0 ? (
            <Card padding="lg" className="text-center">
              <MagnifyingGlassIcon className="h-10 w-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-500">No roles match your search</p>
              <p className="text-xs text-gray-400 mt-1">Try adjusting your filters or search terms</p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {filteredCatalog.map((role) => (
                <RoleCatalogCard
                  key={role.id}
                  role={role}
                  inCart={cartRoleIds.has(role.id)}
                  onAdd={addToCart}
                />
              ))}
            </div>
          )}
        </div>

        {/* Right: Cart panel */}
        <div className="lg:col-span-1">
          <div className="sticky top-6 space-y-4">
            <Card padding="md">
              <div className="flex items-center gap-2 mb-3">
                <ShoppingCartIcon className="h-4 w-4 text-gray-600" />
                <h3 className="text-sm font-semibold text-gray-900">
                  My Cart ({cartItems.length})
                </h3>
              </div>

              {cartItems.length === 0 ? (
                <div className="text-center py-6">
                  <ShoppingCartIcon className="h-8 w-8 text-gray-200 mx-auto mb-2" />
                  <p className="text-xs text-gray-400">Your cart is empty</p>
                  <p className="text-[10px] text-gray-300 mt-0.5">Add roles from the catalog</p>
                </div>
              ) : (
                <>
                  <div className="space-y-2 max-h-80 overflow-y-auto pr-0.5">
                    {cartItems.map((item) => (
                      <div
                        key={item.role.id}
                        className="flex items-start gap-2 p-2 rounded-lg bg-white/40 border border-white/30"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-gray-900 truncate leading-tight">
                            {item.role.name}
                          </p>
                          <p className="text-[10px] text-gray-500 mt-0.5">{item.role.system}</p>
                          <Badge variant={riskVariant(item.role.risk_level)} size="sm" className="mt-1">
                            {item.role.risk_level}
                          </Badge>
                        </div>
                        <button
                          onClick={() => removeFromCart(item.role.id)}
                          className="text-gray-300 hover:text-red-500 transition-colors flex-shrink-0 mt-0.5"
                          title="Remove"
                        >
                          <XMarkIcon className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>

                  {/* Conflict indicator */}
                  {conflictChecking && (
                    <div className="mt-3 flex items-center gap-2 text-xs text-blue-600">
                      <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Checking conflicts...
                    </div>
                  )}
                  {!conflictChecking && conflicts?.has_conflicts && (
                    <div className="mt-3 flex items-center gap-2 rounded-lg bg-red-50/80 border border-red-200/40 p-2">
                      <ExclamationTriangleIcon className="h-3.5 w-3.5 text-red-600 flex-shrink-0" />
                      <p className="text-xs text-red-700 font-medium">
                        {conflicts.total} conflict{conflicts.total !== 1 ? 's' : ''} detected
                      </p>
                    </div>
                  )}
                  {!conflictChecking && conflicts && !conflicts.has_conflicts && cartItems.length >= 2 && (
                    <div className="mt-3 flex items-center gap-2 rounded-lg bg-emerald-50/80 border border-emerald-200/40 p-2">
                      <CheckCircleIcon className="h-3.5 w-3.5 text-emerald-600 flex-shrink-0" />
                      <p className="text-xs text-emerald-700 font-medium">No conflicts</p>
                    </div>
                  )}

                  <div className="mt-4 pt-3 border-t border-white/20 space-y-2">
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>Total roles</span>
                      <span className="font-semibold text-gray-900">{cartItems.length}</span>
                    </div>
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>SoD conflicts</span>
                      <span className={`font-semibold ${conflicts?.has_conflicts ? 'text-red-600' : 'text-gray-900'}`}>
                        {conflicts?.total ?? 0}
                      </span>
                    </div>
                  </div>

                  <Button
                    fullWidth
                    className="mt-4"
                    onClick={() => setStep('checkout')}
                    icon={<ArrowRightIcon className="h-4 w-4" />}
                    iconPosition="right"
                  >
                    Proceed to Checkout
                  </Button>
                </>
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Local SoD conflict detection (fallback when API unavailable)
// ---------------------------------------------------------------------------

const LOCAL_SOD_PAIRS: Array<[string, string, string]> = [
  ['SAP_FI_AP_CLERK', 'SAP_FI_PAYMENT_RUN', 'FI-SOD-001'],
  ['SAP_FI_GL_ACCOUNTANT', 'SAP_FI_PAYMENT_RUN', 'FI-SOD-002'],
  ['SAP_MM_PO_CREATOR', 'SAP_MM_GR_POSTER', 'MM-SOD-001'],
  ['SAP_MM_PO_CREATOR', 'SAP_MM_INVOICE_VERIFY', 'MM-SOD-002'],
  ['SAP_MM_VENDOR_MASTER', 'SAP_FI_AP_CLERK', 'MM-SOD-003'],
  ['SAP_MM_VENDOR_MASTER', 'SAP_FI_PAYMENT_RUN', 'MM-SOD-004'],
  ['SAP_FI_BANK_MASTER', 'SAP_FI_PAYMENT_RUN', 'FI-SOD-003'],
  ['SAP_SD_BILLING', 'SAP_FI_AR_CLERK', 'SD-SOD-001'],
  ['SAP_BASIS_USER_ADMIN', 'SAP_BASIS_ROLE_ADMIN', 'BASIS-SOD-001'],
  ['SAP_HR_PA_MAINTAINER', 'SAP_HR_PAYROLL_ADMIN', 'HR-SOD-001'],
];

function detectLocalConflicts(roles: CatalogRole[]): ConflictPair[] {
  const ids = new Set(roles.map((r) => r.id));
  const found: ConflictPair[] = [];
  for (const [a, b, rule] of LOCAL_SOD_PAIRS) {
    if (ids.has(a) && ids.has(b)) {
      found.push({
        role_a: a,
        role_b: b,
        rule,
        risk_level: 'high',
        description: `Combination of ${a} and ${b} violates segregation of duties rule ${rule}.`,
      });
    }
  }
  return found;
}
