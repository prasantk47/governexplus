import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeftIcon,
  DocumentDuplicateIcon,
  UserGroupIcon,
  MagnifyingGlassIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ArrowUpTrayIcon,
  TableCellsIcon,
} from '@heroicons/react/24/outline';
import { REQUEST_TEMPLATES, RequestTemplate, DEPARTMENTS } from '../../config/requestTemplates';

interface BulkUser {
  id: string;
  username: string;
  displayName: string;
  email: string;
  department: string;
  selected: boolean;
  status?: 'pending' | 'success' | 'error';
  errorMessage?: string;
}

const mockUsers: BulkUser[] = [
  { id: '1', username: 'jsmith', displayName: 'John Smith', email: 'john.smith@company.com', department: 'Finance', selected: false },
  { id: '2', username: 'mjones', displayName: 'Mary Jones', email: 'mary.jones@company.com', department: 'Finance', selected: false },
  { id: '3', username: 'rwilson', displayName: 'Robert Wilson', email: 'robert.wilson@company.com', department: 'IT', selected: false },
  { id: '4', username: 'sbrown', displayName: 'Sarah Brown', email: 'sarah.brown@company.com', department: 'HR', selected: false },
  { id: '5', username: 'dlee', displayName: 'David Lee', email: 'david.lee@company.com', department: 'Sales', selected: false },
  { id: '6', username: 'agarcia', displayName: 'Ana Garcia', email: 'ana.garcia@company.com', department: 'Procurement', selected: false },
  { id: '7', username: 'tchen', displayName: 'Tom Chen', email: 'tom.chen@company.com', department: 'IT', selected: false },
  { id: '8', username: 'kpatel', displayName: 'Kavita Patel', email: 'kavita.patel@company.com', department: 'Finance', selected: false },
];

type BulkMode = 'template' | 'csv' | 'manual';

