import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Scan,
  History,
  BookOpen,
  Settings as SettingsIcon,
  Shield,
  Menu,
  X
} from 'lucide-react';
import { Dashboard } from './views/Dashboard';
import { ScanProduct } from './views/ScanProduct';
import { InspectionHistory } from './views/InspectionHistory';
import { InspectionDetail } from './views/InspectionDetail';
import { RuleLibrary } from './views/RuleLibrary';
import { Settings } from './views/Settings';
import { checkHealth } from './api';

const SidebarLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState(true);
  const location = useLocation();

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
          <div className="sidebar-status">
            <span className={`status-dot ${isBackendOnline ? '' : 'offline'}`}></span>
            <span>
              {isBackendOnline ? 'System Online (Local Engine)' : 'Backend Disconnected'}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        <div className="page-content">{children}</div>
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <SidebarLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scan" element={<ScanProduct />} />
          <Route path="/history" element={<InspectionHistory />} />
          <Route path="/inspections/:id" element={<InspectionDetail />} />
          <Route path="/rules" element={<RuleLibrary />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </SidebarLayout>
    </BrowserRouter>
  );
};

export default App;
