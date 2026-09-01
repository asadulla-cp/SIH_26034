import React, { useEffect, useState, useMemo } from 'react';
import {
  Info, Search, ChevronDown, ChevronUp, ExternalLink,
  Scale, AlertTriangle, ShieldCheck, BookOpen, Filter,
  FileText, CheckCircle2, Zap
} from 'lucide-react';
import { getRules } from '../api';
import type { Rule } from '../types';

// Extended Rule type with v2 fields
type RuleV2 = Rule & {
  category?: string;
  legal_basis?: string;
  penalty_section?: string;
  penalty_amount?: string;
  amendment_notes?: string | null;
  automation_level?: string;
  automation_note?: string;
  exemptions?: string[];
};

const CATEGORY_META: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  mandatory_declarations: {
    label: 'Mandatory Declarations',
    icon: <FileText size={14} />,
    color: '#6366f1',
  },
  quantity_measurement: {
    label: 'Quantity & Measurement',
    icon: <Scale size={14} />,
    color: '#10b981',
  },
  mrp_pricing: {
    label: 'MRP & Pricing',
    icon: <CheckCircle2 size={14} />,
    color: '#f59e0b',
  },
  display_visibility: {
    label: 'Display & Visibility',
    icon: <Zap size={14} />,
    color: '#06b6d4',
  },
  exemptions: {
    label: 'Exemptions',
    icon: <ShieldCheck size={14} />,
    color: '#8b5cf6',
  },
  wholesale_import: {
    label: 'Wholesale & Import',
    icon: <BookOpen size={14} />,
    color: '#ec4899',
  },
  uncategorised: {
    label: 'Other Rules',
    icon: <Info size={14} />,
    color: '#94a3b8',
  },
};

const SEVERITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  high: { bg: 'rgba(239,68,68,0.12)', text: '#ef4444', border: 'rgba(239,68,68,0.3)' },
  medium: { bg: 'rgba(245,158,11,0.12)', text: '#f59e0b', border: 'rgba(245,158,11,0.3)' },
  low: { bg: 'rgba(6,182,212,0.12)', text: '#06b6d4', border: 'rgba(6,182,212,0.3)' },
};

