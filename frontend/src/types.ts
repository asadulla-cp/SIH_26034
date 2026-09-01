export interface ExtractedField {
  id?: string;
  field_name: string;
  field_label: string;
  detected_value: string | null;
  normalized_value: string | null;
  confidence: number;
  status: 'PASS' | 'FAIL' | 'NEEDS_REVIEW' | 'PENDING';
  bounding_box: [number, number, number, number] | null;
  source_text: string;
  extraction_method: string;
  candidates?: Array<{ value: string; confidence: number; score: number }>;
}

export interface Violation {
  id?: string;
  rule_id: string;
  field: string;
  severity: 'high' | 'medium' | 'low';
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

export interface Inspection {
  id: string;
  inspection_id: string;
  product_name: string;
  overall_status: 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW' | 'PENDING';
  compliance_score: number;
  total_fields: number;
  passed_fields: number;
  failed_fields: number;
  review_fields: number;
  is_demo: boolean;
  image_quality_score?: number | null;
  image_quality_issues?: string[] | null;
  ocr_engine?: string;
  processing_time_ms?: number | null;
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
}

export interface Rule {
  rule_id: string;
  title: string;
  field: string;
  description: string;
  requirement: string;
  applicability: string;
  validation_type: string;
  severity: 'high' | 'medium' | 'low';
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
  recent_inspections: Array<{
    id: string;
    inspection_id: string;
    product_name: string;
    overall_status: 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW';
    compliance_score: number;
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
    inspection_id: string;
  }>;
}

export interface DemoProduct {
  id: string;
  name: string;
  description: string;
  is_compliant: boolean | null;
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
