import React, { useState } from 'react';
import {
  Globe,
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ShieldCheck,
  Layers,
  DollarSign
} from 'lucide-react';
import { scanEcommerceUrl } from '../api';
import type { EcommerceReport } from '../types';

const SAMPLE_URLS = [
  { label: 'Amazon Shampoo (Missing MRP In Images)', url: 'https://www.amazon.in/dp/B08SAMPLE123' },
  { label: 'Flipkart Packaged Tea (Compliant)', url: 'https://www.flipkart.com/tata-tea-premium/p/itmSAMPLE456' }
];

export const EcommerceScan: React.FC = () => {
  const [urlInput, setUrlInput] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [report, setReport] = useState<EcommerceReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState(0);

  const steps = [
    'Connecting to E-Commerce Portal...',
    'Scraping Product Gallery & Listed Price...',
    'Running Multi-Pass OCR on Product Photos...',
    'Verifying E-Commerce Legal Metrology Mandates...'
  ];

  const handleScan = async (targetUrl?: string) => {
    const urlToScan = targetUrl || urlInput;
    if (!urlToScan.trim()) {
      setError('Please enter a product listing URL.');
      return;
    }

    try {
      setError(null);
      setReport(null);
      setIsScanning(true);
      setStepIndex(0);

      const interval = setInterval(() => {
        setStepIndex((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
      }, 700);

      const res = await scanEcommerceUrl(urlToScan);
      clearInterval(interval);
      setReport(res);
    } catch (err: any) {
      setError(err.message || 'Failed to scan e-commerce listing.');
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <div className="animate-in">
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <Globe size={20} color="var(--accent-primary)" />
          <span style={{ fontSize: '12px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--accent-primary)', letterSpacing: '0.5px' }}>
            E-Commerce Compliance Verification
          </span>
        </div>
        <h2 style={{ fontSize: '24px', fontWeight: 800 }}>Online Marketplace Listing Scanner</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
          Scrapes product pages from Amazon, Flipkart, and Quick Commerce to verify mandatory Legal Metrology declaration visibility in listing photos (Rule 6(10) / E-Commerce Directives).
        </p>
      </div>

      {/* URL Input Card */}
      <div className="card" style={{ padding: '24px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: '280px' }}>
            <Search size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Paste Amazon, Flipkart, or Quick Commerce product URL..."
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleScan(); }}
              style={{
                width: '100%',
                padding: '12px 14px 12px 42px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-default)',
                background: 'var(--bg-elevated)',
                color: 'var(--text-primary)',
                fontSize: '14px'
              }}
            />
          </div>
          <button
            className="btn btn-primary"
            onClick={() => handleScan()}
            disabled={isScanning}
            style={{ minWidth: '140px' }}
          >
            {isScanning ? 'Scanning...' : 'Scan Listing'}
          </button>
        </div>

        {/* Quick Sample Links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '14px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Try Sample URLs:</span>
          {SAMPLE_URLS.map((s, idx) => (
            <button
              key={idx}
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '11px', padding: '4px 10px' }}
              onClick={() => {
                setUrlInput(s.url);
                handleScan(s.url);
              }}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div style={{
          background: 'var(--status-fail-bg)',
          border: '1px solid var(--status-fail-border)',
          color: 'var(--status-fail)',
          padding: '14px 18px',
          borderRadius: 'var(--radius-md)',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <AlertTriangle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Scanning Progress */}
      {isScanning && (
        <div className="card" style={{ padding: '32px', textAlign: 'center', marginBottom: '24px' }}>
          <div className="spinner" style={{ margin: '0 auto 16px' }}></div>
          <h3 style={{ fontSize: '16px', fontWeight: 700 }}>{steps[stepIndex]}</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px' }}>
            Fetching product gallery, downloading high-res images, and running OCR extraction...
          </p>
        </div>
      )}

      {/* Scan Results Report */}
      {report && (
        <div className="animate-in">
          {/* Top Result Banner */}
          <div className="card" style={{
            padding: '20px 24px',
            marginBottom: '20px',
            borderLeft: `5px solid ${report.is_compliant ? 'var(--status-pass)' : 'var(--status-fail)'}`
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span style={{
                    background: 'var(--accent-primary)',
                    color: '#fff',
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '4px'
                  }}>
                    {report.platform}
                  </span>
                  <span style={{
                    background: report.is_compliant ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                    color: report.is_compliant ? '#10b981' : '#ef4444',
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '4px'
                  }}>
                    {report.overall_status}
                  </span>
                </div>
                <h3 style={{ fontSize: '18px', fontWeight: 800 }}>{report.product_name}</h3>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Listed Price: <strong>₹{report.listed_price}</strong> &middot; Scanned {report.images_scanned} gallery photos
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Compliance Score</div>
                <div style={{ fontSize: '28px', fontWeight: 800, color: report.is_compliant ? '#10b981' : '#ef4444' }}>
                  {report.compliance_score}/100
                </div>
              </div>
            </div>
          </div>

          {/* Overpricing Warning if applicable */}
          {report.is_overpriced && (
            <div style={{
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.3)',
              padding: '14px 18px',
              borderRadius: 'var(--radius-md)',
              color: '#ef4444',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <DollarSign size={20} />
              <div>
                <strong>Overpricing Alert:</strong> Online listed price (₹{report.listed_price}) exceeds physical packaged MRP by {report.price_diff_pct}%. Prohibited under Section 18(2).
              </div>
            </div>
          )}

          {/* Grid Layout: Mandate Checklist + Evidence Photos */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px', alignItems: 'start' }}>
            {/* Checklist */}
            <div className="card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={18} color="var(--accent-primary)" />
                Mandatory E-Commerce Declarations Checklist
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {report.checks.map((c, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '12px 14px',
                      background: 'var(--bg-elevated)',
                      borderRadius: 'var(--radius-md)',
                      borderLeft: `4px solid ${c.status === 'PASS' ? '#10b981' : '#ef4444'}`
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <strong style={{ fontSize: '13px' }}>{c.requirement}</strong>
                      <span style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        color: c.status === 'PASS' ? '#10b981' : '#ef4444',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}>
                        {c.status === 'PASS' ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                        {c.status}
                      </span>
                    </div>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                      {c.details}
                    </p>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px', display: 'inline-block' }}>
                      Ref: {c.rule}
                    </span>
                  </div>
                ))}
              </div>

              {/* Recommendations */}
              {report.recommendations.length > 0 && (
                <div style={{ marginTop: '18px', padding: '14px', background: 'rgba(99,102,241,0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(99,102,241,0.2)' }}>
                  <h4 style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Seller Action Required:
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {report.recommendations.map((rec, idx) => (
                      <li key={idx} style={{ marginBottom: '4px' }}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Scraped Images Evidence */}
            <div className="card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layers size={18} color="var(--accent-primary)" />
                Scanned Listing Photos ({report.image_urls.length})
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px' }}>
                {report.image_urls.map((imgUrl, i) => (
                  <div key={i} style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--border-default)', background: 'var(--bg-elevated)' }}>
                    <img
                      src={imgUrl}
                      alt={`Gallery item ${i + 1}`}
                      style={{ width: '100%', height: '140px', objectFit: 'contain', display: 'block', background: '#fff' }}
                    />
                    <div style={{ padding: '6px', textAlign: 'center', fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
                      Photo #{i + 1}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
