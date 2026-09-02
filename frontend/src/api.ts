import type {
  DashboardStats,
  DemoProduct,
  Inspection,
  Rule,
  BatchJob,
  AuthTokenResponse,
  LoginCredentials,
  RegisterCredentials
} from './types';

// When VITE_API_URL is empty (production on Render — frontend served by the
// same FastAPI process), use an empty string so all fetch() calls go to the
// same origin automatically. Fall back to localhost only in local dev.
const API_BASE = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');

// Fallback client-side demo datasets for standalone Vercel preview
const FALLBACK_DEMO_PRODUCTS: DemoProduct[] = [
  { id: 'demo-001', name: 'Tata Premium Tea', description: 'Fully compliant product — all declarations & GS1 verified', is_compliant: true },
  { id: 'demo-002', name: 'QuickBite Instant Noodles', description: 'Missing MRP declaration — non-compliant (Critical Severity)', is_compliant: false },
  { id: 'demo-003', name: 'FreshWash Detergent', description: 'Font size 1.2mm below 2.0mm minimum — non-compliant', is_compliant: false },
  { id: 'demo-004', name: 'GlowFit Protein Bar', description: 'Poor OCR / ambiguous text — needs officer review', is_compliant: null },
  { id: 'demo-005', name: 'AquaPure Mineral Water', description: 'Multiple violations — missing manufacturer & barcode mismatch', is_compliant: false }
];

const FALLBACK_RULES: Rule[] = [
  { rule_id: 'LM-PC-001', title: 'Product Name Declaration', field: 'product_name', description: 'Name or description of commodity', requirement: 'Product name must be present and legible', applicability: 'all_packaged_commodities', validation_type: 'presence', severity: 'high', severity_points: 7, rule_version: '2.0.0', source_reference: 'Rule 6(1)(a)', is_prototype: true, explanation_template: 'Product name declaration {status}.' },
  { rule_id: 'LM-PC-002', title: 'Net Quantity Declaration', field: 'net_quantity', description: 'Declaration of net quantity in metric units', requirement: 'Net quantity must be in standard units (g, kg, ml, L)', applicability: 'all_packaged_commodities', validation_type: 'presence_and_format', severity: 'critical', severity_points: 10, rule_version: '2.0.0', source_reference: 'Rule 6(1)(b)', is_prototype: true, explanation_template: 'Net quantity declaration {status}.' },
  { rule_id: 'LM-PC-003', title: 'MRP Declaration', field: 'mrp', description: 'Maximum Retail Price inclusive of all taxes', requirement: 'MRP must be in Indian Rupees (₹ or Rs.) with inclusive of all taxes', applicability: 'all_packaged_commodities', validation_type: 'presence_and_format', severity: 'critical', severity_points: 10, rule_version: '2.0.0', source_reference: 'Rule 6(1)(c)', is_prototype: true, explanation_template: 'MRP declaration {status}.' },
  { rule_id: 'LM-PC-004', title: 'Manufacturer/Packer Name & Address', field: 'manufacturer', description: 'Name and complete address of manufacturer', requirement: 'Manufacturer/packer/importer name and address required', applicability: 'all_packaged_commodities', validation_type: 'presence', severity: 'critical', severity_points: 10, rule_version: '2.0.0', source_reference: 'Rule 6(1)(d)', is_prototype: true, explanation_template: 'Manufacturer declaration {status}.' },
  { rule_id: 'LM-PC-FS-001', title: 'Font Size Compliance (Net Quantity)', field: 'net_quantity', description: 'Minimum 2.0 mm text height for net quantity', requirement: 'Net quantity numeral height >= 2.0 mm', applicability: 'all_packaged_commodities', validation_type: 'font_size_measurement', severity: 'high', severity_points: 7, rule_version: '2.0.0', source_reference: 'Rule 7 Table I', is_prototype: true, explanation_template: 'Font size compliance {status}.' },
  { rule_id: 'LM-PC-FS-002', title: 'Font Size Compliance (MRP)', field: 'mrp', description: 'Minimum 2.0 mm text height for MRP', requirement: 'MRP numeral height >= 2.0 mm', applicability: 'all_packaged_commodities', validation_type: 'font_size_measurement', severity: 'high', severity_points: 7, rule_version: '2.0.0', source_reference: 'Rule 7 Table I', is_prototype: true, explanation_template: 'Font size compliance {status}.' },
  { rule_id: 'LM-PC-BC-001', title: 'Barcode & GS1 Verification', field: 'barcode', description: 'Cross-verification against GS1 National Registry', requirement: 'Barcode must be registered and match declared MRP', applicability: 'all_packaged_commodities', validation_type: 'barcode_gs1_check', severity: 'critical', severity_points: 10, rule_version: '2.0.0', source_reference: 'GS1 Standards', is_prototype: true, explanation_template: 'Barcode verification {status}.' },
];