export function BulkAccessRequest() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [bulkMode, setBulkMode] = useState<BulkMode>('template');
  const [selectedTemplate, setSelectedTemplate] = useState<RequestTemplate | null>(null);
  const [users, setUsers] = useState<BulkUser[]>(mockUsers);
  const [searchTerm, setSearchTerm] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [justification, setJustification] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionComplete, setSubmissionComplete] = useState(false);

  const selectedUsers = users.filter((u) => u.selected);
  const filteredUsers = users.filter(
    (u) =>
      (u.displayName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.email.toLowerCase().includes(searchTerm.toLowerCase())) &&
      (departmentFilter === '' || u.department === departmentFilter)
  );

  const toggleUser = (id: string) => {
    setUsers(users.map((u) => (u.id === id ? { ...u, selected: !u.selected } : u)));
  };

  const selectAll = () => {
    setUsers(users.map((u) => ({ ...u, selected: filteredUsers.some((f) => f.id === u.id) ? true : u.selected })));
  };

  const deselectAll = () => {
    setUsers(users.map((u) => ({ ...u, selected: false })));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);

    // Simulate submission for each user
    for (let i = 0; i < selectedUsers.length; i++) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      setUsers((prev) =>
        prev.map((u) =>
          u.id === selectedUsers[i].id
            ? { ...u, status: Math.random() > 0.1 ? 'success' : 'error', errorMessage: Math.random() > 0.1 ? undefined : 'SoD conflict detected' }
            : u
        )
      );
    }

    setIsSubmitting(false);
    setSubmissionComplete(true);
  };

  const successCount = users.filter((u) => u.status === 'success').length;
  const errorCount = users.filter((u) => u.status === 'error').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Link
            to="/access-requests"
            className="mr-4 p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Bulk Access Request</h1>
            <p className="text-sm text-gray-500">
              Submit access requests for multiple users at once
            </p>
          </div>
        </div>
      </div>

      {/* Progress */}
      <div className="bg-white shadow rounded-lg p-4">
        <div className="flex items-center justify-between">
          {[1, 2, 3, 4].map((s) => (
            <div key={s} className="flex items-center">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full text-sm ${
                  step >= s ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-500'
                }`}
              >
                {s}
              </div>
              <span className={`ml-2 text-sm font-medium ${step >= s ? 'text-primary-600' : 'text-gray-500'}`}>
                {s === 1 && 'Select Method'}
                {s === 2 && 'Select Users'}
                {s === 3 && 'Justification'}
                {s === 4 && 'Submit'}
              </span>
              {s < 4 && <div className={`mx-4 h-0.5 w-20 ${step > s ? 'bg-primary-600' : 'bg-gray-200'}`} />}
            </div>
          ))}
        </div>
      </div>

      {/* Step 1: Select Method */}
      {step === 1 && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Select Request Method</h2>
            <p className="mt-1 text-sm text-gray-500">Choose how you want to create bulk access requests</p>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div
                onClick={() => setBulkMode('template')}
                className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                  bulkMode === 'template'
                    ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-200'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <DocumentDuplicateIcon className="h-8 w-8 text-primary-600 mb-3" />
                <h3 className="font-medium text-gray-900">Use Template</h3>
                <p className="text-xs text-gray-500 mt-1">Select from pre-defined role bundles</p>
              </div>
              <div
                onClick={() => setBulkMode('csv')}
                className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                  bulkMode === 'csv'
                    ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-200'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <ArrowUpTrayIcon className="h-8 w-8 text-green-600 mb-3" />
                <h3 className="font-medium text-gray-900">Upload CSV</h3>
                <p className="text-xs text-gray-500 mt-1">Import users and roles from file</p>
              </div>
              <div
                onClick={() => setBulkMode('manual')}
                className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                  bulkMode === 'manual'
                    ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-200'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <TableCellsIcon className="h-8 w-8 text-blue-600 mb-3" />
                <h3 className="font-medium text-gray-900">Manual Selection</h3>
                <p className="text-xs text-gray-500 mt-1">Pick users and roles manually</p>
              </div>
            </div>

            {bulkMode === 'template' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-gray-700">Select a Template</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {REQUEST_TEMPLATES.map((template) => (
                    <div
                      key={template.id}
                      onClick={() => {
                        setSelectedTemplate(template);
                        setJustification(template.defaultJustification);
                      }}
                      className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                        selectedTemplate?.id === template.id
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-gray-900">{template.name}</h4>
                        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                          {template.department}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mb-2">{template.description}</p>
                      <div className="flex items-center gap-2 text-xs text-gray-400">
                        <span>{template.roles.length} roles</span>
                        <span>|</span>
                        <span>Used {template.usageCount} times</span>
                        {template.isTemporary && (
                          <>
                            <span>|</span>
                            <span className="text-orange-500">{template.defaultDurationDays} days</span>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {bulkMode === 'csv' && (
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                <ArrowUpTrayIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-sm text-gray-600 mb-2">Drag and drop your CSV file here, or click to browse</p>
                <button className="text-sm text-primary-600 hover:text-primary-700 font-medium">
                  Download CSV Template
                </button>
              </div>
            )}
          </div>
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end">
            <button
              onClick={() => setStep(2)}
              disabled={bulkMode === 'template' && !selectedTemplate}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Select Users */}
      {step === 2 && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Select Users</h2>
                <p className="mt-1 text-sm text-gray-500">
                  {selectedTemplate
                    ? `Applying template: ${selectedTemplate.name}`
                    : 'Select users to include in this bulk request'}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">{selectedUsers.length} selected</span>
                <button onClick={selectAll} className="text-xs text-primary-600 hover:text-primary-700">
                  Select All
                </button>
                <span className="text-gray-300">|</span>
                <button onClick={deselectAll} className="text-xs text-gray-500 hover:text-gray-700">
                  Clear
                </button>
              </div>
            </div>
          </div>
          <div className="p-6">
            {/* Filters */}
            <div className="flex gap-4 mb-4">
              <div className="flex-1 relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search users..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              <select
                value={departmentFilter}
                onChange={(e) => setDepartmentFilter(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">All Departments</option>
                {DEPARTMENTS.map((dept) => (
                  <option key={dept} value={dept}>{dept}</option>
                ))}
              </select>
            </div>

            {/* User List */}
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-12">
                      <input
                        type="checkbox"
                        checked={filteredUsers.every((u) => u.selected)}
                        onChange={() => filteredUsers.every((u) => u.selected) ? deselectAll() : selectAll()}
                        className="h-4 w-4 rounded border-gray-300 text-primary-600"
                      />
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Department</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredUsers.map((user) => (
                    <tr
                      key={user.id}
                      onClick={() => toggleUser(user.id)}
                      className={`cursor-pointer ${user.selected ? 'bg-primary-50' : 'hover:bg-gray-50'}`}
                    >
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={user.selected}
                          onChange={() => toggleUser(user.id)}
                          className="h-4 w-4 rounded border-gray-300 text-primary-600"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-sm font-medium text-gray-600">
                            {user.displayName.split(' ').map((n) => n[0]).join('')}
                          </div>
                          <div>
                            <div className="text-sm font-medium text-gray-900">{user.displayName}</div>
                            <div className="text-xs text-gray-500">{user.username}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">{user.email}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                          {user.department}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep(3)}
              disabled={selectedUsers.length === 0}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Continue ({selectedUsers.length} users)
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Justification */}
      {step === 3 && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Business Justification</h2>
            <p className="mt-1 text-sm text-gray-500">Provide a reason for this bulk access request</p>
          </div>
          <div className="p-6 space-y-6">
            {/* Summary */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-700 mb-3">Request Summary</h3>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Users:</span>
                  <span className="ml-2 font-medium">{selectedUsers.length}</span>
                </div>
                {selectedTemplate && (
                  <>
                    <div>
                      <span className="text-gray-500">Template:</span>
                      <span className="ml-2 font-medium">{selectedTemplate.name}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Roles:</span>
                      <span className="ml-2 font-medium">{selectedTemplate.roles.length}</span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Roles being assigned */}
            {selectedTemplate && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3">Roles to be Assigned</h3>
                <div className="space-y-2">
                  {selectedTemplate.roles.map((role) => (
                    <div key={role.roleId} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <span className="text-sm font-medium text-gray-900">{role.roleName}</span>
                        <span className="ml-2 text-xs text-gray-500">({role.system})</span>
                      </div>
                      <span
                        className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                          role.riskLevel === 'critical' ? 'bg-red-100 text-red-800' :
                          role.riskLevel === 'high' ? 'bg-orange-100 text-orange-800' :
                          role.riskLevel === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        }`}
                      >
                        {role.riskLevel}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Justification */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Justification</label>
              <textarea
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                rows={4}
                placeholder="Explain the business need for this access..."
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
              />
              <p className="mt-1 text-xs text-gray-500">{justification.length}/500 characters</p>
            </div>
          </div>
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            <button
              onClick={() => setStep(2)}
              className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep(4)}
              disabled={justification.length < 20}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Review & Submit
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Submit */}
      {step === 4 && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              {submissionComplete ? 'Submission Complete' : 'Confirm & Submit'}
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              {submissionComplete
                ? 'Your bulk access requests have been processed'
                : 'Review and submit your bulk access request'}
            </p>
          </div>
          <div className="p-6">
            {!submissionComplete && !isSubmitting && (
              <div className="space-y-4">
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex">
                    <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400 flex-shrink-0" />
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-yellow-800">Confirm Bulk Request</h3>
                      <p className="mt-1 text-sm text-yellow-700">
                        You are about to submit {selectedUsers.length} access requests. Each request will go through the standard approval workflow.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-3">Users to receive access:</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedUsers.map((user) => (
                      <span key={user.id} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-700">
                        {user.displayName}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {isSubmitting && (
              <div className="space-y-4">
                <div className="text-center mb-6">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
                  <p className="text-sm text-gray-600">Processing requests...</p>
                </div>
                <div className="space-y-2">
                  {selectedUsers.map((user) => (
                    <div key={user.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-sm text-gray-900">{user.displayName}</span>
                      {user.status === 'pending' && <span className="text-xs text-gray-400">Pending...</span>}
                      {user.status === 'success' && (
                        <CheckCircleIcon className="h-5 w-5 text-green-500" />
                      )}
                      {user.status === 'error' && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-red-500">{user.errorMessage}</span>
                          <XCircleIcon className="h-5 w-5 text-red-500" />
                        </div>
                      )}
                      {!user.status && <span className="text-xs text-gray-400">Waiting...</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {submissionComplete && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-green-50 rounded-lg p-4 text-center">
                    <CheckCircleIcon className="h-8 w-8 text-green-500 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-green-700">{successCount}</p>
                    <p className="text-sm text-green-600">Successful</p>
                  </div>
                  <div className="bg-red-50 rounded-lg p-4 text-center">
                    <XCircleIcon className="h-8 w-8 text-red-500 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-red-700">{errorCount}</p>
                    <p className="text-sm text-red-600">Failed</p>
                  </div>
                </div>

                {errorCount > 0 && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h4 className="text-sm font-medium text-red-800 mb-2">Failed Requests</h4>
                    <div className="space-y-1">
                      {users.filter((u) => u.status === 'error').map((user) => (
                        <div key={user.id} className="text-sm text-red-700">
                          {user.displayName}: {user.errorMessage}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
            {!submissionComplete && !isSubmitting && (
              <>
                <button
                  onClick={() => setStep(3)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
                >
                  Back
                </button>
                <button
                  onClick={handleSubmit}
                  className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700"
                >
                  Submit {selectedUsers.length} Requests
                </button>
              </>
            )}
            {submissionComplete && (
              <button
                onClick={() => navigate('/access-requests')}
                className="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 ml-auto"
              >
                View All Requests
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
