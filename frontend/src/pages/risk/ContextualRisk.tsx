import { useState } from 'react';
import {
  ClockIcon,
  GlobeAltIcon,
  DevicePhoneMobileIcon,
  ComputerDesktopIcon,
  MapPinIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  UserIcon,
  ArrowTrendingUpIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';

interface ContextualRiskEvent {
  id: string;
  user: string;
  userId: string;
  eventType: 'time' | 'location' | 'device' | 'behavior';
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  description: string;
  details: {
    key: string;
    value: string;
    anomaly?: boolean;
  }[];
  action: 'allowed' | 'blocked' | 'mfa_required' | 'reviewed';
}

interface RiskFactor {
  id: string;
  name: string;
  description: string;
  weight: number;
  enabled: boolean;
  icon: React.ComponentType<{ className?: string }>;
  currentImpact: number;
}

const riskFactors: RiskFactor[] = [
  {
    id: 'time',
    name: 'Time-Based Risk',
    description: 'Assess risk based on access time patterns',
    weight: 15,
    enabled: true,
    icon: ClockIcon,
    currentImpact: 23,
  },
  {
    id: 'location',
    name: 'Location-Based Risk',
    description: 'Evaluate geographic anomalies and travel patterns',
    weight: 25,
    enabled: true,
    icon: MapPinIcon,
    currentImpact: 45,
  },
  {
    id: 'device',
    name: 'Device-Based Risk',
    description: 'Check device trust and compliance status',
    weight: 20,
    enabled: true,
    icon: DevicePhoneMobileIcon,
    currentImpact: 18,
  },
  {
    id: 'network',
    name: 'Network-Based Risk',
    description: 'Analyze network and IP reputation',
    weight: 15,
    enabled: true,
    icon: GlobeAltIcon,
    currentImpact: 12,
  },
  {
    id: 'behavior',
    name: 'Behavioral Risk',
    description: 'Detect anomalous user behavior patterns',
    weight: 25,
    enabled: true,
    icon: ArrowTrendingUpIcon,
    currentImpact: 67,
  },
];

const recentEvents: ContextualRiskEvent[] = [
  {
    id: 'EVT-001',
    user: 'John Smith',
    userId: 'jsmith',
    eventType: 'location',
    riskLevel: 'high',
    timestamp: '2024-01-18 09:45:23',
    description: 'Impossible travel detected - login from different continents within 2 hours',
    details: [
      { key: 'Previous Location', value: 'New York, USA', anomaly: false },
      { key: 'Current Location', value: 'London, UK', anomaly: true },
      { key: 'Time Between', value: '2 hours 15 minutes', anomaly: true },
    ],
    action: 'mfa_required',
  },
  {
    id: 'EVT-002',
    user: 'Mary Jones',
    userId: 'mjones',
    eventType: 'time',
    riskLevel: 'medium',
    timestamp: '2024-01-18 03:22:15',
    description: 'Access attempt outside normal working hours',
    details: [
      { key: 'Access Time', value: '03:22 AM', anomaly: true },
      { key: 'Normal Hours', value: '08:00 AM - 06:00 PM', anomaly: false },
      { key: 'User Timezone', value: 'EST (UTC-5)', anomaly: false },
    ],
    action: 'allowed',
  },
  {
    id: 'EVT-003',
    user: 'Robert Wilson',
    userId: 'rwilson',
    eventType: 'device',
    riskLevel: 'critical',
    timestamp: '2024-01-18 10:15:00',
    description: 'Access from unregistered device with suspicious characteristics',
    details: [
      { key: 'Device Type', value: 'Unknown Android', anomaly: true },
      { key: 'Device Trust', value: 'Not Registered', anomaly: true },
      { key: 'MDM Status', value: 'Not Enrolled', anomaly: true },
    ],
    action: 'blocked',
  },
  {
    id: 'EVT-004',
    user: 'Sarah Brown',
    userId: 'sbrown',
    eventType: 'behavior',
    riskLevel: 'high',
    timestamp: '2024-01-18 11:30:45',
    description: 'Unusual data access pattern - 500% increase in file downloads',
    details: [
      { key: 'Files Downloaded', value: '2,345 files', anomaly: true },
      { key: 'Normal Average', value: '47 files/day', anomaly: false },
      { key: 'Data Volume', value: '15.2 GB', anomaly: true },
    ],
    action: 'reviewed',
  },
  {
    id: 'EVT-005',
    user: 'David Lee',
    userId: 'dlee',
    eventType: 'location',
    riskLevel: 'low',
    timestamp: '2024-01-18 08:00:00',
    description: 'Access from new but expected office location',
    details: [
      { key: 'Location', value: 'Chicago Office', anomaly: false },
      { key: 'Previous Locations', value: 'HQ, Remote', anomaly: false },
      { key: 'Travel Request', value: 'Approved', anomaly: false },
    ],
    action: 'allowed',
  },
];

const stats = {
  totalEvents: 1247,
  highRiskEvents: 89,
  blockedAccess: 34,
  mfaChallenges: 156,
};

export function ContextualRisk() {
  const [selectedEvent, setSelectedEvent] = useState<ContextualRiskEvent | null>(null);
  const [timeRange, setTimeRange] = useState('24h');

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'time': return ClockIcon;
      case 'location': return MapPinIcon;
      case 'device': return DevicePhoneMobileIcon;
      case 'behavior': return ArrowTrendingUpIcon;
      default: return ExclamationTriangleIcon;
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-green-100 text-green-800';
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'blocked': return 'bg-red-100 text-red-800';
      case 'mfa_required': return 'bg-yellow-100 text-yellow-800';
      case 'reviewed': return 'bg-blue-100 text-blue-800';
      default: return 'bg-green-100 text-green-800';
    }
  };

  const getActionLabel = (action: string) => {
    switch (action) {
      case 'blocked': return 'Blocked';
      case 'mfa_required': return 'MFA Required';
      case 'reviewed': return 'Under Review';
      default: return 'Allowed';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contextual Risk Intelligence</h1>
          <p className="text-sm text-gray-500">
            Real-time risk assessment based on time, location, device, and behavior
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="1h">Last 1 Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
          <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm">
            Configure Policies
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <EyeIcon className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.totalEvents.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Total Events</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <ExclamationTriangleIcon className="h-5 w-5 text-orange-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-orange-600">{stats.highRiskEvents}</p>
              <p className="text-xs text-gray-500">High Risk Events</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <ShieldCheckIcon className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-red-600">{stats.blockedAccess}</p>
              <p className="text-xs text-gray-500">Blocked Access</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <DevicePhoneMobileIcon className="h-5 w-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-yellow-600">{stats.mfaChallenges}</p>
              <p className="text-xs text-gray-500">MFA Challenges</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Factors Panel */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Risk Factors</h2>
            <p className="text-xs text-gray-500">Configure contextual risk evaluation weights</p>
          </div>
          <div className="p-4 space-y-4">
            {riskFactors.map((factor) => {
              const Icon = factor.icon;
              return (
                <div key={factor.id} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Icon className="h-5 w-5 text-gray-600" />
                      <span className="text-sm font-medium text-gray-900">{factor.name}</span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={factor.enabled}
                        className="sr-only peer"
                        readOnly
                      />
                      <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-600"></div>
                    </label>
                  </div>
                  <p className="text-xs text-gray-500 mb-2">{factor.description}</p>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Weight: {factor.weight}%</span>
                    <span className={`font-medium ${factor.currentImpact > 50 ? 'text-orange-600' : 'text-green-600'}`}>
                      Impact: {factor.currentImpact} events
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent Events */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Recent Risk Events</h2>
            <p className="text-xs text-gray-500">Contextual anomalies detected in real-time</p>
          </div>
          <div className="divide-y divide-gray-200">
            {recentEvents.map((event) => {
              const EventIcon = getEventIcon(event.eventType);
              return (
                <div
                  key={event.id}
                  className="p-4 hover:bg-gray-50 cursor-pointer"
                  onClick={() => setSelectedEvent(event)}
                >
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg ${
                      event.riskLevel === 'critical' ? 'bg-red-100' :
                      event.riskLevel === 'high' ? 'bg-orange-100' :
                      event.riskLevel === 'medium' ? 'bg-yellow-100' : 'bg-green-100'
                    }`}>
                      <EventIcon className={`h-5 w-5 ${
                        event.riskLevel === 'critical' ? 'text-red-600' :
                        event.riskLevel === 'high' ? 'text-orange-600' :
                        event.riskLevel === 'medium' ? 'text-yellow-600' : 'text-green-600'
                      }`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-gray-900">{event.user}</span>
                        <span className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${getRiskColor(event.riskLevel)}`}>
                          {event.riskLevel}
                        </span>
                        <span className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${getActionColor(event.action)}`}>
                          {getActionLabel(event.action)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 truncate">{event.description}</p>
                      <p className="text-xs text-gray-400 mt-1">{event.timestamp}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Event Detail Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">Risk Event Details</h2>
                <button
                  onClick={() => setSelectedEvent(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  &times;
                </button>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                  <UserIcon className="h-5 w-5 text-gray-600" />
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-900">{selectedEvent.user}</div>
                  <div className="text-xs text-gray-500">{selectedEvent.userId}</div>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getRiskColor(selectedEvent.riskLevel)}`}>
                    {selectedEvent.riskLevel} risk
                  </span>
                  <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getActionColor(selectedEvent.action)}`}>
                    {getActionLabel(selectedEvent.action)}
                  </span>
                </div>
                <p className="text-sm text-gray-700">{selectedEvent.description}</p>
                <p className="text-xs text-gray-500 mt-2">{selectedEvent.timestamp}</p>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Context Details</h4>
                <div className="space-y-2">
                  {selectedEvent.details.map((detail, i) => (
                    <div key={i} className={`flex items-center justify-between p-2 rounded ${detail.anomaly ? 'bg-red-50' : 'bg-gray-50'}`}>
                      <span className="text-sm text-gray-600">{detail.key}</span>
                      <span className={`text-sm font-medium ${detail.anomaly ? 'text-red-700' : 'text-gray-900'}`}>
                        {detail.value}
                        {detail.anomaly && <ExclamationTriangleIcon className="h-4 w-4 inline ml-1" />}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm"
              >
                Close
              </button>
              <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm">
                Investigate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
