import { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  breadcrumbs?: { label: string; href?: string }[];
  className?: string;
}

export function PageHeader({ title, subtitle, actions, breadcrumbs, className = '' }: PageHeaderProps) {
  return (
    <div className={`mb-8 ${className}`}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="flex items-center gap-1.5 text-sm text-gray-400 dark:text-gray-500 mb-3">
          {breadcrumbs.map((crumb, i) => (
            <span key={i} className="flex items-center gap-1.5">
              {i > 0 && <span className="text-gray-300 dark:text-gray-600">/</span>}
              {crumb.href ? (
                <a href={crumb.href} className="hover:text-gray-600 dark:hover:text-gray-300 transition-colors">{crumb.label}</a>
              ) : (
                <span className="text-gray-600 dark:text-gray-300">{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="page-title">{title}</h1>
          {subtitle && <p className="page-subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-3 flex-shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
