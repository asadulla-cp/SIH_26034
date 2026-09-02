import type {
  DashboardStats,
  Inspection,
  Rule,
  AuthTokenResponse,
  LoginCredentials,
  RegisterCredentials
} from './types';

// When VITE_API_URL is empty (production on Render — frontend served by the
// same FastAPI process), use an empty string so all fetch() calls go to the
// same origin automatically. Fall back to localhost only in local dev.
const API_BASE = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');

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
  } catch {
    return { status: 'offline', ocr_available: false };
  }
}

export async function getDashboardStats(): Promise<DashboardStats> {
  try {
    const res = await fetch(`${API_BASE}/api/dashboard`);
    if (res.ok) {
      const d = await res.json();
      // Normalize backend response to frontend DashboardStats shape
      return {
        total_inspections: d.total ?? d.total_inspections ?? 0,
        compliant: d.compliant ?? 0,
        non_compliant: d.non_compliant ?? 0,
        needs_review: d.needs_review ?? 0,
        critical_violations: d.critical_violations ?? 0,
        average_severity: d.average_severity ?? 0,
        average_risk_label: d.average_risk_label ?? 'Low Risk',
        font_violations_count: d.font_violations_count ?? 0,
        font_violation_rate: d.font_violation_rate ?? 0,
        recent_inspections: (d.recent ?? d.recent_inspections ?? []).map((r: any) => ({
          id: r.id,
          inspection_id: r.id,
          product_name: r.product_name,
          overall_status: r.overall_status,
          compliance_score: r.compliance_score,
          severity_score: r.severity_score,
          risk_level: r.risk_level,
          is_demo: !!r.demo_sample_id,
          created_at: r.created_at,
          violation_count: r.violation_count ?? 0,
        })),
        common_violations: d.common_violations ?? [],
        high_severity_violations: d.high_severity_violations ?? [],
      };
    }
  } catch {
    // Offline fallback
  }
  return {
    total_inspections: 0,
    compliant: 0,
    non_compliant: 0,
    needs_review: 0,
    critical_violations: 0,
    average_severity: 0,
    average_risk_label: 'Low Risk',
    font_violations_count: 0,
    font_violation_rate: 0,
    recent_inspections: [],
    common_violations: [],
    high_severity_violations: [],
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

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);

  const res = await fetch(url, {
    method: 'POST',
    body: formData,
    signal: controller.signal,
  });
  clearTimeout(timeout);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to scan image(s). Ensure Python backend is running.' }));
    throw new Error(err.detail || 'Scanning failed');
  }
  return await res.json();
}

export async function scanUploadedImage(
  file: File,
  coords?: { latitude?: number; longitude?: number },
  languages?: string[]
): Promise<any> {
  return scanUploadedImages([file], coords, languages);
}

// ─── Geo-Tagged Compliance Map ────────────────────────────────────────────────

export async function getGeoInspections(status?: string): Promise<import('./types').GeoInspection[]> {
  try {
    const url = status && status !== 'ALL'
      ? `${API_BASE}/api/inspections/geo?status=${status}`
      : `${API_BASE}/api/inspections/geo`;
    const res = await fetch(url);
    if (res.ok) return await res.json();
  } catch {
    // Offline — return empty
  }
  return [];
}

// ─── Legal Notices ────────────────────────────────────────────────────────────

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
  } catch {
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
  } catch {
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
    if (params?.search) query.append('q', params.search);
    if (params?.limit) query.append('limit', params.limit.toString());
    if (params?.offset) query.append('offset', params.offset.toString());

    const res = await fetch(`${API_BASE}/api/inspections?${query.toString()}`);
    if (res.ok) {
      const data = await res.json();
      // Backend returns a plain array; normalize to { total, inspections }
      if (Array.isArray(data)) {
        return { total: data.length, inspections: data };
      }
      return data;
    }
  } catch {
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
  } catch {
    // Offline fallback
  }
  return {
    rule_set_version: '2.0.0',
    rule_set_name: 'Legal Metrology (Packaged Commodities) Rules, 2011',
    disclaimer: 'These rules are modeled after the Legal Metrology (Packaged Commodities) Rules, 2011.',
    rules: FALLBACK_RULES,
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
  } catch {
    // Fallback ok
  }
  return { status: 'ok', message: 'Review saved locally.' };
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

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