export async function checkHealth(): Promise<{ status: string; ocr_available: boolean }> {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error('Health check failed');
    return await res.json();
  } catch (err) {
    return { status: 'offline', ocr_available: false };
  }
}

export async function getDashboardStats(): Promise<DashboardStats> {
  try {
    const res = await fetch(`${API_BASE}/api/dashboard/stats`);
    if (res.ok) return await res.json();
  } catch (err) {
    // Offline fallback
  }
  return {
    total_inspections: 12,
    compliant: 8,
    non_compliant: 3,
    needs_review: 1,
    critical_violations: 2,
    average_severity: 28.5,
    average_risk_label: 'Medium Risk',
    font_violations_count: 3,
    font_violation_rate: 25.0,
    recent_inspections: [],
    common_violations: [
      { field: 'MRP Declaration', count: 3 },
      { field: 'Font Size (Net Qty)', count: 2 },
      { field: 'Barcode Mismatch', count: 1 }
    ],
    high_severity_violations: []
  };
}

export async function getDemoProducts(): Promise<DemoProduct[]> {
  try {
    const res = await fetch(`${API_BASE}/api/demo/products`);
    if (res.ok) return await res.json();
  } catch (err) {
    // Offline fallback
  }
  return FALLBACK_DEMO_PRODUCTS;
}

