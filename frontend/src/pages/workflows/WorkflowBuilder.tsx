import { useState, useCallback, useRef, type DragEvent } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Edge,
  type Node,
  type NodeTypes,
  ReactFlowProvider,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  PlayIcon,
  FireIcon,
  UserIcon,
  ArrowTrendingUpIcon,
  SparklesIcon,
  CalendarIcon,
  FunnelIcon,
  ChartBarIcon,
  ServerIcon,
  CubeIcon,
  KeyIcon,
  TagIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ShieldCheckIcon,
  BriefcaseIcon,
  UserGroupIcon,
  CircleStackIcon,
  BoltIcon,
  EnvelopeIcon,
  EyeIcon,
  DocumentTextIcon,
  ArrowsPointingOutIcon,
  ArrowsPointingInIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  ArrowDownTrayIcon,
  XMarkIcon,
  InformationCircleIcon,
  ExclamationCircleIcon,
  CheckIcon,
  RectangleGroupIcon,
} from '@heroicons/react/24/outline';

import { Button, Badge } from '../../components/ui';
import { api } from '../../services/api';

import {
  TriggerNode,
  ConditionNode,
  ApprovalNode,
  ProvisioningNode,
  ActionNode,
  SplitNode,
  JoinNode,
} from './nodes';

// ============================================================
// Types
// ============================================================

interface PaletteBlock {
  type: string;
  name: string;
  icon: string;
  color: string;
  description?: string;
  trigger_type?: string;
  attribute?: string;
  approver_type?: string;
  mode?: string;
  action_type?: string;
  split_by?: string;
}

interface PaletteData {
  triggers: PaletteBlock[];
  conditions: PaletteBlock[];
  approvals: PaletteBlock[];
  provisioning: PaletteBlock[];
  actions: PaletteBlock[];
  flow: PaletteBlock[];
}

interface ValidationResult {
  valid: boolean;
  errors: Array<{ code: string; message: string }>;
  warnings: Array<{ code: string; message: string }>;
}

interface WorkflowTemplate {
  template_id?: string;
  name: string;
  description: string;
}

// ============================================================
// Icon map for palette blocks
// ============================================================

const iconMap: Record<string, React.ElementType> = {
  key: KeyIcon,
  fire: FireIcon,
  'user-cog': UserIcon,
  'trending-up': ArrowTrendingUpIcon,
  brain: SparklesIcon,
  calendar: CalendarIcon,
  'chart-bar': ChartBarIcon,
  server: ServerIcon,
  cube: CubeIcon,
  tag: TagIcon,
  user: UserIcon,
  clock: ClockIcon,
  'exclamation-triangle': ExclamationTriangleIcon,
  'user-tie': UserIcon,
  'user-shield': ShieldCheckIcon,
  briefcase: BriefcaseIcon,
  shield: ShieldCheckIcon,
  'check-square': CheckCircleIcon,
  database: CircleStackIcon,
  users: UserGroupIcon,
  'check-circle': CheckCircleIcon,
  bolt: BoltIcon,
  mail: EnvelopeIcon,
  eye: EyeIcon,
  'file-text': DocumentTextIcon,
  'git-branch': ArrowsPointingOutIcon,
  'git-merge': ArrowsPointingInIcon,
  play: PlayIcon,
  filter: FunnelIcon,
};

// ============================================================
// Node type registration
// ============================================================

const nodeTypes: NodeTypes = {
  trigger: TriggerNode,
  condition: ConditionNode,
  approval: ApprovalNode,
  provisioning: ProvisioningNode,
  action: ActionNode,
  split: SplitNode,
  join: JoinNode,
};

function blockTypeToNodeType(blockType: string): string {
  const map: Record<string, string> = {
    TRIGGER: 'trigger',
    CONDITION: 'condition',
    CONDITION_GROUP: 'condition',
    APPROVAL: 'approval',
    APPROVAL_GROUP: 'approval',
    PROVISIONING_GATE: 'provisioning',
    ACTION: 'action',
    SPLIT: 'split',
    JOIN: 'join',
    PARALLEL: 'split',
  };
  return map[blockType] || 'action';
}

// ============================================================
// Category colors and labels
// ============================================================

