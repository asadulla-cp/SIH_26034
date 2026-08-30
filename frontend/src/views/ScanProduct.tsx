import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Upload,
  Scan,
  ShieldCheck,
  XCircle,
  AlertTriangle,
  Download,
  Eye,
  Edit3,
  CheckCircle2,
  RefreshCw,
  Sparkles,
  Info,
  Layers,
  AlertCircle
} from 'lucide-react';
import {
  scanUploadedImage,
  scanDemoProduct,
  getDemoProducts,
  getImageUrl,
  getReportDownloadUrl,
  submitReviewAction
} from '../api';
import type { DemoProduct, ExtractedField, Violation } from '../types';

export const ScanProduct: React.FC = () => {
  const [searchParams] = useSearchParams();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // States
  const [demoProducts, setDemoProducts] = useState<DemoProduct[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState<number>(0);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Active highlighted field for evidence overlay
  const [activeHighlightField, setActiveHighlightField] = useState<string | null>(null);
  const [showAnnotatedImage, setShowAnnotatedImage] = useState<boolean>(true);

  // Review modal state
  const [reviewingField, setReviewingField] = useState<ExtractedField | null>(null);
  const [editedValue, setEditedValue] = useState<string>('');
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);

  // Load demo products on mount
  useEffect(() => {
    getDemoProducts().then(setDemoProducts).catch(console.error);

    const demoParam = searchParams.get('demo');
    if (demoParam) {
      handleRunDemo(demoParam);
    }
  }, [searchParams]);

  // Image processing steps progression
  const stepTitles = [
    'Image Upload & Quality Assessment',
    'Preprocessing (Denoise & Contrast Enhancement)',
    'OCR & Spatial Bounding Box Extraction',
    'Structured Declaration Pattern Matching',
    'Deterministic Legal Rule Validation',
    'Generating Compliance Evidence & Score'
  ];

  const simulateStepProgression = async (actualCall: () => Promise<any>) => {
    setIsProcessing(true);
    setError(null);
    setProcessingStep(0);

    const stepInterval = setInterval(() => {
      setProcessingStep((prev) => (prev < stepTitles.length - 1 ? prev + 1 : prev));
    }, 450);

    try {
      const data = await actualCall();
      clearInterval(stepInterval);
      setProcessingStep(stepTitles.length);
      setResult(data);
    } catch (err: any) {
      clearInterval(stepInterval);
      setError(err.message || 'Inspection failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
      setError(null);
    }
  };

  const handleStartScan = () => {
    if (!selectedFile) return;
    simulateStepProgression(() => scanUploadedImage(selectedFile));
  };

  const handleRunDemo = (productId: string) => {
    setSelectedFile(null);
    setPreviewUrl(null);
    simulateStepProgression(() => scanDemoProduct(productId));
  };

  const handleOpenReview = (field: ExtractedField) => {
    setReviewingField(field);
    setEditedValue(field.detected_value || '');
    setReviewNotes('');
  };

  const handleSaveReview = async (action: 'APPROVE' | 'REJECT' | 'EDIT') => {
    if (!reviewingField || !result) return;
    try {
      setIsSubmittingReview(true);
      await submitReviewAction(result.id, {
        field_name: reviewingField.field_name,
        action,
        original_value: reviewingField.detected_value,
        corrected_value: editedValue,
        notes: reviewNotes
      });

      // Update local state
      const updatedFields = result.fields.map((f: ExtractedField) => {
        if (f.field_name === reviewingField.field_name) {
          return {
            ...f,
            detected_value: editedValue,
            status: action === 'APPROVE' ? 'PASS' : (action === 'REJECT' ? 'FAIL' : 'PASS')
          };
        }
        return f;
      });

      setResult({
        ...result,
        fields: updatedFields
      });

      setReviewingField(null);
    } catch (err: any) {
      alert('Failed to save review: ' + err.message);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  return (
    <div className="animate-in">
      {/* Top Banner */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 800 }}>
            {result ? `Inspection: ${result.product_name}` : 'Package Label Scanner & Compliance Verifier'}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
            AI extracts raw text. Deterministic rules decide compliance. Human verifies uncertainty.
          </p>
        </div>

        {result && (
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setResult(null);
                setSelectedFile(null);
                setPreviewUrl(null);
              }}
            >
              <RefreshCw size={14} /> Scan Another
            </button>
            <a
              href={getReportDownloadUrl(result.id)}
              target="_blank"
              rel="noreferrer"
              className="btn btn-primary btn-sm"
            >
              <Download size={14} /> Download PDF Report
            </a>
          </div>
        )}
      </div>

      {/* Preset Demo Selection Bar (Crucial for SIH Judge evaluation) */}
      {!result && !isProcessing && (
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-primary)',
          borderRadius: 'var(--radius-lg)',
          padding: '16px 20px',
          marginBottom: '24px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Sparkles size={16} color="var(--accent-secondary)" />
            <span style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Quick Demo Presets for Hackathon Evaluation
            </span>
          </div>

          <div className="demo-grid" style={{ marginTop: '8px' }}>
            {demoProducts.map((p) => (
              <div
                key={p.id}
                className="demo-card"
                onClick={() => handleRunDemo(p.id)}
                style={{ position: 'relative' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                  <h4 style={{ fontSize: '14px', margin: 0 }}>{p.name}</h4>
                  {p.is_compliant === true && (
                    <span className="status-badge compliant" style={{ fontSize: '10px', padding: '1px 6px' }}>Pass</span>
                  )}
                  {p.is_compliant === false && (
                    <span className="status-badge non-compliant" style={{ fontSize: '10px', padding: '1px 6px' }}>Fail</span>
                  )}
                  {p.is_compliant === null && (
                    <span className="status-badge needs-review" style={{ fontSize: '10px', padding: '1px 6px' }}>Review</span>
                  )}
                </div>
                <p style={{ fontSize: '12px', margin: 0 }}>{p.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Zone (when no result and not processing) */}
      {!result && !isProcessing && (
        <div className="card" style={{ padding: '32px', marginBottom: '24px' }}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="image/*"
            style={{ display: 'none' }}
          />

          {!previewUrl ? (
            <div
              className="upload-zone"
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="upload-zone-icon">
                <Upload size={36} />
              </div>
              <h3>Upload Package Label Image</h3>
              <p>Drag and drop a photo of a commodity package, or click to browse files</p>
              <p style={{ fontSize: '11px', marginTop: '8px', color: 'var(--text-muted)' }}>
                Supported formats: JPG, PNG, WEBP, TIFF (Max 20MB)
              </p>
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', gap: '24px', alignItems: 'center', flexWrap: 'wrap' }}>
                <div style={{
                  maxWidth: '300px',
                  maxHeight: '260px',
                  borderRadius: 'var(--radius-md)',
                  overflow: 'hidden',
                  border: '1px solid var(--border-primary)'
                }}>
                  <img
                    src={previewUrl}
                    alt="Selected package"
                    style={{ width: '100%', height: 'auto', display: 'block' }}
                  />
                </div>
                <div style={{ flex: 1, minWidth: '240px' }}>
                  <h4 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '6px' }}>
                    {selectedFile?.name}
                  </h4>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                    Size: {selectedFile ? (selectedFile.size / (1024 * 1024)).toFixed(2) : 0} MB
                  </p>

                  <div style={{ display: 'flex', gap: '12px' }}>
                    <button className="btn btn-primary" onClick={handleStartScan}>
                      <Scan size={18} /> Run Compliance Scan
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={() => {
                        setSelectedFile(null);
                        setPreviewUrl(null);
                      }}
                    >
                      Change Image
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div style={{
              background: 'var(--status-fail-bg)',
              border: '1px solid var(--status-fail-border)',
              color: 'var(--status-fail)',
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              marginTop: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}>
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}
        </div>
      )}

      {/* Processing Animation Screen */}
      {isProcessing && (
        <div className="card" style={{ padding: '40px' }}>
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <div className="spinner" style={{ width: '40px', height: '40px', margin: '0 auto 16px' }}></div>
            <h3 style={{ fontSize: '20px', fontWeight: 700 }}>Processing Package Label</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              Executing OCR, extracting declarations, and applying Legal Metrology Rules...
            </p>
          </div>

          <div className="processing-steps" style={{ maxWidth: '600px', margin: '0 auto' }}>
            {stepTitles.map((title, idx) => {
              const isDone = processingStep > idx;
              const isActive = processingStep === idx;

              return (
                <div key={idx} className="processing-step">
                  <div className={`step-indicator ${isDone ? 'done' : (isActive ? 'active' : 'pending')}`}>
                    {isDone ? '✓' : idx + 1}
                  </div>
                  <div className={`step-text ${isDone ? 'done' : (isActive ? 'active' : 'pending')}`}>
                    {title}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* FLAGSHIP INSPECTION RESULT SCREEN (SIH Presentation Layout) */}
      {result && (
        <div className="inspection-layout">
          {/* LEFT PANEL: Package Visual Evidence & Bounding Boxes */}
          <div className="image-panel">
            <div className="card" style={{ padding: '16px' }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '12px'
              }}>
                <span style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Visual Package Evidence
                </span>
                {result.has_annotated_image && (
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button
                      className={`btn btn-sm ${showAnnotatedImage ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setShowAnnotatedImage(true)}
                    >
                      <Layers size={12} /> Annotated OCR
                    </button>
                    <button
                      className={`btn btn-sm ${!showAnnotatedImage ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setShowAnnotatedImage(false)}
                    >
                      <Eye size={12} /> Original
                    </button>
                  </div>
                )}
              </div>

              {result.is_demo ? (
                <div style={{
                  background: 'var(--bg-elevated)',
                  borderRadius: 'var(--radius-md)',
                  padding: '24px',
                  textAlign: 'center',
                  minHeight: '380px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '1px dashed var(--border-primary)'
                }}>
                  <div style={{
                    width: '64px',
                    height: '64px',
                    borderRadius: '50%',
                    background: 'rgba(99, 102, 241, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '16px',
                    color: 'var(--accent-primary)'
                  }}>
                    <Layers size={32} />
                  </div>
                  <h4 style={{ fontSize: '16px', fontWeight: 600 }}>Demo Dataset Mode</h4>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '340px', marginTop: '6px' }}>
                    {result.demo_description || 'Deterministic declarations and rule validation results loaded from verified sample.'}
                  </p>
                  <div style={{
                    marginTop: '20px',
                    padding: '8px 16px',
                    background: 'rgba(245, 158, 11, 0.1)',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '12px',
                    color: 'var(--status-review)'
                  }}>
                    Verified Sample: <strong>{result.product_name}</strong>
                  </div>
                </div>
              ) : (
                <div className="image-container" style={{ position: 'relative', borderRadius: 'var(--radius-md)' }}>
                  <img
                    src={getImageUrl(result.id, showAnnotatedImage && result.has_annotated_image)}
                    alt="Inspection Evidence"
                    style={{ width: '100%', height: 'auto', display: 'block' }}
                  />
                </div>
              )}

              {/* Image Quality Assessment Info */}
              {result.image_quality && (
                <div style={{
                  marginTop: '16px',
                  padding: '12px 14px',
                  background: 'var(--bg-elevated)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '12px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Image Clarity / Suitability:</span>
                    <strong style={{
                      color: result.image_quality.overall_score >= 0.7 ? 'var(--status-pass)' : 'var(--status-review)'
                    }}>
                      {(result.image_quality.overall_score * 100).toFixed(0)}%
                    </strong>
                  </div>
                  {result.image_quality.issues?.length > 0 && (
                    <div style={{ color: 'var(--status-review)', marginTop: '4px' }}>
                      ⚠️ {result.image_quality.issues.join('; ')}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* RIGHT PANEL: Compliance Assessment & Field-by-Field Table */}
          <div className="assessment-panel">
            {/* Top Overall Status Card */}
            <div className="card" style={{
              borderLeft: `6px solid ${
                result.overall_status === 'COMPLIANT'
                  ? 'var(--status-pass)'
                  : (result.overall_status === 'NON_COMPLIANT' ? 'var(--status-fail)' : 'var(--status-review)')
              }`
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
                <div>
                  <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '1px' }}>
                    Inspection Verdict
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px' }}>
                    <span className={`status-badge ${result.overall_status.toLowerCase().replace('_', '-')}`} style={{ fontSize: '14px', padding: '6px 16px' }}>
                      {result.overall_status === 'COMPLIANT' && <ShieldCheck size={16} />}
                      {result.overall_status === 'NON_COMPLIANT' && <XCircle size={16} />}
                      {result.overall_status === 'NEEDS_REVIEW' && <AlertTriangle size={16} />}
                      {result.overall_status.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '1px' }}>
                    Compliance Score
                  </div>
                  <div style={{ fontSize: '28px', fontWeight: 800, color: result.compliance_score >= 80 ? 'var(--status-pass)' : (result.compliance_score >= 50 ? 'var(--status-review)' : 'var(--status-fail)') }}>
                    {result.compliance_score}<span style={{ fontSize: '16px', color: 'var(--text-muted)' }}>/100</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Extracted Declarations Table */}
            <div className="card">
              <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={16} color="var(--accent-primary)" />
                Mandatory Declarations (Rule 6 Mapping)
              </h3>

              <table className="data-table">
                <thead>
                  <tr>
                    <th>Declaration</th>
                    <th>Detected Value</th>
                    <th>Confidence</th>
                    <th>Status</th>
                    <th>Review</th>
                  </tr>
                </thead>
                <tbody>
                  {result.fields?.map((f: ExtractedField, idx: number) => {
                    const isMissing = !f.detected_value;
                    const confPercent = Math.round((f.confidence || 0) * 100);

                    return (
                      <tr
                        key={idx}
                        style={{
                          background: activeHighlightField === f.field_name ? 'var(--bg-elevated)' : undefined,
                          cursor: 'pointer'
                        }}
                        onClick={() => setActiveHighlightField(f.field_name)}
                      >
                        <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {f.field_label}
                        </td>
                        <td style={{ maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {isMissing ? (
                            <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Not detected</span>
                          ) : (
                            <span>{f.detected_value}</span>
                          )}
                        </td>
                        <td>
                          {confPercent > 0 ? (
                            <div>
                              <span className="confidence-bar">
                                <span
                                  className={`confidence-bar-fill ${confPercent >= 70 ? 'high' : (confPercent >= 50 ? 'medium' : 'low')}`}
                                  style={{ width: `${confPercent}%` }}
                                ></span>
                              </span>
                              <span style={{ fontSize: '11px', fontWeight: 600 }}>{confPercent}%</span>
                            </div>
                          ) : (
                            <span style={{ color: 'var(--text-muted)' }}>—</span>
                          )}
                        </td>
                        <td>
                          <span className={`status-badge ${f.status.toLowerCase().replace('_', '-')}`} style={{ fontSize: '10px', padding: '2px 8px' }}>
                            {f.status === 'PASS' && '✓ PASS'}
                            {f.status === 'FAIL' && '✕ FAIL'}
                            {f.status === 'NEEDS_REVIEW' && '⚠ REVIEW'}
                            {f.status === 'PENDING' && 'PENDING'}
                          </span>
                        </td>
                        <td>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '3px 8px', fontSize: '11px' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenReview(f);
                            }}
                          >
                            <Edit3 size={12} /> Edit
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Violations & Evidence Explanation Cards */}
            {result.violations?.length > 0 && (
              <div className="card">
                <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-fail)' }}>
                  <AlertTriangle size={16} />
                  Legal Violations & Non-Compliance Explanations ({result.violations.length})
                </h3>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {result.violations.map((v: Violation, idx: number) => (
                    <div key={idx} className={`violation-card ${v.severity}`}>
                      <div className="violation-header">
                        <div className="violation-title">
                          <span>❌ {v.title}</span>
                          <span className="rule-id">{v.rule_id}</span>
                        </div>
                        <span className={`severity-badge ${v.severity}`}>
                          {v.severity} Severity
                        </span>
                      </div>

                      <div className="violation-detail">
                        <dt>Detected:</dt>
                        <dd>{v.detected_value || 'Missing from package declaration'}</dd>

                        <dt>Requirement:</dt>
                        <dd>{v.expected_requirement}</dd>

                        <dt>Explanation:</dt>
                        <dd style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                          {v.reason}
                        </dd>
                      </div>

                      {v.is_prototype_rule && (
                        <div className="prototype-badge">
                          <Info size={12} /> Prototype validation rule — requires official legal verification before deployment.
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Human-in-the-Loop Review Modal */}
      {reviewingField && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999,
          padding: '20px'
        }}>
          <div className="card" style={{ maxWidth: '480px', width: '100%', padding: '24px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '4px' }}>
              Officer Review: {reviewingField.field_label}
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Adjust extracted declaration or manually override verification status.
            </p>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                Extracted Value (OCR):
              </label>
              <input
                type="text"
                className="input-field"
                value={editedValue}
                onChange={(e) => setEditedValue(e.target.value)}
                placeholder="Enter corrected value..."
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                Officer Notes / Justification:
              </label>
              <input
                type="text"
                className="input-field"
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="e.g., Verified visually on physical label..."
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setReviewingField(null)}
                disabled={isSubmittingReview}
              >
                Cancel
              </button>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => handleSaveReview('REJECT')}
                  disabled={isSubmittingReview}
                >
                  Mark Non-Compliant
                </button>
                <button
                  className="btn btn-success btn-sm"
                  onClick={() => handleSaveReview('APPROVE')}
                  disabled={isSubmittingReview}
                >
                  Approve as Compliant
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
