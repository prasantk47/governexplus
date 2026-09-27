import { useQuery } from '@tanstack/react-query';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  UserPlusIcon,
  KeyIcon,
} from '@heroicons/react/24/outline';
import { auditApi } from '../services/api';

const iconMap: Record<string, { icon: typeof CheckCircleIcon; color: string }> = {
  access_granted: { icon: CheckCircleIcon, color: 'text-green-500' },
  violation_detected: { icon: ExclamationTriangleIcon, color: 'text-red-500' },
  user_created: { icon: UserPlusIcon, color: 'text-blue-500' },
  firefighter_session: { icon: KeyIcon, color: 'text-orange-500' },
  access_revoked: { icon: CheckCircleIcon, color: 'text-gray-500' },
};

interface RecentActivityListProps {
  limit?: number;
}

export function RecentActivityList({ limit = 5 }: RecentActivityListProps) {
  const { data: activitiesData } = useQuery({
    queryKey: ['recent-activity', limit],
    queryFn: () => auditApi.getLogs({ limit }).then((res) => {
      const d = res.data;
      if (Array.isArray(d)) return d;
      if (d?.logs && Array.isArray(d.logs)) return d.logs;
      return [];
    }),
  });

  const activities = (activitiesData || []).slice(0, limit).map((a: any, idx: number) => {
    const mapping = iconMap[a.action] || iconMap['access_granted'];
    return {
      id: a.id || idx,
      icon: mapping.icon,
      iconColor: mapping.color,
      message: a.message || `${a.action}: ${a.details || a.target_id || ''}`,
      time: a.timestamp || a.created_at || '',
    };
  });

  return (
    <div className="flow-root">
      <ul className="-mb-8">
        {activities.map((activity: any, activityIdx: number) => (
          <li key={activity.id}>
            <div className="relative pb-8">
              {activityIdx !== activities.length - 1 && (
                <span
                  className="absolute left-4 top-4 -ml-px h-full w-0.5 bg-gray-200"
                  aria-hidden="true"
                />
              )}
              <div className="relative flex space-x-3">
                <div>
                  <span className="h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white bg-gray-100">
                    <activity.icon className={`h-5 w-5 ${activity.iconColor}`} />
                  </span>
                </div>
                <div className="flex min-w-0 flex-1 justify-between space-x-4 pt-1.5">
                  <div>
                    <p className="text-sm text-gray-500">{activity.message}</p>
                  </div>
                  <div className="whitespace-nowrap text-right text-sm text-gray-500">
                    {activity.time}
                  </div>
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
