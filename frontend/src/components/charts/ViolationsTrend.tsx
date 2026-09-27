import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../../services/api';

interface ViolationsTrendProps {
  compact?: boolean;
}

export function ViolationsTrend({ compact = false }: ViolationsTrendProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const { data: trendData } = useQuery({
    queryKey: ['violations-trend'],
    queryFn: () => dashboardApi.getRiskMetrics().then((res) => {
      const d = res.data;
      if (Array.isArray(d?.violations_trend)) return d.violations_trend;
      return [];
    }),
  });

  const data = Array.isArray(trendData) && trendData.length > 0
    ? trendData
    : [{ month: '', violations: 0 }];

  const maxValue = Math.max(...data.map((d: any) => d.violations), 1);
  const barHeight = compact ? 100 : 140;

  return (
    <div className={`${compact ? 'h-36' : 'h-48'}`}>
      <div className="flex items-end justify-between gap-3 h-full px-1">
        {data.map((item: any, index: number) => {
          const height = (item.violations / maxValue) * barHeight;
          const isHovered = hoveredIndex === index;

          return (
            <div
              key={item.month || index}
              className="flex-1 flex flex-col items-center group relative"
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              {isHovered && (
                <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-gray-900 text-white px-2.5 py-1.5 rounded-lg text-xs font-medium shadow-lg whitespace-nowrap z-10">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
                    {item.violations} violations
                  </div>
                  <div className="absolute left-1/2 -bottom-1 w-2 h-2 bg-gray-900 -translate-x-1/2 rotate-45"></div>
                </div>
              )}

              <div className="w-full flex justify-center" style={{ height: `${barHeight}px` }}>
                <div className="relative w-full max-w-[32px] flex items-end">
                  <div
                    className={`w-full rounded-t-lg transition-all duration-300 cursor-pointer ${
                      isHovered ? 'shadow-lg' : ''
                    }`}
                    style={{
                      height: `${height}px`,
                      background: isHovered
                        ? 'linear-gradient(180deg, #818cf8 0%, #4f46e5 100%)'
                        : 'linear-gradient(180deg, #a5b4fc 0%, #6366f1 100%)',
                    }}
                  />
                </div>
              </div>

              <div className="mt-2 text-xs font-medium text-gray-500">{item.month}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function AccessRequestsTrend({ compact = false }: { compact?: boolean }) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const { data: trendData } = useQuery({
    queryKey: ['access-requests-trend'],
    queryFn: () => dashboardApi.getRiskMetrics().then((res) => {
      const d = res.data;
      if (Array.isArray(d?.access_requests_trend)) return d.access_requests_trend;
      return [];
    }),
  });

  const data = Array.isArray(trendData) && trendData.length > 0
    ? trendData
    : [{ month: '', approved: 0, pending: 0, rejected: 0 }];

  const maxValue = Math.max(...data.map((d: any) => d.approved + d.pending + d.rejected), 1);
  const barHeight = compact ? 100 : 140;

  return (
    <div className={`${compact ? 'h-36' : 'h-48'}`}>
      <div className="flex items-end justify-between gap-3 h-full px-1">
        {data.map((item: any, index: number) => {
          const total = item.approved + item.pending + item.rejected;
          const totalHeight = (total / maxValue) * barHeight;
          const approvedHeight = total > 0 ? (item.approved / total) * totalHeight : 0;
          const pendingHeight = total > 0 ? (item.pending / total) * totalHeight : 0;
          const rejectedHeight = total > 0 ? (item.rejected / total) * totalHeight : 0;
          const isHovered = hoveredIndex === index;

          return (
            <div
              key={item.month || index}
              className="flex-1 flex flex-col items-center group relative"
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              {isHovered && (
                <div className="absolute -top-16 left-1/2 -translate-x-1/2 bg-gray-900 text-white px-3 py-2 rounded-lg text-xs shadow-lg whitespace-nowrap z-10">
                  <div className="font-medium text-gray-300 mb-1">{item.month}</div>
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                      Approved: {item.approved}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                      Pending: {item.pending}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-red-400"></span>
                      Rejected: {item.rejected}
                    </div>
                  </div>
                  <div className="absolute left-1/2 -bottom-1 w-2 h-2 bg-gray-900 -translate-x-1/2 rotate-45"></div>
                </div>
              )}

              <div className="w-full flex justify-center" style={{ height: `${barHeight}px` }}>
                <div className="relative w-full max-w-[32px] flex items-end">
                  <div
                    className={`w-full rounded-t-lg overflow-hidden transition-all duration-300 cursor-pointer ${
                      isHovered ? 'shadow-lg scale-105' : ''
                    }`}
                    style={{ height: `${totalHeight}px` }}
                  >
                    <div
                      className="w-full"
                      style={{
                        height: `${rejectedHeight}px`,
                        background: isHovered
                          ? 'linear-gradient(180deg, #fca5a5 0%, #ef4444 100%)'
                          : 'linear-gradient(180deg, #fecaca 0%, #f87171 100%)',
                      }}
                    />
                    <div
                      className="w-full"
                      style={{
                        height: `${pendingHeight}px`,
                        background: isHovered
                          ? 'linear-gradient(180deg, #fcd34d 0%, #f59e0b 100%)'
                          : 'linear-gradient(180deg, #fde68a 0%, #fbbf24 100%)',
                      }}
                    />
                    <div
                      className="w-full"
                      style={{
                        height: `${approvedHeight}px`,
                        background: isHovered
                          ? 'linear-gradient(180deg, #6ee7b7 0%, #10b981 100%)'
                          : 'linear-gradient(180deg, #a7f3d0 0%, #34d399 100%)',
                      }}
                    />
                  </div>
                </div>
              </div>

              <div className="mt-2 text-xs font-medium text-gray-500">{item.month}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