const categoryConfig: Record<string, { label: string; color: string; bgClass: string; textClass: string; borderClass: string }> = {
  triggers: { label: 'Triggers', color: '#3B82F6', bgClass: 'bg-blue-50', textClass: 'text-blue-700', borderClass: 'border-blue-200' },
  conditions: { label: 'Conditions', color: '#F59E0B', bgClass: 'bg-amber-50', textClass: 'text-amber-700', borderClass: 'border-amber-200' },
  approvals: { label: 'Approvals', color: '#10B981', bgClass: 'bg-emerald-50', textClass: 'text-emerald-700', borderClass: 'border-emerald-200' },
  provisioning: { label: 'Provisioning', color: '#8B5CF6', bgClass: 'bg-violet-50', textClass: 'text-violet-700', borderClass: 'border-violet-200' },
  actions: { label: 'Actions', color: '#EF4444', bgClass: 'bg-red-50', textClass: 'text-red-700', borderClass: 'border-red-200' },
  flow: { label: 'Flow Control', color: '#6366F1', bgClass: 'bg-indigo-50', textClass: 'text-indigo-700', borderClass: 'border-indigo-200' },
};

// ============================================================
// Default palette (fallback when API not yet available)
// ============================================================

const defaultPalette: PaletteData = {
  triggers: [
    { type: 'TRIGGER', trigger_type: 'ACCESS_REQUEST', name: 'Access Request', icon: 'key', color: '#3B82F6' },
    { type: 'TRIGGER', trigger_type: 'FIREFIGHTER_REQUEST', name: 'Privileged Access Request', icon: 'fire', color: '#3B82F6' },
    { type: 'TRIGGER', trigger_type: 'ROLE_CHANGE', name: 'Role Change', icon: 'user-cog', color: '#3B82F6' },
    { type: 'TRIGGER', trigger_type: 'RISK_SPIKE', name: 'Risk Spike', icon: 'trending-up', color: '#3B82F6' },
    { type: 'TRIGGER', trigger_type: 'SCHEDULED_REVIEW', name: 'Scheduled Review', icon: 'calendar', color: '#3B82F6' },
  ],
  conditions: [
    { type: 'CONDITION', attribute: 'RISK_SCORE', name: 'Risk Score', icon: 'chart-bar', color: '#F59E0B' },
    { type: 'CONDITION', attribute: 'SYSTEM_TYPE', name: 'System Type', icon: 'cube', color: '#F59E0B' },
    { type: 'CONDITION', attribute: 'ACCESS_TYPE', name: 'Access Type', icon: 'key', color: '#F59E0B' },
    { type: 'CONDITION', attribute: 'ROLE_TAG', name: 'Role Tag', icon: 'tag', color: '#F59E0B' },
    { type: 'CONDITION', attribute: 'HAS_SOD', name: 'Has SoD Conflict', icon: 'exclamation-triangle', color: '#F59E0B' },
  ],
  approvals: [
    { type: 'APPROVAL', approver_type: 'LINE_MANAGER', name: 'Line Manager', icon: 'user-tie', color: '#10B981' },
    { type: 'APPROVAL', approver_type: 'ROLE_OWNER', name: 'Role Owner', icon: 'user-shield', color: '#10B981' },
    { type: 'APPROVAL', approver_type: 'SECURITY_OFFICER', name: 'Security', icon: 'shield', color: '#10B981' },
    { type: 'APPROVAL', approver_type: 'COMPLIANCE_OFFICER', name: 'Compliance', icon: 'check-square', color: '#10B981' },
    { type: 'APPROVAL', approver_type: 'CUSTOM_GROUP', name: 'Custom Group', icon: 'users', color: '#10B981' },
    { type: 'APPROVAL', approver_type: 'AI_RECOMMENDED', name: 'AI Recommended', icon: 'brain', color: '#10B981' },
  ],
  provisioning: [
    { type: 'PROVISIONING_GATE', mode: 'PER_ITEM', name: 'Per Item', icon: 'check-circle', color: '#8B5CF6', description: 'Provision each approved item immediately' },
    { type: 'PROVISIONING_GATE', mode: 'ALL_OR_NOTHING', name: 'All or Nothing', icon: 'shield', color: '#8B5CF6', description: 'Wait for all approvals' },
    { type: 'PROVISIONING_GATE', mode: 'RISK_BASED', name: 'Risk Based', icon: 'chart-bar', color: '#8B5CF6', description: 'Provision low-risk first' },
  ],
  actions: [
    { type: 'ACTION', action_type: 'NOTIFY_USER', name: 'Notify User', icon: 'mail', color: '#EF4444' },
    { type: 'ACTION', action_type: 'NOTIFY_MANAGER', name: 'Notify Manager', icon: 'mail', color: '#EF4444' },
    { type: 'ACTION', action_type: 'TRIGGER_AUDIT', name: 'Trigger Audit', icon: 'file-text', color: '#EF4444' },
    { type: 'ACTION', action_type: 'SCHEDULE_REVIEW', name: 'Schedule Review', icon: 'calendar', color: '#EF4444' },
    { type: 'ACTION', action_type: 'START_POST_REVIEW', name: 'Start Post Review', icon: 'eye', color: '#EF4444' },
  ],
  flow: [
    { type: 'SPLIT', split_by: 'ACCESS_ITEM', name: 'Split by Item', icon: 'git-branch', color: '#6366F1' },
    { type: 'SPLIT', split_by: 'SYSTEM', name: 'Split by System', icon: 'git-branch', color: '#6366F1' },
    { type: 'JOIN', name: 'Join', icon: 'git-merge', color: '#6366F1' },
  ],
};

