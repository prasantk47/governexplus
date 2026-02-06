import { ReactNode } from 'react';

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';
type BadgeSize = 'sm' | 'md';

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  dot?: boolean;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-gray-100/80 text-gray-700 border-gray-200/50',
  success: 'bg-emerald-50/80 text-emerald-700 border-emerald-200/50',
  warning: 'bg-amber-50/80 text-amber-700 border-amber-200/50',
  danger: 'bg-red-50/80 text-red-700 border-red-200/50',
  info: 'bg-blue-50/80 text-blue-700 border-blue-200/50',
  neutral: 'bg-slate-50/80 text-slate-600 border-slate-200/50',
};

const dotColors: Record<BadgeVariant, string> = {
  default: 'bg-gray-400',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
  info: 'bg-blue-500',
  neutral: 'bg-slate-400',
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: 'px-2 py-0.5 text-[10px]',
  md: 'px-2.5 py-1 text-xs',
};

export function Badge({ children, variant = 'default', size = 'md', dot = false, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border backdrop-blur-sm ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {children}
    </span>
  );
}

// Convenience helpers
export function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { variant: BadgeVariant; label: string }> = {
    active: { variant: 'success', label: 'Active' },
    inactive: { variant: 'neutral', label: 'Inactive' },
    locked: { variant: 'danger', label: 'Locked' },
    suspended: { variant: 'warning', label: 'Suspended' },
    disabled: { variant: 'neutral', label: 'Disabled' },
    expired: { variant: 'warning', label: 'Expired' },
    deleted: { variant: 'danger', label: 'Deleted' },
    pending: { variant: 'info', label: 'Pending' },
    approved: { variant: 'success', label: 'Approved' },
    rejected: { variant: 'danger', label: 'Rejected' },
    open: { variant: 'warning', label: 'Open' },
    closed: { variant: 'neutral', label: 'Closed' },
    mitigated: { variant: 'success', label: 'Mitigated' },
    draft: { variant: 'neutral', label: 'Draft' },
  };

  const c = config[status?.toLowerCase()] || { variant: 'default' as BadgeVariant, label: status };
  return <Badge variant={c.variant} dot>{c.label}</Badge>;
}

export function RiskBadge({ level }: { level: string }) {
  const config: Record<string, BadgeVariant> = {
    low: 'success',
    medium: 'warning',
    high: 'danger',
    critical: 'danger',
  };
  return (
    <Badge variant={config[level?.toLowerCase()] || 'default'} dot>
      {level?.charAt(0).toUpperCase() + level?.slice(1)}
    </Badge>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  return <RiskBadge level={severity} />;
}
