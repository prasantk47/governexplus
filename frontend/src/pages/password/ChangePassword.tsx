import { useState } from 'react';
import { LockClosedIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../services/api';

export function ChangePassword() {
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const passwordRequirements = [
    { label: 'At least 12 characters', met: newPassword.length >= 12 },
    { label: 'Contains uppercase letter', met: /[A-Z]/.test(newPassword) },
    { label: 'Contains lowercase letter', met: /[a-z]/.test(newPassword) },
    { label: 'Contains number', met: /[0-9]/.test(newPassword) },
    { label: 'Contains special character', met: /[!@#$%^&*(),.?":{}|<>]/.test(newPassword) },
  ];

  const allRequirementsMet = passwordRequirements.every((req) => req.met);
  const passwordsMatch = newPassword === confirmPassword && confirmPassword.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!allRequirementsMet || !passwordsMatch) return;

    setIsSubmitting(true);
    setMessage(null);

    try {
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setMessage({ type: 'success', text: 'Password changed successfully!' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const errorMessage = axiosError?.response?.data?.detail || 'Failed to change password. Please try again.';
      setMessage({ type: 'error', text: errorMessage });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="page-title">Change Password</h1>
        <p className="page-subtitle">Update your login password for the GRC platform</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Change Password Form */}
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-header">
              <h2 className="section-title">New Password</h2>
            </div>
            <form onSubmit={handleSubmit} className="card-body space-y-4">
              {message && (
                <div
                  className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
                    message.type === 'success'
                      ? 'bg-green-50 text-green-700 border border-green-200'
                      : 'bg-red-50 text-red-700 border border-red-200'
                  }`}
                >
                  {message.type === 'success' ? (
                    <CheckCircleIcon className="h-5 w-5" />
                  ) : (
                    <ExclamationCircleIcon className="h-5 w-5" />
                  )}
                  {message.text}
                </div>
              )}

              <div>
                <label htmlFor="currentPassword" className="block text-sm font-medium text-gray-700 mb-1">
                  Current Password
                </label>
                <input
                  type="password"
                  id="currentPassword"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                  required
                />
              </div>

              <div>
                <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700 mb-1">
                  New Password
                </label>
                <input
                  type="password"
                  id="newPassword"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                  required
                />
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  id="confirmPassword"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={`block w-full rounded-md shadow-sm sm:text-sm ${
                    confirmPassword && !passwordsMatch
                      ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                      : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500'
                  }`}
                  required
                />
                {confirmPassword && !passwordsMatch && (
                  <p className="mt-1 text-xs text-red-600">Passwords do not match</p>
                )}
              </div>

              <div className="pt-4">
                <button
                  type="submit"
                  disabled={isSubmitting || !allRequirementsMet || !passwordsMatch}
                  className="btn-primary w-full sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Changing Password...' : 'Change Password'}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Password Requirements */}
        <div>
          <div className="card">
            <div className="card-header">
              <h2 className="section-title">Password Requirements</h2>
            </div>
            <div className="card-body">
              <ul className="space-y-2">
                {passwordRequirements.map((req, idx) => (
                  <li key={idx} className="flex items-center gap-2 text-sm">
                    <span
                      className={`flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center ${
                        req.met ? 'bg-green-100' : 'bg-gray-100'
                      }`}
                    >
                      {req.met && <CheckCircleIcon className="h-3 w-3 text-green-600" />}
                    </span>
                    <span className={req.met ? 'text-green-700' : 'text-gray-500'}>{req.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="card mt-4">
            <div className="card-header">
              <h2 className="section-title">Account Info</h2>
            </div>
            <div className="card-body space-y-2">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center">
                  <LockClosedIcon className="h-5 w-5 text-primary-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                  <p className="text-xs text-gray-500">{user?.email}</p>
                </div>
              </div>
              <div className="pt-2 border-t border-gray-100">
                <p className="text-xs text-gray-500">
                  Last password change: <span className="font-medium">45 days ago</span>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