// ============================================================
// Configuration Panel fields per node type
// ============================================================

interface ConfigField {
  key: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'checkbox';
  options?: { value: string; label: string }[];
}

const configFields: Record<string, ConfigField[]> = {
  trigger: [
    { key: 'label', label: 'Name', type: 'text' },
    {
      key: 'trigger_type', label: 'Trigger Type', type: 'select',
      options: [
        { value: 'ACCESS_REQUEST', label: 'Access Request' },
        { value: 'FIREFIGHTER_REQUEST', label: 'Privileged Access Request' },
        { value: 'ROLE_CHANGE', label: 'Role Change' },
        { value: 'RISK_SPIKE', label: 'Risk Spike' },
        { value: 'PREDICTIVE_ALERT', label: 'Predictive Alert' },
        { value: 'SCHEDULED_REVIEW', label: 'Scheduled Review' },
        { value: 'EMERGENCY_ACCESS', label: 'Emergency Access' },
        { value: 'TERMINATION', label: 'Termination' },
        { value: 'TRANSFER', label: 'Transfer' },
        { value: 'CERTIFICATION', label: 'Certification' },
      ],
    },
    { key: 'auto_start', label: 'Auto Start', type: 'checkbox' },
    { key: 'require_justification', label: 'Require Justification', type: 'checkbox' },
  ],
  condition: [
    { key: 'label', label: 'Name', type: 'text' },
    {
      key: 'attribute', label: 'Attribute', type: 'select',
      options: [
        { value: 'RISK_SCORE', label: 'Risk Score' },
        { value: 'SYSTEM', label: 'System' },
        { value: 'SYSTEM_TYPE', label: 'System Type' },
        { value: 'ACCESS_TYPE', label: 'Access Type' },
        { value: 'ROLE_TAG', label: 'Role Tag' },
        { value: 'USER_TYPE', label: 'User Type' },
        { value: 'DEPARTMENT', label: 'Department' },
        { value: 'IS_TEMPORARY', label: 'Is Temporary' },
        { value: 'IS_EMERGENCY', label: 'Is Emergency' },
        { value: 'HAS_SOD', label: 'Has SoD Conflict' },
        { value: 'COUNTRY', label: 'Country' },
        { value: 'SENSITIVITY', label: 'Sensitivity' },
      ],
    },
    {
      key: 'operator', label: 'Operator', type: 'select',
      options: [
        { value: 'EQUALS', label: 'Equals' },
        { value: 'NOT_EQUALS', label: 'Not Equals' },
        { value: 'GREATER_THAN', label: 'Greater Than' },
        { value: 'LESS_THAN', label: 'Less Than' },
        { value: 'GREATER_OR_EQUAL', label: 'Greater or Equal' },
        { value: 'LESS_OR_EQUAL', label: 'Less or Equal' },
        { value: 'CONTAINS', label: 'Contains' },
        { value: 'IN_LIST', label: 'In List' },
        { value: 'IS_TRUE', label: 'Is True' },
        { value: 'IS_FALSE', label: 'Is False' },
        { value: 'BETWEEN', label: 'Between' },
      ],
    },
    { key: 'value', label: 'Value', type: 'text' },
  ],
  approval: [
    { key: 'label', label: 'Name', type: 'text' },
    {
      key: 'approver_type', label: 'Approver Type', type: 'select',
      options: [
        { value: 'LINE_MANAGER', label: 'Line Manager' },
        { value: 'ROLE_OWNER', label: 'Role Owner' },
        { value: 'PROCESS_OWNER', label: 'Process Owner' },
        { value: 'SECURITY_OFFICER', label: 'Security Officer' },
        { value: 'COMPLIANCE_OFFICER', label: 'Compliance Officer' },
        { value: 'DATA_OWNER', label: 'Data Owner' },
        { value: 'SYSTEM_OWNER', label: 'System Owner' },
        { value: 'CUSTOM_GROUP', label: 'Custom Group' },
        { value: 'AI_RECOMMENDED', label: 'AI Recommended' },
      ],
    },
    { key: 'sla_hours', label: 'SLA (hours)', type: 'number' },
    { key: 'is_required', label: 'Required', type: 'checkbox' },
    { key: 'allow_delegate', label: 'Allow Delegation', type: 'checkbox' },
    { key: 'allow_skip_if_unavailable', label: 'Skip if Unavailable', type: 'checkbox' },
  ],
  provisioning: [
    { key: 'label', label: 'Name', type: 'text' },
    {
      key: 'mode', label: 'Provisioning Mode', type: 'select',
      options: [
        { value: 'PER_ITEM', label: 'Per Item' },
        { value: 'ALL_OR_NOTHING', label: 'All or Nothing' },
        { value: 'RISK_BASED', label: 'Risk Based' },
        { value: 'TEMPORARY_FIRST', label: 'Temporary First' },
        { value: 'CRITICAL_LAST', label: 'Critical Last' },
      ],
    },
    { key: 'risk_threshold', label: 'Risk Threshold', type: 'number' },
    { key: 'allow_partial', label: 'Allow Partial', type: 'checkbox' },
    { key: 'block_sod_items', label: 'Block SoD Items', type: 'checkbox' },
    { key: 'log_all_decisions', label: 'Log All Decisions', type: 'checkbox' },
  ],
  action: [
    { key: 'label', label: 'Name', type: 'text' },
    {
      key: 'action_type', label: 'Action Type', type: 'select',
      options: [
        { value: 'PROVISION_ACCESS', label: 'Provision Access' },
        { value: 'REVOKE_ACCESS', label: 'Revoke Access' },
        { value: 'NOTIFY_USER', label: 'Notify User' },
        { value: 'NOTIFY_MANAGER', label: 'Notify Manager' },
        { value: 'NOTIFY_SECURITY', label: 'Notify Security' },
        { value: 'START_POST_REVIEW', label: 'Start Post Review' },
        { value: 'TRIGGER_AUDIT', label: 'Trigger Audit' },
        { value: 'CLOSE_REQUEST', label: 'Close Request' },
        { value: 'SCHEDULE_REVIEW', label: 'Schedule Review' },
        { value: 'LOG_EVENT', label: 'Log Event' },
        { value: 'CALL_WEBHOOK', label: 'Call Webhook' },
      ],
    },
    { key: 'review_days', label: 'Review Days', type: 'number' },
    { key: 'webhook_url', label: 'Webhook URL', type: 'text' },
  ],
  split: [
    { key: 'label', label: 'Name', type: 'text' },
    {
      key: 'split_by', label: 'Split By', type: 'select',
      options: [
        { value: 'ACCESS_ITEM', label: 'Access Item' },
        { value: 'SYSTEM', label: 'System' },
        { value: 'RISK_LEVEL', label: 'Risk Level' },
      ],
    },
  ],
  join: [
    { key: 'label', label: 'Name', type: 'text' },
    { key: 'wait_for_all', label: 'Wait for All', type: 'checkbox' },
    { key: 'timeout_hours', label: 'Timeout (hours)', type: 'number' },
  ],
};

