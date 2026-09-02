import { useEffect, useMemo, useRef, useState } from "react";
import { api, cacheInspection, officerName, type Inspection } from "../api";

const STEPS = ["Upload image", "Preprocess", "OCR", "Field extraction", "Rule validation", "Compliance result"];

type Sample = { id: string; title: string; scenario: string; image_url: string; notes: string };

const badge: Record<string, string> = {
  COMPLIANT: "bg-emerald-500/15 text-emerald-300 border-emerald-400/30",
  NON_COMPLIANT: "bg-red-500/15 text-red-300 border-red-400/30",
  NEEDS_REVIEW: "bg-amber-500/15 text-amber-300 border-amber-400/30",
  PASS: "text-emerald-300",
  FAIL: "text-red-300",
};

export default function Scan() {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(-1);
  const [err, setErr] = useState("");
  const [insp, setInsp] = useState<Inspection | null>(null);
  const [activeField, setActiveField] = useState<string | null>(null);
  const [edit, setEdit] = useState<Record<string, string>>({});
  const imgRef = useRef<HTMLImageElement>(null);
  const [nat, setNat] = useState({ w: 1, h: 1 });

  useEffect(() => {
    api<Sample[]>("/api/demo/samples").then(setSamples).catch(() => setSamples([]));
  }, []);

  function pickFile(f: File | null) {
    setFile(f);
    setInsp(null);
    setErr("");
    if (f) setPreview(URL.createObjectURL(f));
  }

  async function run(sampleId?: string) {
    setErr("");
    setBusy(true);
    setInsp(null);
    setStep(0);
    const timers = STEPS.map((_, i) => setTimeout(() => setStep(i), 180 * (i + 1)));
    try {
      const fd = new FormData();
      fd.append("officer_name", officerName());
      if (sampleId) fd.append("sample_id", sampleId);
      else if (file) fd.append("file", file);
      else throw new Error("Choose a package image or a demo sample.");
      const result = await api<Inspection>("/api/scan", { method: "POST", body: fd });
      cacheInspection(result);
      setInsp(result);
      setPreview(result.image_url);
      setStep(STEPS.length - 1);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Scan failed");
    } finally {
      timers.forEach(clearTimeout);
      setBusy(false);
    }
  }

  async function review(field_key: string, action: "approve" | "reject" | "edit") {
    if (!insp) return;
    const body: Record<string, string> = { field_key, action, reviewer: officerName() };
    if (action === "edit") body.corrected_value = edit[field_key] ?? insp.fields.find((f) => f.field_key === field_key)?.value ?? "";
    const result = await api<Inspection>(`/api/inspections/${insp.id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    cacheInspection(result);
    setInsp(result);
  }

  const boxes = useMemo(() => {
    if (!insp) return [];
    return insp.fields
      .filter((f) => f.bbox)
      .map((f) => ({ ...f.bbox!, key: f.field_key, status: f.status }));
  }, [insp]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Scan packaged commodity</h1>
        <p className="text-white/50 text-sm mt-1">Upload → preprocess → OCR → extract → deterministic rules → evidence. LLM never decides legality.</p>
      </div>

      <div className="rounded-xl border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
        Prototype rule pack maps commonly cited LM(PC) 2011 declarations. It is <b>not</b> official gazette text. Demo samples are labelled.
      </div>

      <div className="grid lg:grid-cols-5 gap-4">
        <div className="lg:col-span-2 space-y-3">
          <label className="block rounded-xl border border-dashed border-white/20 p-6 text-center cursor-pointer hover:border-gold/50 bg-[#141e32]">
            <input type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => pickFile(e.target.files?.[0] || null)} />
            <div className="text-sm">Upload / capture package image</div>
            <div className="text-xs text-white/40 mt-1">PNG, JPEG, WebP · max 12 MB</div>
            {file && <div className="mt-2 text-gold text-sm">{file.name}</div>}
          </label>
          <button disabled={busy} onClick={() => run()} className="w-full py-2.5 rounded-lg bg-gold text-navy font-semibold disabled:opacity-50">
            {busy ? "Processing…" : "Run inspection"}
          </button>
          <div>
            <div className="text-xs uppercase tracking-wide text-white/40 mb-2">Demo samples (no camera needed)</div>
            <div className="grid grid-cols-1 gap-2">
              {samples.map((s) => (
                <button key={s.id} disabled={busy} onClick={() => run(s.id)} className="text-left rounded-lg border border-white/10 bg-[#141e32] p-3 hover:border-gold/40">
                  <div className="flex gap-3">
                    <img src={s.image_url} alt="" className="w-12 h-16 object-cover rounded" />
                    <div>
                      <div className="text-sm font-semibold">{s.title} <span className="text-[10px] text-gold ml-1">DEMO</span></div>
                      <div className="text-xs text-white/50">{s.scenario}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="lg:col-span-3 space-y-3">
          <ol className="grid grid-cols-6 gap-1 text-[10px]">
            {STEPS.map((s, i) => (
              <li key={s} className={`rounded px-1 py-2 text-center border ${i <= step ? "border-gold/50 text-gold bg-gold/10" : "border-white/10 text-white/40"}`}>{s}</li>
            ))}
          </ol>
          {err && <div className="rounded-lg bg-red-500/15 border border-red-400/30 px-3 py-2 text-sm text-red-200">{err}</div>}
          {(preview || insp) && (
            <div className="relative rounded-xl overflow-hidden border border-white/10 bg-black/40">
              <img
                ref={imgRef}
                src={preview || insp?.image_url}
                alt="Package"
                className="w-full max-h-[520px] object-contain"
                onLoad={(e) => {
                  const im = e.currentTarget;
                  setNat({ w: im.naturalWidth, h: im.naturalHeight });
                }}
              />
              {insp && imgRef.current && (
                <Overlay img={imgRef.current} boxes={boxes} active={activeField} nat={nat} />
              )}
            </div>
          )}
        </div>
      </div>

      {insp && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-end gap-6 rounded-xl bg-[#141e32] border border-white/10 p-5">
            <div>
              <div className="text-xs text-white/50">Compliance score</div>
              <div className="text-5xl font-semibold text-gold">{insp.compliance_score} <span className="text-lg text-white/40">/ 100</span></div>
            </div>
            <div className={`px-3 py-1 rounded-full border text-sm ${badge[insp.overall_status]}`}>{insp.overall_status.replace("_", " ")}</div>
            <div className="text-sm text-white/60">
              <div className="font-mono">{insp.id}</div>
              <div>Pipeline: {insp.pipeline_mode} · quality {insp.image_quality.toFixed(2)}</div>
              {insp.demo_sample_id && <div className="text-gold">Sample dataset: {insp.demo_sample_id}</div>}
            </div>
            <a className="ml-auto px-4 py-2 rounded-lg border border-gold/40 text-gold text-sm" href={`/api/reports/${insp.id}/pdf`} target="_blank" rel="noreferrer">Download PDF report</a>
          </div>

          <section className="rounded-xl bg-[#141e32] border border-white/10 overflow-x-auto">
            <div className="px-4 py-3 text-sm font-semibold border-b border-white/10">Extracted declarations</div>
            <table className="w-full text-sm">
              <thead className="text-white/40 text-xs">
                <tr>
                  <th className="text-left px-3 py-2">Field</th>
                  <th className="text-left px-3 py-2">Value</th>
                  <th className="text-left px-3 py-2">Confidence</th>
                  <th className="text-left px-3 py-2">Status</th>
                  <th className="text-left px-3 py-2">Review</th>
                </tr>
              </thead>
              <tbody>
                {insp.fields.map((f) => (
                  <tr key={f.field_key} className={`border-t border-white/5 cursor-pointer ${activeField === f.field_key ? "bg-gold/10" : ""}`} onClick={() => setActiveField(f.field_key)}>
                    <td className="px-3 py-2 font-medium">{f.field_key}</td>
                    <td className="px-3 py-2">{f.value || <span className="text-white/40">Missing</span>}</td>
                    <td className="px-3 py-2">{f.confidence == null ? "—" : `${Math.round(f.confidence * 100)}%`}</td>
                    <td className={`px-3 py-2 ${badge[f.status] || ""}`}>{f.status}</td>
                    <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                      {(f.status === "NEEDS_REVIEW" || insp.overall_status === "NEEDS_REVIEW") && (
                        <div className="flex flex-wrap gap-1 items-center">
                          <button className="px-2 py-0.5 text-xs rounded bg-emerald-600" onClick={() => review(f.field_key, "approve")}>Approve</button>
                          <button className="px-2 py-0.5 text-xs rounded bg-red-700" onClick={() => review(f.field_key, "reject")}>Reject</button>
                          <input className="bg-black/40 border border-white/10 rounded px-1 text-xs w-28" placeholder="Edit value" value={edit[f.field_key] ?? ""} onChange={(e) => setEdit({ ...edit, [f.field_key]: e.target.value })} />
                          <button className="px-2 py-0.5 text-xs rounded border border-white/20" onClick={() => review(f.field_key, "edit")}>Save</button>
                        </div>
                      )}
                      {f.reviewer_action && <div className="text-[10px] text-white/40">Reviewed: {f.reviewer_action}{f.corrected_value ? ` → ${f.corrected_value}` : ""}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="rounded-xl bg-[#141e32] border border-white/10 p-4 space-y-3">
            <h2 className="text-sm font-semibold">Violations & review items</h2>
            {insp.violations.length === 0 && <p className="text-emerald-300 text-sm">No violations from the prototype rule engine.</p>}
            {insp.violations.map((v, i) => (
              <button key={i} className="w-full text-left rounded-lg border border-white/10 p-3 hover:border-gold/30" onClick={() => setActiveField(v.field)}>
                <div className="flex gap-2 text-xs mb-1">
                  <span className="uppercase text-gold">{v.severity}</span>
                  <span className="font-mono">{v.rule_id} v{v.rule_version}</span>
                  <span className={badge[v.status]}>{v.status}</span>
                </div>
                <div className="text-sm">Field <b>{v.field}</b> · Detected: {v.detected_value || "Missing"}</div>
                <div className="text-xs text-white/50 mt-1">Expected: {v.expected}</div>
                <div className="text-xs mt-1">{v.reason}</div>
                <div className="text-xs text-white/40 mt-1">{v.evidence.bbox ? "Evidence: bounding box on image (click to highlight)." : "Not detected in supplied image."}</div>
              </button>
            ))}
          </section>
        </div>
      )}
    </div>
  );
}

function Overlay({ img, boxes, active, nat }: { img: HTMLImageElement; boxes: { x: number; y: number; w: number; h: number; key: string; status: string }[]; active: string | null; nat: { w: number; h: number } }) {
  const r = img.getBoundingClientRect();
  const parent = img.parentElement!.getBoundingClientRect();
  const scale = Math.min(r.width / nat.w, r.height / nat.h);
  const dw = nat.w * scale;
  const dh = nat.h * scale;
  const ox = (r.width - dw) / 2 + (r.left - parent.left);
  const oy = (r.height - dh) / 2 + (r.top - parent.top);
  return (
    <svg className="absolute inset-0 w-full h-full pointer-events-none">
      {boxes.map((b) => {
        const on = active === b.key;
        return (
          <rect
            key={b.key}
            x={ox + b.x * dw}
            y={oy + b.y * dh}
            width={b.w * dw}
            height={b.h * dh}
            fill={on ? "rgba(212,160,23,0.25)" : "rgba(76,141,255,0.12)"}
            stroke={on ? "#d4a017" : b.status === "FAIL" ? "#f87171" : "#60a5fa"}
            strokeWidth={on ? 3 : 1.5}
          />
        );
      })}
    </svg>
  );
}
