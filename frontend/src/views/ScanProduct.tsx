import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  AlertCircle,
  Plus,
  X,
  Camera,
  Loader,
  Package,
  Globe
} from 'lucide-react';
import {
  scanUploadedImages,
  scanDemoProduct,
  getDemoProducts,
  getImageUrl,
  getReportDownloadUrl,
  submitReviewAction
} from '../api';
import { queueOfflineInspection } from '../offline-queue';
import type { DemoProduct, ExtractedField, Violation } from '../types';

// ─────────────────────────── Types ────────────────────────────────────────────
interface ImageSlot {
  id: string;
  file: File;
  previewUrl: string;
  quality: 'good' | 'fair' | 'poor' | 'pending' | 'failed';
  qualityLabel: string;
  qualityIssues: string[];
  status: 'waiting' | 'analyzing' | 'done' | 'failed';
}

const MAX_IMAGES = 5;

const ANGLE_HINTS = [
  'Front of package',
  'Back of package',
  'Side panel',
  'Bottom / MRP panel',
  'Close-up of declarations',
];

// ─────────────────────────── Main Component ───────────────────────────────────
export const ScanProduct: React.FC = () => {
  const [searchParams] = useSearchParams();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Multi-image state
  const [imageSlots, setImageSlots] = useState<ImageSlot[]>([]);
  const [demoProducts, setDemoProducts] = useState<DemoProduct[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingSteps, setProcessingSteps] = useState<{ label: string; status: 'waiting' | 'active' | 'done' | 'failed' }[]>([]);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Evidence panel
  const [activeHighlightField, setActiveHighlightField] = useState<string | null>(null);
  const [showAnnotatedImage, setShowAnnotatedImage] = useState(true);
  const [showDebug, setShowDebug] = useState(false);

  // Review modal
  const [reviewingField, setReviewingField] = useState<ExtractedField | null>(null);
  const [editedValue, setEditedValue] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);

  // Drag state
  const [isDragging, setIsDragging] = useState(false);

  // Multi-Language selection
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(['en', 'hi']);

  useEffect(() => {
    getDemoProducts().then(setDemoProducts).catch(console.error);

    const demoParam = searchParams.get('demo');
    if (demoParam) {
      handleRunDemo(demoParam);
    }
  }, [searchParams]);

  // ─────────────────── Image Slot Management ──────────────────────────────────
  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const filesArray = Array.from(newFiles);
    const allowed = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
    const validFiles = filesArray.filter(f => allowed.includes(f.type));

    setImageSlots(prev => {
      const remaining = MAX_IMAGES - prev.length;
      if (remaining <= 0) return prev;

      const toAdd = validFiles.slice(0, remaining).map((file): ImageSlot => ({
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        file,
        previewUrl: URL.createObjectURL(file),
        quality: 'pending',
        qualityLabel: 'Pending',
        qualityIssues: [],
        status: 'waiting',
      }));

      return [...prev, ...toAdd];
    });
    setResult(null);
    setError(null);
  }, []);

  const removeImage = (id: string) => {
    setImageSlots(prev => {
      const slot = prev.find(s => s.id === id);
      if (slot) URL.revokeObjectURL(slot.previewUrl);
      return prev.filter(s => s.id !== id);
    });
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      addFiles(e.target.files);
      e.target.value = '';
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.length) {
      addFiles(e.dataTransfer.files);
    }
  };

  // ─────────────────── Scan Pipeline ──────────────────────────────────────────
  const buildProcessingSteps = (count: number) => {
    const steps: { label: string; status: 'waiting' | 'active' | 'done' | 'failed' }[] = [];
    for (let i = 0; i < count; i++) {
      steps.push({ label: `Analyzing Image ${i + 1}`, status: 'waiting' });
    }
    steps.push({ label: 'Fusing declarations across images', status: 'waiting' });
    steps.push({ label: 'Resolving conflicts & normalizing values', status: 'waiting' });
    steps.push({ label: 'Applying Legal Metrology Rules', status: 'waiting' });
    steps.push({ label: 'Generating compliance evidence', status: 'waiting' });
    return steps;
  };

  const handleStartScan = async () => {
    if (imageSlots.length === 0) return;
    setIsProcessing(true);
    setError(null);
    setResult(null);

    const files = imageSlots.map(s => s.file);
    const steps = buildProcessingSteps(files.length);
    setProcessingSteps(steps);

    // Simulate step-by-step progression
    let stepIdx = 0;
    const advanceStep = () => {
      setProcessingSteps(prev => prev.map((s, i) => {
        if (i < stepIdx) return { ...s, status: 'done' };
        if (i === stepIdx) return { ...s, status: 'active' };
        return { ...s, status: 'waiting' };
      }));
    };

    // Advance image steps with timing
    const interval = setInterval(() => {
      if (stepIdx < steps.length - 1) {
        stepIdx++;
        advanceStep();
      }
    }, Math.min(800, 3000 / steps.length));

    advanceStep();

    // Capture GPS Geolocation
    let coords: { latitude?: number; longitude?: number } | undefined;
    if (navigator.geolocation) {
      try {
        const pos: any = await new Promise((resolve) => {
          navigator.geolocation.getCurrentPosition(resolve, () => resolve(null), { timeout: 3000 });
        });
        if (pos?.coords) {
          coords = { latitude: pos.coords.latitude, longitude: pos.coords.longitude };
        }
      } catch (e) {
        console.debug('Geolocation skipped:', e);
      }
    }

    try {
      if (!navigator.onLine) {
        throw new Error('OFFLINE_MODE');
      }

      const data = await scanUploadedImages(files, coords, selectedLanguages);
      clearInterval(interval);
      setProcessingSteps(prev => prev.map(s => ({ ...s, status: 'done' })));
      setResult(data);
    } catch (err: any) {
      clearInterval(interval);
      if (err.message === 'OFFLINE_MODE' || !navigator.onLine) {
        await queueOfflineInspection(files, coords);
        setError('Device is offline. Your inspection has been queued locally in IndexedDB and will auto-sync when online.');
      } else {
        setError(err.message || 'Inspection failed');
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRunDemo = (productId: string) => {
    setImageSlots([]);
    setResult(null);
    setError(null);
    setIsProcessing(true);
    const steps = [
      { label: 'Loading demo dataset', status: 'active' as const },
      { label: 'Applying Legal Metrology Rules', status: 'waiting' as const },
      { label: 'Generating compliance evidence', status: 'waiting' as const },
    ];
    setProcessingSteps(steps);

    const interval = setInterval(() => {
      setProcessingSteps(prev => {
        const firstWaiting = prev.findIndex(s => s.status === 'waiting');
        if (firstWaiting === -1) {
          clearInterval(interval);
          return prev.map(s => ({ ...s, status: 'done' }));
        }
        return prev.map((s, i) => {
          if (i < firstWaiting) return { ...s, status: 'done' };
          if (i === firstWaiting) return { ...s, status: 'active' };
          return s;
        });
      });
    }, 500);

    scanDemoProduct(productId)
      .then(data => {
        clearInterval(interval);
        setProcessingSteps(prev => prev.map(s => ({ ...s, status: 'done' })));
        setResult(data);
      })
      .catch(err => {
        clearInterval(interval);
        setError(err.message || 'Demo failed');
      })
      .finally(() => setIsProcessing(false));
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

      setResult({ ...result, fields: updatedFields });
      setReviewingField(null);
    } catch (err: any) {
      alert('Failed to save review: ' + err.message);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  // ─────────────────── Quality Icon Helpers ───────────────────────────────────
  const qualityIconForScore = (score: number) => {
    if (score >= 0.75) return '✓';
    if (score >= 0.5) return '⚠';
    return '✗';
  };

  const qualityColorForScore = (score: number) => {
    if (score >= 0.75) return 'var(--status-pass)';
    if (score >= 0.5) return 'var(--status-review)';
    return 'var(--status-fail)';
  };

  // ─────────────────────────── Render ─────────────────────────────────────────
  return (
    <div className="animate-in">

      {/* ── Top Banner ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 800 }}>
            {result ? `Inspection: ${result.product_name}` : 'Package Label Scanner & Compliance Verifier'}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
            AI extracts raw text · Deterministic rules decide compliance · Human verifies uncertainty
          </p>
        </div>

        {result && (
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary btn-sm" onClick={() => {
              setResult(null);
              setImageSlots([]);
              setError(null);
            }}>
              <RefreshCw size={14} /> Scan Another
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowDebug(!showDebug)}>
              <Info size={14} /> Debug Mode
            </button>
            <a href={getReportDownloadUrl(result.id)} target="_blank" rel="noreferrer" className="btn btn-primary btn-sm">
              <Download size={14} /> Download PDF Report
            </a>
          </div>
        )}
      </div>

      {/* ── Demo Presets ── */}
      {!result && !isProcessing && (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-lg)', padding: '16px 20px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Sparkles size={16} color="var(--accent-secondary)" />
            <span style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Quick Demo Presets for Hackathon Evaluation
            </span>
          </div>
          <div className="demo-grid" style={{ marginTop: '8px' }}>
            {demoProducts.map((p) => (
              <div key={p.id} className="demo-card" onClick={() => handleRunDemo(p.id)} style={{ position: 'relative' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                  <h4 style={{ fontSize: '14px', margin: 0 }}>{p.name}</h4>
                  {p.is_compliant === true && <span className="status-badge compliant" style={{ fontSize: '10px', padding: '1px 6px' }}>Pass</span>}
                  {p.is_compliant === false && <span className="status-badge non-compliant" style={{ fontSize: '10px', padding: '1px 6px' }}>Fail</span>}
                  {p.is_compliant === null && <span className="status-badge needs-review" style={{ fontSize: '10px', padding: '1px 6px' }}>Review</span>}
                </div>
                <p style={{ fontSize: '12px', margin: 0 }}>{p.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Multi-Image Upload Zone ── */}
      {!result && !isProcessing && (
        <div className="card" style={{ padding: '24px', marginBottom: '24px' }}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            accept="image/jpeg,image/png,image/webp"
            multiple
            style={{ display: 'none' }}
          />

          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Camera size={18} color="var(--accent-primary)" />
                Multi-Image Package Scan
                <span style={{ fontSize: '11px', background: 'rgba(99, 102, 241, 0.15)', color: 'var(--accent-primary)', padding: '2px 8px', borderRadius: '999px', fontWeight: 600 }}>
                  Up to 5 images
                </span>
              </h3>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: '4px 0 0' }}>
                Upload up to 5 photos of the same package. Capture different sides/angles to improve declaration detection.
              </p>
            </div>
            {imageSlots.length > 0 && imageSlots.length < MAX_IMAGES && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => fileInputRef.current?.click()}
                style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <Plus size={14} /> Add Image ({imageSlots.length}/{MAX_IMAGES})
              </button>
            )}
          </div>

          {/* Angle hint guide */}
          {imageSlots.length === 0 && (
            <div style={{
              display: 'flex',
              gap: '6px',
              flexWrap: 'wrap',
              marginBottom: '16px',
            }}>
              {ANGLE_HINTS.map((hint, i) => (
                <span key={i} style={{
                  fontSize: '11px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-primary)',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  color: 'var(--text-secondary)',
                }}>
                  {i + 1}. {hint}
                </span>
              ))}
            </div>
          )}

          {/* Drop zone (shown when no images yet) */}
          {imageSlots.length === 0 && (
            <div
              className={`upload-zone ${isDragging ? 'drag-active' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              style={{ cursor: 'pointer' }}
            >
              <div className="upload-zone-icon"><Upload size={36} /></div>
              <h3>Upload Package Images</h3>
              <p>Drag & drop up to 5 package photos, or click to browse</p>
              <p style={{ fontSize: '11px', marginTop: '8px', color: 'var(--text-muted)' }}>
                JPG, PNG, WebP · Max 20MB each · Up to 5 images
              </p>
            </div>
          )}

          {/* Image Thumbnail Grid */}
          {imageSlots.length > 0 && (
            <div>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
                gap: '12px',
                marginBottom: '16px',
              }}>
                {imageSlots.map((slot, idx) => (
                  <div
                    key={slot.id}
                    style={{
                      position: 'relative',
                      borderRadius: 'var(--radius-md)',
                      border: '2px solid var(--border-primary)',
                      overflow: 'hidden',
                      background: 'var(--bg-elevated)',
                      transition: 'border-color 0.2s',
                    }}
                  >
                    {/* Image preview */}
                    <div style={{ position: 'relative', aspectRatio: '4/3', overflow: 'hidden' }}>
                      <img
                        src={slot.previewUrl}
                        alt={`Image ${idx + 1}`}
                        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                      />
                      {/* Remove button */}
                      <button
                        onClick={() => removeImage(slot.id)}
                        style={{
                          position: 'absolute',
                          top: '6px',
                          right: '6px',
                          background: 'rgba(0,0,0,0.75)',
                          border: 'none',
                          borderRadius: '50%',
                          width: '24px',
                          height: '24px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: 'pointer',
                          color: '#fff',
                          padding: 0,
                          zIndex: 2,
                        }}
                      >
                        <X size={14} />
                      </button>
                      {/* Image number badge */}
                      <div style={{
                        position: 'absolute',
                        top: '6px',
                        left: '6px',
                        background: 'var(--accent-primary)',
                        color: '#fff',
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '2px 7px',
                        borderRadius: '4px',
                      }}>
                        Img {idx + 1}
                      </div>
                    </div>
                    {/* Image info footer */}
                    <div style={{ padding: '8px 10px' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {ANGLE_HINTS[idx] || `Image ${idx + 1}`}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                        {(slot.file.size / (1024 * 1024)).toFixed(1)} MB
                      </div>
                    </div>
                  </div>
                ))}

                {/* Add more slot */}
                {imageSlots.length < MAX_IMAGES && (
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={handleDrop}
                    style={{
                      aspectRatio: '4/3',
                      border: '2px dashed var(--border-primary)',
                      borderRadius: 'var(--radius-md)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: 'pointer',
                      color: 'var(--text-muted)',
                      gap: '8px',
                      fontSize: '12px',
                      transition: 'border-color 0.2s, background 0.2s',
                      background: isDragging ? 'var(--bg-elevated)' : 'transparent',
                      minHeight: '120px',
                    }}
                  >
                    <Plus size={24} />
                    <span>Add Image</span>
                    <span style={{ fontSize: '10px' }}>{imageSlots.length}/{MAX_IMAGES}</span>
                  </div>
                )}
              </div>

              {/* Multi-Language Selector */}
              <div style={{ marginBottom: '16px', padding: '12px 14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-default)' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Globe size={14} color="var(--accent-primary)" />
                  Multi-Language OCR Recognition:
                </div>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {[
                    { id: 'en', label: 'English (Default)' },
                    { id: 'hi', label: 'Hindi (हिन्दी)' },
                    { id: 'ta', label: 'Tamil (தமிழ்)' },
                    { id: 'bn', label: 'Bengali (বাংলা)' },
                    { id: 'mr', label: 'Marathi (मराठी)' },
                    { id: 'gu', label: 'Gujarati (ગુજરાતી)' },
                  ].map((lang) => {
                    const isSel = selectedLanguages.includes(lang.id);
                    return (
                      <button
                        key={lang.id}
                        type="button"
                        onClick={() => {
                          if (lang.id === 'en') return; // English is mandatory base
                          setSelectedLanguages((prev) =>
                            isSel ? prev.filter((l) => l !== lang.id) : [...prev, lang.id]
                          );
                        }}
                        style={{
                          padding: '4px 10px',
                          borderRadius: '999px',
                          fontSize: '11px',
                          fontWeight: 600,
                          cursor: lang.id === 'en' ? 'default' : 'pointer',
                          background: isSel ? 'var(--accent-primary)' : 'var(--bg-card)',
                          color: isSel ? '#fff' : 'var(--text-secondary)',
                          border: `1px solid ${isSel ? 'var(--accent-primary)' : 'var(--border-default)'}`,
                          transition: 'all 0.15s ease'
                        }}
                      >
                        {isSel ? '✓ ' : '+ '}{lang.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                <button className="btn btn-primary" onClick={handleStartScan} style={{ gap: '8px' }}>
                  <Scan size={18} />
                  Run Compliance Scan ({imageSlots.length} image{imageSlots.length > 1 ? 's' : ''})
                </button>
                <button className="btn btn-secondary" onClick={() => { setImageSlots([]); setError(null); }}>
                  Clear All
                </button>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  {imageSlots.length < 2 && '💡 Add more images for better extraction accuracy'}
                  {imageSlots.length >= 2 && `✓ ${imageSlots.length} images ready — system will cross-reference all angles`}
                </span>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div style={{ background: 'var(--status-fail-bg)', border: '1px solid var(--status-fail-border)', color: 'var(--status-fail)', padding: '12px 16px', borderRadius: 'var(--radius-md)', marginTop: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}
        </div>
      )}

      {/* ── Processing Animation Screen ── */}
      {isProcessing && (
        <div className="card" style={{ padding: '40px' }}>
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <div className="spinner" style={{ width: '40px', height: '40px', margin: '0 auto 16px' }} />
            <h3 style={{ fontSize: '20px', fontWeight: 700 }}>
              Analyzing {imageSlots.length > 0 ? imageSlots.length + ' Package Image' + (imageSlots.length > 1 ? 's' : '') : 'Demo Data'}...
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              OCR · Field Extraction · Cross-Image Fusion · Legal Rule Engine
            </p>
          </div>

          <div style={{ maxWidth: '560px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {processingSteps.map((step, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  fontSize: '12px',
                  fontWeight: 700,
                  background: step.status === 'done' ? 'var(--status-pass)' :
                    step.status === 'active' ? 'var(--accent-primary)' :
                      step.status === 'failed' ? 'var(--status-fail)' :
                        'var(--bg-elevated)',
                  color: step.status === 'waiting' ? 'var(--text-muted)' : '#fff',
                  border: step.status === 'active' ? '2px solid rgba(99,102,241,0.5)' : '2px solid transparent',
                  boxShadow: step.status === 'active' ? '0 0 12px rgba(99,102,241,0.4)' : 'none',
                  transition: 'all 0.3s',
                }}>
                  {step.status === 'done' ? '✓' :
                    step.status === 'active' ? <Loader size={12} className="spinning" style={{ animation: 'spin 1s linear infinite' }} /> :
                      step.status === 'failed' ? '✗' :
                        idx + 1}
                </div>
                <span style={{
                  fontSize: '14px',
                  fontWeight: step.status === 'active' ? 600 : 400,
                  color: step.status === 'done' ? 'var(--status-pass)' :
                    step.status === 'active' ? 'var(--text-primary)' :
                      'var(--text-muted)',
                  transition: 'color 0.3s',
                }}>
                  {step.label}
                </span>
                {step.status === 'active' && (
                  <span style={{ fontSize: '11px', color: 'var(--accent-primary)', fontWeight: 600 }}>
                    Processing...
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── INSPECTION RESULT SCREEN ── */}
      {result && (
        <div>
          {/* Multi-image summary bar */}
          {result.total_images > 1 && (
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-primary)',
              borderRadius: 'var(--radius-lg)',
              padding: '16px 20px',
              marginBottom: '20px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
                <Package size={16} color="var(--accent-primary)" />
                <span style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Package Analysis — {result.total_images} Images Analyzed
                </span>
                {result.has_conflicts && (
                  <span style={{
                    fontSize: '11px',
                    background: 'rgba(245, 158, 11, 0.15)',
                    color: 'var(--status-review)',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontWeight: 600,
                  }}>
                    ⚠ Conflicts Detected — Human Review Required
                  </span>
                )}
              </div>

              {/* Per-image status row */}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                {result.per_image_results?.map((imgRes: any) => {
                  const q = imgRes.quality?.overall_score ?? 0;
                  return (
                    <div
                      key={imgRes.image_index}
                      style={{
                        padding: '8px 14px',
                        background: 'var(--bg-elevated)',
                        borderRadius: 'var(--radius-md)',
                        border: `1px solid ${imgRes.success ? 'var(--border-primary)' : 'var(--status-fail-border)'}`,
                        fontSize: '12px',
                        minWidth: '120px',
                      }}
                    >
                      <div style={{ fontWeight: 700, marginBottom: '4px' }}>
                        Image {imgRes.image_number}
                      </div>
                      {imgRes.success ? (
                        <>
                          <div style={{ color: qualityColorForScore(q) }}>
                            {qualityIconForScore(q)} {imgRes.quality?.quality_label || 'OK'}
                          </div>
                          <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>
                            {imgRes.fields_found?.length || 0} fields found
                          </div>
                          {imgRes.quality?.issues?.length > 0 && (
                            <div style={{ color: 'var(--status-review)', fontSize: '10px', marginTop: '4px' }}>
                              ⚠ {imgRes.quality.issues[0]}
                            </div>
                          )}
                        </>
                      ) : (
                        <div style={{ color: 'var(--status-fail)' }}>
                          ✗ OCR Failed
                          {imgRes.error && <div style={{ fontSize: '10px', marginTop: '2px' }}>{imgRes.error.slice(0, 40)}</div>}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="inspection-layout">
            {/* ── LEFT PANEL: Visual Evidence ── */}
            <div className="image-panel">
              <div className="card" style={{ padding: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Visual Package Evidence
                  </span>
                  {result.has_annotated_image && (
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button className={`btn btn-sm ${showAnnotatedImage ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setShowAnnotatedImage(true)}>
                        <ShieldCheck size={12} /> Legal Evidence
                      </button>
                      <button className={`btn btn-sm ${!showAnnotatedImage ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setShowAnnotatedImage(false)}>
                        <Eye size={12} /> Original
                      </button>
                    </div>
                  )}
                </div>

                {result.is_demo ? (
                  <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', padding: '24px', textAlign: 'center', minHeight: '260px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: '1px dashed var(--border-primary)' }}>
                    <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(99, 102, 241, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '16px', color: 'var(--accent-primary)' }}>
                      <Layers size={32} />
                    </div>
                    <h4 style={{ fontSize: '16px', fontWeight: 600 }}>Demo Dataset Mode</h4>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '340px', marginTop: '6px' }}>
                      {result.demo_description || 'Verified sample with deterministic Legal Metrology rules.'}
                    </p>
                    <div style={{ marginTop: '20px', padding: '8px 16px', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: 'var(--radius-md)', fontSize: '12px', color: 'var(--status-review)' }}>
                      Verified Sample: <strong>{result.product_name}</strong>
                    </div>
                  </div>
                ) : (
                  <div className="image-container" style={{ position: 'relative', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                    <img
                      src={getImageUrl(result.id, showAnnotatedImage && result.has_annotated_image)}
                      alt="Inspection Evidence"
                      style={{ width: '100%', height: 'auto', display: 'block' }}
                    />
                  </div>
                )}

                {/* Image Quality Assessment */}
                {result.image_quality && (
                  <div style={{ marginTop: '16px', padding: '12px 14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', fontSize: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ color: 'var(--text-muted)' }}>
                        {result.total_images > 1 ? `Avg. Image Quality (${result.total_images} images):` : 'Image Quality:'}
                      </span>
                      <strong style={{ color: result.image_quality.overall_score >= 0.7 ? 'var(--status-pass)' : 'var(--status-review)' }}>
                        {(result.image_quality.overall_score * 100).toFixed(0)}% — {result.image_quality.quality_label || 'OK'}
                      </strong>
                    </div>
                    {result.image_quality.issues?.length > 0 && (
                      <div style={{ color: 'var(--status-review)', marginTop: '4px' }}>
                        ⚠️ {result.image_quality.issues.slice(0, 2).join('; ')}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* ── RIGHT PANEL: Compliance Assessment ── */}
            <div className="assessment-panel">
              {/* Overall verdict card */}
              <div className="card" style={{
                borderLeft: `6px solid ${result.overall_status === 'COMPLIANT' ? 'var(--status-pass)' :
                  result.overall_status === 'NON_COMPLIANT' ? 'var(--status-fail)' : 'var(--status-review)'}`
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
                  <div>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '1px' }}>Inspection Verdict</div>
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
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '1px' }}>Compliance Score</div>
                    <div style={{ fontSize: '28px', fontWeight: 800, color: result.compliance_score >= 80 ? 'var(--status-pass)' : result.compliance_score >= 50 ? 'var(--status-review)' : 'var(--status-fail)' }}>
                      {result.compliance_score}<span style={{ fontSize: '16px', color: 'var(--text-muted)' }}>/100</span>
                    </div>
                  </div>
                </div>
                {result.total_images > 1 && (
                  <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-primary)', fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                    <span>📸 {result.total_images} images analyzed</span>
                    <span>✓ {result.passed} checks passed</span>
                    {result.failed > 0 && <span style={{ color: 'var(--status-fail)' }}>✗ {result.failed} failed</span>}
                    {result.needs_review > 0 && <span style={{ color: 'var(--status-review)' }}>⚠ {result.needs_review} need review</span>}
                    {result.has_conflicts && (
                      <span style={{ color: 'var(--status-review)', fontWeight: 600 }}>
                        ⚡ Conflicts: {result.conflict_fields?.join(', ')}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Extracted Declarations Table */}
              <div className="card">
                <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <CheckCircle2 size={16} color="var(--accent-primary)" />
                  Extracted Declarations (Rule 6 Mapping)
                </h3>

                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Declaration</th>
                      <th>Detected Value</th>
                      <th>Confidence</th>
                      {result.total_images > 1 && <th>Source</th>}
                      <th>Status</th>
                      <th>Review</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.fields?.map((f: any, idx: number) => {
                      const isMissing = !f.detected_value;
                      const confPercent = Math.round((f.confidence || 0) * 100);
                      const hasConflict = f.conflict_detected;

                      return (
                        <tr
                          key={idx}
                          style={{ background: activeHighlightField === f.field_name ? 'var(--bg-elevated)' : undefined, cursor: 'pointer' }}
                          onClick={() => setActiveHighlightField(f.field_name)}
                        >
                          <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                            {f.field_label}
                          </td>
                          <td style={{ maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {hasConflict ? (
                              <div>
                                <div style={{ color: 'var(--status-review)', fontWeight: 600, fontSize: '11px', marginBottom: '2px' }}>
                                  ⚡ CONFLICT
                                </div>
                                <div style={{ fontSize: '12px' }}>
                                  {f.all_image_candidates?.slice(0, 2).map((c: any, ci: number) => (
                                    <div key={ci} style={{ color: 'var(--text-secondary)' }}>
                                      Img{c.source_image_number}: {c.value}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ) : isMissing ? (
                              <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Not detected</span>
                            ) : (
                              <span title={f.detected_value}>{f.detected_value}</span>
                            )}
                          </td>
                          <td>
                            {confPercent > 0 ? (
                              <div>
                                <span className="confidence-bar">
                                  <span className={`confidence-bar-fill ${confPercent >= 70 ? 'high' : confPercent >= 50 ? 'medium' : 'low'}`} style={{ width: `${confPercent}%` }} />
                                </span>
                                <span style={{ fontSize: '11px', fontWeight: 600 }}>{confPercent}%</span>
                              </div>
                            ) : (
                              <span style={{ color: 'var(--text-muted)' }}>—</span>
                            )}
                          </td>
                          {result.total_images > 1 && (
                            <td>
                              {f.source_image_number != null ? (
                                <span style={{ fontSize: '11px', background: 'var(--bg-elevated)', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                                  Img {f.source_image_number}
                                </span>
                              ) : (
                                <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>—</span>
                              )}
                            </td>
                          )}
                          <td>
                            <span className={`status-badge ${f.status?.toLowerCase().replace('_', '-') || 'pending'}`} style={{ fontSize: '10px', padding: '2px 8px' }}>
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
                              onClick={(e) => { e.stopPropagation(); handleOpenReview(f); }}
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

              {/* ── Conflict Detected Cards ── */}
              {result.has_conflicts && result.fields?.some((f: any) => f.conflict_detected) && (
                <div className="card" style={{ borderLeft: '4px solid var(--status-review)' }}>
                  <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-review)' }}>
                    <AlertTriangle size={16} />
                    Conflicting Declarations Detected
                  </h3>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                    Different values were found for the same field across images. Officer must manually resolve these.
                  </p>
                  {result.fields?.filter((f: any) => f.conflict_detected).map((f: any, idx: number) => (
                    <div key={idx} style={{
                      background: 'rgba(245, 158, 11, 0.05)',
                      border: '1px solid rgba(245, 158, 11, 0.3)',
                      borderRadius: 'var(--radius-md)',
                      padding: '14px',
                      marginBottom: '10px',
                    }}>
                      <div style={{ fontWeight: 700, marginBottom: '8px', color: 'var(--status-review)' }}>
                        ⚡ {f.field_label} — CONFLICT DETECTED
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {f.all_image_candidates?.map((c: any, ci: number) => (
                          <div key={ci} style={{ display: 'flex', gap: '12px', fontSize: '13px', alignItems: 'center' }}>
                            <span style={{ background: 'var(--bg-elevated)', padding: '2px 7px', borderRadius: '4px', fontWeight: 600, fontSize: '11px', flexShrink: 0 }}>
                              Image {c.source_image_number}
                            </span>
                            <span style={{ fontWeight: 600 }}>{c.value}</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                              {Math.round((c.confidence || 0) * 100)}% confidence
                            </span>
                          </div>
                        ))}
                      </div>
                      <div style={{ marginTop: '10px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                        Status: <strong style={{ color: 'var(--status-review)' }}>NEEDS REVIEW</strong> — Please visually verify the physical package.
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Violations */}
              {result.violations?.length > 0 && (
                <div className="card">
                  <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-fail)' }}>
                    <AlertTriangle size={16} />
                    Legal Violations & Non-Compliance ({result.violations.length})
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {result.violations.map((v: Violation, idx: number) => (
                      <div key={idx} className={`violation-card ${v.severity}`}>
                        <div className="violation-header">
                          <div className="violation-title">
                            <span>❌ {v.title}</span>
                            <span className="rule-id">{v.rule_id}</span>
                          </div>
                          <span className={`severity-badge ${v.severity}`}>{v.severity} Severity</span>
                        </div>
                        <div className="violation-detail">
                          <dt>Detected:</dt>
                          <dd>{v.detected_value || 'Missing from package declaration'}</dd>
                          <dt>Requirement:</dt>
                          <dd>{v.expected_requirement}</dd>
                          <dt>Explanation:</dt>
                          <dd style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{v.reason}</dd>
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
          
          {/* ── Developer Debug Panel ── */}
          {showDebug && (
            <div className="card" style={{ marginTop: '24px', border: '2px dashed var(--accent-secondary)' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-secondary)' }}>
                <Info size={16} />
                Developer Debug Mode: Extraction Pipeline Trace
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
                {result.fields?.map((f: any, idx: number) => (
                  <div key={idx} style={{ background: 'var(--bg-elevated)', padding: '12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-primary)' }}>
                    <div style={{ fontWeight: 700, fontSize: '13px', marginBottom: '8px', color: 'var(--text-primary)' }}>
                      {f.field_name.toUpperCase()} 
                      <span style={{ fontWeight: 400, color: 'var(--text-muted)', fontSize: '11px', marginLeft: '6px' }}>({f.extraction_method})</span>
                    </div>
                    {f.candidates?.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {f.candidates.map((c: any, ci: number) => (
                          <div key={ci} style={{ fontSize: '11px', padding: '6px', background: ci === 0 ? 'rgba(40,200,40,0.1)' : 'var(--bg-card)', border: ci === 0 ? '1px solid rgba(40,200,40,0.3)' : '1px solid var(--border-primary)', borderRadius: '4px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                              <strong style={{ fontSize: '12px' }}>{c.value}</strong>
                              <span style={{ color: 'var(--text-muted)' }}>Score: {c.score?.toFixed(2)}</span>
                            </div>
                            <div style={{ color: 'var(--text-secondary)' }}>Reason: {c.reason || 'Keyword match'}</div>
                            <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>Confidence: {Math.round((c.confidence || 0)*100)}%</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic' }}>No candidates found during extraction.</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Officer Review Modal ── */}
      {reviewingField && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999, padding: '20px' }}>
          <div className="card" style={{ maxWidth: '500px', width: '100%', padding: '24px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '4px' }}>
              Officer Review: {reviewingField.field_label}
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Adjust extracted declaration or manually override verification status.
            </p>

            {/* Show conflict context if available */}
            {(reviewingField as any).conflict_detected && (reviewingField as any).all_image_candidates?.length > 0 && (
              <div style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 'var(--radius-md)', padding: '12px', marginBottom: '16px', fontSize: '12px' }}>
                <div style={{ fontWeight: 700, color: 'var(--status-review)', marginBottom: '6px' }}>⚡ Conflict — Values found across images:</div>
                {(reviewingField as any).all_image_candidates.map((c: any, i: number) => (
                  <div key={i}>Image {c.source_image_number}: <strong>{c.value}</strong> ({Math.round(c.confidence * 100)}%)</div>
                ))}
              </div>
            )}

            <div style={{ marginBottom: '14px' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                Extracted Value (OCR):
              </label>
              <input type="text" className="input-field" value={editedValue} onChange={(e) => setEditedValue(e.target.value)} placeholder="Enter corrected value..." />
            </div>
            <div style={{ marginBottom: '20px' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                Officer Notes / Justification:
              </label>
              <input type="text" className="input-field" value={reviewNotes} onChange={(e) => setReviewNotes(e.target.value)} placeholder="e.g., Verified visually on physical label..." />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setReviewingField(null)} disabled={isSubmittingReview}>Cancel</button>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn btn-danger btn-sm" onClick={() => handleSaveReview('REJECT')} disabled={isSubmittingReview}>Mark Non-Compliant</button>
                <button className="btn btn-success btn-sm" onClick={() => handleSaveReview('APPROVE')} disabled={isSubmittingReview}>Approve as Compliant</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
