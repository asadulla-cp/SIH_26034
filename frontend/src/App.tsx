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
  Package,
  Globe,
  MapPin
} from 'lucide-react';
import { Dashboard } from './views/Dashboard';
import { ScanProduct } from './views/ScanProduct';
import { BatchScan } from './views/BatchScan';
import { LiveCameraScan } from './views/LiveCameraScan';
import { EcommerceScan } from './views/EcommerceScan';
import { ComplianceMap } from './views/ComplianceMap';
import { InspectionHistory } from './views/InspectionHistory';
import { InspectionDetail } from './views/InspectionDetail';
import { RuleLibrary } from './views/RuleLibrary';
import { Settings } from './views/Settings';
import { Login } from './Login';
import { AuthProvider, useAuth } from './AuthContext';
import { PwaInstall } from './pwa-install';
import { checkHealth } from './api';
import { getOfflineCount, getQueuedInspections, removeQueuedInspection } from './offline-queue';

// ─── Direct Route wrapper (Auth Bypassed for Testing/Demo) ─────────────────
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <>{children}</>;
};

// ─── Sidebar + layout ────────────────────────────────────────────────────────
const SidebarLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState(true);
  const [isNetworkOnline, setIsNetworkOnline] = useState(navigator.onLine);
  const [offlineQueuedCount, setOfflineQueuedCount] = useState(0);
  const location = useLocation();
  const { user, logout } = useAuth();

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location]);

  useEffect(() => {
    const handleOnline = () => {
      setIsNetworkOnline(true);
      syncQueuedOffline();
    };
    const handleOffline = () => setIsNetworkOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    const ping = () => {
      checkHealth().then((res) => setIsBackendOnline(res.status !== 'offline'));
      getOfflineCount().then(setOfflineQueuedCount);
    };
    ping();
    const interval = setInterval(ping, 10000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearInterval(interval);
    };
  }, []);

  const syncQueuedOffline = async () => {
    try {
      const items = await getQueuedInspections();
      for (const item of items) {
        if (item.status === 'PENDING') {
          // Remove from local IndexedDB once online sync triggers
          await removeQueuedInspection(item.id);
        }
      }
      const remaining = await getOfflineCount();
      setOfflineQueuedCount(remaining);
    } catch (e) {
      console.debug('Offline sync notice:', e);
    }
  };

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
            to="/batch-scan"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Package />
            Batch Scan (ZIP)
          </NavLink>

          <NavLink
            to="/ecommerce-scan"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Globe />
            E-Commerce Scanner
          </NavLink>

          <NavLink
            to="/map"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <MapPin />
            Compliance Map
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
          {/* Officer profile info */}
          {(() => {
            const displayUser = user || {
              username: 'demo_officer',
              full_name: 'Inspector Sharma',
              role: 'Enforcement Officer'
            };
            return (
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
                      {displayUser.full_name || displayUser.username}
                    </p>
                    <p style={{ fontSize: '11px', color: '#64748b', textTransform: 'capitalize' }}>
                      {displayUser.role}
                    </p>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Network & Offline Status */}
          <div className="sidebar-status" style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-start' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className={`status-dot ${isBackendOnline && isNetworkOnline ? '' : 'offline'}`}></span>
              <span>
                {isNetworkOnline
                  ? (isBackendOnline ? 'System Online (Ready)' : 'Backend Offline (Demo Fallback)')
                  : 'Offline Mode (PWA)'}
              </span>
            </div>
            {offlineQueuedCount > 0 && (
              <span style={{ fontSize: '10px', color: '#f59e0b', fontWeight: 600 }}>
                &bull; {offlineQueuedCount} queued inspections pending sync
              </span>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <div className="page-content">
          {children}
        </div>
      </main>

      {/* PWA Mobile Installation Banner */}
      <PwaInstall />
    </div>
  );
};

// ─── Root app ────────────────────────────────────────────────────────────────
export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Direct routing without authentication */}
          <Route path="/login" element={<Navigate to="/" replace />} />
          
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <SidebarLayout>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/scan" element={<ScanProduct />} />
                    <Route path="/batch-scan" element={<BatchScan />} />
                    <Route path="/ecommerce-scan" element={<EcommerceScan />} />
                    <Route path="/map" element={<ComplianceMap />} />
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
