import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Eye, EyeOff, LogIn, UserPlus, AlertCircle, Loader } from 'lucide-react';
import { loginUser, registerUser } from './api';
import { useAuth } from './AuthContext';
import type { AuthUser } from './types';

type Mode = 'login' | 'register';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('login');
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Form state
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');

  const switchMode = (m: Mode) => {
    setMode(m);
    setError('');
    setUsername('');
    setEmail('');
    setFullName('');
    setPassword('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let res;
      if (mode === 'login') {
        res = await loginUser({ username, password });
      } else {
        res = await registerUser({ username, email, password, full_name: fullName });
      }
      login(res.access_token, res.user as AuthUser);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Something went wrong. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      minHeight: '100vh',
      width: '100vw',
      background: 'linear-gradient(135deg, #0a0e17 0%, #1a1f2e 50%, #0f1419 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      overflow: 'auto',
      zIndex: 9999,
    }}>
      {/* Background gradients */}
      <div style={{
        position: 'fixed',
        width: '500px',
        height: '500px',
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)',
        top: '-100px',
        left: '-100px',
        animation: 'float 8s ease-in-out infinite',
        pointerEvents: 'none',
        zIndex: 0,
      }} />
      <div style={{
        position: 'fixed',
        width: '400px',
        height: '400px',
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(6,182,212,0.12) 0%, transparent 70%)',
        bottom: '-80px',
        right: '-80px',
        animation: 'float 6s ease-in-out infinite reverse',
        pointerEvents: 'none',
        zIndex: 0,
      }} />

      {/* Login Card */}
      <div style={{
        background: 'rgba(26, 31, 46, 0.95)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '24px',
        padding: '48px 40px',
        width: '100%',
        maxWidth: '460px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.5), 0 0 1px rgba(255,255,255,0.1)',
        position: 'relative',
        zIndex: 100,
        margin: 'auto',
      }}>
        {/* Logo */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          marginBottom: '32px',
          justifyContent: 'center',
        }}>
          <div style={{
            width: '56px',
            height: '56px',
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 8px 24px rgba(99,102,241,0.3)',
          }}>
            <Shield size={32} color="#fff" strokeWidth={2.5} />
          </div>
          <div style={{ textAlign: 'left' }}>
            <h1 style={{
              fontSize: '32px',
              fontWeight: 800,
              background: 'linear-gradient(135deg, #fff 0%, #94a3b8 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              margin: 0,
              letterSpacing: '-0.5px',
            }}>
              MetaLex
            </h1>
            <p style={{
              fontSize: '13px',
              color: '#64748b',
              margin: 0,
              fontWeight: 500,
            }}>
              Legal Metrology AI
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex',
          gap: '8px',
          padding: '6px',
          background: 'rgba(15, 20, 31, 0.6)',
          borderRadius: '12px',
          marginBottom: '24px',
        }}>
          {['login', 'register'].map((m) => (
            <button
              key={m}
              style={{
                flex: 1,
                padding: '12px 20px',
                border: 'none',
                borderRadius: '9px',
                background: mode === m ? 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)' : 'transparent',
                color: mode === m ? '#fff' : '#64748b',
                fontSize: '14px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                transition: 'all 0.2s',
                fontFamily: 'inherit',
                boxShadow: mode === m ? '0 4px 12px rgba(99,102,241,0.3)' : 'none',
              }}
              onClick={() => switchMode(m as Mode)}
              type="button"
            >
              {m === 'login' ? <LogIn size={16} /> : <UserPlus size={16} />}
              {m === 'login' ? 'Sign In' : 'Register'}
            </button>
          ))}
        </div>

        <p style={{
          fontSize: '14px',
          color: '#94a3b8',
          textAlign: 'center',
          marginBottom: '24px',
          fontWeight: 500,
        }}>
          {mode === 'login' ? 'Welcome back to Enforcement Dashboard' : 'Create your officer account'}
        </p>

        {/* Error */}
        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '12px',
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            marginBottom: '20px',
          }}>
            <AlertCircle size={18} color="#ef4444" style={{ flexShrink: 0 }} />
            <span style={{ fontSize: '13px', color: '#fca5a5', flex: 1 }}>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Full Name - Register only (First) */}
          {mode === 'register' && (
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#cbd5e1', marginBottom: '8px' }}>
                Full Name
              </label>
              <input
                style={{
                  width: '100%', padding: '14px 16px', background: 'rgba(15, 20, 31, 0.5)',
                  border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', color: '#f0f4ff',
                  fontSize: '14px', fontFamily: 'inherit', outline: 'none', transition: 'all 0.2s', boxSizing: 'border-box',
                }}
                onFocus={(e) => e.target.style.borderColor = '#6366f1'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.08)'}
                type="text"
                placeholder="Officer Rajesh Kumar"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
              />
            </div>
          )}

          {/* Email - Register only OR show for both (Second) */}
          {mode === 'register' && (
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#cbd5e1', marginBottom: '8px' }}>
                Email Address
              </label>
              <input
                style={{
                  width: '100%', padding: '14px 16px', background: 'rgba(15, 20, 31, 0.5)',
                  border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', color: '#f0f4ff',
                  fontSize: '14px', fontFamily: 'inherit', outline: 'none', transition: 'all 0.2s', boxSizing: 'border-box',
                }}
                onFocus={(e) => e.target.style.borderColor = '#6366f1'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.08)'}
                type="email"
                placeholder="officer@legalmetrology.gov.in"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
          )}

          {/* Username (Third) */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#cbd5e1', marginBottom: '8px' }}>
              Username
            </label>
            <input
              style={{
                width: '100%', padding: '14px 16px', background: 'rgba(15, 20, 31, 0.5)',
                border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', color: '#f0f4ff',
                fontSize: '14px', fontFamily: 'inherit', outline: 'none', transition: 'all 0.2s', boxSizing: 'border-box',
              }}
              onFocus={(e) => e.target.style.borderColor = '#6366f1'}
              onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.08)'}
              type="text"
              placeholder={mode === 'login' ? 'demo_officer' : 'officer_username'}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              autoComplete="username"
            />
          </div>

          {/* Password (Fourth) */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#cbd5e1', marginBottom: '8px' }}>
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                style={{
                  width: '100%', padding: '14px 16px', paddingRight: '48px', background: 'rgba(15, 20, 31, 0.5)',
                  border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', color: '#f0f4ff',
                  fontSize: '14px', fontFamily: 'inherit', outline: 'none', transition: 'all 0.2s', boxSizing: 'border-box',
                }}
                onFocus={(e) => e.target.style.borderColor = '#6366f1'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.08)'}
                type={showPass ? 'text' : 'password'}
                placeholder={mode === 'login' ? 'demo123' : 'Min. 6 characters'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
              <button
                type="button"
                style={{
                  position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                  background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer',
                  padding: '8px', display: 'flex', alignItems: 'center', transition: 'color 0.2s',
                }}
                onClick={() => setShowPass(!showPass)}
                tabIndex={-1}
                onMouseEnter={(e) => e.currentTarget.style.color = '#94a3b8'}
                onMouseLeave={(e) => e.currentTarget.style.color = '#64748b'}
              >
                {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '16px', marginTop: '8px',
              background: loading ? 'rgba(99, 102, 241, 0.5)' : 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
              border: 'none', borderRadius: '12px', color: '#fff', fontSize: '15px', fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center',
              justifyContent: 'center', gap: '10px', transition: 'all 0.2s', fontFamily: 'inherit',
              boxShadow: loading ? 'none' : '0 8px 24px rgba(99, 102, 241, 0.4)',
            }}
            onMouseEnter={(e) => { if (!loading) e.currentTarget.style.transform = 'translateY(-2px)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; }}
          >
            {loading ? (
              <>
                <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} />
                {mode === 'login' ? 'Signing in...' : 'Creating account...'}
              </>
            ) : (
              <>
                {mode === 'login' ? <LogIn size={18} /> : <UserPlus size={18} />}
                {mode === 'login' ? 'Sign In' : 'Create Account'}
              </>
            )}
          </button>
        </form>

        {/* Demo Hint */}
        {mode === 'login' && (
          <div style={{
            marginTop: '24px', padding: '12px 16px',
            background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.2)',
            borderRadius: '10px', textAlign: 'center',
          }}>
            <p style={{ fontSize: '12px', color: '#94a3b8', margin: '0 0 4px 0' }}>
              🎯 <strong style={{ color: '#a5b4fc' }}>Demo Account</strong>
            </p>
            <p style={{ fontSize: '12px', color: '#64748b', margin: 0 }}>
              demo_officer / demo123
            </p>
          </div>
        )}

        {/* Footer */}
        <p style={{ fontSize: '13px', color: '#64748b', textAlign: 'center', marginTop: '24px', marginBottom: '20px' }}>
          {mode === 'login' ? "Don't have an account? " : 'Already registered? '}
          <button
            style={{
              background: 'none', border: 'none', color: '#6366f1', fontSize: '13px',
              fontWeight: 600, cursor: 'pointer', padding: 0, fontFamily: 'inherit', textDecoration: 'underline',
            }}
            onClick={() => switchMode(mode === 'login' ? 'register' : 'login')}
            type="button"
          >
            {mode === 'login' ? 'Create account' : 'Sign in'}
          </button>
        </p>

        {/* Badge */}
        <div style={{
          textAlign: 'center', padding: '8px', background: 'rgba(15, 20, 31, 0.4)',
          borderRadius: '8px', fontSize: '11px', color: '#64748b', fontWeight: 500,
        }}>
          🏛️ Smart India Hackathon 2026 · Prototype
        </div>
      </div>

      {/* Animations */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translate(0, 0); }
          50% { transform: translate(30px, 30px); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