export const RuleLibrary: React.FC = () => {
  const [rules, setRules] = useState<RuleV2[]>([]);
  const [ruleSetVersion, setRuleSetVersion] = useState('');
  const [disclaimer, setDisclaimer] = useState('');
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    getRules()
      .then((res) => {
        setRules(res.rules as RuleV2[]);
        setRuleSetVersion(res.rule_set_version);
        setDisclaimer(res.disclaimer);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Build category grouping
  const categories = useMemo(() => {
    const cats = new Set(rules.map(r => r.category || 'uncategorised'));
    return Array.from(cats);
  }, [rules]);

  // Filtered rules
  const filteredRules = useMemo(() => {
    return rules.filter(r => {
      const q = search.toLowerCase();
      const matchesSearch =
        !q ||
        r.rule_id.toLowerCase().includes(q) ||
        r.title.toLowerCase().includes(q) ||
        r.description.toLowerCase().includes(q) ||
        r.requirement.toLowerCase().includes(q) ||
        r.source_reference.toLowerCase().includes(q);
      const matchesSeverity = filterSeverity === 'all' || r.severity === filterSeverity;
      const matchesCategory = filterCategory === 'all' || (r.category || 'uncategorised') === filterCategory;
      return matchesSearch && matchesSeverity && matchesCategory;
    });
  }, [rules, search, filterSeverity, filterCategory]);

  // Group filtered rules by category
  const grouped = useMemo(() => {
    const g: Record<string, RuleV2[]> = {};
    for (const r of filteredRules) {
      const cat = r.category || 'uncategorised';
      if (!g[cat]) g[cat] = [];
      g[cat].push(r);
    }
    return g;
  }, [filteredRules]);

  const toggleExpand = (id: string) => setExpandedId(prev => prev === id ? null : id);

  if (loading) {
    return (
      <div className="animate-in">
        <div className="loading-overlay" style={{ padding: '60px' }}>
          <div className="spinner" />
          <p>Loading rule engine definitions…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-in">
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
          <Scale size={22} color="var(--accent-primary)" />
          <h2 style={{ fontSize: '22px', fontWeight: 800 }}>
            Legal Metrology Rule Library
          </h2>
          <span style={{
            background: 'var(--accent-primary)', color: '#fff',
            fontSize: '10px', fontWeight: 700, padding: '2px 7px',
            borderRadius: '4px', letterSpacing: '0.5px'
          }}>v{ruleSetVersion}</span>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          {rules.length} deterministic rules · Legal Metrology (Packaged Commodities) Rules, 2011 ·
          Amendments up to August 2026
        </p>
      </div>

      {/* Disclaimer */}
      {disclaimer && (
        <div style={{
          background: 'rgba(99,102,241,0.07)', border: '1px solid rgba(99,102,241,0.2)',
          borderRadius: 'var(--radius-md)', padding: '12px 16px', marginBottom: '20px',
          display: 'flex', gap: '10px', alignItems: 'flex-start'
        }}>
          <Info size={16} color="var(--accent-primary)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{disclaimer}</p>
        </div>
      )}

      {/* Search + Filters */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '200px', position: 'relative' }}>
          <Search size={14} style={{
            position: 'absolute', left: '12px', top: '50%',
            transform: 'translateY(-50%)', color: 'var(--text-muted)'
          }} />
          <input
            type="text"
            placeholder="Search rules by ID, title, requirement…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              width: '100%', padding: '9px 12px 9px 34px',
              background: 'var(--bg-card)', border: '1px solid var(--border-primary)',
              borderRadius: 'var(--radius-md)', color: 'var(--text-primary)',
              fontSize: '13px', fontFamily: 'inherit', boxSizing: 'border-box', outline: 'none'
            }}
          />
        </div>

        {/* Severity filter */}
        <div style={{ position: 'relative' }}>
          <Filter size={13} style={{
            position: 'absolute', left: '10px', top: '50%',
            transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none'
          }} />
          <select
            value={filterSeverity}
            onChange={e => setFilterSeverity(e.target.value)}
            style={{
              padding: '9px 12px 9px 28px', background: 'var(--bg-card)',
              border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)', fontSize: '13px', fontFamily: 'inherit',
              cursor: 'pointer', outline: 'none', appearance: 'none', paddingRight: '28px'
            }}
          >
            <option value="all">All Severities</option>
            <option value="high">High Only</option>
            <option value="medium">Medium Only</option>
            <option value="low">Low Only</option>
          </select>
        </div>

        {/* Category filter */}
        <div style={{ position: 'relative' }}>
          <select
            value={filterCategory}
            onChange={e => setFilterCategory(e.target.value)}
            style={{
              padding: '9px 12px', background: 'var(--bg-card)',
              border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)', fontSize: '13px', fontFamily: 'inherit',
              cursor: 'pointer', outline: 'none', appearance: 'none', paddingRight: '28px'
            }}
          >
            <option value="all">All Categories</option>
            {categories.map(c => (
              <option key={c} value={c}>{CATEGORY_META[c]?.label || c}</option>
            ))}
          </select>
        </div>

        <div style={{
          padding: '9px 14px', background: 'var(--bg-elevated)',
          borderRadius: 'var(--radius-md)', fontSize: '13px', color: 'var(--text-muted)',
          display: 'flex', alignItems: 'center'
        }}>
          {filteredRules.length} / {rules.length} rules
        </div>
      </div>

      {/* Grouped rule cards */}
      {filteredRules.length === 0 ? (
        <div className="empty-state" style={{ padding: '60px 20px' }}>
          <Search size={40} />
          <h3>No rules match your search</h3>
          <p style={{ fontSize: '13px' }}>Try a different keyword or clear the filters.</p>
        </div>
      ) : (
        Object.entries(grouped).map(([cat, catRules]) => {
          const meta = CATEGORY_META[cat] || CATEGORY_META.uncategorised;
          return (
            <div key={cat} style={{ marginBottom: '28px' }}>
              {/* Category header */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                marginBottom: '12px', paddingBottom: '8px',
                borderBottom: `2px solid ${meta.color}30`
              }}>
                <span style={{ color: meta.color }}>{meta.icon}</span>
                <h3 style={{ fontSize: '14px', fontWeight: 700, color: meta.color }}>
                  {meta.label}
                </h3>
                <span style={{
                  fontSize: '11px', padding: '1px 7px', borderRadius: '10px',
                  background: `${meta.color}20`, color: meta.color, fontWeight: 600
                }}>
                  {catRules.length} rule{catRules.length > 1 ? 's' : ''}
                </span>
              </div>

              {/* Rule cards */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {catRules.map(rule => {
                  const sev = SEVERITY_COLORS[rule.severity] || SEVERITY_COLORS.low;
                  const isExpanded = expandedId === rule.rule_id;

                  return (
                    <div
                      key={rule.rule_id}
                      style={{
                        background: 'var(--bg-card)',
                        border: `1px solid ${isExpanded ? 'var(--border-accent)' : 'var(--border-primary)'}`,
                        borderRadius: 'var(--radius-md)',
                        overflow: 'hidden',
                        transition: 'border-color 150ms ease',
                      }}
                    >
                      {/* Card header row — always visible */}
                      <div
                        style={{
                          display: 'flex', alignItems: 'center', gap: '12px',
                          padding: '13px 16px', cursor: 'pointer',
                          background: isExpanded ? 'rgba(99,102,241,0.04)' : 'transparent'
                        }}
                        onClick={() => toggleExpand(rule.rule_id)}
                      >
                        {/* Rule ID */}
                        <code style={{
                          fontSize: '11px', fontWeight: 700, color: 'var(--accent-secondary)',
                          background: 'rgba(6,182,212,0.1)', padding: '2px 7px', borderRadius: '4px',
                          flexShrink: 0
                        }}>
                          {rule.rule_id}
                        </code>

                        {/* Title */}
                        <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', flex: 1 }}>
                          {rule.title}
                        </span>

                        {/* Severity badge */}
                        <span style={{
                          fontSize: '10px', fontWeight: 700, padding: '3px 8px',
                          borderRadius: '10px', textTransform: 'uppercase',
                          background: sev.bg, color: sev.text, border: `1px solid ${sev.border}`,
                          flexShrink: 0
                        }}>
                          {rule.severity}
                        </span>

                        {/* Validation type chip */}
                        <span style={{
                          fontSize: '10px', padding: '3px 7px', borderRadius: '4px',
                          background: 'var(--bg-elevated)', color: 'var(--text-muted)', flexShrink: 0,
                          display: 'none' // hide on small screens via inline; OK for desktop
                        } as React.CSSProperties}>
                          {rule.validation_type}
                        </span>

                        {/* Expand chevron */}
                        <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </span>
                      </div>

                      {/* Expanded detail */}
                      {isExpanded && (
                        <div style={{
                          padding: '0 16px 16px',
                          borderTop: '1px solid var(--border-primary)'
                        }}>
                          {/* Description */}
                          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '14px 0 12px', lineHeight: 1.6 }}>
                            {rule.description}
                          </p>

                          {/* Requirement box */}
                          <div style={{
                            background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)',
                            padding: '10px 14px', marginBottom: '12px',
                            borderLeft: `3px solid ${sev.text}`
                          }}>
                            <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                              Requirement
                            </div>
                            <p style={{ fontSize: '12px', color: 'var(--text-primary)', lineHeight: 1.6 }}>
                              {rule.requirement}
                            </p>
                          </div>

                          {/* Meta grid */}
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px', marginBottom: '12px' }}>
                            <MetaItem label="Legal Source" value={rule.source_reference} />
                            {(rule as RuleV2).legal_basis && (
                              <MetaItem label="Legal Basis" value={(rule as RuleV2).legal_basis!} />
                            )}
                            <MetaItem label="Validation Type" value={rule.validation_type} mono />
                            <MetaItem label="Field" value={rule.field} mono />
                            {(rule as RuleV2).penalty_section && (
                              <MetaItem label="Penalty Section" value={(rule as RuleV2).penalty_section!} />
                            )}
                            {(rule as RuleV2).penalty_amount && (
                              <MetaItem label="Penalty" value={(rule as RuleV2).penalty_amount!} />
                            )}
                            {(rule as RuleV2).automation_level && (
                              <MetaItem label="Automation" value={(rule as RuleV2).automation_level!} />
                            )}
                          </div>

                          {/* Exemptions */}
                          {(rule as RuleV2).exemptions && (rule as RuleV2).exemptions!.length > 0 && (
                            <div style={{ marginBottom: '10px' }}>
                              <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '5px' }}>
                                Exemptions
                              </div>
                              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                {(rule as RuleV2).exemptions!.map(ex => (
                                  <span key={ex} style={{
                                    fontSize: '11px', padding: '2px 8px', borderRadius: '10px',
                                    background: 'rgba(139,92,246,0.12)', color: '#a78bfa',
                                    border: '1px solid rgba(139,92,246,0.25)'
                                  }}>
                                    {ex.replace(/_/g, ' ')}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Amendment notes */}
                          {(rule as RuleV2).amendment_notes && (
                            <div style={{
                              padding: '9px 12px', borderRadius: 'var(--radius-sm)',
                              background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)',
                              display: 'flex', gap: '8px', alignItems: 'flex-start', marginBottom: '10px'
                            }}>
                              <AlertTriangle size={13} color="#f59e0b" style={{ flexShrink: 0, marginTop: '2px' }} />
                              <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                                <strong style={{ color: '#f59e0b' }}>Amendment note: </strong>
                                {(rule as RuleV2).amendment_notes}
                              </p>
                            </div>
                          )}

                          {/* Footer: source link + prototype badge */}
                          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                            <a
                              href="https://egazette.gov.in"
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
                                fontSize: '11px', color: 'var(--accent-secondary)',
                                display: 'flex', alignItems: 'center', gap: '4px',
                                textDecoration: 'none'
                              }}
                            >
                              <ExternalLink size={11} /> Verify on e-Gazette
                            </a>
                            <a
                              href="https://consumeraffairs.nic.in"
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
                                fontSize: '11px', color: 'var(--accent-secondary)',
                                display: 'flex', alignItems: 'center', gap: '4px',
                                textDecoration: 'none'
                              }}
                            >
                              <ExternalLink size={11} /> Consumer Affairs
                            </a>
                            {rule.is_prototype && (
                              <span style={{
                                fontSize: '10px', color: 'var(--text-muted)',
                                background: 'var(--bg-elevated)', padding: '2px 7px',
                                borderRadius: '4px', marginLeft: 'auto'
                              }}>
                                ⚗ Prototype rule — not for production enforcement
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })
      )}

      {/* Footer notice */}
      <div style={{
        marginTop: '24px', padding: '14px 18px',
        background: 'rgba(99,102,241,0.05)', border: '1px solid rgba(99,102,241,0.15)',
        borderRadius: 'var(--radius-md)', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.6
      }}>
        <strong style={{ color: 'var(--text-secondary)' }}>⚖️ Legal note:</strong>{' '}
        This rule library is built from the Legal Metrology (Packaged Commodities) Rules, 2011 (GSR 202(E)) and secondary-source summaries of
        amendments up to August 2026. Before using for real enforcement actions, verify all rules and amendment text against the official
        e-Gazette of India (egazette.gov.in) and the Department of Consumer Affairs website (consumeraffairs.nic.in → Legal Metrology).
        Penalties shown are subject to gazette verification.
      </div>
    </div>
  );
};

// ── Helper sub-component ──────────────────────────────────────────────────────
const MetaItem: React.FC<{ label: string; value: string; mono?: boolean }> = ({ label, value, mono }) => (
  <div style={{
    background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)',
    padding: '8px 10px'
  }}>
    <div style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: '3px' }}>
      {label}
    </div>
    <div style={{
      fontSize: '12px', color: 'var(--text-primary)', lineHeight: 1.4,
      ...(mono ? { fontFamily: 'JetBrains Mono, monospace', color: 'var(--accent-secondary)', fontSize: '11px' } : {})
    }}>
      {value}
    </div>
  </div>
);
