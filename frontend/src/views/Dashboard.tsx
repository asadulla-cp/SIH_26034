import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  AlertTriangle,
  XCircle,
  FileCheck,
  ArrowRight,
  TrendingUp,
  Scan,
  Database,
  Clock
} from 'lucide-react';
import { getDashboardStats } from '../api';
import type { DashboardStats } from '../types';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await getDashboardStats();
      setStats(data);
      setError(null);
    } catch (err: any) {
      console.error(err);
      setError('Could not load statistics. Ensure backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const compliantRate = stats && stats.total_inspections > 0
    ? Math.round((stats.compliant / stats.total_inspections) * 100)
    : 0;

  return (
    <div className="animate-in">
      {/* Top Banner / Enforcement Notice */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(6, 182, 212, 0.08))',
        border: '1px solid var(--border-accent)',
        borderRadius: 'var(--radius-lg)',
        padding: '20px 24px',
        marginBottom: '24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{
              background: 'var(--accent-primary)',
              color: '#fff',
              fontSize: '11px',
              fontWeight: 800,
              padding: '2px 8px',
              borderRadius: '4px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              SIH 2026 Enforcement Portal
            </span>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Legal Metrology (Packaged Commodities) Rules, 2011
            </span>
          </div>
          <h3 style={{ fontSize: '18px', fontWeight: 700 }}>
            Automated Package Compliance & Evidence Verification System
          </h3>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => navigate('/scan')}
        >
          <Scan size={18} />
          New Inspection
        </button>
      </div>

      {error && (
        <div style={{
          background: 'var(--status-fail-bg)',
          border: '1px solid var(--status-fail-border)',
          color: 'var(--status-fail)',
          padding: '12px 16px',
          borderRadius: 'var(--radius-md)',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '14px'
        }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
          <button
            onClick={fetchStats}
            style={{
              marginLeft: 'auto',
              background: 'transparent',
              border: 'none',
              color: 'inherit',
              textDecoration: 'underline',
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* 4 Core Stat Cards */}
      <div className="stats-grid">
        <div className="stat-card total">
          <div className="stat-icon total">
            <FileCheck size={24} />
          </div>
          <div className="stat-info">
            <h3>{loading ? '—' : stats?.total_inspections ?? 0}</h3>
            <p>Total Inspections</p>
          </div>
        </div>

        <div className="stat-card compliant">
          <div className="stat-icon compliant">
            <ShieldCheck size={24} />
          </div>
          <div className="stat-info">
            <h3>{loading ? '—' : stats?.compliant ?? 0}</h3>
            <p>Fully Compliant ({compliantRate}%)</p>
          </div>
        </div>

        <div className="stat-card non-compliant">
          <div className="stat-icon non-compliant">
            <XCircle size={24} />
          </div>
          <div className="stat-info">
            <h3>{loading ? '—' : stats?.non_compliant ?? 0}</h3>
            <p>Non-Compliant Violations</p>
          </div>
        </div>

        <div className="stat-card review">
          <div className="stat-icon review">
            <AlertTriangle size={24} />
          </div>
          <div className="stat-info">
            <h3>{loading ? '—' : stats?.needs_review ?? 0}</h3>
            <p>Pending Officer Review</p>
          </div>
        </div>
      </div>

      {/* Middle Grid: Recent Inspections & Common Violations */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', marginBottom: '24px' }}>
        {/* Recent Inspections Table */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Clock size={18} color="var(--accent-primary)" />
              Recent Inspections
            </h3>
            <button
              onClick={() => navigate('/history')}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-primary-hover)',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              View All <ArrowRight size={14} />
            </button>
          </div>

          {loading ? (
            <div className="loading-overlay" style={{ padding: '30px' }}>
              <div className="spinner"></div>
              <p>Loading recent records...</p>
            </div>
          ) : !stats?.recent_inspections?.length ? (
            <div className="empty-state" style={{ padding: '40px 20px' }}>
              <Database size={40} />
              <h3>No Inspections Yet</h3>
              <p style={{ fontSize: '13px', marginBottom: '16px' }}>
                Scan a package label or run a preset demo dataset to start recording compliance data.
              </p>
              <button className="btn btn-primary btn-sm" onClick={() => navigate('/scan')}>
                Start First Scan
              </button>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Product</th>
                  <th>Status</th>
                  <th>Score</th>
                  <th>Violations</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_inspections.map((item) => (
                  <tr key={item.id}>
                    <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                      {item.inspection_id}
                      {item.is_demo && (
                        <span style={{
                          marginLeft: '6px',
                          fontSize: '9px',
                          padding: '1px 4px',
                          background: 'rgba(245, 158, 11, 0.15)',
                          color: 'var(--status-review)',
                          borderRadius: '3px',
                          fontWeight: 700
                        }}>DEMO</span>
                      )}
                    </td>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {item.product_name}
                    </td>
                    <td>
                      <span className={`status-badge ${item.overall_status.toLowerCase().replace('_', '-')}`}>
                        {item.overall_status.replace('_', ' ')}
                      </span>
                    </td>
                    <td>
                      <strong style={{
                        color: item.compliance_score >= 80 ? 'var(--status-pass)' : (item.compliance_score >= 50 ? 'var(--status-review)' : 'var(--status-fail)')
                      }}>
                        {item.compliance_score}%
                      </strong>
                    </td>
                    <td>
                      {item.violation_count > 0 ? (
                        <span style={{ color: 'var(--status-fail)', fontWeight: 600 }}>
                          {item.violation_count} Issue{item.violation_count > 1 ? 's' : ''}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--status-pass)' }}>None</span>
                      )}
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => navigate(`/inspections/${item.id}`)}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Common Violations / Analytics */}
        <div className="card">
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={18} color="var(--accent-secondary)" />
            Top Violation Trends
          </h3>

          {!stats?.common_violations?.length ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '20px 0' }}>
              No violations recorded yet. As non-compliant packages are scanned, trends will appear here.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {stats.common_violations.map((v, idx) => (
                <div key={idx} style={{
                  background: 'var(--bg-elevated)',
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {v.field}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Legal Rule Non-Compliance
                    </div>
                  </div>
                  <span style={{
                    background: 'var(--status-fail-bg)',
                    color: 'var(--status-fail)',
                    border: '1px solid var(--status-fail-border)',
                    borderRadius: '12px',
                    padding: '2px 8px',
                    fontSize: '12px',
                    fontWeight: 700
                  }}>
                    {v.count} hit{v.count > 1 ? 's' : ''}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Quick Demo Launchers */}
          <div style={{
            marginTop: '24px',
            paddingTop: '16px',
            borderTop: '1px solid var(--border-primary)'
          }}>
            <h4 style={{ fontSize: '13px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
              Instant Demo Presets
            </h4>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              Click to run immediate sample inspections for judge evaluation:
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <button
                className="btn btn-secondary btn-sm"
                style={{ justifyContent: 'flex-start', fontSize: '12px' }}
                onClick={() => navigate('/scan?demo=demo-001')}
              >
                <ShieldCheck size={14} color="var(--status-pass)" /> 1. Fully Compliant Package
              </button>
              <button
                className="btn btn-secondary btn-sm"
                style={{ justifyContent: 'flex-start', fontSize: '12px' }}
                onClick={() => navigate('/scan?demo=demo-002')}
              >
                <XCircle size={14} color="var(--status-fail)" /> 2. Missing MRP Declaration
              </button>
              <button
                className="btn btn-secondary btn-sm"
                style={{ justifyContent: 'flex-start', fontSize: '12px' }}
                onClick={() => navigate('/scan?demo=demo-004')}
              >
                <AlertTriangle size={14} color="var(--status-review)" /> 3. Ambiguous / Low OCR Confidence
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
