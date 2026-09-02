import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, listCached } from "../api";

type Row = {
  id: string;
  created_at: string;
  product_name: string | null;
  overall_status: string;
  compliance_score: number;
  violation_count: number;
  demo_sample_id: string | null;
};

const badge: Record<string, string> = {
  COMPLIANT: "bg-emerald-500/15 text-emerald-300",
  NON_COMPLIANT: "bg-red-500/15 text-red-300",
  NEEDS_REVIEW: "bg-amber-500/15 text-amber-300",
};

export default function History() {
  const [rows, setRows] = useState<Row[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  useEffect(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (status) params.set("status", status);
    api<Row[]>(`/api/inspections?${params}`)
      .then(setRows)
      .catch(() => {
        setRows(
          listCached()
            .filter((x) => !status || x.overall_status === status)
            .filter((x) => !q || `${x.id} ${x.product_name}`.toLowerCase().includes(q.toLowerCase()))
            .map((x) => ({
              id: x.id,
              created_at: x.created_at,
              product_name: x.product_name,
              overall_status: x.overall_status,
              compliance_score: x.compliance_score,
              violation_count: x.violation_count,
              demo_sample_id: x.demo_sample_id,
            }))
        );
      });
  }, [q, status]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Inspection history</h1>
      <div className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search ID or product" className="flex-1 bg-[#141e32] border border-white/10 rounded-lg px-3 py-2 text-sm" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="bg-[#141e32] border border-white/10 rounded-lg px-3 py-2 text-sm">
          <option value="">All statuses</option>
          <option value="COMPLIANT">Compliant</option>
          <option value="NON_COMPLIANT">Non-compliant</option>
          <option value="NEEDS_REVIEW">Needs review</option>
        </select>
      </div>
      <div className="rounded-xl border border-white/10 overflow-hidden bg-[#141e32]">
        <table className="w-full text-sm">
          <thead className="text-xs text-white/40">
            <tr>
              <th className="text-left px-3 py-2">Inspection</th>
              <th className="text-left px-3 py-2">When</th>
              <th className="text-left px-3 py-2">Product</th>
              <th className="text-left px-3 py-2">Result</th>
              <th className="text-left px-3 py-2">Score</th>
              <th className="text-left px-3 py-2">Violations</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-white/5">
                <td className="px-3 py-2 font-mono text-xs">
                  <Link className="text-gold" to={`/history/${r.id}`}>{r.id}</Link>
                  {r.demo_sample_id && <div className="text-[10px] text-white/40">DEMO {r.demo_sample_id}</div>}
                </td>
                <td className="px-3 py-2 text-white/60">{new Date(r.created_at).toLocaleString()}</td>
                <td className="px-3 py-2">{r.product_name || "—"}</td>
                <td className="px-3 py-2"><span className={`px-2 py-0.5 rounded text-xs ${badge[r.overall_status]}`}>{r.overall_status.replace("_", " ")}</span></td>
                <td className="px-3 py-2">{r.compliance_score}</td>
                <td className="px-3 py-2">{r.violation_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
