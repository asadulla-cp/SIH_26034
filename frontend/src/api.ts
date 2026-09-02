export type BBox = { x: number; y: number; w: number; h: number };

export type FieldRow = {
  field_key: string;
  value: string | null;
  confidence: number | null;
  status: string;
  bbox: BBox | null;
  original_value?: string | null;
  corrected_value?: string | null;
  reviewer_action?: string | null;
};

export type Violation = {
  field: string;
  rule_id: string;
  rule_version: string;
  severity: string;
  detected_value: string | null;
  expected: string;
  reason: string;
  confidence: number | null;
  status: string;
  evidence: { bbox?: BBox; note?: string };
};

export type Inspection = {
  id: string;
  created_at: string;
  product_name: string | null;
  overall_status: string;
  compliance_score: number;
  violation_count: number;
  image_url: string;
  demo_sample_id: string | null;
  pipeline_mode: string;
  ocr_available: boolean;
  image_quality: number;
  officer_name: string | null;
  ocr_lines: { text: string; confidence: number; bbox?: BBox; field_hint?: string }[];
  fields: FieldRow[];
  violations: Violation[];
  disclaimer: string;
};

const LS = "metalex.local.inspections";

export function officerName() {
  return localStorage.getItem("metalex.officer") || "Demo officer";
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let msg = "Request failed";
    try {
      const j = await res.json();
      msg = j.message || j.detail?.message || (typeof j.detail === "string" ? j.detail : msg);
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return res.json();
}

export function cacheInspection(insp: Inspection) {
  const all = listCached();
  const next = [insp, ...all.filter((x) => x.id !== insp.id)].slice(0, 50);
  localStorage.setItem(LS, JSON.stringify(next));
}

export function listCached(): Inspection[] {
  try {
    return JSON.parse(localStorage.getItem(LS) || "[]");
  } catch {
    return [];
  }
}