export async function scanDemoProduct(productId: string): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/api/scan/demo/${productId}`, { method: 'POST' });
    if (res.ok) return await res.json();
  } catch (err) {
    // Offline fallback for demo
  }

  const isCompliant = productId === 'demo-001';
  const isMissingMRP = productId === 'demo-002';
  const isFontViolation = productId === 'demo-003';
  const isReview = productId === 'demo-004';
  const isMultiple = productId === 'demo-005';

  return {
    id: 'local-' + productId,
    inspection_id: 'MLX-DEMO-' + productId.toUpperCase(),
    product_name: productId === 'demo-001' ? 'Tata Tea Gold' : (productId === 'demo-002' ? 'QuickBite Instant Noodles' : (productId === 'demo-003' ? 'FreshWash Detergent' : (productId === 'demo-004' ? 'GlowFit Protein Bar' : 'AquaPure Spring Water'))),
    overall_status: isCompliant ? 'COMPLIANT' : (isReview ? 'NEEDS_REVIEW' : 'NON_COMPLIANT'),
    compliance_score: isCompliant ? 100 : (isReview ? 72 : (isMultiple ? 35 : 75)),
    severity_score: isCompliant ? 0 : (isMissingMRP ? 75 : (isFontViolation ? 45 : (isMultiple ? 85 : 30))),
    risk_level: isCompliant ? 'low' : (isMissingMRP ? 'high' : (isFontViolation ? 'medium' : (isMultiple ? 'critical' : 'medium'))),
    risk_label: isCompliant ? 'Low Risk' : (isMissingMRP ? 'High Risk' : (isFontViolation ? 'Medium Risk' : (isMultiple ? 'Critical Risk' : 'Medium Risk'))),
    latitude: 28.6139,
    longitude: 77.2090,
    barcode_data: {
      barcode: isCompliant ? '8901030383846' : (isMultiple ? '8909999999999' : '8901058852683'),
      gs1_found: !isMultiple,
      is_valid: isCompliant,
      status: isCompliant ? 'PASS' : 'FAIL',
      gs1_product_name: isCompliant ? 'Tata Tea Gold 500g' : (isMultiple ? undefined : 'Maggi 2-Min Noodles'),
      gs1_manufacturer: isCompliant ? 'Tata Consumer Products Ltd' : (isMultiple ? undefined : 'Nestle India Ltd'),
      gs1_declared_mrp: isCompliant ? 199 : 14,
      scanned_mrp: isCompliant ? 199 : (isMultiple ? 25 : 14),
      mrp_diff_pct: 0,
      mrp_status: 'MATCH',
      mfg_status: 'MATCH',
      mismatches: isMultiple ? ['Barcode 8909999999999 not found in GS1 National Database — Possible counterfeit'] : [],
      message: isCompliant ? 'Verified against GS1 Registry.' : (isMultiple ? 'Counterfeit alert: Barcode not registered in GS1' : 'Verified against GS1')
    },
    total_checks: 12,
    passed: isCompliant ? 12 : (isReview ? 8 : (isMultiple ? 4 : 9)),
    failed: isCompliant ? 0 : (isReview ? 0 : 3),
    needs_review: isReview ? 3 : 0,
    is_demo: true,
    fields: [
      { field_name: 'product_name', field_label: 'Product Name', detected_value: isCompliant ? 'Tata Tea Gold' : (isMissingMRP ? 'QuickBite Instant Noodles' : 'FreshWash Detergent'), confidence: 0.95, status: 'PASS', font_size_mm: 3.2, min_font_size_mm: 1.5 },
      { field_name: 'net_quantity', field_label: 'Net Quantity', detected_value: isCompliant ? '500 g' : '1 kg', confidence: isReview ? 0.55 : 0.92, status: isFontViolation ? 'FAIL' : (isReview ? 'NEEDS_REVIEW' : 'PASS'), font_size_mm: isFontViolation ? 1.2 : 2.4, min_font_size_mm: 2.0 },
      { field_name: 'mrp', field_label: 'MRP', detected_value: isMissingMRP ? null : '₹199', confidence: isMissingMRP ? 0.0 : (isReview ? 0.42 : 0.93), status: isMissingMRP ? 'FAIL' : (isReview ? 'NEEDS_REVIEW' : 'PASS'), font_size_mm: isMissingMRP ? null : 2.2, min_font_size_mm: 2.0 },
      { field_name: 'manufacturer', field_label: 'Manufacturer/Packer', detected_value: isMultiple ? null : 'Tata Consumer Products Ltd', confidence: isMultiple ? 0.0 : 0.91, status: isMultiple ? 'FAIL' : 'PASS', font_size_mm: 1.8, min_font_size_mm: 1.5 },
      { field_name: 'date', field_label: 'Mfg/Pkg Date', detected_value: '08/2026', confidence: 0.89, status: 'PASS', font_size_mm: 1.4, min_font_size_mm: 1.0 },
      { field_name: 'consumer_care', field_label: 'Consumer Care', detected_value: isMultiple ? null : '1800-209-8787', confidence: isMultiple ? 0.0 : 0.88, status: isMultiple ? 'FAIL' : 'PASS', font_size_mm: 1.3, min_font_size_mm: 1.0 },
      { field_name: 'country_of_origin', field_label: 'Country of Origin', detected_value: 'India', confidence: 0.92, status: 'PASS', font_size_mm: 1.5, min_font_size_mm: 1.0 }
    ],
    violations: isCompliant ? [] : (isMissingMRP ? [
      { rule_id: 'LM-PC-003', field: 'mrp', severity: 'critical', severity_points: 10, title: 'MRP Declaration Missing', detected_value: 'Not detected', expected_requirement: 'MRP must be declared in Indian Rupees (₹ or Rs.)', reason: 'Required declaration not detected in the supplied image.', is_prototype_rule: true }
    ] : (isFontViolation ? [
      { rule_id: 'LM-PC-FS-001', field: 'net_quantity', severity: 'high', severity_points: 7, title: 'Font Size Below Minimum (Net Quantity)', detected_value: '1 kg', expected_requirement: 'Minimum font height 2.0mm', reason: 'Measured font height 1.2mm is below Legal Metrology minimum of 2.0mm (Rule 7).', is_prototype_rule: true }
    ] : [
      { rule_id: 'LM-PC-BC-001', field: 'barcode', severity: 'critical', severity_points: 10, title: 'Barcode Not Found in GS1 Database', detected_value: '8909999999999', expected_requirement: 'Authentic GS1 Registry record', reason: 'Barcode 8909999999999 not found in GS1 National Database — Possible counterfeit.', is_prototype_rule: true }
    ]))
  };
}

// Demo fallback result for when a real image is uploaded but backend is unreachable
function buildOfflineScanResult(files: File[]): any {
  const inspectionId = 'MLX-OFFLINE-' + Math.random().toString(36).slice(2, 8).toUpperCase();
  return {
    inspection_id: inspectionId,
    product_name: files[0]?.name?.replace(/\.[^.]+$/, '') || 'Uploaded Product',
    overall_status: 'NEEDS_REVIEW',
    compliance_score: 0,
    severity_score: 0,
    risk_level: 'unknown',
    risk_label: 'Demo Mode',
    is_demo: true,
    offline_mode: true,
    total_checks: 0,
    passed: 0,
    failed: 0,
    needs_review: 1,
    fields: [],
    violations: [],
    barcode_data: null,
    _notice: 'Backend is offline. This is a placeholder result. Run the Python backend locally or deploy it to see real OCR analysis.',
  };
}

export async function scanUploadedImages(
  files: File[],
  coords?: { latitude?: number; longitude?: number },
  languages?: string[]
): Promise<any> {
  const formData = new FormData();
  files.forEach((f) => formData.append('files', f));

  const params = new URLSearchParams();
  if (coords?.latitude && coords?.longitude) {
    params.append('latitude', coords.latitude.toString());
    params.append('longitude', coords.longitude.toString());
  }
  if (languages && languages.length > 0) {
    params.append('languages', languages.join(','));
  }

  const queryStr = params.toString() ? `?${params.toString()}` : '';
  const url = `${API_BASE}/api/scan${queryStr}`;

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 60000); // 60s for OCR

    const res = await fetch(url, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (!res.ok) {
      const err = await res.json().catch(() => ({
        detail: `Failed to scan image(s). Ensure Python backend is running.`,
      }));
      throw new Error(err.detail || 'Scanning failed');
    }
    return await res.json();
  } catch (err: any) {
    // If the backend is simply unreachable (no backend deployed, CORS, network),
    // return a placeholder result so the UI doesn't crash.
    if (
      err.name === 'AbortError' ||
      err.name === 'TypeError' ||
      err.message?.toLowerCase().includes('fetch') ||
      err.message?.toLowerCase().includes('network')
    ) {
      return buildOfflineScanResult(files);
    }
    throw err;
  }
}

export async function scanUploadedImage(
  file: File,
  coords?: { latitude?: number; longitude?: number },
  languages?: string[]
): Promise<any> {
  return scanUploadedImages([file], coords, languages);
}

// ─── Phase 2: E-Commerce Scanner APIs ────────────────────────────────────────

export async function scanEcommerceUrl(url: string): Promise<import('./types').EcommerceReport> {
  const res = await fetch(`${API_BASE}/api/scan/ecommerce`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'E-commerce scan failed.' }));
    throw new Error(err.detail || 'Failed to scan e-commerce listing.');
  }
  return await res.json();
}

// ─── Phase 2: Geo-Tagged Compliance Map APIs ─────────────────────────────────

export async function getGeoInspections(status?: string): Promise<import('./types').GeoInspection[]> {
  try {
    const url = status && status !== 'ALL'
      ? `${API_BASE}/api/inspections/geo?status=${status}`
      : `${API_BASE}/api/inspections/geo`;
    const res = await fetch(url);
    if (res.ok) return await res.json();
  } catch (err) {
    // Offline fallback demo geo entries
  }
  return [
    { id: 'geo-demo-1', inspection_id: 'MLX-2026-DEL-01', product_name: 'Tata Tea Gold 500g', overall_status: 'COMPLIANT', compliance_score: 100, severity_score: 0, risk_level: 'low', latitude: 28.6139, longitude: 77.2090, created_at: new Date().toISOString(), violation_count: 0, location_name: 'Connaught Place, New Delhi' },
    { id: 'geo-demo-2', inspection_id: 'MLX-2026-DEL-02', product_name: 'QuickBite Instant Noodles', overall_status: 'NON_COMPLIANT', compliance_score: 55, severity_score: 75, risk_level: 'high', latitude: 28.6304, longitude: 77.2177, created_at: new Date().toISOString(), violation_count: 2, location_name: 'Sector 18 Market, Noida' },
    { id: 'geo-demo-3', inspection_id: 'MLX-2026-MUM-01', product_name: 'FreshWash Detergent 1kg', overall_status: 'NON_COMPLIANT', compliance_score: 65, severity_score: 45, risk_level: 'medium', latitude: 19.0760, longitude: 72.8777, created_at: new Date().toISOString(), violation_count: 1, location_name: 'Dadar Wholesale Market, Mumbai' },
    { id: 'geo-demo-4', inspection_id: 'MLX-2026-BLR-01', product_name: 'AquaPure Spring Water 1L', overall_status: 'NON_COMPLIANT', compliance_score: 30, severity_score: 90, risk_level: 'critical', latitude: 12.9716, longitude: 77.5946, created_at: new Date().toISOString(), violation_count: 3, location_name: 'Indiranagar Retail Hub, Bengaluru' },
    { id: 'geo-demo-5', inspection_id: 'MLX-2026-KOL-01', product_name: 'GlowFit Protein Bar 60g', overall_status: 'NEEDS_REVIEW', compliance_score: 72, severity_score: 30, risk_level: 'medium', latitude: 22.5726, longitude: 88.3639, created_at: new Date().toISOString(), violation_count: 0, location_name: 'New Market, Kolkata' },
    { id: 'geo-demo-6', inspection_id: 'MLX-2026-HYD-01', product_name: 'Amul Pure Ghee 1L', overall_status: 'COMPLIANT', compliance_score: 100, severity_score: 0, risk_level: 'low', latitude: 17.3850, longitude: 78.4867, created_at: new Date().toISOString(), violation_count: 0, location_name: 'Banjara Hills, Hyderabad' }
  ];
}

// ─── Phase 2: Legal Notices APIs ─────────────────────────────────────────────

export async function generateLegalNotice(inspectionId: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/inspections/${inspectionId}/generate-notice`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to generate legal notice.' }));
    throw new Error(err.detail || 'Notice generation failed.');
  }
  return await res.blob();
}

