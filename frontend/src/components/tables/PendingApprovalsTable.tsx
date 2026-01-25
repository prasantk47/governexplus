import { Link } from 'react-router-dom';

interface PendingApprovalsTableProps {
  limit?: number;
}

export function PendingApprovalsTable({ limit = 5 }: PendingApprovalsTableProps) {
  const approvals = [
    { id: 'REQ-001', requester: 'John Smith', role: 'SAP_MM_BUYER', type: 'Role Request', date: '2024-01-20' },
    { id: 'REQ-002', requester: 'Mary Brown', role: 'SAP_FI_USER', type: 'Role Request', date: '2024-01-19' },
    { id: 'FF-001', requester: 'Tom Davis', role: 'FF_EMERGENCY_01', type: 'Firefighter', date: '2024-01-20' },
  ].slice(0, limit);

  if (approvals.length === 0) {
    return (
      <div className="p-6 text-center text-gray-500">
        No pending approvals
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Request
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Requester
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Date
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Action
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {approvals.map((approval) => (
            <tr key={approval.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {approval.id}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {approval.requester}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <span className={`px-2 py-1 rounded-full text-xs ${
                  approval.type === 'Firefighter'
                    ? 'bg-orange-100 text-orange-800'
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  {approval.type}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {approval.date}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                <Link
                  to={`/approvals/${approval.id}`}
                  className="text-primary-600 hover:text-primary-900"
                >
                  Review
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
