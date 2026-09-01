import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Download,
  AlertTriangle,
  Layers,
  Eye,
  UserCheck,
  QrCode,
  ShieldCheck,
  ShieldAlert,
  Type,
  MapPin,
  Flame,
  FileText,
  Globe,
  Sparkles
} from 'lucide-react';
import { getInspection, getImageUrl, getReportDownloadUrl, generateLegalNotice } from '../api';
import type { Inspection, Violation } from '../types';

export const InspectionDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAnnotated, setShowAnnotated] = useState(true);
  const [generatingNotice, setGeneratingNotice] = useState(false);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadRecord();
    }
  }, [id]);

  const loadRecord = () => {
    if (!id) return;
    getInspection(id)
      .then(setInspection)
      .catch((err) => setError(err.message || 'Failed to load inspection'))
      .finally(() => setLoading(false));
  };

  const handleGenerateNotice = async () => {
    if (!inspection) return;
    try {
      setGeneratingNotice(true);
      setNoticeMessage(null);
      const blob = await generateLegalNotice(inspection.id);
      
      // Auto-trigger browser download
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `NOTICE-${inspection.inspection_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);

      setNoticeMessage('Official Legal Notice generated & downloaded successfully.');
      loadRecord();
    } catch (e: any) {
      setError(e.message || 'Failed to generate legal notice.');
    } finally {
      setGeneratingNotice(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-overlay" style={{ minHeight: '400px' }}>
        <div className="spinner"></div>
        <p>Loading inspection record...</p>
      </div>
    );
  }

  if (error || !inspection) {
    return (
      <div className="card" style={{ padding: '32px', textAlign: 'center' }}>
        <AlertTriangle size={36} color="var(--status-fail)" style={{ margin: '0 auto 12px' }} />
        <h3>Error Loading Record</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>{error || 'Record not found'}</p>
        <button className="btn btn-secondary" onClick={() => navigate('/history')}>
          Back to History
        </button>
      </div>
    );
  }

  const severityScore = inspection.severity_score ?? 0;
  const riskLevel = inspection.risk_level || (severityScore > 80 ? 'critical' : (severityScore > 50 ? 'high' : (severityScore > 20 ? 'medium' : 'low')));
  const riskLabel = inspection.risk_label || (riskLevel === 'critical' ? 'Critical Risk' : (riskLevel === 'high' ? 'High Risk' : (riskLevel === 'medium' ? 'Medium Risk' : 'Low Risk')));
  
  const riskColor = riskLevel === 'critical' ? '#ef4444' : (riskLevel === 'high' ? '#f97316' : (riskLevel === 'medium' ? '#eab308' : '#10b981'));

  // Group and sort violations by severity points
  const sortedViolations: Violation[] = [...(inspection.violations || [])].sort((a, b) => {
    const ptsA = a.severity_points ?? (a.severity === 'critical' ? 10 : (a.severity === 'high' ? 7 : (a.severity === 'medium' ? 5 : 2)));
    const ptsB = b.severity_points ?? (b.severity === 'critical' ? 10 : (b.severity === 'high' ? 7 : (b.severity === 'medium' ? 5 : 2)));
    return ptsB - ptsA;
  });

  const getSeverityBadge = (v: Violation) => {
    const pts = v.severity_points ?? (v.severity === 'critical' ? 10 : (v.severity === 'high' ? 7 : (v.severity === 'medium' ? 5 : 2)));
    const sev = v.severity.toLowerCase();

    if (sev === 'critical' || pts >= 10) {
      return <span style={{ background: 'rgba(239,68,68,0.15)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.3)', padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>🔴 CRITICAL ({pts} pts)</span>;
    } else if (sev === 'high' || pts >= 7) {
      return <span style={{ background: 'rgba(249,115,22,0.15)', color: '#f97316', border: '1px solid rgba(249,115,22,0.3)', padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>🟠 HIGH ({pts} pts)</span>;
    } else if (sev === 'medium' || pts >= 5) {
      return <span style={{ background: 'rgba(234,179,8,0.15)', color: '#eab308', border: '1px solid rgba(234,179,8,0.3)', padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>🟡 MEDIUM ({pts} pts)</span>;
    } else {
      return <span style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981', border: '1px solid rgba(16,185,129,0.3)', padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>🟢 LOW ({pts} pts)</span>;
    }
  };

  return (
    <div className="animate-in">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/history')}>
            <ArrowLeft size={14} /> Back
          </button>
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: 800 }}>
              {inspection.product_name}
            </h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '3px' }}>
              <span style={{ fontFamily: 'monospace', fontSize: '12px', color: 'var(--text-muted)' }}>
                {inspection.inspection_id}
              </span>
              {inspection.latitude && inspection.longitude && (
                <span style={{ fontSize: '11px', color: '#6366f1', display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <MapPin size={11} /> {inspection.latitude.toFixed(4)}°N, {inspection.longitude.toFixed(4)}°E
                </span>
              )}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {inspection.overall_status === 'NON_COMPLIANT' && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={handleGenerateNotice}
              disabled={generatingNotice}
              style={{ borderColor: 'rgba(239,68,68,0.4)', color: '#ef4444' }}
            >
              <FileText size={14} />
              {generatingNotice ? 'Generating Notice...' : 'Generate Legal Notice (s.18)'}
            </button>
          )}

          <a
            href={getReportDownloadUrl(inspection.id)}
            target="_blank"
            rel="noreferrer"
            className="btn btn-primary btn-sm"
          >
            <Download size={14} /> Download Official PDF Report
          </a>
        </div>
      </div>

      {noticeMessage && (
        <div style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', color: '#10b981', padding: '10px 16px', borderRadius: 'var(--radius-md)', marginBottom: '16px', fontSize: '13px' }}>
          {noticeMessage}
        </div>
      )}

      <div className="inspection-layout">
        {/* Visual Evidence Panel */}
        <div className="image-panel">
          <div className="card" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Visual Evidence
              </span>
              {inspection.has_annotated_image && (
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    className={`btn btn-sm ${showAnnotated ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setShowAnnotated(true)}
                  >
                    <Layers size={12} /> Annotated
                  </button>
                  <button
                    className={`btn btn-sm ${!showAnnotated ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setShowAnnotated(false)}
                  >
                    <Eye size={12} /> Original
                  </button>
                </div>
              )}
            </div>

            {inspection.is_demo ? (
              <div style={{
                background: 'var(--bg-elevated)',
                padding: '30px',
                borderRadius: 'var(--radius-md)',
                textAlign: 'center',
                minHeight: '300px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Layers size={36} color="var(--accent-primary)" style={{ marginBottom: '12px' }} />
                <h4>Demo Package Record</h4>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  Extracted from test dataset with Legal Metrology validation rules.
                </p>
              </div>
            ) : (
              <div className="image-container" style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                <img
                  src={getImageUrl(inspection.id, showAnnotated && inspection.has_annotated_image)}
                  alt="Inspection evidence"
                  style={{ width: '100%', height: 'auto', display: 'block' }}
                />
              </div>
            )}

            {/* Officer Audit Trail */}
            {inspection.reviews && inspection.reviews.length > 0 && (
              <div style={{ marginTop: '16px', padding: '12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
                <h4 style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <UserCheck size={14} color="var(--accent-secondary)" /> Officer Review Log
                </h4>
                {inspection.reviews.map((r, i) => (
                  <div key={i} style={{ fontSize: '11px', color: 'var(--text-secondary)', paddingBottom: '6px' }}>
                    <strong>{r.field_name}:</strong> {r.action} — "{r.corrected_value}" {r.reviewer_notes ? `(${r.reviewer_notes})` : ''}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Barcode & GS1 Verification Card */}
          {inspection.barcode_data && (
            <div className="card" style={{ marginTop: '16px', borderLeft: `4px solid ${inspection.barcode_data.is_valid ? 'var(--status-pass)' : 'var(--status-fail)'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <QrCode size={18} color="var(--accent-primary)" />
                  <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0 }}>
                    Barcode & GS1 Registry Lookup
                  </h3>
                </div>
                {inspection.barcode_data.gs1_found ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#10b981', fontSize: '12px', fontWeight: 600 }}>
                    <ShieldCheck size={14} /> Registered in GS1
                  </span>
                ) : (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#ef4444', fontSize: '12px', fontWeight: 600 }}>
                    <ShieldAlert size={14} /> Unregistered / Counterfeit Alert
                  </span>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '12px', background: 'var(--bg-elevated)', padding: '12px', borderRadius: 'var(--radius-md)' }}>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Barcode Number</div>
                  <div style={{ fontWeight: 700, fontFamily: 'monospace', fontSize: '13px', marginTop: '2px' }}>
                    {inspection.barcode_data.barcode}
                  </div>
                </div>

                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Manufacturer Match</div>
                  <div style={{ fontWeight: 600, marginTop: '2px', color: inspection.barcode_data.mfg_status === 'MATCH' ? '#10b981' : '#ef4444' }}>
                    {inspection.barcode_data.mfg_status === 'MATCH' ? '✅ Verified' : '❌ Mismatch'} ({inspection.barcode_data.gs1_manufacturer || 'N/A'})
                  </div>
                </div>

                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>GS1 Declared MRP</div>
                  <div style={{ fontWeight: 600, marginTop: '2px' }}>
                    {inspection.barcode_data.gs1_declared_mrp ? `₹${inspection.barcode_data.gs1_declared_mrp}` : '—'}
                  </div>
                </div>

                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Scanned MRP Comparison</div>
                  <div style={{ fontWeight: 700, marginTop: '2px', color: inspection.barcode_data.mrp_status === 'OVERPRICED' ? '#ef4444' : '#10b981' }}>
                    {inspection.barcode_data.scanned_mrp ? `₹${inspection.barcode_data.scanned_mrp}` : '—'}
                    {inspection.barcode_data.mrp_status === 'OVERPRICED' && (
                      <span style={{ fontSize: '11px', color: '#ef4444', marginLeft: '6px' }}>
                        ❌ OVERPRICING (+{inspection.barcode_data.mrp_diff_pct}%)
                      </span>
                    )}
                    {inspection.barcode_data.mrp_status === 'MATCH' && (
                      <span style={{ fontSize: '11px', color: '#10b981', marginLeft: '6px' }}>
                        ✅ Matches
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {inspection.barcode_data.mismatches && inspection.barcode_data.mismatches.length > 0 && (
                <div style={{ marginTop: '10px', padding: '8px 12px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '6px', fontSize: '11px', color: '#ef4444' }}>
                  <strong>Alert:</strong> {inspection.barcode_data.mismatches.join('; ')}
                </div>
              )}
            </div>
          )}

          {/* AI Anomaly & Forensics Card */}
          {inspection.anomaly_data && (
            <div className="card" style={{ marginTop: '16px', borderLeft: `4px solid ${inspection.anomaly_data.has_anomaly ? '#f97316' : '#10b981'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Sparkles size={16} color="var(--accent-primary)" />
                  AI Anomaly & Anti-Tampering Inspection
                </h3>
                <span style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  color: inspection.anomaly_data.tampering_detected ? '#ef4444' : '#10b981',
                  background: inspection.anomaly_data.tampering_detected ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)',
                  padding: '2px 8px',
                  borderRadius: '4px'
                }}>
                  {inspection.anomaly_data.tampering_detected ? '⚠️ Tampering Flagged' : '✅ Packaging Authentic'}
                </span>
              </div>

              {inspection.anomaly_data.findings && inspection.anomaly_data.findings.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                  {inspection.anomaly_data.findings.map((f, i) => (
                    <div key={i} style={{ background: 'var(--bg-elevated)', padding: '10px', borderRadius: 'var(--radius-md)', fontSize: '12px' }}>
                      <div style={{ fontWeight: 700, color: f.severity === 'CRITICAL' ? '#ef4444' : '#f97316' }}>
                        {f.title} ({Math.round(f.confidence * 100)}% confidence)
                      </div>
                      <div style={{ color: 'var(--text-secondary)', marginTop: '2px', fontSize: '11px' }}>
                        {f.details}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                  Computer vision edge gradients and ELA error-level analysis found no adhesive sticker overlays or digital tampering over MRP.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Assessment & Declarations Panel */}
        <div className="assessment-panel">
          {/* Status & Severity Risk Score Banner */}
          <div className="card" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Overall Compliance</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '6px' }}>
                <span className={`status-badge ${inspection.overall_status.toLowerCase().replace('_', '-')}`}>
                  {inspection.overall_status.replace('_', ' ')}
                </span>
                <span style={{ fontSize: '18px', fontWeight: 800 }}>{inspection.compliance_score}/100</span>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Flame size={12} color={riskColor} /> Violation Risk Score
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
                <div style={{ fontSize: '18px', fontWeight: 800, color: riskColor }}>
                  {severityScore}/100
                </div>
                <span style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  color: riskColor,
                  background: `${riskColor}20`,
                  border: `1px solid ${riskColor}50`,
                  padding: '2px 8px',
                  borderRadius: '6px'
                }}>
                  {riskLabel}
                </span>
              </div>
            </div>
          </div>

          {/* Multi-Language Detection Info */}
          {inspection.detected_languages && (
            <div className="card" style={{ padding: '12px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Globe size={16} color="var(--accent-primary)" />
                <span style={{ fontSize: '12px', fontWeight: 700 }}>Language Readability (Rule 9):</span>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Detected: <strong>{inspection.detected_languages.detected_languages.map(l => l.toUpperCase()).join(', ')}</strong>
                </span>
              </div>
              <span style={{
                fontSize: '11px',
                fontWeight: 700,
                color: inspection.detected_languages.is_dual_language ? '#10b981' : '#6366f1',
                background: inspection.detected_languages.is_dual_language ? 'rgba(16,185,129,0.15)' : 'rgba(99,102,241,0.15)',
                padding: '2px 8px',
                borderRadius: '4px'
              }}>
                {inspection.detected_languages.is_dual_language ? '✅ Dual Language (English + Hindi)' : 'Standard Language Verification'}
              </span>
            </div>
          )}

          {/* Declarations Table with Font Measurements */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Type size={16} color="var(--accent-primary)" /> Mandatory Legal Declarations
              </h3>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Rule 6 & Rule 7 Standards
              </span>
            </div>

            <table className="data-table">
              <thead>
                <tr>
                  <th>Declaration</th>
                  <th>Detected Value</th>
                  <th>Font Height</th>
                  <th>Confidence</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {inspection.fields?.map((f, i) => {
                  const minFont = f.min_font_size_mm || 1.0;
                  const actualFont = f.font_size_mm;
                  const isFontOk = actualFont !== undefined && actualFont !== null ? actualFont >= minFont : null;

                  return (
                    <tr key={i}>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{f.field_label}</td>
                      <td>{f.detected_value || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Missing</span>}</td>
                      <td style={{ fontSize: '12px' }}>
                        {actualFont !== undefined && actualFont !== null ? (
                          <span style={{ color: isFontOk ? '#10b981' : '#f97316', fontWeight: 600 }}>
                            {actualFont}mm (Min: {minFont}mm) {isFontOk ? '✅' : '❌'}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>—</span>
                        )}
                      </td>
                      <td>{f.confidence > 0 ? `${(f.confidence * 100).toFixed(0)}%` : '—'}</td>
                      <td>
                        <span className={`status-badge ${f.status.toLowerCase().replace('_', '-')}`}>
                          {f.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Violations by Severity */}
          {sortedViolations && sortedViolations.length > 0 && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: 'var(--status-fail)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertTriangle size={16} /> Violations by Severity ({sortedViolations.length})
                </h3>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Sorted by Risk Priority
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {sortedViolations.map((v, i) => (
                  <div key={i} className={`violation-card ${v.severity.toLowerCase()}`}>
                    <div className="violation-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {getSeverityBadge(v)}
                        <strong style={{ fontSize: '13px' }}>{v.title}</strong>
                      </div>
                      <span className="rule-id">{v.rule_id}</span>
                    </div>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: '1.4' }}>
                      {v.reason}
                    </p>
                    {v.expected_requirement && (
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', fontStyle: 'italic' }}>
                        <strong>Legal Requirement:</strong> {v.expected_requirement}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
