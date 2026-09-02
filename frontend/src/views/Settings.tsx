import React, { useEffect, useState } from 'react';
import { Cpu, Database, CheckCircle2, AlertTriangle } from 'lucide-react';
import { checkHealth } from '../api';

export const Settings: React.FC = () => {
  const [health, setHealth] = useState<{ status: string; ocr_available: boolean } | null>(null);

  useEffect(() => {
    checkHealth().then(setHealth);
  }, []);

  return (
    <div className="animate-in">
      <div className="page-header" style={{ background: 'transparent', padding: '0 0 20px 0', borderBottom: 'none' }}>
        <h2>System Diagnostics & Configuration</h2>
        <p>Runtime engine health, OCR configuration, and offline fallback settings.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        <div className="card">
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={18} color="var(--accent-primary)" /> OCR & Vision Engine Status
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Primary OCR Engine:</span>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>EasyOCR / PyTorch</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>OCR Engine Status:</span>
              {health?.ocr_available ? (
                <span className="status-badge pass" style={{ fontSize: '11px' }}>
                  <CheckCircle2 size={12} /> Active (GPU/CPU)
                </span>
              ) : (
                <span className="status-badge review" style={{ fontSize: '11px' }}>
                  <AlertTriangle size={12} /> Fallback Demo Active
                </span>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Preprocessing:</span>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>OpenCV CLAHE + Bilateral Denoise</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Review Threshold:</span>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>&lt; 60% Confidence</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={18} color="var(--accent-secondary)" /> Storage & Offline Architecture
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Database Layer:</span>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>SQLite (Zero-friction local / Postgres ready)</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Offline Mode:</span>
              <span className="status-badge pass" style={{ fontSize: '11px' }}>
                <CheckCircle2 size={12} /> Fully Offline Capable
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Report Engine:</span>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>ReportLab PDF Builder</span>
            </div>
          </div>
        </div>

        <div className="card" style={{ gridColumn: '1 / -1' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '8px', color: 'var(--status-fail)' }}>
            Danger Zone: Reset Inspection Audit History
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Permanently delete all scanned inspection logs, evidence coordinates, and officer audit actions.
          </p>
          <button
            className="btn btn-danger btn-sm"
            onClick={async () => {
              if (window.confirm('Are you sure you want to permanently clear all inspection records?')) {
                const { clearAllInspections } = await import('../api');
                await clearAllInspections();
                alert('Inspection history cleared successfully.');
              }
            }}
          >
            Clear All Inspection Data
          </button>
        </div>
      </div>
    </div>
  );
};
