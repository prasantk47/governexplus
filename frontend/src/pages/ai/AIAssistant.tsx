/**
 * Governex+ AI Assistant
 * Intelligent chat interface with action capabilities
 */
import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  SparklesIcon,
  PaperAirplaneIcon,
  UserCircleIcon,
  ClipboardDocumentIcon,
  ArrowPathIcon,
  LightBulbIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  PlusCircleIcon,
  MagnifyingGlassIcon,
  UserGroupIcon,
  CheckCircleIcon,
  ArrowTopRightOnSquareIcon,
  ClockIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../services/api';

interface ActionButton {
  label: string;
  icon: React.ElementType;
  action: () => void;
  variant?: 'primary' | 'secondary';
}

// Request types
type RequestType = 'new_account' | 'change' | 'remove' | 'transfer' | 'emergency' | 'bulk';

interface RequestTypeInfo {
  id: RequestType;
  name: string;
  description: string;
  icon: string;
}

const REQUEST_TYPES: RequestTypeInfo[] = [
  { id: 'new_account', name: 'New Account', description: 'Request access for a new user account', icon: '👤' },
  { id: 'change', name: 'Change/Modify', description: 'Modify existing access or add roles', icon: '✏️' },
  { id: 'remove', name: 'Remove Access', description: 'Remove roles or deactivate access', icon: '🗑️' },
  { id: 'transfer', name: 'Transfer', description: 'Transfer access during job change/role move', icon: '🔄' },
  { id: 'emergency', name: 'Emergency/Firefighter', description: 'Temporary elevated access for urgent issues', icon: '🚨' },
  { id: 'bulk', name: 'Bulk Upload', description: 'Upload Excel file for multiple users/roles', icon: '📊' },
];

interface PendingRequest {
  requestType?: RequestType;
  roles: string[];
  justification: string;
  targetUser?: string;
  duration?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  actions?: ActionButton[];
  data?: Record<string, unknown>;
  selectable?: {
    type: 'request_type' | 'roles' | 'confirm';
    options: Array<{ id: string; label: string; description?: string; selected?: boolean }>;
    multiSelect?: boolean;
    onSelect: (selected: string[]) => void;
  };
}

const suggestedPrompts = [
  {
    icon: PlusCircleIcon,
    title: 'New Request',
    prompt: 'I need to create an access request',
  },
  {
    icon: CpuChipIcon,
    title: 'ML Analytics',
    prompt: 'Show me ML analytics and predictions',
  },
  {
    icon: ExclamationTriangleIcon,
    title: 'Anomaly Detection',
    prompt: 'Check for suspicious activities and anomalies',
  },
  {
    icon: LightBulbIcon,
    title: 'Smart Recommendations',
    prompt: 'Get AI recommendations for my access',
  },
];

// Selectable Options Component
interface SelectableOptionsProps {
  options: Array<{ id: string; label: string; description?: string; selected?: boolean }>;
  multiSelect: boolean;
  onSelect: (selected: string[]) => void;
  type: 'request_type' | 'roles' | 'confirm';
}