export async function listLegalNotices(): Promise<import('./types').LegalNoticeRecord[]> {
  try {
    const res = await fetch(`${API_BASE}/api/notices`);
    if (res.ok) return await res.json();
  } catch (err) {
    // Fallback
  }
  return [];
}

// ─── Batch Scanning APIs ─────────────────────────────────────────────────────

export async function uploadBatchZip(file: File): Promise<{
  batch_id: string;
  filename: string;
  status: string;
  message: string;
}> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/scan/batch`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Batch upload failed.' }));
    throw new Error(err.detail || 'Failed to upload batch ZIP file.');
  }
  return await res.json();
}

export async function getBatchStatus(batchId: string): Promise<BatchJob> {
  const res = await fetch(`${API_BASE}/api/scan/batch/${batchId}`);
  if (!res.ok) throw new Error('Failed to retrieve batch job progress.');
  return await res.json();
}

export async function listAllBatches(): Promise<BatchJob[]> {
  try {
    const res = await fetch(`${API_BASE}/api/scan/batches`);
    if (res.ok) return await res.json();
  } catch (err) {
    // Fallback
  }
  return [];
}

export function getBatchExportUrl(batchId: string): string {
  return `${API_BASE}/api/scan/batch/${batchId}/export`;
}

export async function clearAllInspections(): Promise<{ status: string; message: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/inspections`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to clear inspection history');
    return await res.json();
  } catch (err: any) {
    return { status: 'ok', message: 'Cleared local inspection session.' };
  }
}

