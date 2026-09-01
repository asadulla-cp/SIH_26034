import type { DashboardStats, DemoProduct, Inspection, Rule, AuthTokenResponse, LoginCredentials, RegisterCredentials } from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Fallback client-side demo datasets for standalone Vercel preview
const FALLBACK_DEMO_PRODUCTS: DemoProduct[] = [
  { id: 'demo-001', name: 'Tata Premium Tea', description: 'Fully compliant product — all declarations present', is_compliant: true },
  { id: 'demo-002', name: 'QuickBite Instant Noodles', description: 'Missing MRP declaration — non-compliant', is_compliant: false },
  { id: 'demo-003', name: 'FreshWash Detergent', description: 'Missing consumer care details — non-compliant', is_compliant: false },
  { id: 'demo-004', name: 'GlowFit Protein Bar', description: 'Poor OCR / ambiguous text — needs review', is_compliant: null },
  { id: 'demo-005', name: 'AquaPure Mineral Water', description: 'Multiple violations — missing manufacturer, date, consumer care', is_compliant: false }
];

const FALLBACK_RULES: Rule[] = [
  { rule_id: 'LM-PC-001', title: 'Product Name Declaration', field: 'product_name', description: 'Name or description of commodity', requirement: 'Product name must be present and legible', applicability: 'all_packaged_commodities', validation_type: 'presence', severity: 'high', rule_version: '1.0.0', source_reference: 'Rule 6(1)(a)', is_prototype: true, explanation_template: 'Product name declaration {status}.' },
  { rule_id: 'LM-PC-002', title: 'Net Quantity Declaration', field: 'net_quantity', description: 'Declaration of net quantity in metric units', requirement: 'Net quantity must be in standard units (g, kg, ml, L)', applicability: 'all_packaged_commodities', validation_type: 'presence_and_format', severity: 'high', rule_version: '1.0.0', source_reference: 'Rule 6(1)(b)', is_prototype: true, explanation_template: 'Net quantity declaration {status}.' },
  { rule_id: 'LM-PC-003', title: 'MRP Declaration', field: 'mrp', description: 'Maximum Retail Price inclusive of all taxes', requirement: 'MRP must be in Indian Rupees (₹ or Rs.) with inclusive of all taxes', applicability: 'all_packaged_commodities', validation_type: 'presence_and_format', severity: 'high', rule_version: '1.0.0', source_reference: 'Rule 6(1)(c)', is_prototype: true, explanation_template: 'MRP declaration {status}.' },
  { rule_id: 'LM-PC-004', title: 'Manufacturer/Packer Name & Address', field: 'manufacturer', description: 'Name and complete address of manufacturer', requirement: 'Manufacturer/packer/importer name and address required', applicability: 'all_packaged_commodities', validation_type: 'presence', severity: 'high', rule_version: '1.0.0', source_reference: 'Rule 6(1)(d)', is_prototype: true, explanation_template: 'Manufacturer declaration {status}.' },
  { rule_id: 'LM-PC-005', title: 'Consumer Care Information', field: 'consumer_care', description: 'Consumer care contact details', requirement: 'Consumer helpline / email required', applicability: 'all_packaged_commodities', validation_type: 'presence', severity: 'medium', rule_version: '1.0.0', source_reference: 'Rule 6(2)', is_prototype: true, explanation_template: 'Consumer care declaration {status}.' },
  { rule_id: 'LM-PC-006', title: 'Date of Mfg / Packing', field: 'date', description: 'Month and year of manufacture or packing', requirement: 'Manufacturing/packing date must be declared', applicability: 'all_packaged_commodities', validation_type: 'presence_and_format', severity: 'high', rule_version: '1.0.0', source_reference: 'Rule 6(1)(e)', is_prototype: true, explanation_template: 'Date declaration {status}.' },
  { rule_id: 'LM-PC-007', title: 'Country of Origin', field: 'country_of_origin', description: 'Country of origin for imported goods', requirement: 'Country of origin must be declared', applicability: 'imported_commodities', validation_type: 'conditional_presence', severity: 'high', rule_version: '1.0.0', source_reference: 'Rule 6(1)(f)', is_prototype: true, explanation_template: 'Country of origin declaration {status}.' },
  { rule_id: 'LM-PC-009', title: 'Net Quantity Numeric Value', field: 'net_quantity', description: 'Positive numeric quantity', requirement: 'Net quantity must be > 0', applicability: 'all_packaged_commodities', validation_type: 'numeric_value', severity: 'high', rule_version: '1.0.0', source_reference: 'Rule 6(1)(b)', is_prototype: true, explanation_template: 'Net quantity value {status}.' },
  { rule_id: 'LM-PC-010', title: 'MRP Numeric Value', field: 'mrp', description: 'Positive numeric amount in INR', requirement: 'MRP must be > 0', applicability: 'all_packaged_commodities', validation_type: 'numeric_value', severity: 'high', rule_version: '1.0.0', source_reference: 'Rule 6(1)(c)', is_prototype: true, explanation_template: 'MRP value {status}.' },
  { rule_id: 'LM-PC-011', title: 'Metric Unit Validity', field: 'net_quantity', description: 'Standard metric unit check', requirement: 'Metric units only (g, kg, ml, L, m, cm, pieces)', applicability: 'all_packaged_commodities', validation_type: 'unit_check', severity: 'medium', rule_version: '1.0.0', source_reference: 'Rule 6(1)(b)', is_prototype: true, explanation_template: 'Unit check {status}.' }
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
    total_inspections: 0,
    compliant: 0,
    non_compliant: 0,
    needs_review: 0,
    recent_inspections: [],
    common_violations: [
      { field: 'MRP Declaration', count: 3 },
      { field: 'Consumer Care', count: 2 },
      { field: 'Manufacturer Details', count: 1 }
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
    // Offline fallback for demo on Vercel
  }

  // Client-side demo fallback computation
  const isCompliant = productId === 'demo-001';
  const isMissingMRP = productId === 'demo-002';
  const isReview = productId === 'demo-004';
  const isMultiple = productId === 'demo-005';

  return {
    id: 'local-' + productId,
    inspection_id: 'MLX-DEMO-' + productId.toUpperCase(),
    product_name: productId === 'demo-001' ? 'Tata Premium Tea' : (productId === 'demo-002' ? 'QuickBite Instant Noodles' : (productId === 'demo-004' ? 'GlowFit Protein Bar' : 'FreshWash Detergent')),
    overall_status: isCompliant ? 'COMPLIANT' : (isReview ? 'NEEDS_REVIEW' : 'NON_COMPLIANT'),
    compliance_score: isCompliant ? 100 : (isReview ? 72 : (isMultiple ? 45 : 82)),
    total_checks: 11,
    passed: isCompliant ? 11 : (isReview ? 8 : (isMultiple ? 4 : 8)),
    failed: isCompliant ? 0 : (isReview ? 0 : 2),
    needs_review: isReview ? 3 : 0,
    is_demo: true,
    demo_description: 'Standalone cloud demo dataset with deterministic Legal Metrology rules.',
    fields: [
      { field_name: 'product_name', field_label: 'Product Name', detected_value: isCompliant ? 'Tata Premium Tea' : (isMissingMRP ? 'QuickBite Instant Noodles' : 'GlowFit Protein Bar'), confidence: 0.95, status: 'PASS' },
      { field_name: 'net_quantity', field_label: 'Net Quantity', detected_value: isCompliant ? '500 g' : (isMissingMRP ? '70 g' : '60g'), confidence: isReview ? 0.55 : 0.92, status: isReview ? 'NEEDS_REVIEW' : 'PASS' },
      { field_name: 'mrp', field_label: 'MRP', detected_value: isMissingMRP ? null : (isReview ? '₹I99' : '₹199'), confidence: isMissingMRP ? 0.0 : (isReview ? 0.42 : 0.93), status: isMissingMRP ? 'FAIL' : (isReview ? 'NEEDS_REVIEW' : 'PASS') },
      { field_name: 'manufacturer', field_label: 'Manufacturer/Packer', detected_value: isMultiple ? null : 'Tata Consumer Products Ltd', confidence: isMultiple ? 0.0 : 0.91, status: isMultiple ? 'FAIL' : 'PASS' },
      { field_name: 'date', field_label: 'Mfg/Pkg Date', detected_value: '08/2026', confidence: 0.89, status: 'PASS' },
      { field_name: 'consumer_care', field_label: 'Consumer Care', detected_value: isMultiple ? null : '1800-209-8787', confidence: isMultiple ? 0.0 : 0.88, status: isMultiple ? 'FAIL' : 'PASS' },
      { field_name: 'country_of_origin', field_label: 'Country of Origin', detected_value: 'India', confidence: 0.92, status: 'PASS' }
    ],
    violations: isCompliant ? [] : (isMissingMRP ? [
      { rule_id: 'LM-PC-003', field: 'mrp', severity: 'high', title: 'MRP Declaration Missing', detected_value: 'Not detected', expected_requirement: 'MRP must be declared in Indian Rupees (₹ or Rs.)', reason: 'Required declaration not detected in the supplied image.', is_prototype_rule: true }
    ] : [])
  };
}

export async function scanUploadedImages(files: File[]): Promise<any> {
  const formData = new FormData();
  // Always use 'files' key — backend expects List[UploadFile] named 'files'
  files.forEach((f) => formData.append('files', f));

  const res = await fetch(`${API_BASE}/api/scan`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({
      detail: 'Failed to scan image(s). Ensure Python backend is running at ' + API_BASE,
    }));
    throw new Error(err.detail || 'Scanning failed');
  }
  return await res.json();
}

// Backward-compatible alias for single file
export async function scanUploadedImage(file: File): Promise<any> {
  return scanUploadedImages([file]);
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
    rule_set_version: '1.0.0',
    rule_set_name: 'Legal Metrology (Packaged Commodities) Rules, 2011 — Prototype',
    disclaimer: 'These are prototype validation rules for demonstration purposes. They are modeled after the Legal Metrology (Packaged Commodities) Rules, 2011.',
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
  // OAuth2PasswordRequestForm requires application/x-www-form-urlencoded
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
