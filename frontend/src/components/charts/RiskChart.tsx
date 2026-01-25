export function RiskChart() {
  const data = [
    { level: 'Critical', count: 5, color: 'bg-red-500' },
    { level: 'High', count: 15, color: 'bg-orange-500' },
    { level: 'Medium', count: 25, color: 'bg-yellow-500' },
    { level: 'Low', count: 45, color: 'bg-green-500' },
  ];

  const total = data.reduce((acc, item) => acc + item.count, 0);

  return (
    <div className="space-y-4">
      {data.map((item) => (
        <div key={item.level} className="flex items-center">
          <div className="w-20 text-sm font-medium text-gray-600">{item.level}</div>
          <div className="flex-1 mx-4">
            <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${item.color} rounded-full`}
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
