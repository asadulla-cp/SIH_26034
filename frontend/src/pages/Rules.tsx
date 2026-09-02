import { useEffect, useState } from "react";
import { api } from "../api";

type Pack = {
  pack_id: string;
  version: string;
  disclaimer: string;
  rules: {
    rule_id: string;
    field: string;
    description: string;
    requirement: string;
    severity: string;
    validation_type: string;
    version: string;
    legal_reference: string;
    demo_simplified: boolean;
  }[];
};

export default function Rules() {
  const [pack, setPack] = useState<Pack | null>(null);
  useEffect(() => {
    api<Pack>("/api/rules").then(setPack).catch(() => setPack(null));
  }, []);
  if (!pack) return <p className="text-white/50">Loading rule pack…</p>;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Rule library</h1>
      <div className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm text-amber-100">{pack.disclaimer}</div>
      <p className="text-white/50 text-sm">Pack {pack.pack_id} · version {pack.version}. Swap <code className="font-mono">rules/rules.json</code> to update official requirements without rewriting the app.</p>
      <div className="space-y-3">
        {pack.rules.map((r) => (
          <article key={r.rule_id} className="rounded-xl bg-[#141e32] border border-white/10 p-4">
            <div className="flex gap-2 items-baseline">
              <span className="font-mono text-gold">{r.rule_id}</span>
              <span className="text-xs text-white/40">v{r.version}</span>
              <span className="text-xs uppercase ml-auto">{r.severity}</span>
            </div>
            <h2 className="font-semibold mt-1">{r.field} · {r.validation_type}</h2>
            <p className="text-sm text-white/70 mt-1">{r.description}</p>
            <p className="text-sm mt-2">{r.requirement}</p>
            <p className="text-xs text-white/40 mt-2">{r.legal_reference}{r.demo_simplified ? " · DEMO SIMPLIFIED" : ""}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
