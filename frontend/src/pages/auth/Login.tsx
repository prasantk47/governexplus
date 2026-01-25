import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../../contexts/AuthContext';

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err) {
      setError('Invalid username or password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      {error && (
        <div className="glass-btn bg-red-50/80 border-red-200 text-red-600 px-4 py-3 rounded-xl text-sm">
          {error}
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1.5">
            Username
          </label>
          <input
            id="username"
            name="username"
            type="text"
            required
            className="glass-input w-full px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1.5">
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              required
              className="glass-input w-full px-4 py-3 pr-12 text-sm text-gray-900 placeholder-gray-400 focus:outline-none"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
            >
              {showPassword ? (
                <EyeSlashIcon className="h-5 w-5" />
              ) : (
                <EyeIcon className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <label className="flex items-center">
          <input
            type="checkbox"
            className="w-4 h-4 rounded border-gray-300 text-gray-700 focus:ring-gray-500"
          />
          <span className="ml-2 text-sm text-gray-600">Remember me</span>
        </label>
        <button type="button" className="text-sm text-gray-600 hover:text-gray-800 font-medium">
          Forgot password?
        </button>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="btn-primary w-full justify-center py-3 text-base disabled:opacity-50"
      >
        {isLoading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Signing in...
          </span>
        ) : (
          'Sign in'
        )}
      </button>

      {/* Demo credentials */}
      <div className="glass-btn p-4 rounded-xl">
        <p className="text-xs text-center text-gray-600 font-medium mb-2">Demo Mode - Use any password</p>
        <div className="grid grid-cols-2 gap-2 text-xs text-center text-gray-500">
          <div className="glass px-2 py-1.5 rounded-lg">
            <span className="font-semibold text-gray-700">admin</span>
            <span className="block text-[10px]">System Admin</span>
          </div>
          <div className="glass px-2 py-1.5 rounded-lg">
            <span className="font-semibold text-gray-700">security</span>
            <span className="block text-[10px]">Security Admin</span>
          </div>
          <div className="glass px-2 py-1.5 rounded-lg">
            <span className="font-semibold text-gray-700">manager</span>
            <span className="block text-[10px]">Approver</span>
          </div>
          <div className="glass px-2 py-1.5 rounded-lg">
            <span className="font-semibold text-gray-700">john</span>
            <span className="block text-[10px]">End User</span>
          </div>
        </div>
      </div>
    </form>
  );
}
