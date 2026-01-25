import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  UserPlusIcon,
  KeyIcon,
} from '@heroicons/react/24/outline';

interface RecentActivityListProps {
  limit?: number;
}

export function RecentActivityList({ limit = 5 }: RecentActivityListProps) {
  const activities = [
    {
      id: 1,
      type: 'access_granted',
      icon: CheckCircleIcon,
      iconColor: 'text-green-500',
      message: 'Access granted to John Smith for SAP_MM_BUYER',
      time: '10 minutes ago',
    },
    {
      id: 2,
      type: 'violation_detected',
      icon: ExclamationTriangleIcon,
      iconColor: 'text-red-500',
      message: 'SoD violation detected for Mary Brown',
      time: '25 minutes ago',
    },
    {
      id: 3,
      type: 'user_created',
      icon: UserPlusIcon,
      iconColor: 'text-blue-500',
      message: 'New user created: Alice Wilson',
      time: '1 hour ago',
    },
    {
      id: 4,
      type: 'firefighter_session',
      icon: KeyIcon,
      iconColor: 'text-orange-500',
      message: 'Firefighter session started by Tom Davis',
      time: '2 hours ago',
    },
    {
      id: 5,
      type: 'access_revoked',
      icon: CheckCircleIcon,
      iconColor: 'text-gray-500',
      message: 'Access revoked for David Chen',
      time: '3 hours ago',
    },
  ].slice(0, limit);

  return (
    <div className="flow-root">
      <ul className="-mb-8">
        {activities.map((activity, activityIdx) => (
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
