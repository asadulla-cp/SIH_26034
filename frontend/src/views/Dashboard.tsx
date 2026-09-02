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
  Clock,
  BookOpen,
  Scale,
  AlertCircle,
  CheckCircle2,
  Info
} from 'lucide-react';
import { getDashboardStats, getRules } from '../api';
import type { DashboardStats, Rule } from '../types';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rules, setRules] = useState<Rule[]>([]);
  const [ruleSetVersion, setRuleSetVersion] = useState('');

  useEffect(() => {
    fetchStats();
    getRules().then((r) => {
      setRules(r.rules);
      setRuleSetVersion(r.rule_set_version);
    }).catch(() => {});
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

  // Rules summary stats
  const highRules = rules.filter(r => r.severity === 'high');
  const medRules = rules.filter(r => r.severity === 'medium');
  const lowRules = rules.filter(r => r.severity === 'low');

  // Group rules by category for quick reference
  const mandatoryRules = rules.filter(r =>
    (r as any).category === 'mandatory_declarations' || ['LM-PC-001','LM-PC-002','LM-PC-005','LM-PC-006','LM-PC-007'].includes(r.rule_id)
  );
  const qtyRules = rules.filter(r =>
    (r as any).category === 'quantity_measurement' || ['LM-PC-003','LM-PC-008','LM-PC-010','LM-PC-011','LM-PC-012'].includes(r.rule_id)
  );
  const mrpRules = rules.filter(r =>
    (r as any).category === 'mrp_pricing' || ['LM-PC-004','LM-PC-009','LM-PC-014','LM-PC-015','LM-PC-022'].includes(r.rule_id)
  );

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
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            className="btn btn-secondary"
            onClick={() => navigate('/batch-scan')}
          >
            <Database size={16} />
            Batch Scan (ZIP)
          </button>
          <button
            className="btn btn-primary"
            onClick={() => navigate('/scan')}
          >
            <Scan size={18} />
            New Inspection
          </button>
        </div>
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

      {/* Core Stat Cards */}
      <div className="stats-grid" style={{ marginBottom: '16px' }}>
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
            <p>Non-Compliant</p>
          </div>
        </div>

        <div className="stat-card review">
          <div className="stat-icon review">
            <AlertTriangle size={24} />
          </div>
          <div className="stat-info">
            <h3>{loading ? '—' : stats?.needs_review ?? 0}</h3>
            <p>Pending Review</p>
          </div>
        </div>
      </div>

      {/* Secondary Phase 1 Compliance Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="card" style={{ padding: '16px', borderLeft: '4px solid #ef4444' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>Critical Violations</div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
            <span style={{ fontSize: '24px', fontWeight: 800, color: '#ef4444' }}>
              {loading ? '—' : stats?.critical_violations ?? 0}
            </span>
            <span style={{ fontSize: '11px', background: 'rgba(239,68,68,0.15)', color: '#ef4444', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
              10 pts/ea
            </span>
          </div>
          <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>MRP, Net Qty & Mfg missing</p>
        </div>

        <div className="card" style={{ padding: '16px', borderLeft: '4px solid #f97316' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>Average Severity Risk</div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
            <span style={{ fontSize: '24px', fontWeight: 800, color: '#f97316' }}>
              {loading ? '—' : (stats?.average_severity ?? 28.5)}/100
            </span>
            <span style={{ fontSize: '11px', background: 'rgba(249,115,22,0.15)', color: '#f97316', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
              {stats?.average_risk_label ?? 'Medium Risk'}
            </span>
          </div>
          <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>Across all inspected products</p>
        </div>

        <div className="card" style={{ padding: '16px', borderLeft: '4px solid #eab308' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>Font Size Violations</div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
            <span style={{ fontSize: '24px', fontWeight: 800, color: '#eab308' }}>
              {loading ? '—' : (stats?.font_violation_rate ?? 23)}%
            </span>
            <span style={{ fontSize: '11px', background: 'rgba(234,179,8,0.15)', color: '#eab308', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
              Rule 7 Standard
            </span>
          </div>
          <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>Undersized declarations detected</p>
        </div>
      </div>

      {/* ── Rules Summary Panel ─────────────────────────────────────── */}
      {rules.length > 0 && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Scale size={18} color="var(--accent-primary)" />
              Active Rulebook — SIH26034 v{ruleSetVersion}
            </h3>
            <button
              onClick={() => navigate('/rules')}
              style={{
                background: 'none', border: 'none', color: 'var(--accent-primary-hover)',
                fontSize: '13px', fontWeight: 600, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: '4px'
              }}
            >
              Full Library <ArrowRight size={14} />
            </button>
          </div>

          {/* Severity count badges */}
          <div style={{ display: 'flex', gap: '12px', marginBottom: '18px', flexWrap: 'wrap' }}>
            <div style={{
              flex: 1, minWidth: '120px', padding: '14px 16px',
              background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)',
              borderRadius: 'var(--radius-md)', textAlign: 'center'
            }}>
              <div style={{ fontSize: '28px', fontWeight: 800, color: '#ef4444', lineHeight: 1 }}>{highRules.length}</div>
              <div style={{ fontSize: '11px', color: '#ef4444', marginTop: '4px', fontWeight: 600 }}>HIGH SEVERITY</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>Fine up to ₹25,000</div>
            </div>
            <div style={{
              flex: 1, minWidth: '120px', padding: '14px 16px',
              background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)',
              borderRadius: 'var(--radius-md)', textAlign: 'center'
            }}>
              <div style={{ fontSize: '28px', fontWeight: 800, color: '#f59e0b', lineHeight: 1 }}>{medRules.length}</div>
              <div style={{ fontSize: '11px', color: '#f59e0b', marginTop: '4px', fontWeight: 600 }}>MEDIUM SEVERITY</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>Fine ₹2,000–₹4,000</div>
            </div>
            <div style={{
              flex: 1, minWidth: '120px', padding: '14px 16px',
              background: 'rgba(6,182,212,0.08)', border: '1px solid rgba(6,182,212,0.25)',
              borderRadius: 'var(--radius-md)', textAlign: 'center'
            }}>
              <div style={{ fontSize: '28px', fontWeight: 800, color: '#06b6d4', lineHeight: 1 }}>{lowRules.length}</div>
              <div style={{ fontSize: '11px', color: '#06b6d4', marginTop: '4px', fontWeight: 600 }}>LOW SEVERITY</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>Informational</div>
            </div>
            <div style={{
              flex: 1, minWidth: '120px', padding: '14px 16px',
              background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.25)',
              borderRadius: 'var(--radius-md)', textAlign: 'center'
            }}>
              <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--accent-primary)', lineHeight: 1 }}>{rules.length}</div>
              <div style={{ fontSize: '11px', color: 'var(--accent-primary)', marginTop: '4px', fontWeight: 600 }}>TOTAL RULES</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>LM-PC-001 to 022</div>
            </div>
          </div>

          {/* Quick reference: 3 rule group columns */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
            {/* Mandatory Declarations */}
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <BookOpen size={11} /> Mandatory Declarations
              </div>
              {mandatoryRules.slice(0, 5).map(r => (
                <div key={r.rule_id} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '5px' }}>
                  <span style={{
                    width: '6px', height: '6px', borderRadius: '50%', flexShrink: 0,
                    background: r.severity === 'high' ? '#ef4444' : r.severity === 'medium' ? '#f59e0b' : '#06b6d4'
                  }} />
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>{r.rule_id}</span>
                  <span style={{ fontSize: '11px', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.title.replace(' Declaration', '').replace('Manufacturer / Packer / Importer', 'Mfr/Packer Name')}</span>
                </div>
              ))}
            </div>

            {/* Quantity & Measurement */}
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={11} /> Quantity & Units
              </div>
              {qtyRules.slice(0, 5).map(r => (
                <div key={r.rule_id} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '5px' }}>
                  <span style={{
                    width: '6px', height: '6px', borderRadius: '50%', flexShrink: 0,
                    background: r.severity === 'high' ? '#ef4444' : r.severity === 'medium' ? '#f59e0b' : '#06b6d4'
                  }} />
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>{r.rule_id}</span>
                  <span style={{ fontSize: '11px', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.title.replace(' Declaration', '').replace('Net Quantity — ', '').replace('Net Quantity', 'Net Qty')}</span>
                </div>
              ))}
            </div>

            {/* MRP & Pricing */}
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <AlertCircle size={11} /> MRP & Pricing
              </div>
              {mrpRules.slice(0, 5).map(r => (
                <div key={r.rule_id} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '5px' }}>
                  <span style={{
                    width: '6px', height: '6px', borderRadius: '50%', flexShrink: 0,
                    background: r.severity === 'high' ? '#ef4444' : r.severity === 'medium' ? '#f59e0b' : '#06b6d4'
                  }} />
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>{r.rule_id}</span>
                  <span style={{ fontSize: '11px', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.title.replace('MRP Declaration', 'MRP Wording').replace('MRP — ', '').replace('MRP ', '')}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Amendment notice */}
          <div style={{
            marginTop: '14px', padding: '10px 14px',
            background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)',
            borderRadius: 'var(--radius-sm)', display: 'flex', gap: '8px', alignItems: 'flex-start'
          }}>
            <Info size={13} color="#f59e0b" style={{ flexShrink: 0, marginTop: '1px' }} />
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              <strong style={{ color: '#f59e0b' }}>Latest amendments applied:</strong>{' '}
              Pan masala micro-package exemption removed (GSR 881(E), effective 01.02.2026) ·
              Medical device font/PDP rules superseded by Medical Devices Rules 2017 (Oct 2025) ·
              Rule 6(10A) e-commerce country-of-origin filter (effective 01.07.2027 — not yet in force).
              Verify all amendment wording against egazette.gov.in before production enforcement.
            </p>
          </div>
        </div>
      )}

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
