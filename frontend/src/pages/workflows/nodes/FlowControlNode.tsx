import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  ArrowsPointingOutIcon,
  ArrowsPointingInIcon,
} from '@heroicons/react/24/outline';

function SplitNodeComponent({ data, selected }: NodeProps) {
  const isValid = (data as any).isValid !== false;

  return (
    <div
      className={`
        min-w-[160px] rounded-lg shadow-md border-2 bg-white
        ${selected ? 'ring-2 ring-indigo-400 ring-offset-1' : ''}
        ${!isValid ? 'border-red-500' : 'border-indigo-400'}
        transition-all duration-150
      `}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-indigo-500 !border-2 !border-white"
      />
      <div className="flex items-center gap-2 px-3 py-2 bg-indigo-500 rounded-t-md">
        <ArrowsPointingOutIcon className="h-4 w-4 text-white flex-shrink-0" />
        <span className="text-xs font-semibold text-white truncate">
          {(data as any).label || 'Split'}
        </span>
      </div>
      <div className="px-3 py-2">
        <p className="text-[10px] text-gray-500">
          Split by {((data as any).split_by || 'ACCESS_ITEM').replace(/_/g, ' ').toLowerCase()}
        </p>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-indigo-500 !border-2 !border-white"
      />
    </div>
  );
}

function JoinNodeComponent({ data, selected }: NodeProps) {
  const isValid = (data as any).isValid !== false;

  return (
    <div
      className={`
        min-w-[160px] rounded-lg shadow-md border-2 bg-white
        ${selected ? 'ring-2 ring-indigo-400 ring-offset-1' : ''}
        ${!isValid ? 'border-red-500' : 'border-indigo-400'}
        transition-all duration-150
      `}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-indigo-500 !border-2 !border-white"
      />
      <div className="flex items-center gap-2 px-3 py-2 bg-indigo-500 rounded-t-md">
        <ArrowsPointingInIcon className="h-4 w-4 text-white flex-shrink-0" />
        <span className="text-xs font-semibold text-white truncate">
          {(data as any).label || 'Join'}
        </span>
      </div>
      <div className="px-3 py-2">
        <p className="text-[10px] text-gray-500">
          {(data as any).wait_for_all !== false ? 'Wait for all paths' : 'Continue on first'}
        </p>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-indigo-500 !border-2 !border-white"
      />
    </div>
  );
}

export const SplitNode = memo(SplitNodeComponent);
export const JoinNode = memo(JoinNodeComponent);
