import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheckIcon,
  KeyIcon,
  EnvelopeIcon,
  ExclamationCircleIcon,
  EyeIcon,
  EyeSlashIcon,
  LockClosedIcon,
  SparklesIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

export function AdminLogin() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [loginSuccess, setLoginSuccess] = useState(false);

  // Animated background particles
  const [particles] = useState(() =>
    Array.from({ length: 50 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 4 + 1,
      duration: Math.random() * 20 + 10,
      delay: Math.random() * 5,
    }))
  );

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (data.success) {
        setLoginSuccess(true);
        localStorage.setItem('admin_token', data.token);
        localStorage.setItem('admin_user', JSON.stringify(data.admin));
        setTimeout(() => navigate('/admin/dashboard'), 800);
      } else {
        setError(data.message || 'Invalid credentials');
      }
    } catch (err) {
      // Demo mode fallback
      if (email === 'admin@governex.local' && password === 'admin123') {
        setLoginSuccess(true);
        localStorage.setItem('admin_token', 'demo_token_' + Date.now());
        localStorage.setItem('admin_user', JSON.stringify({
          email: 'admin@governex.local',
          name: 'Platform Administrator',
          role: 'super_admin',
          avatar: null
        }));
        setTimeout(() => navigate('/admin/dashboard'), 800);
      } else {
        setError('Invalid credentials');
      }
    }

    if (!loginSuccess) {
      setIsLoading(false);
    }
  };

  // Check if already logged in
  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (token) {
      navigate('/admin/dashboard');
    }
  }, [navigate]);

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900">
        {/* Animated orbs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-500/10 rounded-full blur-3xl" />

        {/* Floating particles */}
        {particles.map(p => (
          <div
            key={p.id}
            className="absolute rounded-full bg-white/10"
            style={{
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: p.size,
              height: p.size,
              animation: `float ${p.duration}s ease-in-out infinite`,
              animationDelay: `${p.delay}s`,
            }}
          />
        ))}
      </div>

      {/* Grid overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:100px_100px]" />

      {/* Content */}
      <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          {/* Logo/Header with animation */}
          <div className="text-center mb-8 animate-fade-in-down">
            <div className="relative inline-block">
              <div className="absolute inset-0 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl blur-xl opacity-50 animate-pulse" />
              <div className="relative inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 rounded-2xl shadow-2xl">
                <ShieldCheckIcon className="h-12 w-12 text-white" />
              </div>
            </div>
            <h1 className="text-3xl font-bold text-white mt-6 tracking-tight">
              Governex<span className="text-indigo-400">+</span>
            </h1>
            <p className="text-indigo-200/70 mt-2 text-sm font-medium tracking-wide uppercase">
              Platform Administration
            </p>
          </div>

          {/* Login Card with glassmorphism */}
          <div className="relative animate-fade-in-up">
            <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-3xl blur-xl" />
            <div className="relative bg-white/10 backdrop-blur-2xl rounded-3xl p-8 shadow-2xl border border-white/10">

              {loginSuccess ? (
                <div className="text-center py-8 animate-fade-in">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-green-500/20 rounded-full mb-4">
                    <CheckCircleIcon className="h-10 w-10 text-green-400 animate-bounce" />
                  </div>
                  <h3 className="text-xl font-semibold text-white">Welcome Back!</h3>
                  <p className="text-indigo-200/70 mt-2">Redirecting to dashboard...</p>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-indigo-500/20 rounded-lg">
                      <LockClosedIcon className="h-5 w-5 text-indigo-400" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold text-white">Super Admin Access</h2>
                      <p className="text-xs text-indigo-200/50">Secure platform management portal</p>
                    </div>
                  </div>

                  {error && (
                    <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3 animate-shake">
                      <div className="p-1 bg-red-500/20 rounded-lg">
                        <ExclamationCircleIcon className="h-5 w-5 text-red-400" />
                      </div>
                      <span className="text-sm text-red-200">{error}</span>
                    </div>
                  )}

                  <form onSubmit={handleLogin} className="space-y-5">
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-indigo-200/70">
                        Email Address
                      </label>
                      <div className="relative group">
                        <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/50 to-purple-500/50 rounded-xl opacity-0 group-focus-within:opacity-100 blur transition-opacity" />
                        <div className="relative">
                          <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-indigo-300/50 group-focus-within:text-indigo-400 transition-colors" />
                          <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="admin@governex.local"
                            className="w-full pl-12 pr-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-indigo-300/30 focus:outline-none focus:border-indigo-500/50 focus:bg-white/10 transition-all"
                            required
                          />
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-indigo-200/70">
                        Password
                      </label>
                      <div className="relative group">
                        <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/50 to-purple-500/50 rounded-xl opacity-0 group-focus-within:opacity-100 blur transition-opacity" />
                        <div className="relative">
                          <KeyIcon className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-indigo-300/50 group-focus-within:text-indigo-400 transition-colors" />
                          <input
                            type={showPassword ? 'text' : 'password'}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter your password"
                            className="w-full pl-12 pr-12 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-indigo-300/30 focus:outline-none focus:border-indigo-500/50 focus:bg-white/10 transition-all"
                            required
                          />
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute right-4 top-1/2 -translate-y-1/2 text-indigo-300/50 hover:text-indigo-400 transition-colors"
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
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={rememberMe}
                          onChange={(e) => setRememberMe(e.target.checked)}
                          className="w-4 h-4 rounded border-white/20 bg-white/5 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-0"
                        />
                        <span className="text-sm text-indigo-200/70">Remember me</span>
                      </label>
                      <button type="button" className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors">
                        Forgot password?
                      </button>
                    </div>

                    <button
                      type="submit"
                      disabled={isLoading}
                      className="relative w-full group"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl blur opacity-70 group-hover:opacity-100 transition-opacity" />
                      <div className="relative flex items-center justify-center gap-2 py-3.5 bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-xl font-semibold hover:from-indigo-600 hover:to-purple-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed">
                        {isLoading ? (
                          <>
                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            <span>Authenticating...</span>
                          </>
                        ) : (
                          <>
                            <LockClosedIcon className="h-5 w-5" />
                            <span>Sign In to Dashboard</span>
                          </>
                        )}
                      </div>
                    </button>
                  </form>

                  {/* Demo Credentials */}
                  <div className="mt-6 p-4 bg-gradient-to-r from-indigo-500/10 to-purple-500/10 rounded-xl border border-indigo-500/20">
                    <div className="flex items-center gap-2 mb-3">
                      <SparklesIcon className="h-4 w-4 text-indigo-400" />
                      <span className="text-xs font-semibold text-indigo-300 uppercase tracking-wide">Demo Credentials</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-indigo-300/50 text-xs">Email</p>
                        <p className="text-indigo-200 font-mono">admin@governex.local</p>
                      </div>
                      <div>
                        <p className="text-indigo-300/50 text-xs">Password</p>
                        <p className="text-indigo-200 font-mono">admin123</p>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-indigo-300/30 text-xs mt-8 animate-fade-in">
            Governex+ GRC Zero Trust Platform v2.0
            <br />
            <span className="text-indigo-400/50">Intelligent Governance. Secure. Compliant.</span>
          </p>
        </div>
      </div>

      {/* CSS for animations */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) translateX(0px); }
          25% { transform: translateY(-20px) translateX(10px); }
          50% { transform: translateY(-10px) translateX(-10px); }
          75% { transform: translateY(-30px) translateX(5px); }
        }
        @keyframes fade-in-down {
          from { opacity: 0; transform: translateY(-20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fade-in-up {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-5px); }
          75% { transform: translateX(5px); }
        }
        .animate-fade-in-down { animation: fade-in-down 0.6s ease-out; }
        .animate-fade-in-up { animation: fade-in-up 0.6s ease-out 0.2s both; }
        .animate-fade-in { animation: fade-in 0.4s ease-out; }
        .animate-shake { animation: shake 0.3s ease-out; }
      `}</style>
    </div>
  );
}

export default AdminLogin;
