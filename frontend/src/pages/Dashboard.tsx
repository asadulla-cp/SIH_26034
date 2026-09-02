import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, listCached } from "../api";

type Dash = {
  total: number;
  compliant: number;
  non_compliant: number;
  needs_review: number;
  common_violations: { field: string; count: number }[];
  trend: { date: string; COMPLIANT: number; NON_COMPLIANT: number; NEEDS_REVIEW: number }[];
  recent: { id: string; product_name: string | null; overall_status: string; compliance_score: number; created_at: string; violation_count: number }[];
};

const badge: Record<string, string> = {
  COMPLIANT: "bg-emerald-500/15 text-emerald-300",
  NON_COMPLIANT: "bg-red-500/15 text-red-300",
  NEEDS_REVIEW: "bg-amber-500/15 text-amber-300",
};

export default function Dashboard() {
  const [d, setD] = useState<Dash | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api<Dash>("/api/dashboard")
      .then(setD)
      .catch(() => {
        const cached = listCached();
        if (!cached.length) setErr("Backend unavailable and no local inspections yet.");
        else {
          setD({
            total: cached.length,
            compliant: cached.filter((x) => x.overall_status === "COMPLIANT").length,
            non_compliant: cached.filter((x) => x.overall_status === "NON_COMPLIANT").length,
            needs_review: cached.filter((x) => x.overall_status === "NEEDS_REVIEW").length,
            common_violations: [],
            trend: [],
            recent: cached.slice(0, 8).map((x) => ({
              id: x.id,
              product_name: x.product_name,
              overall_status: x.overall_status,
              compliance_score: x.compliance_score,
              created_at: x.created_at,
              violation_count: x.violation_count,
            })),
          });
        }
      });
  }, []);

  if (err) return <p className="text-amber-300">{err}</p>;
  if (!d) return <p className="text-white/50">Loading dashboard…</p>;

  const cards = [
    ["Total inspections", d.total, "text-white"],
    ["Compliant", d.compliant, "text-emerald-300"],
    ["Non-compliant", d.non_compliant, "text-red-300"],
    ["Needs review", d.needs_review, "text-amber-300"],
  ] as const;

  const maxTrend = Math.max(1, ...d.trend.flatMap((t) => [t.COMPLIANT, t.NON_COMPLIANT, t.NEEDS_REVIEW]));
  const maxV = Math.max(1, ...d.common_violations.map((v) => v.count));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Inspection overview</h1>
        <p className="text-white/50 text-sm mt-1">Deterministic LM(PC) prototype pack · seeded demo inspections appear on first launch.</p>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {cards.map(([l, n, c]) => (
          <div key={l} className="rounded-xl bg-[#141e32] border border-white/10 p-4">
            <div className="text-xs text-white/50">{l}</div>
            <div className={`text-3xl font-semibold mt-1 ${c}`}>{n}</div>
          </div>
        ))}
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <section className="rounded-xl bg-[#141e32] border border-white/10 p-4">
          <h2 className="text-sm font-semibold mb-3">Violation trend (by day)</h2>
          {d.trend.length === 0 ? (
            <p className="text-white/40 text-sm">No trend data yet.</p>
          ) : (
            <div className="flex items-end gap-3 h-40">
              {d.trend.map((t) => (
                <div key={t.date} className="flex-1 flex flex-col justify-end items-stretch gap-1">
                  <div className="flex gap-0.5 items-end h-32">
                    <div className="flex-1 bg-emerald-400/70 rounded-t" style={{ height: `${(t.COMPLIANT / maxTrend) * 100}%` }} />
                    <div className="flex-1 bg-red-400/70 rounded-t" style={{ height: `${(t.NON_COMPLIANT / maxTrend) * 100}%` }} />
                    <div className="flex-1 bg-amber-400/70 rounded-t" style={{ height: `${(t.NEEDS_REVIEW / maxTrend) * 100}%` }} />
                  </div>
                  <div className="text-[10px] text-white/40 text-center">{t.date.slice(5)}</div>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-3 text-[11px] text-white/50 mt-3">
            <span>Green compliant</span><span>Red non-compliant</span><span>Amber review</span>
          </div>
        </section>
        <section className="rounded-xl bg-[#141e32] border border-white/10 p-4">
          <h2 className="text-sm font-semibold mb-3">Common violations</h2>
          {d.common_violations.length === 0 ? (
            <p className="text-white/40 text-sm">No FAIL violations recorded yet.</p>
          ) : (
            <ul className="space-y-2">
              {d.common_violations.map((v) => (
                <li key={v.field}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{v.field}</span>
                    <span className="text-white/50">{v.count}</span>
                  </div>
                  <div className="h-1.5 bg-white/10 rounded">
                    <div className="h-1.5 bg-gold rounded" style={{ width: `${(v.count / maxV) * 100}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
      <section className="rounded-xl bg-[#141e32] border border-white/10 overflow-hidden">
        <div className="px-4 py-3 border-b border-white/10 text-sm font-semibold">Recent inspections</div>
        <table className="w-full text-sm">
          <thead className="text-white/40 text-xs">
            <tr>
              <th className="text-left px-4 py-2">ID</th>
              <th className="text-left px-4 py-2">Product</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Score</th>
              <th className="text-left px-4 py-2">Violations</th>
            </tr>
          </thead>
          <tbody>
            {d.recent.map((r) => (
              <tr key={r.id} className="border-t border-white/5 hover:bg-white/5">
                <td className="px-4 py-2 font-mono text-xs">
                  <Link className="text-gold" to={`/history/${r.id}`}>{r.id}</Link>
                </td>
                <td className="px-4 py-2">{r.product_name || "—"}</td>
                <td className="px-4 py-2"><span className={`px-2 py-0.5 rounded text-xs ${badge[r.overall_status]}`}>{r.overall_status.replace("_", " ")}</span></td>
                <td className="px-4 py-2">{r.compliance_score}</td>
                <td className="px-4 py-2">{r.violation_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
