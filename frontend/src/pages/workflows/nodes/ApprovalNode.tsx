import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  CheckCircleIcon,
  UserIcon,
  ShieldCheckIcon,
  BriefcaseIcon,
  UserGroupIcon,
  SparklesIcon,
  CircleStackIcon,
} from '@heroicons/react/24/outline';

const approvalIcons: Record<string, React.ElementType> = {
  LINE_MANAGER: UserIcon,
  ROLE_OWNER: ShieldCheckIcon,
  PROCESS_OWNER: BriefcaseIcon,
  SECURITY_OFFICER: ShieldCheckIcon,
  COMPLIANCE_OFFICER: CheckCircleIcon,
  DATA_OWNER: CircleStackIcon,
  CUSTOM_GROUP: UserGroupIcon,
  AI_RECOMMENDED: SparklesIcon,
};

function ApprovalNodeComponent({ data, selected }: NodeProps) {
  const Icon = approvalIcons[(data as any).approver_type] || CheckCircleIcon;
  const isValid = (data as any).isValid !== false;

  return (
    <div
      className={`
        min-w-[180px] rounded-lg shadow-md border-2 bg-white
        ${selected ? 'ring-2 ring-emerald-400 ring-offset-1' : ''}
        ${!isValid ? 'border-red-500' : 'border-emerald-400'}
        transition-all duration-150
      `}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-emerald-500 !border-2 !border-white"
      />
      <div className="flex items-center gap-2 px-3 py-2 bg-emerald-500 rounded-t-md">
        <Icon className="h-4 w-4 text-white flex-shrink-0" />
        <span className="text-xs font-semibold text-white truncate">
          {(data as any).label || 'Approval'}
        </span>
      </div>
      <div className="px-3 py-2 space-y-1">
        <p className="text-[10px] text-gray-500">
          {((data as any).approver_type || 'LINE_MANAGER').replace(/_/g, ' ')}
        </p>
        {(data as any).sla_hours && (
          <p className="text-[10px] text-gray-400">
            SLA: {(data as any).sla_hours}h
          </p>
        )}
        <div className="flex gap-1 flex-wrap">
          {(data as any).is_required !== false && (
            <span className="text-[9px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full">
              Required
            </span>
          )}
          {(data as any).allow_delegate && (
            <span className="text-[9px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">
              Delegatable
            </span>
          )}
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-emerald-500 !border-2 !border-white"
      />
    </div>
  );
}

export const ApprovalNode = memo(ApprovalNodeComponent);
