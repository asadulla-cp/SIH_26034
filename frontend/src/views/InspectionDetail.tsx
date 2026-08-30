import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Download,
  AlertTriangle,
  Layers,
  Eye,
  UserCheck
} from 'lucide-react';
import { getInspection, getImageUrl, getReportDownloadUrl } from '../api';
import type { Inspection } from '../types';

export const InspectionDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAnnotated, setShowAnnotated] = useState(true);

  useEffect(() => {
    if (id) {
      getInspection(id)
        .then(setInspection)
        .catch((err) => setError(err.message || 'Failed to load inspection'))
        .finally(() => setLoading(false));
    }
  }, [id]);

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

  return (
    <div className="animate-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/history')}>
            <ArrowLeft size={14} /> Back
          </button>
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: 800 }}>
              {inspection.product_name}
            </h2>
            <span style={{ fontFamily: 'monospace', fontSize: '12px', color: 'var(--text-muted)' }}>
              {inspection.inspection_id}
            </span>
          </div>
        </div>

        <a
          href={getReportDownloadUrl(inspection.id)}
          target="_blank"
          rel="noreferrer"
          className="btn btn-primary btn-sm"
        >
          <Download size={14} /> Download Official PDF Report
        </a>
      </div>

      <div className="inspection-layout">
        {/* Visual Evidence Panel */}
        <div className="image-panel">
          <div className="card" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase' }}>Visual Evidence</span>
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
                  Extracted from preset test dataset for evaluation.
                </p>
              </div>
            ) : (
              <div className="image-container" style={{ borderRadius: 'var(--radius-md)' }}>
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
        </div>

        {/* Assessment & Declarations Panel */}
        <div className="assessment-panel">
          {/* Status Banner */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Status</div>
                <span className={`status-badge ${inspection.overall_status.toLowerCase().replace('_', '-')}`} style={{ marginTop: '4px' }}>
                  {inspection.overall_status.replace('_', ' ')}
                </span>
              </div>

              <div>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Score</div>
                <div style={{ fontSize: '24px', fontWeight: 800 }}>{inspection.compliance_score}/100</div>
              </div>
            </div>
          </div>

          {/* Declarations */}
          <div className="card">
            <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px' }}>
              Mandatory Legal Declarations
            </h3>

            <table className="data-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Value</th>
                  <th>Confidence</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {inspection.fields?.map((f, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{f.field_label}</td>
                    <td>{f.detected_value || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Missing</span>}</td>
                    <td>{f.confidence > 0 ? `${(f.confidence * 100).toFixed(0)}%` : '—'}</td>
                    <td>
                      <span className={`status-badge ${f.status.toLowerCase().replace('_', '-')}`}>
                        {f.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Violations */}
          {inspection.violations && inspection.violations.length > 0 && (
            <div className="card">
              <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px', color: 'var(--status-fail)' }}>
                Violations ({inspection.violations.length})
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {inspection.violations.map((v, i) => (
                  <div key={i} className={`violation-card ${v.severity}`}>
                    <div className="violation-header">
                      <strong>{v.title}</strong>
                      <span className="rule-id">{v.rule_id}</span>
                    </div>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      {v.reason}
                    </p>
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
