import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  FunnelIcon,
  ChartBarIcon,
  ServerIcon,
  CubeIcon,
  KeyIcon,
  TagIcon,
  UserIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

const conditionIcons: Record<string, React.ElementType> = {
  RISK_SCORE: ChartBarIcon,
  SYSTEM: ServerIcon,
  SYSTEM_TYPE: CubeIcon,
  ACCESS_TYPE: KeyIcon,
  ROLE_TAG: TagIcon,
  USER_TYPE: UserIcon,
  IS_TEMPORARY: ClockIcon,
  HAS_SOD: ExclamationTriangleIcon,
};

function ConditionNodeComponent({ data, selected }: NodeProps) {
  const Icon = conditionIcons[(data as any).attribute] || FunnelIcon;
  const isValid = (data as any).isValid !== false;

  return (
    <div
      className={`
        min-w-[180px] rounded-lg shadow-md border-2 bg-white
        ${selected ? 'ring-2 ring-amber-400 ring-offset-1' : ''}
        ${!isValid ? 'border-red-500' : 'border-amber-400'}
        transition-all duration-150
      `}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-amber-500 !border-2 !border-white"
      />
      <div className="flex items-center gap-2 px-3 py-2 bg-amber-500 rounded-t-md">
        <Icon className="h-4 w-4 text-white flex-shrink-0" />
        <span className="text-xs font-semibold text-white truncate">
          {(data as any).label || 'Condition'}
        </span>
      </div>
      <div className="px-3 py-2">
        <p className="text-[10px] text-gray-500">
          {((data as any).attribute || '').replace(/_/g, ' ')}
        </p>
        {(data as any).operator && (
          <p className="text-[10px] text-gray-400 mt-0.5">
            {((data as any).operator || '').replace(/_/g, ' ').toLowerCase()}{' '}
            {(data as any).value !== undefined ? (data as any).value : ''}
          </p>
        )}
      </div>
      <div className="flex justify-between px-2 pb-1">
        <div className="flex flex-col items-center">
          <span className="text-[9px] text-green-600 font-medium">True</span>
          <Handle
            type="source"
            position={Position.Bottom}
            id="true"
            className="!relative !transform-none !w-2.5 !h-2.5 !bg-green-500 !border-2 !border-white"
          />
        </div>
        <div className="flex flex-col items-center">
          <span className="text-[9px] text-red-600 font-medium">False</span>
          <Handle
            type="source"
            position={Position.Bottom}
            id="false"
            className="!relative !transform-none !w-2.5 !h-2.5 !bg-red-500 !border-2 !border-white"
          />
        </div>
      </div>
    </div>
  );
}

export const ConditionNode = memo(ConditionNodeComponent);