// ============================================================
// Helpers
// ============================================================

let nodeIdCounter = 0;
function generateNodeId(): string {
  nodeIdCounter += 1;
  return `node_${Date.now()}_${nodeIdCounter}`;
}

function createNodeFromPaletteBlock(block: PaletteBlock, position: { x: number; y: number }): Node {
  const nodeType = blockTypeToNodeType(block.type);
  const nodeData: Record<string, any> = {
    label: block.name,
    blockType: block.type,
  };

  if (block.trigger_type) nodeData.trigger_type = block.trigger_type;
  if (block.attribute) {
    nodeData.attribute = block.attribute;
    nodeData.operator = 'GREATER_THAN';
    nodeData.value = '';
  }
  if (block.approver_type) {
    nodeData.approver_type = block.approver_type;
    nodeData.sla_hours = 48;
    nodeData.is_required = true;
    nodeData.allow_delegate = true;
    nodeData.allow_skip_if_unavailable = false;
  }
  if (block.mode) {
    nodeData.mode = block.mode;
    nodeData.risk_threshold = 50;
    nodeData.allow_partial = true;
    nodeData.block_sod_items = true;
    nodeData.log_all_decisions = true;
  }
  if (block.action_type) {
    nodeData.action_type = block.action_type;
    nodeData.review_days = 90;
  }
  if (block.split_by) nodeData.split_by = block.split_by;
  if (block.type === 'JOIN') {
    nodeData.wait_for_all = true;
  }

  return {
    id: generateNodeId(),
    type: nodeType,
    position,
    data: nodeData,
  };
}

// ============================================================
// WorkflowBuilder Inner Component (needs ReactFlowProvider context)
// ============================================================