function SelectableOptions({ options, multiSelect, onSelect, type }: SelectableOptionsProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [submitted, setSubmitted] = useState(false);

  const handleToggle = (id: string) => {
    if (submitted) return;

    if (multiSelect) {
      setSelected(prev => {
        const newSet = new Set(prev);
        if (newSet.has(id)) {
          newSet.delete(id);
        } else {
          newSet.add(id);
        }
        return newSet;
      });
    } else {
      // Single select - immediately trigger
      setSubmitted(true);
      onSelect([id]);
    }
  };

  const handleConfirm = () => {
    if (selected.size === 0 || submitted) return;
    setSubmitted(true);
    onSelect(Array.from(selected));
  };

  return (
    <div className="mt-3 space-y-2">
      <div className={clsx(
        'grid gap-2',
        type === 'request_type' ? 'grid-cols-1' : 'grid-cols-1 sm:grid-cols-2'
      )}>
        {options.map(option => (
          <button
            key={option.id}
            onClick={() => handleToggle(option.id)}
            disabled={submitted}
            className={clsx(
              'flex items-start gap-3 p-3 text-left rounded-lg border-2 transition-all',
              submitted && !selected.has(option.id) && type !== 'request_type'
                ? 'opacity-50 cursor-not-allowed'
                : '',
              selected.has(option.id) || (submitted && !multiSelect)
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-200 bg-white hover:border-primary-300 hover:bg-gray-50',
              submitted ? 'cursor-default' : 'cursor-pointer'
            )}
          >
            {multiSelect && (
              <div className={clsx(
                'w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5',
                selected.has(option.id)
                  ? 'border-primary-500 bg-primary-500'
                  : 'border-gray-300'
              )}>
                {selected.has(option.id) && (
                  <CheckCircleIcon className="h-3 w-3 text-white" />
                )}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900">{option.label}</p>
              {option.description && (
                <p className="text-xs text-gray-500 mt-0.5">{option.description}</p>
              )}
            </div>
          </button>
        ))}
      </div>

      {multiSelect && !submitted && (
        <div className="flex items-center gap-2 pt-2">
          <button
            onClick={handleConfirm}
            disabled={selected.size === 0}
            className={clsx(
              'inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-md transition-colors',
              selected.size > 0
                ? 'bg-primary-600 text-white hover:bg-primary-700'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            )}
          >
            <CheckCircleIcon className="h-4 w-4" />
            Continue with {selected.size} selected
          </button>
          <span className="text-xs text-gray-500">
            {selected.size === 0 ? 'Select at least one option' : `${selected.size} selected`}
          </span>
        </div>
      )}
    </div>
  );
}

export function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [pendingRequest, setPendingRequest] = useState<PendingRequest | null>(null);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const navigate = useNavigate();
  const { user } = useAuth();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Parse user intent and generate appropriate response
  const processUserMessage = async (userMessage: string): Promise<Message> => {
    const lowerMessage = userMessage.toLowerCase();

    // Intent: Bulk Upload / Excel
    if (lowerMessage.includes('excel') || lowerMessage.includes('bulk') || lowerMessage.includes('upload') ||
        (lowerMessage.includes('multiple') && lowerMessage.includes('user'))) {
      return handleBulkUploadIntent(userMessage);
    }

    // Intent: Create Access Request (including simple "i request" or "create request")
    if (lowerMessage.includes('request') ||
        lowerMessage.includes('i need access') ||
        lowerMessage.includes('create') ||
        lowerMessage.includes('new account')) {
      return handleAccessRequestIntent(userMessage);
    }

    // Intent: Check Risk/SoD
    if (lowerMessage.includes('risk') || lowerMessage.includes('sod') || lowerMessage.includes('violation')) {
      return handleRiskCheckIntent(userMessage);
    }

    // Intent: Search Roles
    if (lowerMessage.includes('search') || lowerMessage.includes('find') || lowerMessage.includes('look for')) {
      return handleSearchIntent(userMessage);
    }

    // Intent: Security Controls
    if (lowerMessage.includes('security') || lowerMessage.includes('control') || lowerMessage.includes('authentication')) {
      return handleSecurityControlsIntent(userMessage);
    }

    // Intent: Compliance
    if (lowerMessage.includes('compliance') || lowerMessage.includes('sox') || lowerMessage.includes('audit')) {
      return handleComplianceIntent(userMessage);
    }

    // Intent: ML Analytics / AI Analysis
    if (lowerMessage.includes('predict') || lowerMessage.includes('anomaly') || lowerMessage.includes('anomalies') ||
        lowerMessage.includes('machine learning') || lowerMessage.includes('ml') || lowerMessage.includes('ai analysis') ||
        lowerMessage.includes('recommendation') || lowerMessage.includes('suggest') || lowerMessage.includes('analytics')) {
      return handleMLAnalyticsIntent(userMessage);
    }

    // Intent: Role Mining
    if (lowerMessage.includes('role mining') || lowerMessage.includes('mine roles') || lowerMessage.includes('optimize roles') ||
        lowerMessage.includes('cluster') || lowerMessage.includes('role optimization')) {
      return handleRoleMiningIntent(userMessage);
    }

    // Intent: Confirm/Yes
    if ((lowerMessage === 'yes' || lowerMessage === 'confirm' || lowerMessage === 'proceed') && pendingRequest) {
      return handleConfirmRequest();
    }

    // Default response
    return handleDefaultIntent();
  };

  const handleBulkUploadIntent = async (userMessage: string): Promise<Message> => {
    // Bulk upload specific flow
    const bulkOperationTypes = [
      { id: 'add_roles', label: '➕ Add Roles', description: 'Add new roles to existing users' },
      { id: 'remove_roles', label: '➖ Remove Roles', description: 'Remove roles from users' },
      { id: 'new_users', label: '👤 Create Users', description: 'Create new user accounts with roles' },
      { id: 'modify_users', label: '✏️ Modify Users', description: 'Update user information and roles' },
    ];

    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: `📊 **Bulk User Management**\n\nI can help you manage multiple users at once via Excel upload.\n\n**What operation do you want to perform?**`,
      timestamp: new Date(),
      selectable: {
        type: 'request_type',
        options: bulkOperationTypes,
        multiSelect: false,
        onSelect: (selected) => handleBulkOperationSelected(selected[0])
      },
      actions: [
        {
          label: '📥 Download All Templates',
          icon: DocumentTextIcon,
          action: () => downloadAllTemplates(),
          variant: 'secondary'
        }
      ]
    };
  };

  const downloadAllTemplates = () => {
    // Download all templates as a zip-like bundle (individual files)
    const templates = [
      { type: 'add_roles', columns: ['User ID', 'Username', 'Role ID', 'Role Name', 'System', 'Start Date', 'End Date', 'Justification'] },
      { type: 'remove_roles', columns: ['User ID', 'Username', 'Role ID', 'Role Name', 'System', 'Removal Reason', 'Effective Date'] },
      { type: 'new_users', columns: ['Username', 'First Name', 'Last Name', 'Email', 'Department', 'Manager', 'Role ID', 'Role Name', 'System'] },
      { type: 'modify_users', columns: ['User ID', 'Username', 'Field to Update', 'New Value', 'Role ID (if applicable)', 'Action (add/remove)'] },
    ];

    templates.forEach((template, index) => {
      setTimeout(() => {
        downloadExcelTemplate(template.type, template.columns);
      }, index * 500); // Stagger downloads
    });

    const confirmMsg: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: `📥 **Downloading All Templates...**\n\nThe following templates are being downloaded:\n\n1. \`governex_bulk_add_roles_template.csv\`\n2. \`governex_bulk_remove_roles_template.csv\`\n3. \`governex_bulk_new_users_template.csv\`\n4. \`governex_bulk_modify_users_template.csv\`\n\nCheck your downloads folder. Fill in the appropriate template and upload when ready.`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Upload Completed File',
          icon: ArrowTopRightOnSquareIcon,
          action: () => {
            // Ask which type to upload
            const uploadMsg: Message = {
              id: Date.now().toString(),
              role: 'assistant',
              content: 'Which type of file are you uploading?',
              timestamp: new Date(),
              selectable: {
                type: 'request_type',
                options: [
                  { id: 'add_roles', label: '➕ Add Roles', description: 'Adding roles to users' },
                  { id: 'remove_roles', label: '➖ Remove Roles', description: 'Removing roles from users' },
                  { id: 'new_users', label: '👤 Create Users', description: 'Creating new users' },
                  { id: 'modify_users', label: '✏️ Modify Users', description: 'Modifying user data' },
                ],
                multiSelect: false,
                onSelect: (selected) => triggerFileUpload(selected[0])
              }
            };
            setMessages(prev => [...prev, uploadMsg]);
          },
          variant: 'primary'
        }
      ]
    };
    setMessages(prev => [...prev, confirmMsg]);
  };

  const handleBulkOperationSelected = async (operationType: string) => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: `I want to ${operationType.replace('_', ' ')}`,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    await new Promise(resolve => setTimeout(resolve, 500));

    // Generate template based on operation type
    const templateColumns = {
      add_roles: ['User ID', 'Username', 'Role ID', 'Role Name', 'System', 'Start Date', 'End Date', 'Justification'],
      remove_roles: ['User ID', 'Username', 'Role ID', 'Role Name', 'System', 'Removal Reason', 'Effective Date'],
      new_users: ['Username', 'First Name', 'Last Name', 'Email', 'Department', 'Manager', 'Role ID', 'Role Name', 'System'],
      modify_users: ['User ID', 'Username', 'Field to Update', 'New Value', 'Role ID (if applicable)', 'Action (add/remove)'],
    };

    const columns = templateColumns[operationType as keyof typeof templateColumns] || templateColumns.add_roles;

    const response: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `📄 **${operationType.replace('_', ' ').toUpperCase()} - Excel Template**\n\nTo process your bulk request, please prepare an Excel file with the following columns:\n\n${columns.map((col, i) => `${i + 1}. **${col}**`).join('\n')}\n\n**Instructions:**\n• First row should contain column headers\n• One row per user/role combination\n• For multiple roles per user, add separate rows\n• Dates should be in YYYY-MM-DD format\n\n**Example:**\n| ${columns.slice(0, 4).join(' | ')} |\n| --- | --- | --- | --- |\n| USR001 | john.doe | SAP_FI_USER | Finance User |\n| USR001 | john.doe | SAP_MM_BUYER | Procurement |\n| USR002 | jane.smith | SAP_HR_USER | HR User |`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Download Template',
          icon: DocumentTextIcon,
          action: () => downloadExcelTemplate(operationType, columns),
          variant: 'primary'
        },
        {
          label: 'Upload Excel File',
          icon: ArrowTopRightOnSquareIcon,
          action: () => triggerFileUpload(operationType),
          variant: 'primary'
        },
        {
          label: 'View Sample Data',
          icon: MagnifyingGlassIcon,
          action: () => showSampleData(operationType),
          variant: 'secondary'
        }
      ]
    };

    setMessages(prev => [...prev, response]);
    setIsLoading(false);
  };

  const downloadExcelTemplate = (operationType: string, columns: string[]) => {
    // Create comprehensive CSV templates based on operation type
    const sampleData: Record<string, string[]> = {
      add_roles: [
        'USR001,john.doe,SAP_FI_USER,Finance User,SAP ECC,2024-02-01,2024-12-31,Business requirement for Q1 reporting',
        'USR001,john.doe,SAP_MM_BUYER,Procurement Buyer,SAP ECC,2024-02-01,,Need to create POs for department',
        'USR002,jane.smith,SAP_HR_USER,HR User,SAP HCM,2024-02-01,,HR onboarding tasks',
        'USR003,bob.wilson,SAP_SD_USER,Sales User,SAP ECC,2024-02-01,2024-06-30,Temporary sales support',
        'USR003,bob.wilson,SAP_FI_APPROVER,Finance Approver,SAP ECC,2024-02-01,,Invoice approval duties',
      ],
      remove_roles: [
        'USR001,john.doe,SAP_FI_USER,Finance User,SAP ECC,Role no longer needed,2024-02-01',
        'USR002,jane.smith,SAP_MM_BUYER,Procurement Buyer,SAP ECC,Department change,2024-02-01',
        'USR003,bob.wilson,SAP_HR_ADMIN,HR Administrator,SAP HCM,Security audit finding,2024-02-01',
      ],
      new_users: [
        'john.doe,John,Doe,john.doe@company.com,Finance,mary.manager,SAP_FI_USER,Finance User,SAP ECC',
        'john.doe,John,Doe,john.doe@company.com,Finance,mary.manager,SAP_MM_BUYER,Procurement Buyer,SAP ECC',
        'jane.smith,Jane,Smith,jane.smith@company.com,HR,tom.supervisor,SAP_HR_USER,HR User,SAP HCM',
        'bob.wilson,Bob,Wilson,bob.wilson@company.com,Sales,mary.manager,SAP_SD_USER,Sales User,SAP ECC',
      ],
      modify_users: [
        'USR001,john.doe,Department,Finance to Accounting,,,',
        'USR001,john.doe,Manager,mary.manager to tom.supervisor,,,',
        'USR002,jane.smith,Role,,,SAP_HR_ADMIN,add',
        'USR002,jane.smith,Role,,,SAP_HR_USER,remove',
        'USR003,bob.wilson,Email,bob.wilson@newdomain.com,,,',
      ],
    };

    const csvContent = columns.join(',') + '\n' +
      (sampleData[operationType] || sampleData.add_roles).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `governex_bulk_${operationType}_template.csv`;
    a.click();
    URL.revokeObjectURL(url);

    // Add confirmation message with instructions
    const instructions: Record<string, string> = {
      add_roles: '**How to fill:**\n• User ID: Existing user ID or leave blank for lookup by username\n• Username: Required - user login name\n• Role ID: SAP role technical name\n• Start/End Date: YYYY-MM-DD format (End Date optional)\n• Justification: Business reason for access',
      remove_roles: '**How to fill:**\n• User ID: Existing user ID\n• Username: User login name\n• Role ID: Role to remove\n• Removal Reason: Why access is being removed\n• Effective Date: When to remove (YYYY-MM-DD)',
      new_users: '**How to fill:**\n• Username: New user login name (must be unique)\n• First/Last Name: User full name\n• Email: Corporate email address\n• Department: User department\n• Manager: Manager username for approvals\n• Role ID/Name: Initial roles to assign',
      modify_users: '**How to fill:**\n• User ID: Existing user ID\n• Field to Update: Department, Manager, Email, or Role\n• New Value: New value for the field\n• Role ID: Only for role changes\n• Action: "add" or "remove" for role changes',
    };

    const confirmMsg: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: `✅ **Template Downloaded!**\n\nFile: \`governex_bulk_${operationType}_template.csv\`\n\n${instructions[operationType] || instructions.add_roles}\n\n**Tips:**\n• Delete sample rows before adding your data\n• One row per user-role combination\n• Save as CSV (UTF-8) format`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Upload Completed File',
          icon: ArrowTopRightOnSquareIcon,
          action: () => triggerFileUpload(operationType),
          variant: 'primary'
        }
      ]
    };
    setMessages(prev => [...prev, confirmMsg]);
  };

  const triggerFileUpload = (operationType: string) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.xlsx,.xls,.csv';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        handleFileUpload(file, operationType);
      }
    };
    input.click();
  };

  const handleFileUpload = async (file: File, operationType: string) => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: `Uploading file: ${file.name}`,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    // Simulate file processing
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Simulated parsing results
    const parsedData = {
      totalRows: Math.floor(Math.random() * 20) + 5,
      validRows: 0,
      errors: [] as string[],
      users: [] as Array<{ userId: string; username: string; roles: string[]; action: string }>
    };

    parsedData.validRows = parsedData.totalRows - Math.floor(Math.random() * 3);
    if (parsedData.validRows < parsedData.totalRows) {
      parsedData.errors = [
        `Row 3: Invalid role ID "SAP_INVALID"`,
        `Row 7: Missing required field "Username"`,
      ].slice(0, parsedData.totalRows - parsedData.validRows);
    }

    // Generate sample users
    parsedData.users = [
      { userId: 'USR001', username: 'john.doe', roles: ['SAP_FI_USER', 'SAP_MM_BUYER'], action: 'add' },
      { userId: 'USR002', username: 'jane.smith', roles: ['SAP_HR_USER'], action: 'add' },
      { userId: 'USR003', username: 'bob.wilson', roles: ['SAP_SD_USER', 'SAP_FI_APPROVER'], action: 'add' },
    ];

    const hasErrors = parsedData.errors.length > 0;

    const response: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `📊 **File Processed: ${file.name}**\n\n**Summary:**\n• Total Rows: ${parsedData.totalRows}\n• Valid Rows: ${parsedData.validRows}\n• Errors: ${parsedData.errors.length}\n\n${hasErrors ? `**Errors Found:**\n${parsedData.errors.map(e => `⚠️ ${e}`).join('\n')}\n\n` : ''}**Users to Process:**\n${parsedData.users.map(u => `• **${u.username}** (${u.userId}): ${u.roles.join(', ')}`).join('\n')}\n\n${hasErrors ? 'Please fix the errors and re-upload, or proceed with valid rows only.' : 'All data looks good! Ready to submit?'}`,
      timestamp: new Date(),
      actions: hasErrors
        ? [
            {
              label: 'Proceed with Valid Rows',
              icon: CheckCircleIcon,
              action: () => submitBulkRequest(parsedData, operationType),
              variant: 'secondary'
            },
            {
              label: 'Upload Corrected File',
              icon: ArrowTopRightOnSquareIcon,
              action: () => triggerFileUpload(operationType),
              variant: 'primary'
            }
          ]
        : [
            {
              label: 'Submit Bulk Request',
              icon: CheckCircleIcon,
              action: () => submitBulkRequest(parsedData, operationType),
              variant: 'primary'
            },
            {
              label: 'Run Risk Analysis First',
              icon: ExclamationTriangleIcon,
              action: () => runBulkRiskAnalysis(parsedData, operationType),
              variant: 'secondary'
            }
          ]
    };

    setMessages(prev => [...prev, response]);
    setIsLoading(false);
  };

  const runBulkRiskAnalysis = async (data: { users: Array<{ userId: string; username: string; roles: string[] }> }, operationType: string) => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: 'Run risk analysis before submitting',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    await new Promise(resolve => setTimeout(resolve, 2000));

    // Simulate risk analysis
    const riskResults = {
      usersWithRisk: [
        { username: 'john.doe', conflicts: ['SOD-FI-001: Vendor Master vs Payment'], severity: 'HIGH' },
      ],
      totalRiskScore: 45,
      recommendation: 'Review high-risk assignments before proceeding'
    };

    const response: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `🔍 **Bulk Risk Analysis Complete**\n\n**Overall Risk Score:** ${riskResults.totalRiskScore}/100\n\n**Users with Potential Conflicts:**\n${riskResults.usersWithRisk.map(u => `• **${u.username}**: ${u.conflicts.join(', ')} (${u.severity})`).join('\n')}\n\n**Recommendation:** ${riskResults.recommendation}\n\nYou can still proceed, but affected users will require additional approval.`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Proceed with Request',
          icon: CheckCircleIcon,
          action: () => submitBulkRequest(data, operationType),
          variant: 'primary'
        },
        {
          label: 'Modify Assignments',
          icon: ArrowPathIcon,
          action: () => triggerFileUpload(operationType),
          variant: 'secondary'
        }
      ]
    };

    setMessages(prev => [...prev, response]);
    setIsLoading(false);
  };

  const submitBulkRequest = async (data: { users: Array<{ userId: string; username: string; roles: string[] }> }, operationType: string) => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: 'Submit the bulk request',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    await new Promise(resolve => setTimeout(resolve, 1500));

    const requestId = `BULK-${Date.now().toString().slice(-6)}`;

    const response: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `🎉 **Bulk Request Submitted Successfully!**\n\n**Request ID:** ${requestId}\n**Type:** ${operationType.replace('_', ' ').toUpperCase()}\n**Status:** Pending Approval\n**Users Affected:** ${data.users.length}\n**Total Role Assignments:** ${data.users.reduce((acc, u) => acc + u.roles.length, 0)}\n\n**Breakdown:**\n${data.users.map(u => `• ${u.username}: ${u.roles.length} role(s)`).join('\n')}\n\nYour bulk request has been submitted and will be processed. Individual approvals may be required for high-risk assignments.`,
      timestamp: new Date(),
      actions: [
        {
          label: 'View Bulk Requests',
          icon: DocumentTextIcon,
          action: () => navigate('/access-requests?type=bulk'),
          variant: 'primary'
        },
        {
          label: 'Create Another Bulk Request',
          icon: PlusCircleIcon,
          action: () => {
            const newRequest: Message = {
              id: Date.now().toString(),
              role: 'assistant',
              content: 'What type of bulk operation would you like to perform?',
              timestamp: new Date(),
              selectable: {
                type: 'request_type',
                options: [
                  { id: 'add_roles', label: '➕ Add Roles', description: 'Add new roles to existing users' },
                  { id: 'remove_roles', label: '➖ Remove Roles', description: 'Remove roles from users' },
                  { id: 'new_users', label: '👤 Create Users', description: 'Create new user accounts with roles' },
                  { id: 'modify_users', label: '✏️ Modify Users', description: 'Update user information and roles' },
                ],
                multiSelect: false,
                onSelect: (selected) => handleBulkOperationSelected(selected[0])
              }
            };
            setMessages(prev => [...prev, newRequest]);
          },
          variant: 'secondary'
        }
      ]
    };

    setMessages(prev => [...prev, response]);
    setIsLoading(false);
  };

  const showSampleData = (operationType: string) => {
    const sampleTables: Record<string, string> = {
      add_roles: `| User ID | Username    | Role ID        | Role Name         | System   | Start Date | End Date   | Justification              |
|---------|-------------|----------------|-------------------|----------|------------|------------|----------------------------|
| USR001  | john.doe    | SAP_FI_USER    | Finance User      | SAP ECC  | 2024-02-01 | 2024-12-31 | Q1 reporting needs         |
| USR001  | john.doe    | SAP_MM_BUYER   | Procurement Buyer | SAP ECC  | 2024-02-01 |            | PO creation duties         |
| USR002  | jane.smith  | SAP_HR_USER    | HR User           | SAP HCM  | 2024-02-01 |            | HR onboarding              |
| USR003  | bob.wilson  | SAP_SD_USER    | Sales User        | SAP ECC  | 2024-02-01 | 2024-06-30 | Temporary sales support    |`,
      remove_roles: `| User ID | Username    | Role ID        | Role Name         | System   | Removal Reason        | Effective Date |
|---------|-------------|----------------|-------------------|----------|-----------------------|----------------|
| USR001  | john.doe    | SAP_FI_USER    | Finance User      | SAP ECC  | Role no longer needed | 2024-02-01     |
| USR002  | jane.smith  | SAP_MM_BUYER   | Procurement Buyer | SAP ECC  | Department change     | 2024-02-01     |
| USR003  | bob.wilson  | SAP_HR_ADMIN   | HR Administrator  | SAP HCM  | Security audit        | 2024-02-01     |`,
      new_users: `| Username    | First Name | Last Name | Email                    | Department | Manager       | Role ID      | Role Name    | System   |
|-------------|------------|-----------|--------------------------|------------|---------------|--------------|--------------|----------|
| john.doe    | John       | Doe       | john.doe@company.com     | Finance    | mary.manager  | SAP_FI_USER  | Finance User | SAP ECC  |
| john.doe    | John       | Doe       | john.doe@company.com     | Finance    | mary.manager  | SAP_MM_BUYER | Procurement  | SAP ECC  |
| jane.smith  | Jane       | Smith     | jane.smith@company.com   | HR         | tom.supervisor| SAP_HR_USER  | HR User      | SAP HCM  |`,
      modify_users: `| User ID | Username    | Field to Update | New Value                    | Role ID      | Action |
|---------|-------------|-----------------|------------------------------|--------------|--------|
| USR001  | john.doe    | Department      | Finance to Accounting        |              |        |
| USR001  | john.doe    | Manager         | mary.manager to tom.super    |              |        |
| USR002  | jane.smith  | Role            |                              | SAP_HR_ADMIN | add    |
| USR002  | jane.smith  | Role            |                              | SAP_HR_USER  | remove |`,
    };

    const sampleMsg: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: `📋 **Sample Data for ${operationType.replace('_', ' ').toUpperCase()}**\n\n\`\`\`\n${sampleTables[operationType] || sampleTables.add_roles}\n\`\`\`\n\n**Note:** Each row represents one user-role combination. For users with multiple roles, add separate rows with the same User ID/Username.`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Download Template',
          icon: DocumentTextIcon,
          action: () => {
            const columns = {
              add_roles: ['User ID', 'Username', 'Role ID', 'Role Name', 'System', 'Start Date', 'End Date', 'Justification'],
              remove_roles: ['User ID', 'Username', 'Role ID', 'Role Name', 'System', 'Removal Reason', 'Effective Date'],
              new_users: ['Username', 'First Name', 'Last Name', 'Email', 'Department', 'Manager', 'Role ID', 'Role Name', 'System'],
              modify_users: ['User ID', 'Username', 'Field to Update', 'New Value', 'Role ID (if applicable)', 'Action (add/remove)'],
            };
            downloadExcelTemplate(operationType, columns[operationType as keyof typeof columns] || columns.add_roles);
          },
          variant: 'primary'
        },
        {
          label: 'Upload File',
          icon: ArrowTopRightOnSquareIcon,
          action: () => triggerFileUpload(operationType),
          variant: 'secondary'
        }
      ]
    };
    setMessages(prev => [...prev, sampleMsg]);
  };

  const handleAccessRequestIntent = async (userMessage: string): Promise<Message> => {
    // Initialize pending request
    setPendingRequest({
      roles: [],
      justification: userMessage
    });

    // First, ask for request type selection
    const requestTypeOptions = REQUEST_TYPES.map(rt => ({
      id: rt.id,
      label: `${rt.icon} ${rt.name}`,
      description: rt.description
    }));

    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: `I can help you create an access request. First, let me understand what type of request you need:\n\n**Select the request type:**`,
      timestamp: new Date(),
      selectable: {
        type: 'request_type',
        options: requestTypeOptions,
        multiSelect: false,
        onSelect: (selected) => handleRequestTypeSelected(selected[0] as RequestType, userMessage)
      }
    };
  };

  const handleRequestTypeSelected = async (requestType: RequestType, justification: string) => {
    setIsLoading(true);

    // Add user selection message
    const selectedType = REQUEST_TYPES.find(rt => rt.id === requestType);
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: `I want to create a ${selectedType?.name} request`,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    // Update pending request with type
    setPendingRequest(prev => prev ? { ...prev, requestType } : { requestType, roles: [], justification });

    await new Promise(resolve => setTimeout(resolve, 500));

    // For bulk upload, redirect to bulk flow
    if (requestType === 'bulk') {
      setIsLoading(false);
      const bulkResponse = await handleBulkUploadIntent(justification);
      setMessages(prev => [...prev, bulkResponse]);
      return;
    }

    // Extract role keywords from original message
    const roleKeywords = ['finance', 'procurement', 'hr', 'it', 'admin', 'buyer', 'approver', 'manager', 'vendor', 'payment', 'accounting'];
    const matchedKeywords = roleKeywords.filter(k => justification.toLowerCase().includes(k));

    // Get available roles based on request type
    const availableRoles = getAvailableRoles(requestType, matchedKeywords);

    // For emergency/firefighter, show different flow
    if (requestType === 'emergency') {
      const response: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `🚨 **Emergency/Firefighter Access Request**\n\nThis type of access is for urgent situations requiring temporary elevated privileges.\n\n**Available Emergency Roles:**`,
        timestamp: new Date(),
        selectable: {
          type: 'roles',
          options: availableRoles.map(r => ({
            id: r.id,
            label: `${r.name} (${r.system})`,
            description: `Risk: ${r.riskLevel} • Max Duration: ${r.maxDuration || '4 hours'}`
          })),
          multiSelect: true,
          onSelect: (selected) => handleRolesSelected(selected, requestType)
        }
      };
      setMessages(prev => [...prev, response]);
      setIsLoading(false);
      return;
    }

    // For remove request, show current access
    if (requestType === 'remove') {
      const currentAccess = [
        { id: 'SAP_FI_USER', name: 'Finance User', system: 'SAP ECC', assignedDate: '2024-01-15' },
        { id: 'SAP_MM_BUYER', name: 'Procurement Buyer', system: 'SAP ECC', assignedDate: '2024-03-20' },
        { id: 'SAP_SD_USER', name: 'Sales User', system: 'SAP ECC', assignedDate: '2024-02-10' },
      ];

      const response: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `🗑️ **Remove Access Request**\n\nSelect the roles you want to remove from ${user?.name || 'the user'}:\n\n**Current Access:**`,
        timestamp: new Date(),
        selectable: {
          type: 'roles',
          options: currentAccess.map(r => ({
            id: r.id,
            label: `${r.name} (${r.system})`,
            description: `Assigned: ${r.assignedDate}`
          })),
          multiSelect: true,
          onSelect: (selected) => handleRolesSelected(selected, requestType)
        }
      };
      setMessages(prev => [...prev, response]);
      setIsLoading(false);
      return;
    }

    // For transfer request, show department selection first
    if (requestType === 'transfer') {
      const response: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `🔄 **Transfer Request**\n\nI'll help you transfer access for a job change or role move.\n\nSelect the roles needed for your new position:`,
        timestamp: new Date(),
        selectable: {
          type: 'roles',
          options: availableRoles.map(r => ({
            id: r.id,
            label: `${r.name} (${r.system})`,
            description: `Risk: ${r.riskLevel}`
          })),
          multiSelect: true,
          onSelect: (selected) => handleRolesSelected(selected, requestType)
        }
      };
      setMessages(prev => [...prev, response]);
      setIsLoading(false);
      return;
    }

    // For new account and change requests
    const response: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: requestType === 'new_account'
        ? `👤 **New Account Request**\n\nI'll help you create a new user account with the appropriate roles.\n\nSelect the roles to assign:`
        : `✏️ **Change/Modify Request**\n\nSelect the additional roles you need:`,
      timestamp: new Date(),
      selectable: {
        type: 'roles',
        options: availableRoles.map(r => ({
          id: r.id,
          label: `${r.name} (${r.system})`,
          description: `Risk: ${r.riskLevel}`
        })),
        multiSelect: true,
        onSelect: (selected) => handleRolesSelected(selected, requestType)
      }
    };

    setMessages(prev => [...prev, response]);
    setIsLoading(false);
  };

  const getAvailableRoles = (requestType: RequestType, keywords: string[]) => {
    // Base roles available for all types
    const allRoles = [
      { id: 'SAP_FI_USER', name: 'Finance User', system: 'SAP ECC', riskLevel: 'MEDIUM', maxDuration: '8 hours' },
      { id: 'SAP_FI_APPROVER', name: 'Finance Approver', system: 'SAP ECC', riskLevel: 'HIGH', maxDuration: '4 hours' },
      { id: 'SAP_MM_BUYER', name: 'Procurement Buyer', system: 'SAP ECC', riskLevel: 'MEDIUM', maxDuration: '8 hours' },
      { id: 'SAP_MM_APPROVER', name: 'Procurement Approver', system: 'SAP ECC', riskLevel: 'HIGH', maxDuration: '4 hours' },
      { id: 'SAP_HR_USER', name: 'HR User', system: 'SAP HCM', riskLevel: 'MEDIUM', maxDuration: '8 hours' },
      { id: 'SAP_HR_ADMIN', name: 'HR Administrator', system: 'SAP HCM', riskLevel: 'HIGH', maxDuration: '4 hours' },
      { id: 'SAP_IT_ADMIN', name: 'IT Administrator', system: 'SAP BASIS', riskLevel: 'CRITICAL', maxDuration: '2 hours' },
      { id: 'SAP_VENDOR_MAINT', name: 'Vendor Maintenance', system: 'SAP ECC', riskLevel: 'HIGH', maxDuration: '4 hours' },
      { id: 'SAP_PAYMENT_RUN', name: 'Payment Processing', system: 'SAP ECC', riskLevel: 'CRITICAL', maxDuration: '2 hours' },
      { id: 'SAP_SD_USER', name: 'Sales User', system: 'SAP ECC', riskLevel: 'MEDIUM', maxDuration: '8 hours' },
    ];

    // Emergency roles are a subset
    if (requestType === 'emergency') {
      return allRoles.filter(r => r.riskLevel === 'HIGH' || r.riskLevel === 'CRITICAL');
    }

    // Filter by keywords if present
    if (keywords.length > 0) {
      const keywordMap: Record<string, string[]> = {
        finance: ['SAP_FI_USER', 'SAP_FI_APPROVER', 'SAP_PAYMENT_RUN'],
        accounting: ['SAP_FI_USER', 'SAP_FI_APPROVER'],
        procurement: ['SAP_MM_BUYER', 'SAP_MM_APPROVER'],
        buyer: ['SAP_MM_BUYER'],
        hr: ['SAP_HR_USER', 'SAP_HR_ADMIN'],
        it: ['SAP_IT_ADMIN'],
        admin: ['SAP_IT_ADMIN', 'SAP_HR_ADMIN'],
        vendor: ['SAP_VENDOR_MAINT'],
        payment: ['SAP_PAYMENT_RUN', 'SAP_FI_APPROVER'],
      };

      const matchedRoleIds = new Set<string>();
      keywords.forEach(k => {
        (keywordMap[k] || []).forEach(id => matchedRoleIds.add(id));
      });

      if (matchedRoleIds.size > 0) {
        const matchedRoles = allRoles.filter(r => matchedRoleIds.has(r.id));
        // Add some additional roles for context
        const additionalRoles = allRoles.filter(r => !matchedRoleIds.has(r.id)).slice(0, 3);
        return [...matchedRoles, ...additionalRoles];
      }
    }

    return allRoles;
  };

  const handleRolesSelected = async (selectedRoleIds: string[], requestType: RequestType) => {
    setIsLoading(true);
    setSelectedRoles(selectedRoleIds);

    // Add user selection message
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: `I selected ${selectedRoleIds.length} role(s): ${selectedRoleIds.join(', ')}`,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    // Update pending request
    setPendingRequest(prev => prev ? { ...prev, roles: selectedRoleIds } : null);

    await new Promise(resolve => setTimeout(resolve, 1000));

    // Run risk simulation
    const riskResult = simulateRiskCheck(selectedRoleIds, requestType);

    let response: Message;

    if (riskResult.hasConflicts) {
      response = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `⚠️ **Risk Analysis Complete**\n\n**Request Type:** ${REQUEST_TYPES.find(rt => rt.id === requestType)?.name}\n**Roles Selected:** ${selectedRoleIds.length}\n\n**SoD Conflicts Detected:**\n${riskResult.conflicts.map(c => `• **${c.rule}**: ${c.description} (${c.severity})`).join('\n')}\n\n**Risk Score:** ${riskResult.riskScore}/100\n\nYou can proceed, but additional justification and approvals will be required.`,
        timestamp: new Date(),
        actions: [
          {
            label: 'Proceed with Request',
            icon: ExclamationTriangleIcon,
            action: () => submitFinalRequest(selectedRoleIds, requestType, true),
            variant: 'secondary'
          },
          {
            label: 'Modify Selection',
            icon: ArrowPathIcon,
            action: () => handleRequestTypeSelected(requestType, pendingRequest?.justification || ''),
            variant: 'secondary'
          }
        ]
      };
    } else {
      response = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `✅ **Risk Analysis Complete**\n\n**Request Type:** ${REQUEST_TYPES.find(rt => rt.id === requestType)?.name}\n**Roles Selected:** ${selectedRoleIds.length}\n**Risk Score:** ${riskResult.riskScore}/100\n\nNo SoD conflicts detected. Your request is ready to submit.\n\n**Summary:**\n${selectedRoleIds.map(id => `• ${id}`).join('\n')}`,
        timestamp: new Date(),
        actions: [
          {
            label: 'Submit Request',
            icon: CheckCircleIcon,
            action: () => submitFinalRequest(selectedRoleIds, requestType, false),
            variant: 'primary'
          },
          {
            label: 'Add More Roles',
            icon: PlusCircleIcon,
            action: () => handleRequestTypeSelected(requestType, pendingRequest?.justification || ''),
            variant: 'secondary'
          }
        ]
      };
    }

    setMessages(prev => [...prev, response]);
    setIsLoading(false);
  };

  const simulateRiskCheck = (roleIds: string[], requestType: RequestType) => {
    // Simulate SoD conflict detection
    const hasVendorAndPayment = roleIds.includes('SAP_VENDOR_MAINT') && roleIds.includes('SAP_PAYMENT_RUN');
    const hasBuyerAndApprover = roleIds.includes('SAP_MM_BUYER') && roleIds.includes('SAP_MM_APPROVER');
    const hasHighRiskRoles = roleIds.some(id => ['SAP_IT_ADMIN', 'SAP_PAYMENT_RUN'].includes(id));

    const conflicts: Array<{rule: string; description: string; severity: string}> = [];

    if (hasVendorAndPayment) {
      conflicts.push({
        rule: 'SOD-FI-001',
        description: 'Vendor Master Maintenance vs Payment Processing',
        severity: 'CRITICAL'
      });
    }

    if (hasBuyerAndApprover) {
      conflicts.push({
        rule: 'SOD-MM-001',
        description: 'Purchase Order Creation vs Purchase Order Approval',
        severity: 'HIGH'
      });
    }

    // Calculate risk score
    let riskScore = roleIds.length * 10;
    if (hasHighRiskRoles) riskScore += 30;
    if (requestType === 'emergency') riskScore += 20;
    conflicts.forEach(c => {
      riskScore += c.severity === 'CRITICAL' ? 25 : 15;
    });
    riskScore = Math.min(riskScore, 100);

    return {
      hasConflicts: conflicts.length > 0,
      conflicts,
      riskScore
    };
  };

  const submitFinalRequest = async (roleIds: string[], requestType: RequestType, hasRisk: boolean) => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: hasRisk ? 'Proceed with the request despite risks' : 'Submit the request',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    await new Promise(resolve => setTimeout(resolve, 1000));

    const requestId = `REQ-${Date.now().toString().slice(-6)}`;
    const requestTypeInfo = REQUEST_TYPES.find(rt => rt.id === requestType);

    const response: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `🎉 **${requestTypeInfo?.name} Request Submitted!**\n\n**Request ID:** ${requestId}\n**Type:** ${requestTypeInfo?.icon} ${requestTypeInfo?.name}\n**Status:** Pending Approval\n**Roles:** ${roleIds.length} role(s)\n${roleIds.map(id => `• ${id}`).join('\n')}\n\n${hasRisk ? '⚠️ This request requires additional approval due to identified risks.\n\n' : ''}Your request has been submitted and routed to the appropriate approvers.`,
      timestamp: new Date(),
      actions: [
        {
          label: 'View My Requests',
          icon: DocumentTextIcon,
          action: () => navigate('/access-requests'),
          variant: 'primary'
        },
        {
          label: 'Create Another Request',
          icon: PlusCircleIcon,
          action: () => {
            setPendingRequest(null);
            setSelectedRoles([]);
            const welcomeBack: Message = {
              id: Date.now().toString(),
              role: 'assistant',
              content: 'What type of request would you like to create next?',
              timestamp: new Date(),
              selectable: {
                type: 'request_type',
                options: REQUEST_TYPES.map(rt => ({
                  id: rt.id,
                  label: `${rt.icon} ${rt.name}`,
                  description: rt.description
                })),
                multiSelect: false,
                onSelect: (selected) => handleRequestTypeSelected(selected[0] as RequestType, '')
              }
            };
            setMessages(prev => [...prev, welcomeBack]);
          },
          variant: 'secondary'
        }
      ]
    };

    setMessages(prev => [...prev, response]);
    setPendingRequest(null);
    setSelectedRoles([]);
    setIsLoading(false);
  };

  const handleConfirmRequest = async (): Promise<Message> => {
    if (!pendingRequest) {
      return handleDefaultIntent();
    }

    // This will be handled by the new flow
    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: 'Processing your request...',
      timestamp: new Date()
    };
  };

  const handleRiskCheckIntent = async (userMessage: string): Promise<Message> => {
    // Simulate fetching user risk data
    await new Promise(resolve => setTimeout(resolve, 1000));

    const riskData = {
      overallRisk: 'MEDIUM',
      sodViolations: 2,
      sensitiveAccess: 3,
      lastReview: '2024-01-15'
    };

    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: `📊 **Risk Profile for ${user?.name || 'Your Account'}**\n\n**Overall Risk Level:** ${riskData.overallRisk}\n\n**Current Status:**\n• SoD Violations: ${riskData.sodViolations} active\n• Sensitive Access: ${riskData.sensitiveAccess} items\n• Last Access Review: ${riskData.lastReview}\n\n**Recommendations:**\n1. Review and remediate the 2 SoD violations\n2. Ensure sensitive access is properly documented\n3. Schedule periodic access certification\n\nWould you like me to show details of the violations or help create remediation plans?`,
      timestamp: new Date(),
      actions: [
        {
          label: 'View Violations',
          icon: ExclamationTriangleIcon,
          action: () => navigate('/risk/violations'),
          variant: 'primary'
        },
        {
          label: 'Run Full Analysis',
          icon: MagnifyingGlassIcon,
          action: () => navigate('/risk/simulation'),
          variant: 'secondary'
        }
      ]
    };
  };

  const handleSearchIntent = async (userMessage: string): Promise<Message> => {
    // Extract search terms
    const searchTerms = userMessage.toLowerCase()
      .replace(/search|find|look for|roles?|related to|about/gi, '')
      .trim();

    // Simulate search results
    await new Promise(resolve => setTimeout(resolve, 800));

    const searchResults = [
      { id: 'SAP_MM_BUYER', name: 'Procurement Buyer', description: 'Create and manage purchase orders', risk: 'MEDIUM' },
      { id: 'SAP_MM_APPROVER', name: 'Procurement Approver', description: 'Approve purchase orders and contracts', risk: 'HIGH' },
      { id: 'SAP_MM_VIEWER', name: 'Procurement Viewer', description: 'View-only access to procurement data', risk: 'LOW' },
    ];

    const resultsList = searchResults.map(r =>
      `• **${r.name}** (${r.id})\n  ${r.description} | Risk: ${r.risk}`
    ).join('\n\n');

    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: `🔍 **Search Results for "${searchTerms || 'roles'}"**\n\nI found ${searchResults.length} matching roles:\n\n${resultsList}\n\nWould you like to request any of these roles? First, select the type of request:`,
      timestamp: new Date(),
      selectable: {
        type: 'request_type',
        options: REQUEST_TYPES.slice(0, 3).map(rt => ({
          id: rt.id,
          label: `${rt.icon} ${rt.name}`,
          description: rt.description
        })),
        multiSelect: false,
        onSelect: (selected) => {
          const requestType = selected[0] as RequestType;
          // Pre-select the found roles and go to role selection
          setPendingRequest({
            requestType,
            roles: [],
            justification: `Requesting roles related to: ${searchTerms}`
          });
          handleRolesSelected(searchResults.map(r => r.id), requestType);
        }
      },
      actions: [
        {
          label: 'Browse Role Catalog',
          icon: UserGroupIcon,
          action: () => navigate('/roles'),
          variant: 'secondary'
        }
      ],
      data: { searchResults }
    };
  };

  const handleSecurityControlsIntent = async (userMessage: string): Promise<Message> => {
    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: `🛡️ **Security Controls Guidance**\n\nBased on your query, here are key security controls to consider:\n\n**Authentication Controls:**\n• Implement MFA for privileged accounts\n• Enforce password complexity (min 8 chars, special characters)\n• Configure account lockout after 5 failed attempts\n• Enable SSO where possible\n\n**Authorization Controls:**\n• Apply principle of least privilege\n• Implement role-based access control (RBAC)\n• Regular access reviews (quarterly recommended)\n• Segregation of duties enforcement\n\n**Monitoring Controls:**\n• Enable comprehensive audit logging\n• Monitor for suspicious login patterns\n• Alert on privilege escalation\n• Track sensitive transaction access\n\nWould you like me to show your organization's current security control status or help you implement specific controls?`,
      timestamp: new Date(),
      actions: [
        {
          label: 'View Security Controls',
          icon: ShieldCheckIcon,
          action: () => navigate('/security-controls'),
          variant: 'primary'
        },
        {
          label: 'Import Controls',
          icon: DocumentTextIcon,
          action: () => navigate('/security-controls/import'),
          variant: 'secondary'
        }
      ]
    };
  };

  const handleComplianceIntent = async (userMessage: string): Promise<Message> => {
    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: `📋 **Compliance Guidance**\n\n**SOX Compliance Requirements:**\n\n1. **User Access Management (Section 404)**\n   • Documented provisioning/deprovisioning\n   • Timely access removal for terminated users\n   • Periodic access reviews (quarterly)\n\n2. **Privileged Access Controls**\n   • Restricted sensitive transaction access\n   • Privileged user activity monitoring\n   • Emergency access procedures (Firefighter)\n\n3. **Segregation of Duties**\n   • Documented SoD matrix\n   • Regular violation reviews\n   • Exception documentation\n\n**Your Compliance Status:**\n• Access Reviews: 85% complete\n• SoD Violations: 12 pending remediation\n• Documentation: 92% complete\n\nWould you like to see detailed compliance reports or start an access review campaign?`,
      timestamp: new Date(),
      actions: [
        {
          label: 'View Compliance Dashboard',
          icon: DocumentTextIcon,
          action: () => navigate('/compliance'),
          variant: 'primary'
        },
        {
          label: 'Start Certification',
          icon: CheckCircleIcon,
          action: () => navigate('/certification'),
          variant: 'secondary'
        }
      ]
    };
  };

  // =============================================================================
  // ML Analytics Handlers
  // =============================================================================

  const handleMLAnalyticsIntent = async (userMessage: string): Promise<Message> => {
    const lowerMessage = userMessage.toLowerCase();
    setIsLoading(true);

    // Determine specific ML action
    if (lowerMessage.includes('anomaly') || lowerMessage.includes('anomalies') || lowerMessage.includes('suspicious')) {
      return handleAnomalyDetection(userMessage);
    }
    if (lowerMessage.includes('predict') || lowerMessage.includes('forecast')) {
      return handleRiskPrediction(userMessage);
    }
    if (lowerMessage.includes('recommend') || lowerMessage.includes('suggest')) {
      return handleSmartRecommendations(userMessage);
    }

    // Default: Show ML capabilities menu
    const mlOptions = [
      { id: 'risk_prediction', label: '📊 Risk Prediction', description: 'Predict risk scores before granting access' },
      { id: 'anomaly_detection', label: '🔍 Anomaly Detection', description: 'Detect unusual access patterns and behaviors' },
      { id: 'smart_recommendations', label: '💡 Smart Recommendations', description: 'AI-powered role and access suggestions' },
      { id: 'role_mining', label: '⛏️ Role Mining', description: 'Discover optimal role structures from usage patterns' },
    ];

    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: `🤖 **ML Analytics Center**\n\nGovernex+ uses Machine Learning to enhance your GRC operations. Select an ML capability to explore:`,
      timestamp: new Date(),
      selectable: {
        type: 'request_type',
        options: mlOptions,
        multiSelect: false,
        onSelect: (selected) => handleMLOptionSelected(selected[0])
      },
      actions: [
        {
          label: 'View ML Dashboard',
          icon: LightBulbIcon,
          action: () => navigate('/ml/dashboard'),
          variant: 'secondary'
        }
      ]
    };
  };

  const handleMLOptionSelected = async (option: string) => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: `I want to use ${option.replace('_', ' ')}`,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    await new Promise(resolve => setTimeout(resolve, 500));

    let response: Message;

    switch (option) {
      case 'risk_prediction':
        response = await handleRiskPrediction('');
        break;
      case 'anomaly_detection':
        response = await handleAnomalyDetection('');
        break;
      case 'smart_recommendations':
        response = await handleSmartRecommendations('');
        break;
      case 'role_mining':
        response = await handleRoleMiningIntent('');
        break;
      default:
        response = await handleMLAnalyticsIntent('');
    }

    setMessages(prev => [...prev, response]);
    setIsLoading(false);
  };

  const handleRiskPrediction = async (userMessage: string): Promise<Message> => {
    // Simulate ML API call
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Simulated ML prediction results
    const predictions = {
      currentRiskScore: 42,
      predictedRiskScore: 38,
      confidence: 87,
      factors: [
        { factor: 'Privileged Access Count', impact: 'HIGH', contribution: 35 },
        { factor: 'SoD Violation Potential', impact: 'MEDIUM', contribution: 25 },
        { factor: 'Dormant Account Risk', impact: 'LOW', contribution: 15 },
        { factor: 'Access Pattern Regularity', impact: 'POSITIVE', contribution: -25 },
      ],
      recommendation: 'Risk is trending downward. Continue monitoring privileged access.',
      trendDirection: 'improving'
    };

    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: `📊 **ML Risk Prediction Analysis**\n\n**Current Risk Score:** ${predictions.currentRiskScore}/100\n**Predicted Score (30 days):** ${predictions.predictedRiskScore}/100 ${predictions.trendDirection === 'improving' ? '📉' : '📈'}\n**Model Confidence:** ${predictions.confidence}%\n\n**Contributing Factors:**\n${predictions.factors.map(f => `• **${f.factor}**: ${f.impact} impact (${f.contribution > 0 ? '+' : ''}${f.contribution}%)`).join('\n')}\n\n**AI Recommendation:** ${predictions.recommendation}\n\n---\n*Prediction based on 6 months of historical data using gradient boosting model.*`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Run Full Analysis',
          icon: MagnifyingGlassIcon,
          action: () => runDetailedRiskAnalysis(),
          variant: 'primary'
        },
        {
          label: 'Predict for Team',
          icon: UserGroupIcon,
          action: () => runTeamRiskPrediction(),
          variant: 'secondary'
        },
        {
          label: 'View Risk Trends',
          icon: ArrowPathIcon,
          action: () => navigate('/risk/trends'),
          variant: 'secondary'
        }
      ]
    };
  };

  const runDetailedRiskAnalysis = async () => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: 'Run detailed ML risk analysis',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    await new Promise(resolve => setTimeout(resolve, 2000));

    const detailedAnalysis: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `🔬 **Detailed ML Risk Analysis Complete**\n\n**Analysis Summary:**\n\n**1. Access Pattern Analysis**\n• Login frequency: Normal\n• After-hours access: 3 instances (within threshold)\n• Geographic anomalies: None detected\n\n**2. Permission Analysis**\n• Total active roles: 5\n• High-risk permissions: 2 (SAP_FI_APPROVER, SAP_PAYMENT_RUN)\n• Unused permissions (90 days): 8\n\n**3. SoD Risk Assessment**\n• Current violations: 1 (Vendor + Payment conflict)\n• Potential violations if unchanged: 2\n• Mitigation effectiveness: 78%\n\n**4. Peer Comparison**\n• Your risk: 42 (Medium)\n• Peer average: 55 (Medium-High)\n• Department average: 48 (Medium)\n\n**ML Model Insights:**\n• Primary risk driver: Privileged financial access\n• Recommended action: Review payment processing necessity\n• Auto-remediation available: Yes`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Apply Auto-Remediation',
          icon: CheckCircleIcon,
          action: () => applyAutoRemediation(),
          variant: 'primary'
        },
        {
          label: 'Export Report',
          icon: DocumentTextIcon,
          action: () => console.log('Export report'),
          variant: 'secondary'
        }
      ]
    };

    setMessages(prev => [...prev, detailedAnalysis]);
    setIsLoading(false);
  };

  const runTeamRiskPrediction = async () => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: 'Predict risk for my team',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    await new Promise(resolve => setTimeout(resolve, 2500));

    const teamAnalysis: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `👥 **Team Risk Prediction**\n\n**Team: Finance Department (12 members)**\n\n**Risk Distribution:**\n• 🟢 Low Risk (0-30): 4 users (33%)\n• 🟡 Medium Risk (31-60): 6 users (50%)\n• 🔴 High Risk (61-100): 2 users (17%)\n\n**High-Risk Team Members:**\n| User | Current | Predicted | Trend |\n|------|---------|-----------|-------|\n| J. Smith | 72 | 68 | 📉 |\n| M. Johnson | 85 | 82 | 📉 |\n\n**Team-Wide Recommendations:**\n1. Review privileged access for 2 high-risk users\n2. 3 users have unused permissions > 90 days\n3. Consider role consolidation (15% overlap detected)\n\n**Predicted Team Risk (30 days):** 48 → 44 (improving)`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Schedule Team Review',
          icon: ClockIcon,
          action: () => navigate('/certification/new?type=team'),
          variant: 'primary'
        },
        {
          label: 'View All Team Members',
          icon: UserGroupIcon,
          action: () => navigate('/users?department=finance'),
          variant: 'secondary'
        }
      ]
    };

    setMessages(prev => [...prev, teamAnalysis]);
    setIsLoading(false);
  };

  const applyAutoRemediation = async () => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: 'Apply ML-recommended auto-remediation',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    await new Promise(resolve => setTimeout(resolve, 1500));

    const remediationResult: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `✅ **Auto-Remediation Applied**\n\n**Actions Taken:**\n\n1. ✓ Removed 8 unused permissions (dormant > 90 days)\n2. ✓ Created access review for SAP_PAYMENT_RUN role\n3. ✓ Scheduled manager approval for Vendor/Payment conflict\n\n**Risk Impact:**\n• Previous Score: 42\n• New Score: 34 (-8 points)\n• Category: Medium → Low-Medium\n\n**Pending Approvals:**\n• 1 role requires manager confirmation\n• Review scheduled for tomorrow\n\n*All changes logged to audit trail.*`,
      timestamp: new Date(),
      actions: [
        {
          label: 'View Audit Log',
          icon: DocumentTextIcon,
          action: () => navigate('/audit'),
          variant: 'secondary'
        }
      ]
    };

    setMessages(prev => [...prev, remediationResult]);
    setIsLoading(false);
  };

  const handleAnomalyDetection = async (userMessage: string): Promise<Message> => {
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Simulated anomaly detection results
    const anomalies = {
      totalAlerts: 5,
      critical: 1,
      warning: 2,
      info: 2,
      recentAlerts: [
        { type: 'UNUSUAL_TIME', severity: 'WARNING', user: 'jsmith', description: 'Login at 3:42 AM from new location', time: '2 hours ago' },
        { type: 'DATA_EXFILTRATION', severity: 'CRITICAL', user: 'mbrown', description: 'Downloaded 5000+ records from customer table', time: '4 hours ago' },
        { type: 'PRIVILEGE_ESCALATION', severity: 'WARNING', user: 'tdavis', description: 'Attempted to access admin functions', time: '6 hours ago' },
      ]
    };

    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: `🔍 **Anomaly Detection Dashboard**\n\n**Active Alerts:** ${anomalies.totalAlerts}\n• 🔴 Critical: ${anomalies.critical}\n• 🟡 Warning: ${anomalies.warning}\n• 🔵 Info: ${anomalies.info}\n\n**Recent Anomalies:**\n${anomalies.recentAlerts.map(a => `\n**${a.severity}** - ${a.type.replace('_', ' ')}\n• User: ${a.user}\n• ${a.description}\n• Detected: ${a.time}`).join('\n')}\n\n**ML Detection Features:**\n• Behavioral baseline deviation\n• Unusual time/location access\n• Data access pattern analysis\n• Privilege escalation attempts`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Investigate Critical Alert',
          icon: ExclamationTriangleIcon,
          action: () => investigateAnomaly('critical'),
          variant: 'primary'
        },
        {
          label: 'View All Anomalies',
          icon: MagnifyingGlassIcon,
          action: () => navigate('/ml/anomalies'),
          variant: 'secondary'
        },
        {
          label: 'Configure Alerts',
          icon: ShieldCheckIcon,
          action: () => navigate('/settings/anomaly-detection'),
          variant: 'secondary'
        }
      ]
    };
  };

  const investigateAnomaly = async (severity: string) => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: `Investigate ${severity} anomaly`,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    await new Promise(resolve => setTimeout(resolve, 2000));

    const investigation: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `🔬 **Critical Anomaly Investigation**\n\n**Alert Details:**\n• Type: DATA_EXFILTRATION\n• User: mbrown (Mark Brown)\n• Time: Today, 4:15 AM\n• System: SAP ECC Production\n\n**Activity Analysis:**\n• Downloaded 5,247 records from BKPF (Accounting Docs)\n• Normal daily average: 50-100 records\n• Deviation: 5,200% above baseline\n• Used transaction SE16 (Table Browser)\n\n**ML Risk Assessment:**\n• Anomaly Score: 94/100 (Very High)\n• Similar incidents in dataset: 3 (all confirmed breaches)\n• False positive probability: 8%\n\n**User Context:**\n• Role: Finance Analyst\n• Employment: 2 years\n• Previous anomalies: 0\n• Current status: Active\n\n**Recommended Actions:**\n1. 🚨 Suspend user access immediately\n2. 📞 Contact user's manager\n3. 🔒 Preserve audit logs\n4. 📋 Open security incident`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Suspend User Access',
          icon: ExclamationTriangleIcon,
          action: () => console.log('Suspend user'),
          variant: 'primary'
        },
        {
          label: 'Mark False Positive',
          icon: CheckCircleIcon,
          action: () => console.log('Mark false positive'),
          variant: 'secondary'
        },
        {
          label: 'View Full Timeline',
          icon: ClockIcon,
          action: () => navigate('/audit?user=mbrown'),
          variant: 'secondary'
        }
      ]
    };

    setMessages(prev => [...prev, investigation]);
    setIsLoading(false);
  };

  const handleSmartRecommendations = async (userMessage: string): Promise<Message> => {
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Simulated recommendations
    const recommendations = [
      {
        type: 'REMOVE_ACCESS',
        confidence: 92,
        title: 'Remove Unused SAP_SD_USER Role',
        reason: 'No activity in 120 days, peer analysis shows 0% need',
        impact: 'Risk reduction: -5 points',
        status: 'pending'
      },
      {
        type: 'ADD_ACCESS',
        confidence: 87,
        title: 'Recommend SAP_FI_DISPLAY Role',
        reason: '85% of peers in Finance have this role, user has requested similar access 3x',
        impact: 'Productivity improvement estimated',
        status: 'pending'
      },
      {
        type: 'ROLE_OPTIMIZATION',
        confidence: 78,
        title: 'Consolidate 3 Procurement Roles',
        reason: 'Overlapping permissions detected, single role would suffice',
        impact: 'Simplifies access management, -2 risk points',
        status: 'pending'
      }
    ];

    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: `💡 **Smart Access Recommendations**\n\nBased on ML analysis of usage patterns, peer access, and risk factors:\n\n${recommendations.map((r, i) => `**${i + 1}. ${r.title}**\n• Type: ${r.type.replace('_', ' ')}\n• Confidence: ${r.confidence}%\n• Reason: ${r.reason}\n• Impact: ${r.impact}`).join('\n\n')}\n\n---\n*Recommendations generated using collaborative filtering and usage pattern analysis*`,
      timestamp: new Date(),
      selectable: {
        type: 'roles',
        options: recommendations.map((r, i) => ({
          id: `rec_${i}`,
          label: r.title,
          description: `${r.confidence}% confidence - ${r.type.replace('_', ' ')}`
        })),
        multiSelect: true,
        onSelect: (selected) => applyRecommendations(selected)
      },
      actions: [
        {
          label: 'Apply All Recommendations',
          icon: CheckCircleIcon,
          action: () => applyRecommendations(['rec_0', 'rec_1', 'rec_2']),
          variant: 'primary'
        },
        {
          label: 'Get More Suggestions',
          icon: LightBulbIcon,
          action: () => getMoreRecommendations(),
          variant: 'secondary'
        }
      ]
    };
  };

  const applyRecommendations = async (selectedIds: string[]) => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: `Apply ${selectedIds.length} recommendation(s)`,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    await new Promise(resolve => setTimeout(resolve, 1500));

    const result: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `✅ **Recommendations Applied**\n\n**Actions Queued:**\n• ${selectedIds.length} recommendation(s) submitted for processing\n• Manager approval required for access changes\n• Estimated completion: Within 24 hours\n\n**Workflow Created:**\n• Request ID: REC-${Date.now().toString().slice(-6)}\n• Status: Pending Approval\n• Approver: Your Manager\n\nYou'll receive a notification when the changes are complete.`,
      timestamp: new Date(),
      actions: [
        {
          label: 'View Request Status',
          icon: DocumentTextIcon,
          action: () => navigate('/access-requests'),
          variant: 'secondary'
        }
      ]
    };

    setMessages(prev => [...prev, result]);
    setIsLoading(false);
  };

  const getMoreRecommendations = async () => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: 'Get more ML recommendations',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    await new Promise(resolve => setTimeout(resolve, 1500));

    const moreRecs: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `💡 **Additional Recommendations**\n\n**Organization-Wide Insights:**\n\n1. **Role Consolidation Opportunity**\n   • 15 roles can be merged into 5 composite roles\n   • Affects 234 users\n   • Estimated risk reduction: 12%\n\n2. **Certification Campaign Suggested**\n   • 45% of users haven't had access review in 6+ months\n   • Recommend quarterly review for high-risk roles\n\n3. **SoD Rule Enhancement**\n   • ML detected 3 new conflict patterns\n   • Similar to existing rules but not covered\n   • Auto-generate suggested rules?\n\n4. **Dormant Access Cleanup**\n   • 1,247 permissions unused > 90 days\n   • Potential risk reduction: 18%`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Start Role Consolidation',
          icon: UserGroupIcon,
          action: () => navigate('/roles/consolidation'),
          variant: 'primary'
        },
        {
          label: 'Generate SoD Rules',
          icon: ShieldCheckIcon,
          action: () => navigate('/sod/generate'),
          variant: 'secondary'
        }
      ]
    };

    setMessages(prev => [...prev, moreRecs]);
    setIsLoading(false);
  };

  const handleRoleMiningIntent = async (userMessage: string): Promise<Message> => {
    await new Promise(resolve => setTimeout(resolve, 1000));

    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: `⛏️ **Role Mining & Optimization**\n\nRole mining uses ML algorithms to discover optimal role structures from actual user access patterns.\n\n**Available Algorithms:**\n• **K-Means Clustering**: Groups users by permission similarity\n• **Hierarchical**: Builds role hierarchy through agglomerative clustering\n• **DBSCAN**: Density-based clustering, good for finding outliers\n\n**Current Analysis:**\n• Total Users Analyzed: 1,250\n• Unique Permissions: 3,456\n• Existing Roles: 187\n• Suggested Optimal Roles: 45-60\n\n**Potential Benefits:**\n• Reduce role complexity by 65%\n• Improve access review efficiency by 40%\n• Decrease SoD violation surface by 25%`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Run Role Mining',
          icon: MagnifyingGlassIcon,
          action: () => runRoleMining(),
          variant: 'primary'
        },
        {
          label: 'View Mining History',
          icon: ClockIcon,
          action: () => navigate('/roles/mining'),
          variant: 'secondary'
        },
        {
          label: 'Configure Algorithm',
          icon: LightBulbIcon,
          action: () => navigate('/settings/role-mining'),
          variant: 'secondary'
        }
      ]
    };
  };

  const runRoleMining = async () => {
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: 'Run role mining analysis',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    // Simulate longer processing
    await new Promise(resolve => setTimeout(resolve, 3000));

    const miningResult: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `⛏️ **Role Mining Complete!**\n\n**Analysis Results:**\n\n**Discovered Role Clusters:** 52\n\n**Top Suggested Roles:**\n\n| Cluster | Users | Permissions | Suggested Name |\n|---------|-------|-------------|----------------|\n| C1 | 145 | 12 | Finance_Basic |\n| C2 | 89 | 18 | Procurement_Standard |\n| C3 | 67 | 8 | HR_Viewer |\n| C4 | 45 | 25 | Finance_Advanced |\n| C5 | 38 | 15 | Sales_Operations |\n\n**Optimization Metrics:**\n• Current Roles: 187\n• Optimal Roles: 52 (72% reduction)\n• Permission Coverage: 98.5%\n• User Coverage: 100%\n\n**Risk Analysis:**\n• SoD conflicts in suggestions: 0\n• High-risk role combinations: 3 (flagged for review)\n\n*Mining job ID: MINE-${Date.now().toString().slice(-6)}*`,
      timestamp: new Date(),
      actions: [
        {
          label: 'Review & Apply',
          icon: CheckCircleIcon,
          action: () => navigate('/roles/mining/review'),
          variant: 'primary'
        },
        {
          label: 'Export Results',
          icon: DocumentTextIcon,
          action: () => console.log('Export mining results'),
          variant: 'secondary'
        },
        {
          label: 'Adjust Parameters',
          icon: ArrowPathIcon,
          action: () => runRoleMining(),
          variant: 'secondary'
        }
      ]
    };

    setMessages(prev => [...prev, miningResult]);
    setIsLoading(false);
  };

  const handleDefaultIntent = (): Message => {
    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: `👋 Hi${user?.name ? ` ${user.name.split(' ')[0]}` : ''}! I'm your Governex+ AI Assistant powered by Machine Learning. I can help you with:\n\n**Access Management:**\n• **Create Requests** - "I need access to SAP Finance roles"\n• **Bulk Upload** - "Upload Excel for multiple users"\n\n**ML-Powered Analytics:**\n• **Risk Prediction** - "Predict my risk score"\n• **Anomaly Detection** - "Show suspicious activities"\n• **Smart Recommendations** - "Suggest access changes"\n• **Role Mining** - "Optimize role structures"\n\n**Compliance & Security:**\n• **Security Controls** - "What controls should I implement?"\n• **Compliance** - "SOX compliance requirements"\n\nJust tell me what you need!`,
      timestamp: new Date(),
      actions: [
        {
          label: 'New Access Request',
          icon: PlusCircleIcon,
          action: () => navigate('/access-requests/new'),
          variant: 'primary'
        },
        {
          label: 'View Dashboard',
          icon: LightBulbIcon,
          action: () => navigate('/dashboard'),
          variant: 'secondary'
        }
      ]
    };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await processUserMessage(userMessage.content);
      setMessages((prev) => [...prev, response]);
    } catch (error) {
      console.error('Error processing message:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestedPrompt = (prompt: string) => {
    setInput(prompt);
    inputRef.current?.focus();
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const clearChat = () => {
    setMessages([]);
    setPendingRequest(null);
    setSelectedRoles([]);
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <SparklesIcon className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">AI Assistant</h1>
            <p className="text-sm text-gray-500">Ask me to create requests, check risks, or find roles</p>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
          >
            <ArrowPathIcon className="h-4 w-4" />
            Clear chat
          </button>
        )}
      </div>

      {/* Chat Container */}
      <div className="flex-1 bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <SparklesIcon className="h-12 w-12 text-primary-400 mb-4" />
              <h2 className="text-lg font-medium text-gray-900 mb-2">
                What can I help you with?
              </h2>
              <p className="text-sm text-gray-500 mb-6 max-w-md">
                I can create access requests, analyze risks, search for roles, and guide you through compliance requirements.
              </p>

              {/* Suggested Prompts */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
                {suggestedPrompts.map((item, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestedPrompt(item.prompt)}
                    className="flex items-start gap-3 p-3 text-left bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition-colors"
                  >
                    <item.icon className="h-5 w-5 text-primary-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{item.title}</p>
                      <p className="text-xs text-gray-500 line-clamp-2">{item.prompt}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={clsx(
                    'flex gap-3',
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  {message.role === 'assistant' && (
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                        <SparklesIcon className="h-4 w-4 text-primary-600" />
                      </div>
                    </div>
                  )}
                  <div className={clsx('max-w-[80%]', message.role === 'user' ? 'order-first' : '')}>
                    <div
                      className={clsx(
                        'rounded-lg px-4 py-3',
                        message.role === 'user'
                          ? 'bg-primary-600 text-white'
                          : 'bg-gray-100 text-gray-900'
                      )}
                    >
                      <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                    </div>

                    {/* Selectable Options (Request Types / Roles) */}
                    {message.role === 'assistant' && message.selectable && (
                      <SelectableOptions
                        options={message.selectable.options}
                        multiSelect={message.selectable.multiSelect || false}
                        onSelect={message.selectable.onSelect}
                        type={message.selectable.type}
                      />
                    )}

                    {/* Action Buttons */}
                    {message.role === 'assistant' && message.actions && message.actions.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {message.actions.map((action, idx) => (
                          <button
                            key={idx}
                            onClick={action.action}
                            className={clsx(
                              'inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                              action.variant === 'primary'
                                ? 'bg-primary-600 text-white hover:bg-primary-700'
                                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                            )}
                          >
                            <action.icon className="h-3.5 w-3.5" />
                            {action.label}
                          </button>
                        ))}
                      </div>
                    )}

                    {message.role === 'assistant' && (
                      <div className="mt-2 flex items-center gap-2">
                        <button
                          onClick={() => copyToClipboard(message.content)}
                          className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
                        >
                          <ClipboardDocumentIcon className="h-3 w-3" />
                          Copy
                        </button>
                      </div>
                    )}
                  </div>
                  {message.role === 'user' && (
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                        <UserCircleIcon className="h-5 w-5 text-gray-500" />
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                      <SparklesIcon className="h-4 w-4 text-primary-600 animate-pulse" />
                    </div>
                  </div>
                  <div className="bg-gray-100 rounded-lg px-4 py-3">
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 p-4">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="Try: 'I need access to finance roles' or 'Check my risk profile'"
              className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              rows={2}
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className={clsx(
                'px-4 py-2 rounded-lg flex items-center justify-center',
                input.trim() && !isLoading
                  ? 'bg-primary-600 text-white hover:bg-primary-700'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              )}
            >
              <PaperAirplaneIcon className="h-5 w-5" />
            </button>
          </form>
          <p className="mt-2 text-xs text-gray-400 text-center">
            I can create requests, check risks, and navigate you to the right place.
          </p>
        </div>
      </div>
    </div>
  );
}
