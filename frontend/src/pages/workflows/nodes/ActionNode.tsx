import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  BoltIcon,
  EnvelopeIcon,
  ShieldCheckIcon,
  EyeIcon,
  DocumentTextIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline';

const actionIcons: Record<string, React.ElementType> = {
  PROVISION_ACCESS: BoltIcon,
  REVOKE_ACCESS: BoltIcon,
  NOTIFY_USER: EnvelopeIcon,
  NOTIFY_MANAGER: EnvelopeIcon,
  NOTIFY_SECURITY: ShieldCheckIcon,
  START_POST_REVIEW: EyeIcon,
  TRIGGER_AUDIT: DocumentTextIcon,
  CLOSE_REQUEST: BoltIcon,
  SCHEDULE_REVIEW: CalendarIcon,
  LOG_EVENT: DocumentTextIcon,
  CALL_WEBHOOK: BoltIcon,
};

function ActionNodeComponent({ data, selected }: NodeProps) {
  const Icon = actionIcons[(data as any).action_type] || BoltIcon;
  const isValid = (data as any).isValid !== false;

  return (
    <div
      className={`
        min-w-[180px] rounded-lg shadow-md border-2 bg-white
        ${selected ? 'ring-2 ring-red-400 ring-offset-1' : ''}
        ${!isValid ? 'border-red-500' : 'border-red-400'}
        transition-all duration-150
      `}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-red-500 !border-2 !border-white"
      />
      <div className="flex items-center gap-2 px-3 py-2 bg-red-500 rounded-t-md">
        <Icon className="h-4 w-4 text-white flex-shrink-0" />
        <span className="text-xs font-semibold text-white truncate">
          {(data as any).label || 'Action'}
        </span>
      </div>
      <div className="px-3 py-2">
        <p className="text-[10px] text-gray-500">
          {((data as any).action_type || 'NOTIFY_USER').replace(/_/g, ' ')}
        </p>
        {(data as any).action_type === 'SCHEDULE_REVIEW' && (data as any).review_days && (
          <p className="text-[10px] text-gray-400 mt-0.5">
            Review in {(data as any).review_days} days
          </p>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-red-500 !border-2 !border-white"
      />
    </div>
  );
}

export const ActionNode = memo(ActionNodeComponent);
