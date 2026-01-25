import { ComponentType } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/solid';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: ComponentType<{ className?: string }>;
  iconBgColor: string;
  iconColor: string;
  trend?: number;
  trendLabel?: string;
  link?: string;
}

export function StatCard({
  title,
  value,
  icon: Icon,
  iconBgColor,
  trend,
  link,
}: StatCardProps) {
  const content = (
    <div className="stat-card glossy">
      <div className="flex items-center gap-4">
        <div className={`stat-icon ${iconBgColor}`}>
          <Icon className="h-5 w-5 relative z-10" />
        </div>
        <div>
          <div className="stat-label">{title}</div>
          <div className="flex items-baseline gap-2">
            <div className="stat-value">{value}</div>
            {trend !== undefined && (
              <div
                className={`flex items-center text-xs font-medium ${
                  trend >= 0 ? 'text-red-500' : 'text-green-500'
                }`}
              >
                {trend >= 0 ? (
                  <ArrowUpIcon className="h-3 w-3" />
                ) : (
                  <ArrowDownIcon className="h-3 w-3" />
                )}
                <span className="ml-0.5">{Math.abs(trend)}%</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  if (link) {
    return (
      <Link to={link} className="block group">
        {content}
      </Link>
    );
  }

  return content;
}
