export interface ExtractedField {
  id?: string;
  field_name: string;
  field_label: string;
  detected_value: string | null;
  normalized_value: string | null;
  confidence: number;
  status: 'PASS' | 'FAIL' | 'NEEDS_REVIEW' | 'PENDING';
  bounding_box: [number, number, number, number] | null;
  font_size_mm?: number | null;
  min_font_size_mm?: number | null;
  source_text: string;
  extraction_method: string;
  candidates?: Array<{ value: string; confidence: number; score: number; reason?: string }>;
}

export interface Violation {
  id?: string;
  rule_id: string;
  field: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  severity_points?: number;
  status?: 'FAIL' | 'NEEDS_REVIEW' | 'PASS';
  title: string;
  detected_value: string | null;
  expected_requirement: string | null;
  reason: string;
  confidence?: number | null;
  evidence_type?: string;
  bounding_box?: [number, number, number, number] | null;
  rule_version: string;
  is_prototype_rule: boolean;
}

export interface BarcodeResult {
  barcode: string;
  gs1_found: boolean;
  is_valid: boolean | null;
  status: 'PASS' | 'FAIL' | 'NEEDS_REVIEW';
  gs1_product_name?: string;
  gs1_manufacturer?: string;
  gs1_category?: string;
  gs1_declared_mrp?: number;
  scanned_mrp?: number;
  mrp_diff_pct?: number;
  mrp_status?: string;
  mfg_status?: string;
  mismatches?: string[];
  message?: string;
}

export interface AnomalyFinding {
  type: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  confidence: number;
  title: string;
  details: string;
  bbox?: [number, number, number, number] | null;
  image_number?: number;
}

export interface AnomalyAnalysis {
  has_anomaly: boolean;
  tampering_detected: boolean;
  tampering_risk: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  findings: AnomalyFinding[];
  damage_analysis?: {
    damage_detected: boolean;
    readability_pct: number;
    condition: string;
    issues?: string[];
  };
  sticker_analysis?: {
    sticker_detected: boolean;
    confidence: number;
    color_discontinuity?: number;
    rectangular_boundary?: boolean;
    details?: string;
  };
}

export interface ForensicsAnalysis {
  verdict: string;
  authenticity_score: number;
  manipulation_detected: boolean;
  findings: string[];
  editor_software?: string | null;
}

export interface LanguageDetectionResult {
  detected_languages: string[];
  has_english: boolean;
  has_hindi: boolean;
  is_dual_language: boolean;
  primary_language?: string;
}

export interface LegalNoticeRecord {
  id: string;
  notice_id: string;
  inspection_id?: string;
  manufacturer_name?: string;
  total_penalty: number;
  status: 'GENERATED' | 'SENT' | 'RESPONDED' | 'PENDING';
  response_deadline?: string | null;
  created_at?: string | null;
}

export interface Inspection {
  id: string;
  inspection_id: string;
  product_name: string;
  overall_status: 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW' | 'PENDING';
  compliance_score: number;
  severity_score?: number;
  risk_level?: 'low' | 'medium' | 'high' | 'critical';
  risk_label?: string;
  severity_breakdown?: { critical: number; high: number; medium: number; low: number };
  latitude?: number | null;
  longitude?: number | null;
  barcode_data?: BarcodeResult | null;
  anomaly_data?: AnomalyAnalysis | null;
  detected_languages?: LanguageDetectionResult | null;
  total_fields: number;
  passed_fields: number;
  failed_fields: number;
  review_fields: number;
  is_demo: boolean;
  image_quality_score?: number | null;
  image_quality_issues?: string[] | null;
  ocr_engine?: string;
  processing_time_ms?: number | null;
  commodity_category?: string | null;
  commodity_confidence?: number | null;
  created_at?: string;
  has_image?: boolean;
  has_annotated_image?: boolean;
  fields?: ExtractedField[];
  violations?: Violation[];
  reviews?: Array<{
    id: string;
    field_name: string;
    action: string;
    original_value: string | null;
    corrected_value: string | null;
    reviewer_notes: string | null;
    created_at: string;
  }>;
  legal_notices?: LegalNoticeRecord[];
}

export interface Rule {
  rule_id: string;
  title: string;
  field: string;
  description: string;
  requirement: string;
  applicability: string;
  validation_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  severity_level?: string;
  severity_points?: number;
  rule_version: string;
  source_reference: string;
  is_prototype: boolean;
  explanation_template: string;
}

export interface DashboardStats {
  total_inspections: number;
  compliant: number;
  non_compliant: number;
  needs_review: number;
  critical_violations?: number;
  average_severity?: number;
  average_risk_label?: string;
  font_violations_count?: number;
  font_violation_rate?: number;
  recent_inspections: Array<{
    id: string;
    inspection_id: string;
    product_name: string;
    overall_status: 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW';
    compliance_score: number;
    severity_score?: number;
    risk_level?: string;
    is_demo: boolean;
    created_at: string | null;
    violation_count: number;
  }>;
  common_violations: Array<{ field: string; count: number }>;
  high_severity_violations: Array<{
    id: string;
    rule_id: string;
    field: string;
    title: string;
    severity: string;
    severity_points?: number;
    inspection_id: string;
  }>;
}

export interface BatchItemResult {
  id?: string;
  inspection_id: string;
  product_name: string;
  filename: string;
  status: 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW' | 'ERROR';
  compliance_score: number;
  severity_score: number;
  risk_level: string;
  violations_count?: number;
  mrp?: string | null;
  net_quantity?: string | null;
  barcode?: string | null;
  success?: boolean;
  error?: string;
}

export interface BatchJob {
  batch_id: string;
  filename: string;
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress_pct: number;
  processed_count: number;
  total_count: number;
  compliant_count: number;
  non_compliant_count: number;
  needs_review_count: number;
  duration_seconds: number;
  created_at: number;
  completed_at: number | null;
  error?: string | null;
  inspections: BatchItemResult[];
}

export interface GeoInspection {
  id: string;
  inspection_id: string;
  product_name: string;
  overall_status: 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW';
  compliance_score: number;
  severity_score: number;
  risk_level: string;
  latitude: number;
  longitude: number;
  created_at: string | null;
  violation_count: number;
  location_name?: string;
}

export interface EcommerceCheck {
  requirement: string;
  status: 'PASS' | 'FAIL';
  details: string;
  rule: string;
}

export interface EcommerceReport {
  url: string;
  platform: string;
  product_name: string;
  listed_price: number;
  description: string;
  images_scanned: number;
  is_compliant: boolean;
  overall_status: 'COMPLIANT' | 'NON_COMPLIANT';
  compliance_score: number;
  is_overpriced: boolean;
  price_diff_pct: number;
  checks: EcommerceCheck[];
  recommendations: string[];
  image_urls: string[];
  ocr_fields: Record<string, any>;
}


// ─── Auth ───────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: 'officer' | 'admin';
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterCredentials {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}
