import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../../services/api';

export function RiskChart() {
  const { data: metricsData } = useQuery({
    queryKey: ['risk-chart'],
    queryFn: () => dashboardApi.getRiskMetrics().then((res) => res.data),
  });

  const colors: Record<string, string> = {
    Critical: 'bg-red-500',
    High: 'bg-orange-500',
    Medium: 'bg-yellow-500',
    Low: 'bg-green-500',
  };

  const data = metricsData?.distribution || [
    { level: 'Critical', count: 0 },
    { level: 'High', count: 0 },
    { level: 'Medium', count: 0 },
    { level: 'Low', count: 0 },
  ];

  const total = data.reduce((acc: number, item: any) => acc + (item.count || 0), 0) || 1;

  return (
    <div className="space-y-4">
      {data.map((item: any) => (
        <div key={item.level} className="flex items-center">
          <div className="w-20 text-sm font-medium text-gray-600">{item.level}</div>
          <div className="flex-1 mx-4">
            <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${colors[item.level] || 'bg-gray-500'} rounded-full`}
                style={{ width: `${(item.count / total) * 100}%` }}
              />
            </div>
          </div>
          <div className="w-10 text-sm font-semibold text-gray-900 text-right">
            {item.count}
          </div>
        </div>
      ))}
    </div>
  );
}
