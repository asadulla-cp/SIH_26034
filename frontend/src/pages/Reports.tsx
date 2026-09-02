import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

type Row = { id: string; product_name: string | null; overall_status: string; created_at: string; compliance_score: number };

export default function Reports() {
  const [rows, setRows] = useState<Row[]>([]);
  useEffect(() => {
    api<Row[]>("/api/inspections").then(setRows).catch(() => setRows([]));
  }, []);
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Reports</h1>
      <p className="text-white/50 text-sm">Each inspection can produce a PDF with product info, declarations, status, violations, evidence image, timestamp and ID.</p>
      <div className="space-y-2">
        {rows.map((r) => (
          <div key={r.id} className="flex items-center gap-3 rounded-xl bg-[#141e32] border border-white/10 px-4 py-3">
            <div className="flex-1">
              <Link to={`/reports/${r.id}`} className="font-mono text-gold text-sm">{r.id}</Link>
              <div className="text-sm text-white/70">{r.product_name || "—"} · {r.overall_status.replace("_", " ")} · {r.compliance_score}/100</div>
            </div>
            <a className="text-sm px-3 py-1.5 rounded border border-gold/40 text-gold" href={`/api/reports/${r.id}/pdf`} target="_blank" rel="noreferrer">PDF</a>
          </div>
        ))}
      </div>
    </div>
  );
}
