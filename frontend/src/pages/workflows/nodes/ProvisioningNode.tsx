import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  ShieldCheckIcon,
  CheckCircleIcon,
  ChartBarIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';

const modeIcons: Record<string, React.ElementType> = {
  PER_ITEM: CheckCircleIcon,
  ALL_OR_NOTHING: ShieldCheckIcon,
  RISK_BASED: ChartBarIcon,
  TEMPORARY_FIRST: ClockIcon,
  CRITICAL_LAST: ShieldCheckIcon,
};

const modeDescriptions: Record<string, string> = {
  PER_ITEM: 'Provision each approved item immediately',
  ALL_OR_NOTHING: 'Wait for all approvals before provisioning',
  RISK_BASED: 'Provision low-risk items first',
  TEMPORARY_FIRST: 'Provision temporary access first',
  CRITICAL_LAST: 'Provision critical access last',
};

function ProvisioningNodeComponent({ data, selected }: NodeProps) {
  const mode = (data as any).mode || 'PER_ITEM';
  const Icon = modeIcons[mode] || ShieldCheckIcon;
  const isValid = (data as any).isValid !== false;

  return (
    <div
      className={`
        min-w-[180px] rounded-lg shadow-md border-2 bg-white
        ${selected ? 'ring-2 ring-violet-400 ring-offset-1' : ''}
        ${!isValid ? 'border-red-500' : 'border-violet-400'}
        transition-all duration-150
      `}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-violet-500 !border-2 !border-white"
      />
      <div className="flex items-center gap-2 px-3 py-2 bg-violet-500 rounded-t-md">
        <Icon className="h-4 w-4 text-white flex-shrink-0" />
        <span className="text-xs font-semibold text-white truncate">
          {(data as any).label || 'Provisioning Gate'}
        </span>
      </div>
      <div className="px-3 py-2 space-y-1">
        <p className="text-[10px] text-gray-500">
          {modeDescriptions[mode] || mode.replace(/_/g, ' ')}
        </p>
        {mode === 'RISK_BASED' && (data as any).risk_threshold && (
          <p className="text-[10px] text-gray-400">
            Threshold: {(data as any).risk_threshold}
          </p>
        )}
        <div className="flex gap-1 flex-wrap">
          {(data as any).allow_partial && (
            <span className="text-[9px] bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded-full">
              Partial OK
            </span>
          )}
          {(data as any).block_sod_items && (
            <span className="text-[9px] bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full">
              Block SoD
            </span>
          )}
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-violet-500 !border-2 !border-white"
      />
    </div>
  );
}

export const ProvisioningNode = memo(ProvisioningNodeComponent);
