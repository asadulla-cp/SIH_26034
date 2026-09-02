import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, cacheInspection, listCached, type Inspection } from "../api";

export default function InspectionDetail() {
  const { id } = useParams();
  const [insp, setInsp] = useState<Inspection | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!id) return;
    api<Inspection>(`/api/inspections/${id}`)
      .then((x) => {
        cacheInspection(x);
        setInsp(x);
      })
      .catch(() => {
        const local = listCached().find((x) => x.id === id);
        if (local) setInsp(local);
        else setErr("Inspection not found (backend offline and not in local cache).");
      });
  }, [id]);
  if (err) return <p className="text-amber-300">{err}</p>;
  if (!insp) return <p className="text-white/50">Loading…</p>;
  return (
    <div className="space-y-4">
      <Link to="/history" className="text-sm text-gold">← History</Link>
      <h1 className="text-2xl font-semibold font-mono">{insp.id}</h1>
      <p className="text-white/50">{insp.product_name} · {insp.overall_status.replace("_", " ")} · {insp.compliance_score}/100</p>
      <img src={insp.image_url} alt="" className="max-h-80 rounded-xl border border-white/10" />
      <a className="inline-block px-4 py-2 rounded-lg bg-gold text-navy font-semibold" href={`/api/reports/${insp.id}/pdf`} target="_blank" rel="noreferrer">Download PDF</a>
      <table className="w-full text-sm bg-[#141e32] rounded-xl overflow-hidden">
        <tbody>
          {insp.fields.map((f) => (
            <tr key={f.field_key} className="border-t border-white/5">
              <td className="px-3 py-2">{f.field_key}</td>
              <td className="px-3 py-2">{f.value || "Missing"}</td>
              <td className="px-3 py-2">{f.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="space-y-2">
        {insp.violations.map((v, i) => (
          <li key={i} className="rounded-lg border border-white/10 p-3 text-sm">
            <b>{v.rule_id}</b> {v.field}: {v.reason}
          </li>
        ))}
      </ul>
    </div>
  );
}