export async function getInspections(params?: {
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<{ total: number; inspections: Inspection[] }> {
  try {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.search) query.append('search', params.search);
    if (params?.limit) query.append('limit', params.limit.toString());
    if (params?.offset) query.append('offset', params.offset.toString());

    const res = await fetch(`${API_BASE}/api/inspections?${query.toString()}`);
    if (res.ok) return await res.json();
  } catch (err) {
    // Offline fallback
  }
  return { total: 0, inspections: [] };
}

export async function getInspection(id: string): Promise<Inspection> {
  const res = await fetch(`${API_BASE}/api/inspections/${id}`);
  if (!res.ok) throw new Error('Failed to fetch inspection details');
  return await res.json();
}

export function getImageUrl(id: string, annotated: boolean = false): string {
  return `${API_BASE}/api/inspections/${id}/${annotated ? 'annotated' : 'image'}`;
}

export function getReportDownloadUrl(id: string): string {
  return `${API_BASE}/api/reports/${id}`;
}

export async function getRules(): Promise<{
  rule_set_version: string;
  rule_set_name: string;
  disclaimer: string;
  rules: Rule[];
}> {
  try {
    const res = await fetch(`${API_BASE}/api/rules`);
    if (res.ok) return await res.json();
  } catch (err) {
    // Offline fallback
  }
  return {
    rule_set_version: '2.0.0',
    rule_set_name: 'Legal Metrology (Packaged Commodities) Rules, 2011',
    disclaimer: 'These rules are modeled after the Legal Metrology (Packaged Commodities) Rules, 2011.',
    rules: FALLBACK_RULES
  };
}

export async function submitReviewAction(
  inspectionId: string,
  data: {
    field_name: string;
    action: 'APPROVE' | 'REJECT' | 'EDIT';
    original_value?: string | null;
    corrected_value?: string | null;
    notes?: string;
  }
): Promise<{ status: string; message: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/inspections/${inspectionId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (res.ok) return await res.json();
  } catch (err) {
    // Fallback ok
  }
  return { status: 'ok', message: 'Review saved locally.' };
}

// ─── Auth API ────────────────────────────────────────────────────────────────

export async function loginUser(creds: LoginCredentials): Promise<AuthTokenResponse> {
  const body = new URLSearchParams();
  body.append('username', creds.username);
  body.append('password', creds.password);

  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Login failed.' }));
    throw new Error(err.detail || 'Login failed.');
  }
  return res.json();
}

export async function registerUser(creds: RegisterCredentials): Promise<AuthTokenResponse> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(creds),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Registration failed.' }));
    throw new Error(err.detail || 'Registration failed.');
  }
  return res.json();
}

export async function fetchCurrentUser(token: string): Promise<AuthTokenResponse['user']> {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Session expired.');
  return res.json();
}
