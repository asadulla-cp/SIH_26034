import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileArchive,
  AlertTriangle,
  Download,
  ArrowRight,
  FileSpreadsheet,
  Package,
  Search
} from 'lucide-react';
import { uploadBatchZip, getBatchStatus, listAllBatches, getBatchExportUrl } from '../api';
import type { BatchJob } from '../types';

export const BatchScan: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [activeJob, setActiveJob] = useState<BatchJob | null>(null);
  const [recentBatches, setRecentBatches] = useState<BatchJob[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadBatches();
  }, []);

  // Poll active batch until complete
  useEffect(() => {
    let timer: any = null;
    if (activeJob && activeJob.status === 'PROCESSING') {
      timer = setInterval(async () => {
        try {
          const updated = await getBatchStatus(activeJob.batch_id);
          setActiveJob(updated);
          if (updated.status !== 'PROCESSING') {
            clearInterval(timer);
            loadBatches();
          }
        } catch (e) {
          console.error(e);
        }
      }, 1500);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [activeJob?.batch_id, activeJob?.status]);

  const loadBatches = async () => {
    try {
      const list = await listAllBatches();
      setRecentBatches(list);
    } catch (e) {
      console.error(e);
    }
  };

  const handleFileSelect = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setError('Please select a valid .ZIP archive containing product images.');
      return;
    }
    if (file.size > 100 * 1024 * 1024) {
      setError('Selected ZIP file exceeds maximum allowed limit of 100MB.');
      return;
    }

    try {
      setError(null);
      setUploading(true);
      const res = await uploadBatchZip(file);
      const initialStatus = await getBatchStatus(res.batch_id);
      setActiveJob(initialStatus);
    } catch (err: any) {
      setError(err.message || 'Failed to upload batch ZIP archive.');
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const filteredInspections = (activeJob?.inspections || []).filter((item) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      item.product_name.toLowerCase().includes(term) ||
      item.filename.toLowerCase().includes(term) ||
      item.inspection_id.toLowerCase().includes(term) ||
      item.status.toLowerCase().includes(term)
    );
  });

  return (
    <div className="animate-in">
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <Package size={20} color="var(--accent-primary)" />
          <span style={{ fontSize: '12px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--accent-primary)', letterSpacing: '0.5px' }}>
            Multi-Product Batch Processing
          </span>
        </div>
        <h2 style={{ fontSize: '24px', fontWeight: 800 }}>Batch Product Compliance Scan</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
          Upload a ZIP archive containing up to 50 packaged commodity photos for parallel OCR extraction and Legal Metrology compliance verification.
        </p>
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
          gap: '10px'
        }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Upload Box */}
      {!activeJob || activeJob.status === 'COMPLETED' || activeJob.status === 'FAILED' ? (
        <div
          className={`card ${isDragOver ? 'drag-over' : ''}`}
          style={{
            border: `2px dashed ${isDragOver ? 'var(--accent-primary)' : 'var(--border-default)'}`,
            padding: '36px 20px',
            textAlign: 'center',
            cursor: 'pointer',
            marginBottom: '24px',
            background: isDragOver ? 'rgba(99, 102, 241, 0.05)' : 'var(--bg-card)'
          }}
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
              }
            }}
          />
          <FileArchive size={48} color="var(--accent-primary)" style={{ margin: '0 auto 12px' }} />
          <h3 style={{ fontSize: '16px', fontWeight: 700 }}>
            {uploading ? 'Uploading and Unpacking ZIP Archive...' : 'Drop your product ZIP archive here, or click to browse'}
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '6px' }}>
            Supports up to 50 packaged product photos (.jpg, .png, .webp) &middot; Max 100MB
          </p>
        </div>
      ) : null}

      {/* Active Job Progress & Summary */}
      {activeJob && (
        <div className="card" style={{ marginBottom: '24px', padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  background: activeJob.status === 'COMPLETED' ? 'rgba(16,185,129,0.15)' : (activeJob.status === 'FAILED' ? 'rgba(239,68,68,0.15)' : 'rgba(99,102,241,0.15)'),
                  color: activeJob.status === 'COMPLETED' ? '#10b981' : (activeJob.status === 'FAILED' ? '#ef4444' : '#6366f1'),
                  fontSize: '11px',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '4px'
                }}>
                  {activeJob.status}
                </span>
                <h3 style={{ fontSize: '18px', fontWeight: 700 }}>{activeJob.filename}</h3>
              </div>
              <span style={{ fontFamily: 'monospace', fontSize: '12px', color: 'var(--text-muted)' }}>
                {activeJob.batch_id}
              </span>
            </div>

            {activeJob.status === 'COMPLETED' && (
              <a
                href={getBatchExportUrl(activeJob.batch_id)}
                download
                className="btn btn-primary btn-sm"
              >
                <FileSpreadsheet size={16} /> Download Consolidated Excel Report
              </a>
            )}
          </div>

          {/* Progress Bar */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
              <span>Processing Status: {activeJob.processed_count} of {activeJob.total_count} products completed</span>
              <span>{activeJob.progress_pct}%</span>
            </div>
            <div style={{ height: '8px', background: 'var(--bg-elevated)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${activeJob.progress_pct}%`,
                background: activeJob.status === 'COMPLETED' ? '#10b981' : 'linear-gradient(90deg, #6366f1, #06b6d4)',
                transition: 'width 0.3s ease'
              }} />
            </div>
          </div>

          {/* Metric Summary Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', marginBottom: '20px' }}>
            <div style={{ background: 'var(--bg-elevated)', padding: '12px', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>TOTAL PRODUCTS</div>
              <div style={{ fontSize: '22px', fontWeight: 800, marginTop: '2px' }}>{activeJob.total_count}</div>
            </div>

            <div style={{ background: 'rgba(16,185,129,0.1)', padding: '12px', borderRadius: 'var(--radius-md)', textAlign: 'center', border: '1px solid rgba(16,185,129,0.2)' }}>
              <div style={{ fontSize: '11px', color: '#10b981', fontWeight: 700 }}>COMPLIANT</div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#10b981', marginTop: '2px' }}>{activeJob.compliant_count}</div>
            </div>

            <div style={{ background: 'rgba(239,68,68,0.1)', padding: '12px', borderRadius: 'var(--radius-md)', textAlign: 'center', border: '1px solid rgba(239,68,68,0.2)' }}>
              <div style={{ fontSize: '11px', color: '#ef4444', fontWeight: 700 }}>NON-COMPLIANT</div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#ef4444', marginTop: '2px' }}>{activeJob.non_compliant_count}</div>
            </div>

            <div style={{ background: 'rgba(234,179,8,0.1)', padding: '12px', borderRadius: 'var(--radius-md)', textAlign: 'center', border: '1px solid rgba(234,179,8,0.2)' }}>
              <div style={{ fontSize: '11px', color: '#eab308', fontWeight: 700 }}>NEEDS REVIEW</div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#eab308', marginTop: '2px' }}>{activeJob.needs_review_count}</div>
            </div>

            {activeJob.duration_seconds > 0 && (
              <div style={{ background: 'var(--bg-elevated)', padding: '12px', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>DURATION</div>
                <div style={{ fontSize: '22px', fontWeight: 800, marginTop: '2px' }}>{activeJob.duration_seconds}s</div>
              </div>
            )}
          </div>

          {/* Results Table */}
          {activeJob.inspections && activeJob.inspections.length > 0 && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '10px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: 700 }}>Processed Products ({filteredInspections.length})</h4>
                <div style={{ position: 'relative', width: '220px' }}>
                  <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input
                    type="text"
                    placeholder="Search product or file..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '6px 10px 6px 30px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-default)',
                      background: 'var(--bg-elevated)',
                      color: 'var(--text-primary)',
                      fontSize: '12px'
                    }}
                  />
                </div>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Product</th>
                      <th>Filename</th>
                      <th>Status</th>
                      <th>Score</th>
                      <th>Risk Level</th>
                      <th>MRP</th>
                      <th>Net Qty</th>
                      <th>Barcode</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredInspections.map((item, idx) => (
                      <tr key={idx}>
                        <td style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{idx + 1}</td>
                        <td style={{ fontWeight: 600 }}>{item.product_name}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: '11px', color: 'var(--text-secondary)' }}>{item.filename}</td>
                        <td>
                          <span className={`status-badge ${item.status.toLowerCase().replace('_', '-')}`}>
                            {item.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td style={{ fontWeight: 700 }}>{item.compliance_score}/100</td>
                        <td>
                          <span style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            color: item.risk_level === 'critical' ? '#ef4444' : (item.risk_level === 'high' ? '#f97316' : (item.risk_level === 'medium' ? '#eab308' : '#10b981'))
                          }}>
                            {item.risk_level.toUpperCase()}
                          </span>
                        </td>
                        <td>{item.mrp || '—'}</td>
                        <td>{item.net_quantity || '—'}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: '11px' }}>{item.barcode || '—'}</td>
                        <td>
                          {item.id ? (
                            <button
                              className="btn btn-secondary btn-sm"
                              style={{ padding: '4px 8px', fontSize: '11px' }}
                              onClick={() => navigate(`/inspections/${item.id}`)}
                            >
                              View <ArrowRight size={10} />
                            </button>
                          ) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Recent Batches List */}
      {recentBatches.length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px' }}>Recent Batch Inspection Runs</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {recentBatches.map((b) => (
              <div
                key={b.batch_id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 16px',
                  background: 'var(--bg-elevated)',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer'
                }}
                onClick={() => setActiveJob(b)}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: '14px' }}>{b.filename}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', display: 'flex', gap: '12px' }}>
                    <span>{b.batch_id}</span>
                    <span>{b.total_count} products</span>
                    <span>{b.compliant_count} compliant, {b.non_compliant_count} non-compliant</span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span className={`status-badge ${b.status.toLowerCase().replace('_', '-')}`} style={{ fontSize: '10px' }}>
                    {b.status}
                  </span>
                  <a
                    href={getBatchExportUrl(b.batch_id)}
                    download
                    className="btn btn-secondary btn-sm"
                    onClick={(e) => e.stopPropagation()}
                    title="Export Excel"
                  >
                    <Download size={12} />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
