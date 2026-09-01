import React, { useRef, useState, useEffect } from 'react';
import { Camera, CameraOff, Loader, CheckCircle2, XCircle, AlertTriangle, RotateCcw } from 'lucide-react';
import { scanUploadedImages } from '../api';
import { useNavigate } from 'react-router-dom';

type CameraState = 'idle' | 'requesting' | 'active' | 'error' | 'capturing' | 'uploading';

export const LiveCameraScan: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const navigate = useNavigate();

  const [cameraState, setCameraState] = useState<CameraState>('idle');
  const [error, setError] = useState('');
  const [capturedImages, setCapturedImages] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  // Start camera on mount
  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, []);

  const startCamera = async () => {
    try {
      setCameraState('requesting');
      setError('');
      
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment', // Prefer back camera on mobile
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setCameraState('active');
    } catch (err: any) {
      console.error('Camera access error:', err);
      setError(err.message || 'Failed to access camera. Please grant camera permissions.');
      setCameraState('error');
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraState('idle');
  };

  const captureImage = () => {
    if (!videoRef.current || !canvasRef.current) return;

    setCameraState('capturing');
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw current video frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert to data URL
    const imageData = canvas.toDataURL('image/jpeg', 0.92);
    
    // Add to captured images (max 5)
    setCapturedImages((prev) => {
      const updated = [...prev, imageData];
      return updated.slice(-5); // Keep only last 5
    });

    setCameraState('active');
  };

  const removeImage = (index: number) => {
    setCapturedImages((prev) => prev.filter((_, i) => i !== index));
  };

  const clearAll = () => {
    setCapturedImages([]);
  };

  const submitScan = async () => {
    if (capturedImages.length === 0) {
      setError('Please capture at least one image.');
      return;
    }

    setIsProcessing(true);
    setError('');

    try {
      // Convert data URLs to File objects
      const files = await Promise.all(
        capturedImages.map(async (dataUrl, idx) => {
          const blob = await (await fetch(dataUrl)).blob();
          return new File([blob], `camera_capture_${idx}.jpg`, { type: 'image/jpeg' });
        })
      );

      // Submit to scan API
      const result = await scanUploadedImages(files);
      
      // Navigate to inspection detail
      navigate(`/inspections/${result.inspection_id}`);
    } catch (err: any) {
      console.error('Scan submission error:', err);
      setError(err.message || 'Failed to process images. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.titleRow}>
          <div style={styles.iconWrapper}>
            <Camera size={24} color="#fff" />
          </div>
          <div>
            <h1 style={styles.title}>Live Camera Scan</h1>
            <p style={styles.subtitle}>
              Capture 1-5 angles of the package for real-time compliance checking
            </p>
          </div>
        </div>

        {/* Status indicator */}
        <div style={styles.statusBadge}>
          {cameraState === 'active' && (
            <>
              <span style={styles.statusDotActive} />
              Camera Active
            </>
          )}
          {cameraState === 'requesting' && (
            <>
              <Loader size={12} style={styles.spin} />
              Requesting Access
            </>
          )}
          {cameraState === 'error' && (
            <>
              <CameraOff size={12} />
              Camera Error
            </>
          )}
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div style={styles.errorBanner}>
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div style={styles.content}>
        {/* Video preview */}
        <div style={styles.videoPanel}>
          <div style={styles.videoWrapper}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={styles.video}
            />
            <canvas ref={canvasRef} style={{ display: 'none' }} />
            
            {cameraState === 'error' && (
              <div style={styles.videoOverlay}>
                <CameraOff size={48} color="#64748b" />
                <p style={styles.overlayText}>Camera not available</p>
                <button style={styles.retryBtn} onClick={startCamera}>
                  <RotateCcw size={16} />
                  Retry
                </button>
              </div>
            )}
          </div>

          {/* Capture button */}
          <div style={styles.controls}>
            <button
              style={{
                ...styles.captureBtn,
                ...(cameraState !== 'active' ? styles.captureBtnDisabled : {}),
              }}
              onClick={captureImage}
              disabled={cameraState !== 'active' || capturedImages.length >= 5}
            >
              <Camera size={20} />
              {capturedImages.length >= 5 ? 'Max 5 Images' : 'Capture Image'}
            </button>

            <p style={styles.hint}>
              📸 {capturedImages.length}/5 images captured
              {capturedImages.length === 0 && ' • Capture front, back, MRP panel, and side views'}
            </p>
          </div>
        </div>

        {/* Captured images preview */}
        <div style={styles.previewPanel}>
          <div style={styles.previewHeader}>
            <h3 style={styles.previewTitle}>Captured Images</h3>
            {capturedImages.length > 0 && (
              <button style={styles.clearBtn} onClick={clearAll}>
                Clear All
              </button>
            )}
          </div>

          {capturedImages.length === 0 ? (
            <div style={styles.emptyState}>
              <Camera size={48} color="#334155" />
              <p style={styles.emptyText}>No images captured yet</p>
              <p style={styles.emptySubtext}>
                Use the camera to capture multiple angles of the package
              </p>
            </div>
          ) : (
            <div style={styles.previewGrid}>
              {capturedImages.map((img, idx) => (
                <div key={idx} style={styles.previewItem}>
                  <img src={img} alt={`Capture ${idx + 1}`} style={styles.previewImg} />
                  <button
                    style={styles.removeBtn}
                    onClick={() => removeImage(idx)}
                    aria-label={`Remove image ${idx + 1}`}
                  >
                    <XCircle size={18} />
                  </button>
                  <div style={styles.previewLabel}>#{idx + 1}</div>
                </div>
              ))}
            </div>
          )}

          {/* Submit button */}
          {capturedImages.length > 0 && (
            <button
              style={{
                ...styles.submitBtn,
                ...(isProcessing ? styles.submitBtnDisabled : {}),
              }}
              onClick={submitScan}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <>
                  <Loader size={18} style={styles.spin} />
                  Processing {capturedImages.length} image{capturedImages.length > 1 ? 's' : ''}...
                </>
              ) : (
                <>
                  <CheckCircle2 size={18} />
                  Scan {capturedImages.length} Image{capturedImages.length > 1 ? 's' : ''}
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// ─── Styles ──────────────────────────────────────────────────────────────────
const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '0',
    minHeight: '100vh',
  },
  header: {
    padding: '24px 32px',
    background: 'linear-gradient(135deg, rgba(99,102,241,0.08), rgba(6,182,212,0.08))',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '20px',
    flexWrap: 'wrap',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  iconWrapper: {
    width: '52px',
    height: '52px',
    borderRadius: '14px',
    background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  title: {
    fontSize: '24px',
    fontWeight: 800,
    color: '#f0f4ff',
    margin: 0,
    letterSpacing: '-0.5px',
  },
  subtitle: {
    fontSize: '14px',
    color: '#94a3b8',
    margin: '4px 0 0',
  },
  statusBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 14px',
    borderRadius: '8px',
    background: 'rgba(0,0,0,0.3)',
    border: '1px solid rgba(255,255,255,0.08)',
    fontSize: '13px',
    fontWeight: 500,
    color: '#e2e8f0',
  },
  statusDotActive: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: '#10b981',
    boxShadow: '0 0 8px rgba(16,185,129,0.6)',
    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
  },
  spin: {
    animation: 'spin 1s linear infinite',
  },
  errorBanner: {
    margin: '20px 32px',
    padding: '12px 16px',
    background: 'rgba(239,68,68,0.12)',
    border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: '10px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    color: '#ef4444',
    fontSize: '14px',
  },
  content: {
    display: 'grid',
    gridTemplateColumns: '1fr 400px',
    gap: '24px',
    padding: '24px 32px',
    minHeight: 'calc(100vh - 180px)',
  },
  videoPanel: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  videoWrapper: {
    position: 'relative',
    background: '#000',
    borderRadius: '16px',
    overflow: 'hidden',
    aspectRatio: '16 / 9',
    boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
  },
  video: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  videoOverlay: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    background: 'rgba(10,14,26,0.95)',
  },
  overlayText: {
    color: '#64748b',
    fontSize: '16px',
    fontWeight: 500,
  },
  retryBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 16px',
    background: '#6366f1',
    border: 'none',
    borderRadius: '8px',
    color: '#fff',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    fontFamily: 'inherit',
  },
  controls: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  captureBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    padding: '16px',
    background: 'linear-gradient(135deg, #6366f1, #818cf8)',
    border: 'none',
    borderRadius: '12px',
    color: '#fff',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'inherit',
    boxShadow: '0 4px 16px rgba(99,102,241,0.4)',
    transition: 'transform 150ms ease, box-shadow 150ms ease',
  },
  captureBtnDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  hint: {
    fontSize: '13px',
    color: '#64748b',
    textAlign: 'center',
    margin: 0,
  },
  previewPanel: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  previewHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  previewTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#f0f4ff',
    margin: 0,
  },
  clearBtn: {
    padding: '6px 12px',
    background: 'rgba(239,68,68,0.15)',
    border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: '6px',
    color: '#ef4444',
    fontSize: '12px',
    fontWeight: 500,
    cursor: 'pointer',
    fontFamily: 'inherit',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    background: 'rgba(0,0,0,0.2)',
    borderRadius: '12px',
    border: '1px dashed rgba(255,255,255,0.1)',
  },
  emptyText: {
    fontSize: '15px',
    fontWeight: 500,
    color: '#64748b',
    margin: '12px 0 4px',
  },
  emptySubtext: {
    fontSize: '13px',
    color: '#475569',
    textAlign: 'center',
    margin: 0,
  },
  previewGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '12px',
  },
  previewItem: {
    position: 'relative',
    aspectRatio: '4 / 3',
    background: '#000',
    borderRadius: '10px',
    overflow: 'hidden',
    border: '2px solid rgba(255,255,255,0.1)',
  },
  previewImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  removeBtn: {
    position: 'absolute',
    top: '6px',
    right: '6px',
    padding: '4px',
    background: 'rgba(239,68,68,0.9)',
    border: 'none',
    borderRadius: '6px',
    color: '#fff',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  previewLabel: {
    position: 'absolute',
    bottom: '6px',
    left: '6px',
    padding: '3px 8px',
    background: 'rgba(0,0,0,0.7)',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 600,
    color: '#fff',
  },
  submitBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    padding: '14px',
    background: 'linear-gradient(135deg, #10b981, #059669)',
    border: 'none',
    borderRadius: '10px',
    color: '#fff',
    fontSize: '15px',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'inherit',
    boxShadow: '0 4px 16px rgba(16,185,129,0.4)',
    marginTop: '8px',
  },
  submitBtnDisabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  },
};
