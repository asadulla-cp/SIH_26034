import React, { useEffect, useState } from 'react';
import { Info } from 'lucide-react';
import { getRules } from '../api';
import type { Rule } from '../types';

export const RuleLibrary: React.FC = () => {
  const [rules, setRules] = useState<Rule[]>([]);
  const [ruleSetVersion, setRuleSetVersion] = useState<string>('');
  const [disclaimer, setDisclaimer] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    getRules()
      .then((res) => {
        setRules(res.rules);
        setRuleSetVersion(res.rule_set_version);
        setDisclaimer(res.disclaimer);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="animate-in">
      <div className="page-header" style={{ background: 'transparent', padding: '0 0 20px 0', borderBottom: 'none' }}>
        <h2>Legal Metrology Rule Library (v{ruleSetVersion || '1.0.0'})</h2>
        <p>Deterministic rules engine mapped directly to the Legal Metrology (Packaged Commodities) Rules, 2011.</p>
      </div>

      {disclaimer && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(6, 182, 212, 0.05))',
          border: '1px solid var(--border-accent)',
          borderRadius: 'var(--radius-lg)',
          padding: '16px 20px',
          marginBottom: '24px',
          display: 'flex',
          gap: '12px',
          alignItems: 'flex-start'
        }}>
          <Info size={20} color="var(--accent-primary)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '2px' }}>Legal Engine Architecture Principle</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              {disclaimer}
            </p>
          </div>
        </div>
      )}

      {loading ? (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p>Loading rules engine definitions...</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '16px' }}>
          {rules.map((rule) => (
            <div key={rule.rule_id} className="rule-card">
              <div className="rule-card-header">
                <span className="rule-id">{rule.rule_id}</span>
                <span className={`severity-badge ${rule.severity}`}>
                  {rule.severity} Severity
                </span>
              </div>

              <h4 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '6px' }}>
                {rule.title}
              </h4>

              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                {rule.requirement}
              </p>

              <div style={{
                background: 'var(--bg-elevated)',
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '11px',
                color: 'var(--text-muted)'
              }}>
                <div><strong>Source:</strong> {rule.source_reference}</div>
                <div style={{ marginTop: '2px' }}><strong>Field:</strong> <code style={{ color: 'var(--accent-secondary)' }}>{rule.field}</code></div>
                <div style={{ marginTop: '2px' }}><strong>Validation:</strong> {rule.validation_type}</div>
              </div>

              {rule.is_prototype && (
                <div className="prototype-badge" style={{ marginTop: '10px' }}>
                  <Info size={10} /> Prototype verification rule
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