function WorkflowBuilderInner() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([] as Node[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([] as Edge[]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [workflowName, setWorkflowName] = useState('New Workflow');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [previewText, setPreviewText] = useState('');
  const [showTemplates, setShowTemplates] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());

  // ---- API Queries ----

  const { data: paletteData } = useQuery<PaletteData>({
    queryKey: ['workflowPalette'],
    queryFn: () => api.get('/workflows/builder/palette').then(r => r.data),
    placeholderData: defaultPalette,
  });

  const { data: templatesData } = useQuery<WorkflowTemplate[]>({
    queryKey: ['workflowTemplates'],
    queryFn: () => api.get('/workflows/builder/templates').then(r => r.data),
    enabled: showTemplates,
  });

  const validateMutation = useMutation({
    mutationFn: (canvas: any) => api.post('/workflows/builder/validate', canvas).then(r => r.data),
    onSuccess: (data) => setValidation(data),
  });

  const previewMutation = useMutation({
    mutationFn: (canvas: any) => api.post('/workflows/builder/preview', canvas).then(r => r.data),
    onSuccess: (data) => {
      setPreviewText(typeof data === 'string' ? data : data.preview || JSON.stringify(data, null, 2));
      setShowPreview(true);
    },
  });

  const saveMutation = useMutation({
    mutationFn: (canvas: any) => api.post('/workflows/builder/export', canvas).then(r => r.data),
  });

  const loadTemplateMutation = useMutation({
    mutationFn: (templateName: string) =>
      api.get(`/workflows/builder/templates/${templateName}`).then(r => r.data),
    onSuccess: (data) => {
      if (data?.blocks) {
        const newNodes: Node[] = data.blocks.map((block: any) => ({
          id: block.block_id || generateNodeId(),
          type: blockTypeToNodeType(block.block_type),
          position: block.position || { x: 200, y: 0 },
          data: {
            label: block.name,
            blockType: block.block_type,
            ...block.settings,
            ...(block.trigger_type ? { trigger_type: block.trigger_type } : {}),
            ...(block.condition ? block.condition : {}),
            ...(block.approver ? { approver_type: block.approver.type, ...block.behavior, ...block.sla } : {}),
            ...(block.provisioning ? { mode: block.provisioning.mode, ...block.provisioning, ...block.safety } : {}),
            ...(block.action ? { action_type: block.action.type, ...block.action } : {}),
            ...(block.split_by ? { split_by: block.split_by } : {}),
            ...(block.wait_for_all !== undefined ? { wait_for_all: block.wait_for_all } : {}),
          },
        }));
        const newEdges: Edge[] = (data.connections || []).map((conn: any, idx: number) => ({
          id: `edge_${idx}`,
          source: conn.from,
          sourceHandle: conn.from_port !== 'output' ? conn.from_port : undefined,
          target: conn.to,
          targetHandle: conn.to_port !== 'input' ? conn.to_port : undefined,
          animated: true,
          style: { stroke: '#94a3b8', strokeWidth: 2 },
        }));
        setNodes(newNodes);
        setEdges(newEdges);
        setWorkflowName(data.name || 'Loaded Workflow');
        setWorkflowDescription(data.description || '');
      }
      setShowTemplates(false);
    },
  });

  const palette: PaletteData = paletteData || defaultPalette;

  // ---- Canvas helpers ----

  function buildCanvasPayload() {
    return {
      name: workflowName,
      description: workflowDescription,
      blocks: nodes.map(n => ({
        block_id: n.id,
        block_type: (n.data as any).blockType || n.type?.toUpperCase(),
        name: (n.data as any).label || '',
        position: n.position,
        ...n.data,
      })),
      connections: edges.map(e => ({
        from: e.source,
        from_port: e.sourceHandle || 'output',
        to: e.target,
        to_port: e.targetHandle || 'input',
      })),
    };
  }

  // ---- Drag & Drop ----

  const onDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      const raw = event.dataTransfer.getData('application/workflow-block');
      if (!raw) return;

      const block: PaletteBlock = JSON.parse(raw);
      const bounds = reactFlowWrapper.current?.getBoundingClientRect();
      if (!bounds || !reactFlowInstance) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      });

      const newNode = createNodeFromPaletteBlock(block, position);
      setNodes((nds) => [...nds, newNode]);
    },
    [reactFlowInstance, setNodes],
  );

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) => {
        const newEdge: Edge = {
          id: `edge_${Date.now()}`,
          source: params.source,
          target: params.target,
          sourceHandle: params.sourceHandle,
          targetHandle: params.targetHandle,
          animated: true,
          style: { stroke: '#94a3b8', strokeWidth: 2 },
        };
        return addEdge(newEdge, eds);
      });
    },
    [setEdges],
  );

  const onNodeClick = useCallback((_: any, node: Node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  // ---- Node config update ----

  const updateNodeData = useCallback(
    (nodeId: string, key: string, value: any) => {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.id !== nodeId) return n;
          const updatedData = { ...n.data, [key]: value };
          return { ...n, data: updatedData };
        }),
      );
      if (selectedNode && selectedNode.id === nodeId) {
        setSelectedNode((prev) =>
          prev ? { ...prev, data: { ...prev.data, [key]: value } } : null,
        );
      }
    },
    [setNodes, selectedNode],
  );

  const deleteSelectedNode = useCallback(() => {
    if (!selectedNode) return;
    setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
    setEdges((eds) =>
      eds.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id),
    );
    setSelectedNode(null);
  }, [selectedNode, setNodes, setEdges]);

  // ---- Category collapse toggle ----

  const toggleCategory = useCallback((cat: string) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }, []);

  // ---- Mini-map node color ----

  const minimapNodeColor = useCallback((node: Node) => {
    const colors: Record<string, string> = {
      trigger: '#3B82F6',
      condition: '#F59E0B',
      approval: '#10B981',
      provisioning: '#8B5CF6',
      action: '#EF4444',
      split: '#6366F1',
      join: '#6366F1',
    };
    return colors[node.type || ''] || '#94a3b8';
  }, []);

  // ---- Render ----

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] -m-6">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200 flex-shrink-0">
        <div className="flex items-center gap-3">
          <RectangleGroupIcon className="h-5 w-5 text-primary-600" />
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            className="text-sm font-semibold text-gray-900 border-none focus:ring-0 focus:outline-none bg-transparent w-48"
            placeholder="Workflow name..."
          />
          {validation && (
            <Badge variant={validation.valid ? 'success' : 'danger'} size="sm">
              {validation.valid ? 'Valid' : `${validation.errors.length} error(s)`}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            icon={<DocumentDuplicateIcon className="h-4 w-4" />}
            onClick={() => setShowTemplates(true)}
          >
            Templates
          </Button>
          <Button
            variant="secondary"
            size="sm"
            icon={<CheckCircleIcon className="h-4 w-4" />}
            onClick={() => validateMutation.mutate(buildCanvasPayload())}
          >
            Validate
          </Button>
          <Button
            variant="secondary"
            size="sm"
            icon={<EyeIcon className="h-4 w-4" />}
            onClick={() => previewMutation.mutate(buildCanvasPayload())}
          >
            Preview
          </Button>
          <Button
            size="sm"
            icon={<ArrowDownTrayIcon className="h-4 w-4" />}
            onClick={() => saveMutation.mutate(buildCanvasPayload())}
          >
            {saveMutation.isPending ? 'Saving...' : 'Save Workflow'}
          </Button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* ---- Left Sidebar: Block Palette ---- */}
        <div className="w-56 bg-gray-50 border-r border-gray-200 overflow-y-auto flex-shrink-0">
          <div className="px-3 py-2 border-b border-gray-200">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Building Blocks
            </h3>
          </div>
          <div className="p-2 space-y-1">
            {Object.entries(palette).map(([category, blocks]) => {
              const config = categoryConfig[category];
              if (!config) return null;
              const isCollapsed = collapsedCategories.has(category);

              return (
                <div key={category}>
                  <button
                    onClick={() => toggleCategory(category)}
                    className={`w-full flex items-center justify-between px-2 py-1.5 rounded text-xs font-semibold ${config.textClass} hover:${config.bgClass} transition-colors`}
                  >
                    <span>{config.label}</span>
                    <span className={`text-[10px] transition-transform ${isCollapsed ? '' : 'rotate-90'}`}>
                      &#9654;
                    </span>
                  </button>
                  {!isCollapsed && (
                    <div className="space-y-0.5 mt-0.5 mb-2">
                      {(blocks as PaletteBlock[]).map((block, idx) => {
                        const Icon = iconMap[block.icon] || BoltIcon;
                        return (
                          <div
                            key={`${category}-${idx}`}
                            draggable
                            onDragStart={(e) => {
                              e.dataTransfer.setData(
                                'application/workflow-block',
                                JSON.stringify(block),
                              );
                              e.dataTransfer.effectAllowed = 'move';
                            }}
                            className={`
                              flex items-center gap-2 px-2 py-1.5 rounded cursor-grab
                              border ${config.borderClass} ${config.bgClass}
                              hover:shadow-sm active:cursor-grabbing
                              transition-all duration-100
                            `}
                          >
                            <div
                              className="flex items-center justify-center w-5 h-5 rounded flex-shrink-0"
                              style={{ backgroundColor: block.color }}
                            >
                              <Icon className="h-3 w-3 text-white" />
                            </div>
                            <span className="text-[11px] font-medium text-gray-700 truncate">
                              {block.name}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ---- Canvas ---- */}
        <div className="flex-1 relative" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
            snapToGrid
            snapGrid={[16, 16]}
            deleteKeyCode={['Backspace', 'Delete']}
            className="bg-gray-100"
          >
            <Background color="#d1d5db" gap={16} size={1} />
            <Controls
              className="!bg-white !border-gray-200 !shadow-md !rounded-lg"
              showInteractive={false}
            />
            <MiniMap
              nodeColor={minimapNodeColor}
              className="!bg-white !border-gray-200 !shadow-md !rounded-lg"
              maskColor="rgba(0,0,0,0.08)"
            />

            {/* Empty canvas hint */}
            {nodes.length === 0 && (
              <Panel position="top-center">
                <div className="mt-32 text-center">
                  <RectangleGroupIcon className="h-12 w-12 text-gray-300 mx-auto" />
                  <p className="mt-3 text-sm text-gray-400 font-medium">
                    Drag blocks from the palette to start building
                  </p>
                  <p className="mt-1 text-xs text-gray-300">
                    or load a template to get started quickly
                  </p>
                  <button
                    onClick={() => setShowTemplates(true)}
                    className="mt-3 text-xs text-primary-600 hover:text-primary-700 font-medium"
                  >
                    Browse Templates
                  </button>
                </div>
              </Panel>
            )}
          </ReactFlow>

          {/* Validation results floating panel */}
          {validation && (
            <div className="absolute bottom-4 left-4 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-10 overflow-hidden">
              <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  {validation.valid ? (
                    <CheckCircleIcon className="h-4 w-4 text-green-500" />
                  ) : (
                    <ExclamationCircleIcon className="h-4 w-4 text-red-500" />
                  )}
                  <span className="text-xs font-semibold text-gray-700">
                    Validation {validation.valid ? 'Passed' : 'Failed'}
                  </span>
                </div>
                <button
                  onClick={() => setValidation(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <XMarkIcon className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="p-3 space-y-1.5 max-h-48 overflow-y-auto">
                {validation.errors.map((err, i) => (
                  <div key={`err-${i}`} className="flex items-start gap-2 text-xs">
                    <ExclamationCircleIcon className="h-3.5 w-3.5 text-red-500 flex-shrink-0 mt-0.5" />
                    <span className="text-red-700">{err.message}</span>
                  </div>
                ))}
                {validation.warnings.map((warn, i) => (
                  <div key={`warn-${i}`} className="flex items-start gap-2 text-xs">
                    <InformationCircleIcon className="h-3.5 w-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                    <span className="text-amber-700">{warn.message}</span>
                  </div>
                ))}
                {validation.valid && validation.errors.length === 0 && validation.warnings.length === 0 && (
                  <div className="flex items-center gap-2 text-xs text-green-700">
                    <CheckIcon className="h-3.5 w-3.5" />
                    Workflow is valid and ready to save.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ---- Right Sidebar: Node Configuration ---- */}
        {selectedNode && (
          <div className="w-72 bg-white border-l border-gray-200 overflow-y-auto flex-shrink-0">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
              <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Configure Block
              </h3>
              <div className="flex items-center gap-1">
                <button
                  onClick={deleteSelectedNode}
                  className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                  title="Delete block"
                >
                  <TrashIcon className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <XMarkIcon className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="p-4 space-y-4">
              {/* Node type indicator */}
              <div
                className="flex items-center gap-2 px-3 py-2 rounded-md text-xs font-medium text-white"
                style={{
                  backgroundColor:
                    selectedNode.type === 'trigger' ? '#3B82F6' :
                    selectedNode.type === 'condition' ? '#F59E0B' :
                    selectedNode.type === 'approval' ? '#10B981' :
                    selectedNode.type === 'provisioning' ? '#8B5CF6' :
                    selectedNode.type === 'action' ? '#EF4444' :
                    '#6366F1',
                }}
              >
                {(selectedNode.type || 'block').toUpperCase()}
              </div>

              {/* Config fields */}
              {(configFields[selectedNode.type || ''] || []).map((field) => (
                <div key={field.key}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    {field.label}
                  </label>
                  {field.type === 'text' && (
                    <input
                      type="text"
                      value={(selectedNode.data as any)[field.key] ?? ''}
                      onChange={(e) =>
                        updateNodeData(selectedNode.id, field.key, e.target.value)
                      }
                      className="w-full border border-gray-300 rounded-md px-2.5 py-1.5 text-xs focus:ring-primary-500 focus:border-primary-500"
                    />
                  )}
                  {field.type === 'number' && (
                    <input
                      type="number"
                      value={(selectedNode.data as any)[field.key] ?? ''}
                      onChange={(e) =>
                        updateNodeData(selectedNode.id, field.key, Number(e.target.value))
                      }
                      className="w-full border border-gray-300 rounded-md px-2.5 py-1.5 text-xs focus:ring-primary-500 focus:border-primary-500"
                    />
                  )}
                  {field.type === 'select' && field.options && (
                    <select
                      value={(selectedNode.data as any)[field.key] ?? ''}
                      onChange={(e) =>
                        updateNodeData(selectedNode.id, field.key, e.target.value)
                      }
                      className="w-full border border-gray-300 rounded-md px-2.5 py-1.5 text-xs focus:ring-primary-500 focus:border-primary-500"
                    >
                      {field.options.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  )}
                  {field.type === 'checkbox' && (
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={!!(selectedNode.data as any)[field.key]}
                        onChange={(e) =>
                          updateNodeData(selectedNode.id, field.key, e.target.checked)
                        }
                        className="rounded border-gray-300 text-primary-600 focus:ring-primary-500 h-3.5 w-3.5"
                      />
                      <span className="text-xs text-gray-500">Enabled</span>
                    </label>
                  )}
                </div>
              ))}

              {/* Node ID for reference */}
              <div className="pt-3 border-t border-gray-100">
                <p className="text-[10px] text-gray-400 font-mono">
                  ID: {selectedNode.id}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ---- Preview Modal ---- */}
      {showPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-900">Workflow Preview</h2>
              <button
                onClick={() => setShowPreview(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 rounded-lg p-4 border border-gray-200">
                {previewText || 'No preview available. Add blocks to the canvas first.'}
              </pre>
            </div>
            <div className="flex justify-end px-6 py-3 border-t border-gray-200">
              <Button variant="secondary" size="sm" onClick={() => setShowPreview(false)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ---- Templates Modal ---- */}
      {showTemplates && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <div>
                <h2 className="text-sm font-semibold text-gray-900">Template Gallery</h2>
                <p className="text-xs text-gray-500 mt-0.5">Start with a pre-built workflow</p>
              </div>
              <button
                onClick={() => setShowTemplates(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Built-in templates always shown */}
                {[
                  {
                    id: 'simple_access',
                    name: 'Simple Access Request',
                    description: 'Basic access request with manager approval. Perfect for low-risk standard workflows.',
                    icon: PlayIcon,
                    color: 'bg-blue-500',
                  },
                  {
                    id: 'multi_approver',
                    name: 'High-Risk Access Request',
                    description: 'Multi-approver workflow with risk-based conditions and parallel approvals.',
                    icon: ShieldCheckIcon,
                    color: 'bg-amber-500',
                  },
                  {
                    id: 'partial_provisioning',
                    name: 'Partial Provisioning',
                    description: 'Provision approved roles immediately without waiting for all items.',
                    icon: BoltIcon,
                    color: 'bg-violet-500',
                  },
                ].map((tpl) => (
                  <button
                    key={tpl.id}
                    onClick={() => loadTemplateMutation.mutate(tpl.id)}
                    disabled={loadTemplateMutation.isPending}
                    className="text-left p-4 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50/30 transition-all group"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <div className={`flex items-center justify-center w-8 h-8 rounded-lg ${tpl.color}`}>
                        <tpl.icon className="h-4 w-4 text-white" />
                      </div>
                      <h3 className="text-sm font-semibold text-gray-900 group-hover:text-primary-700">
                        {tpl.name}
                      </h3>
                    </div>
                    <p className="text-xs text-gray-500 leading-relaxed">
                      {tpl.description}
                    </p>
                  </button>
                ))}

                {/* API-loaded templates */}
                {(templatesData || []).map((tpl, idx) => (
                  <button
                    key={tpl.template_id || idx}
                    onClick={() =>
                      loadTemplateMutation.mutate(tpl.template_id || tpl.name)
                    }
                    disabled={loadTemplateMutation.isPending}
                    className="text-left p-4 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50/30 transition-all group"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gray-500">
                        <DocumentDuplicateIcon className="h-4 w-4 text-white" />
                      </div>
                      <h3 className="text-sm font-semibold text-gray-900 group-hover:text-primary-700">
                        {tpl.name}
                      </h3>
                    </div>
                    <p className="text-xs text-gray-500 leading-relaxed">
                      {tpl.description || 'Custom workflow template'}
                    </p>
                  </button>
                ))}
              </div>
            </div>
            <div className="flex justify-end px-6 py-3 border-t border-gray-200">
              <Button variant="secondary" size="sm" onClick={() => setShowTemplates(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Exported Page Component (wraps with ReactFlowProvider)
// ============================================================

export function WorkflowBuilder() {
  return (
    <ReactFlowProvider>
      <WorkflowBuilderInner />
    </ReactFlowProvider>
  );
}
