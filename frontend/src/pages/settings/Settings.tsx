import { useState } from 'react';
import {
  Cog6ToothIcon,
  ShieldCheckIcon,
  BellIcon,
  ServerIcon,
  GlobeAltIcon,
  ClockIcon,
  TableCellsIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { RequestFormConfig } from './RequestFormConfig';
import {
  ACCESS_REQUEST_SLAS,
  FIREFIGHTER_SLAS,
  SOD_VIOLATION_SLAS,
  CERTIFICATION_SLAS,
  formatSLA,
} from '../../config/sla';
import {
  ACCESS_REQUEST_RACI,
  SOD_RISK_RACI,
  FIREFIGHTER_RACI,
  CERTIFICATION_RACI,
  getRACIColor,
  getRACILabel,
  type RACIRole,
} from '../../config/raci';

interface SettingsSection {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const settingsSections: SettingsSection[] = [
  {
    id: 'general',
    name: 'General Settings',
    description: 'Basic platform configuration',
    icon: Cog6ToothIcon,
  },
  {
    id: 'request_forms',
    name: 'Request Forms',
    description: 'Configure access request form fields',
    icon: DocumentTextIcon,
  },
  {
    id: 'security',
    name: 'Security Settings',
    description: 'Authentication and access controls',
    icon: ShieldCheckIcon,
  },
  {
    id: 'sla',
    name: 'SLA Configuration',
    description: 'Service level agreements and auto-actions',
    icon: ClockIcon,
  },
  {
    id: 'raci',
    name: 'RACI Matrix',
    description: 'Workflow roles and responsibilities',
    icon: TableCellsIcon,
  },
  {
    id: 'notifications',
    name: 'Notifications',
    description: 'Email and alert preferences',
    icon: BellIcon,
  },
  {
    id: 'integrations',
    name: 'Integrations',
    description: 'Connected systems and APIs',
    icon: ServerIcon,
  },
];

export function Settings() {
  const [activeSection, setActiveSection] = useState('general');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage platform configuration and preferences
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <nav className="space-y-1">
            {settingsSections.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center px-4 py-3 text-left rounded-lg ${
                    activeSection === section.id
                      ? 'bg-primary-50 text-primary-700 border border-primary-200'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <Icon className={`h-5 w-5 mr-3 ${activeSection === section.id ? 'text-primary-600' : 'text-gray-400'}`} />
                  <div>
                    <div className="text-sm font-medium">{section.name}</div>
                    <div className="text-xs text-gray-500">{section.description}</div>
                  </div>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="lg:col-span-3">
          {activeSection === 'general' && (
            <div className="bg-white shadow rounded-lg">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">General Settings</h2>
                <p className="mt-1 text-sm text-gray-500">Configure basic platform settings</p>
              </div>
              <div className="p-6 space-y-6">
                {/* Organization */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Organization Name
                  </label>
                  <input
                    type="text"
                    defaultValue="Acme Corporation"
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>

                {/* Timezone */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <ClockIcon className="h-4 w-4 inline mr-1" />
                    Default Timezone
                  </label>
                  <select className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500">
                    <option>UTC</option>
                    <option selected>US/Eastern</option>
                    <option>US/Pacific</option>
                    <option>Europe/London</option>
                    <option>Asia/Tokyo</option>
                  </select>
                </div>

                {/* Language */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <GlobeAltIcon className="h-4 w-4 inline mr-1" />
                    Language
                  </label>
                  <select className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500">
                    <option selected>English (US)</option>
                    <option>English (UK)</option>
                    <option>Spanish</option>
                    <option>French</option>
                    <option>German</option>
                  </select>
                </div>

                {/* Date Format */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Date Format
                  </label>
                  <select className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500">
                    <option selected>MM/DD/YYYY</option>
                    <option>DD/MM/YYYY</option>
                    <option>YYYY-MM-DD</option>
                  </select>
                </div>

                <div className="pt-4 flex justify-end">
                  <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm font-medium">
                    Save Changes
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeSection === 'request_forms' && <RequestFormConfig />}

          {activeSection === 'security' && (
            <div className="bg-white shadow rounded-lg">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Security Settings</h2>
                <p className="mt-1 text-sm text-gray-500">Configure authentication and access controls</p>
              </div>
              <div className="p-6 space-y-6">
                {/* Password Policy */}
                <div>
                  <h3 className="text-sm font-medium text-gray-900 mb-4">Password Policy</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-900">Minimum Password Length</div>
                        <div className="text-xs text-gray-500">Require passwords to be at least this long</div>
                      </div>
                      <select className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500">
                        <option>8 characters</option>
                        <option selected>12 characters</option>
                        <option>16 characters</option>
                      </select>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-900">Require Special Characters</div>
                        <div className="text-xs text-gray-500">Passwords must contain special characters</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                      </label>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-900">Password Expiry</div>
                        <div className="text-xs text-gray-500">Force password reset after this period</div>
                      </div>
                      <select className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500">
                        <option>30 days</option>
                        <option>60 days</option>
                        <option selected>90 days</option>
                        <option>Never</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* MFA Settings */}
                <div className="pt-4 border-t border-gray-200">
                  <h3 className="text-sm font-medium text-gray-900 mb-4">Multi-Factor Authentication</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-900">Require MFA for All Users</div>
                        <div className="text-xs text-gray-500">All users must enable MFA</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                      </label>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-900">MFA for High-Risk Actions</div>
                        <div className="text-xs text-gray-500">Require MFA for approvals and sensitive operations</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                      </label>
                    </div>
                  </div>
                </div>

                {/* Session Settings */}
                <div className="pt-4 border-t border-gray-200">
                  <h3 className="text-sm font-medium text-gray-900 mb-4">Session Management</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-900">Session Timeout</div>
                        <div className="text-xs text-gray-500">Auto-logout after inactivity</div>
                      </div>
                      <select className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500">
                        <option>15 minutes</option>
                        <option selected>30 minutes</option>
                        <option>1 hour</option>
                        <option>4 hours</option>
                      </select>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-900">Maximum Concurrent Sessions</div>
                        <div className="text-xs text-gray-500">Limit active sessions per user</div>
                      </div>
                      <select className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500">
                        <option>1</option>
                        <option selected>3</option>
                        <option>5</option>
                        <option>Unlimited</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="pt-4 flex justify-end">
                  <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm font-medium">
                    Save Changes
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeSection === 'notifications' && (
            <div className="bg-white shadow rounded-lg">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Notification Settings</h2>
                <p className="mt-1 text-sm text-gray-500">Configure email and alert preferences</p>
              </div>
              <div className="p-6 space-y-6">
                {/* Email Notifications */}
                <div>
                  <h3 className="text-sm font-medium text-gray-900 mb-4">Email Notifications</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-900">Access Request Submitted</div>
                        <div className="text-xs text-gray-500">Notify when new access requests are submitted</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                      </label>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-900">Approval Reminders</div>
                        <div className="text-xs text-gray-500">Send reminders for pending approvals</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                      </label>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-900">Certification Campaigns</div>
                        <div className="text-xs text-gray-500">Notify about certification deadlines</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                      </label>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-900">SoD Violations Detected</div>
                        <div className="text-xs text-gray-500">Alert when new violations are found</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                      </label>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-900">Firefighter Session Alerts</div>
                        <div className="text-xs text-gray-500">Notify on emergency access usage</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                      </label>
                    </div>
                  </div>
                </div>

                <div className="pt-4 flex justify-end">
                  <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm font-medium">
                    Save Changes
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeSection === 'sla' && (
            <div className="space-y-6">
              {/* Access Request SLAs */}
              <div className="bg-white shadow rounded-lg">
                <div className="p-6 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">Access Request SLAs</h2>
                  <p className="mt-1 text-sm text-gray-500">Risk-based SLA configuration with auto-actions</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Level</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Approval SLA</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Auto-Action</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {ACCESS_REQUEST_SLAS.map((sla) => (
                        <tr key={sla.riskLevel} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              sla.riskLevel === 'critical' ? 'bg-red-100 text-red-800' :
                              sla.riskLevel === 'high' ? 'bg-orange-100 text-orange-800' :
                              sla.riskLevel === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-green-100 text-green-800'
                            }`}>
                              {sla.riskLevel.charAt(0).toUpperCase() + sla.riskLevel.slice(1)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatSLA(sla.approvalSLA)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                            {sla.autoAction.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">{sla.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Firefighter SLAs */}
              <div className="bg-white shadow rounded-lg">
                <div className="p-6 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">Firefighter / Privileged Access SLAs</h2>
                  <p className="mt-1 text-sm text-gray-500">Emergency access session controls</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stage</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">SLA</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Auto-Action</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {FIREFIGHTER_SLAS.map((sla) => (
                        <tr key={sla.stage} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {sla.stage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatSLA(sla.sla)}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">{sla.autoAction}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* SoD Violation SLAs */}
              <div className="bg-white shadow rounded-lg">
                <div className="p-6 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">SoD Violation SLAs</h2>
                  <p className="mt-1 text-sm text-gray-500">Remediation timelines by severity</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Remediation SLA</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Escalation At</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Auto-Action</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {SOD_VIOLATION_SLAS.map((sla) => (
                        <tr key={sla.severity} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              sla.severity === 'critical' ? 'bg-red-100 text-red-800' :
                              sla.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                              sla.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-green-100 text-green-800'
                            }`}>
                              {sla.severity.charAt(0).toUpperCase() + sla.severity.slice(1)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatSLA(sla.remediationSLA)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                            {formatSLA(sla.escalationAt)}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">{sla.autoAction}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Certification SLAs */}
              <div className="bg-white shadow rounded-lg">
                <div className="p-6 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">Certification / Access Review SLAs</h2>
                  <p className="mt-1 text-sm text-gray-500">Review window and escalation timelines</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stage</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timing</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {CERTIFICATION_SLAS.map((sla) => (
                        <tr key={sla.stage} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {sla.stage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {formatSLA(sla.timing)}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">{sla.action}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeSection === 'raci' && (
            <div className="space-y-6">
              {/* RACI Legend */}
              <div className="bg-white shadow rounded-lg p-4">
                <div className="flex items-center gap-4 flex-wrap">
                  <span className="text-sm font-medium text-gray-700">Legend:</span>
                  {(['R', 'A', 'C', 'I', '-'] as RACIRole[]).map((role) => (
                    <span key={role} className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-medium ${getRACIColor(role)}`}>
                      {role} = {getRACILabel(role)}
                    </span>
                  ))}
                </div>
              </div>

              {/* Access Request RACI */}
              <div className="bg-white shadow rounded-lg">
                <div className="p-6 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">Access Request Workflow</h2>
                  <p className="mt-1 text-sm text-gray-500">RACI matrix for access request processing</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Activity</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">End User</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Manager</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Role Owner</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Platform</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Security Admin</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Auditor</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {ACCESS_REQUEST_RACI.map((entry, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">{entry.activity}</td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.endUser)}`}>{entry.endUser}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.manager)}`}>{entry.manager}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.roleOwner)}`}>{entry.roleOwner}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.platform)}`}>{entry.platform}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.securityAdmin)}`}>{entry.securityAdmin}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.auditor)}`}>{entry.auditor}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* SoD & Risk Management RACI */}
              <div className="bg-white shadow rounded-lg">
                <div className="p-6 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">SoD & Risk Management</h2>
                  <p className="mt-1 text-sm text-gray-500">RACI matrix for risk and compliance activities</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Activity</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">End User</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Manager</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Role Owner</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Platform</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Security Admin</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Auditor</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {SOD_RISK_RACI.map((entry, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">{entry.activity}</td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.endUser)}`}>{entry.endUser}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.manager)}`}>{entry.manager}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.roleOwner)}`}>{entry.roleOwner}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.platform)}`}>{entry.platform}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.securityAdmin)}`}>{entry.securityAdmin}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.auditor)}`}>{entry.auditor}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Firefighter RACI */}
              <div className="bg-white shadow rounded-lg">
                <div className="p-6 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">Firefighter / Privileged Access</h2>
                  <p className="mt-1 text-sm text-gray-500">RACI matrix for emergency access management</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Activity</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">End User</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Manager</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Role Owner</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Platform</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Security Admin</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Auditor</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {FIREFIGHTER_RACI.map((entry, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">{entry.activity}</td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.endUser)}`}>{entry.endUser}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.manager)}`}>{entry.manager}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.roleOwner)}`}>{entry.roleOwner}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.platform)}`}>{entry.platform}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.securityAdmin)}`}>{entry.securityAdmin}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.auditor)}`}>{entry.auditor}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Certification RACI */}
              <div className="bg-white shadow rounded-lg">
                <div className="p-6 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">Certification / Access Reviews</h2>
                  <p className="mt-1 text-sm text-gray-500">RACI matrix for access certification campaigns</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Activity</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">End User</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Manager</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Role Owner</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Platform</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Security Admin</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Auditor</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {CERTIFICATION_RACI.map((entry, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">{entry.activity}</td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.endUser)}`}>{entry.endUser}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.manager)}`}>{entry.manager}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.roleOwner)}`}>{entry.roleOwner}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.platform)}`}>{entry.platform}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.securityAdmin)}`}>{entry.securityAdmin}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-bold ${getRACIColor(entry.auditor)}`}>{entry.auditor}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Key Difference Note */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex">
                  <ExclamationTriangleIcon className="h-5 w-5 text-blue-400 flex-shrink-0" />
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-blue-800">Key Difference from Traditional GRC</h3>
                    <div className="mt-2 text-sm text-blue-700">
                      <ul className="list-disc list-inside space-y-1">
                        <li>Platform takes over risk evaluation and evidence generation</li>
                        <li>Fewer human dependencies with automated workflows</li>
                        <li>Faster, cleaner ownership with real-time risk scoring</li>
                        <li>Auto-escalation and auto-revoke based on SLA timers</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === 'integrations' && (
            <div className="bg-white shadow rounded-lg">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">System Integrations</h2>
                <p className="mt-1 text-sm text-gray-500">Manage connected systems and APIs</p>
              </div>
              <div className="p-6 space-y-4">
                {/* Connected Systems */}
                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="p-2 bg-blue-100 rounded-lg mr-4">
                        <ServerIcon className="h-6 w-6 text-blue-600" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">SAP ECC</div>
                        <div className="text-xs text-gray-500">Connected • Last sync: 5 minutes ago</div>
                      </div>
                    </div>
                    <span className="inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      Active
                    </span>
                  </div>
                </div>

                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="p-2 bg-orange-100 rounded-lg mr-4">
                        <ServerIcon className="h-6 w-6 text-orange-600" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">AWS</div>
                        <div className="text-xs text-gray-500">Connected • Last sync: 10 minutes ago</div>
                      </div>
                    </div>
                    <span className="inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      Active
                    </span>
                  </div>
                </div>

                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="p-2 bg-purple-100 rounded-lg mr-4">
                        <ServerIcon className="h-6 w-6 text-purple-600" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">Azure AD</div>
                        <div className="text-xs text-gray-500">Connected • Last sync: 2 minutes ago</div>
                      </div>
                    </div>
                    <span className="inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      Active
                    </span>
                  </div>
                </div>

                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="p-2 bg-green-100 rounded-lg mr-4">
                        <ServerIcon className="h-6 w-6 text-green-600" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">Workday</div>
                        <div className="text-xs text-gray-500">Connected • Last sync: 1 hour ago</div>
                      </div>
                    </div>
                    <span className="inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      Active
                    </span>
                  </div>
                </div>

                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="p-2 bg-gray-100 rounded-lg mr-4">
                        <ServerIcon className="h-6 w-6 text-gray-600" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">Salesforce</div>
                        <div className="text-xs text-gray-500">Disconnected • Configuration required</div>
                      </div>
                    </div>
                    <span className="inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      Inactive
                    </span>
                  </div>
                </div>

                <button className="mt-4 w-full px-4 py-2 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-primary-500 hover:text-primary-600">
                  + Add New Integration
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
