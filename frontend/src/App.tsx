import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useLocation, Navigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Scan,
  Camera,
  History,
  BookOpen,
  Settings as SettingsIcon,
  Shield,
  Menu,
  X,
  LogOut,
  User as UserIcon,
} from 'lucide-react';
import { Dashboard } from './views/Dashboard';
import { ScanProduct } from './views/ScanProduct';
import { LiveCameraScan } from './views/LiveCameraScan';
import { InspectionHistory } from './views/InspectionHistory';
import { InspectionDetail } from './views/InspectionDetail';
import { RuleLibrary } from './views/RuleLibrary';
import { Settings } from './views/Settings';
import { Login } from './Login';
import { AuthProvider, useAuth } from './AuthContext';
import { checkHealth } from './api';

// ─── Protected Route wrapper ──────────────────────────────────────────────────
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{
        display: 'flex', justifyContent: 'center', alignItems: 'center',
        height: '100vh', background: '#0a0e17', flexDirection: 'column', gap: '16px',
      }}>
        <Shield size={48} color="#6366f1" />
        <p style={{ color: '#94a3b8', marginTop: '12px' }}>Loading MetaLex...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

// ─── Sidebar + layout ────────────────────────────────────────────────────────
const SidebarLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState(true);
  const location = useLocation();
  const { user, logout } = useAuth();

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location]);

  useEffect(() => {
    const ping = () => {
      checkHealth().then((res) => setIsBackendOnline(res.status !== 'offline'));
    };
    ping();
    const interval = setInterval(ping, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-layout">
      {/* Mobile Toggle */}
      <button
        className="mobile-menu-btn"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        aria-label="Toggle navigation"
      >
        {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Sidebar */}
      <aside className={`sidebar ${mobileMenuOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">
              <Shield size={22} color="#fff" />
            </div>
            <div>
              <h1>MetaLex</h1>
              <span>Legal Metrology AI</span>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section-title">Enforcement Suite</div>

          <NavLink
            to="/"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <LayoutDashboard />
            Dashboard
          </NavLink>

          <NavLink
            to="/scan"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Scan />
            Scan Product
          </NavLink>

          <NavLink
            to="/camera"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Camera />
            Live Camera Scan
          </NavLink>

          <NavLink
            to="/history"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <History />
            Inspection History
          </NavLink>

          <div className="nav-section-title">Compliance & System</div>

          <NavLink
            to="/rules"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <BookOpen />
            Rule Library
          </NavLink>

          <NavLink
            to="/settings"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <SettingsIcon />
            Diagnostics & Settings
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          {/* Logged-in user info + logout */}
          {user && (
            <div style={{
              padding: '10px 16px 12px',
              borderTop: '1px solid rgba(255,255,255,0.06)',
              marginBottom: '8px',
            }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                marginBottom: '10px',
              }}>
                <div style={{
                  width: '32px', height: '32px', borderRadius: '8px',
                  background: 'linear-gradient(135deg,#6366f1,#06b6d4)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <UserIcon size={15} color="#fff" />
                </div>
                <div style={{ overflow: 'hidden' }}>
                  <p style={{
                    fontSize: '12px', fontWeight: 600, color: '#f0f4ff',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {user.full_name || user.username}
                  </p>
                  <p style={{ fontSize: '11px', color: '#64748b', textTransform: 'capitalize' }}>
                    {user.role}
                  </p>
                </div>
              </div>
              <button
                onClick={logout}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: '8px',
                  padding: '8px 10px', borderRadius: '7px',
                  background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)',
                  color: '#ef4444', fontSize: '12px', fontWeight: 500,
                  cursor: 'pointer', fontFamily: 'inherit', transition: 'background 150ms',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(239,68,68,0.18)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(239,68,68,0.1)')}
              >
                <LogOut size={13} />
                Sign Out
              </button>
            </div>
          )}

          <div className="sidebar-status">
            <span className={`status-dot ${isBackendOnline ? '' : 'offline'}`}></span>
            <span>
              {isBackendOnline ? 'System Online (Local Engine)' : 'Backend Disconnected'}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <div className="page-content">{children}</div>
      </main>
    </div>
  );
};

// ─── Root app ────────────────────────────────────────────────────────────────
export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public login route */}
          <Route path="/login" element={<Login />} />
          
          {/* Protected routes - require authentication */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <SidebarLayout>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/scan" element={<ScanProduct />} />
                    <Route path="/camera" element={<LiveCameraScan />} />
                    <Route path="/history" element={<InspectionHistory />} />
                    <Route path="/inspections/:id" element={<InspectionDetail />} />
                    <Route path="/rules" element={<RuleLibrary />} />
                    <Route path="/settings" element={<Settings />} />
                    {/* Catch-all → dashboard */}
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </SidebarLayout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
