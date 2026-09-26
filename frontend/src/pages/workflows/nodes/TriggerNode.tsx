import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  PlayIcon,
  FireIcon,
  UserIcon,
  ArrowTrendingUpIcon,
  SparklesIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline';

const triggerIcons: Record<string, React.ElementType> = {
  ACCESS_REQUEST: PlayIcon,
  FIREFIGHTER_REQUEST: FireIcon,
  ROLE_CHANGE: UserIcon,
  RISK_SPIKE: ArrowTrendingUpIcon,
  PREDICTIVE_ALERT: SparklesIcon,
  SCHEDULED_REVIEW: CalendarIcon,
};

function TriggerNodeComponent({ data, selected }: NodeProps) {
  const Icon = triggerIcons[(data as any).trigger_type] || PlayIcon;
  const isValid = (data as any).isValid !== false;

  return (
    <div
      className={`
        min-w-[180px] rounded-lg shadow-md border-2 bg-white
        ${selected ? 'ring-2 ring-blue-400 ring-offset-1' : ''}
        ${!isValid ? 'border-red-500' : 'border-blue-400'}
        transition-all duration-150
      `}
    >
      <div className="flex items-center gap-2 px-3 py-2 bg-blue-500 rounded-t-md">
        <Icon className="h-4 w-4 text-white flex-shrink-0" />
        <span className="text-xs font-semibold text-white truncate">
          {(data as any).label || 'Trigger'}
        </span>
      </div>
      <div className="px-3 py-2">
        <p className="text-[10px] text-gray-500">
          {((data as any).trigger_type || 'ACCESS_REQUEST').replace(/_/g, ' ')}
        </p>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-blue-500 !border-2 !border-white"
      />
    </div>
  );
}

export const TriggerNode = memo(TriggerNodeComponent);
