import { useEffect, useState } from "react";
import { api, officerName } from "../api";

export default function Settings() {
  const [name, setName] = useState(officerName());
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  useEffect(() => {
    api<Record<string, unknown>>("/api/health").then(setHealth).catch(() => setHealth({ ok: false, mode: "offline" }));
  }, []);
  return (
    <div className="space-y-4 max-w-xl">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <label className="block text-sm">
        Officer display name
        <input
          className="mt-1 w-full bg-[#141e32] border border-white/10 rounded-lg px-3 py-2"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            localStorage.setItem("metalex.officer", e.target.value);
          }}
        />
      </label>
      <div className="rounded-xl bg-[#141e32] border border-white/10 p-4 text-sm space-y-1">
        <div>No login is required for this prototype.</div>
        <div>If you need demo credentials for the presentation: officer <code className="font-mono">ML-OFF-001</code> / passphrase <code className="font-mono">metalex2026</code> (not enforced).</div>
        <pre className="text-xs text-white/50 mt-3 overflow-auto">{JSON.stringify(health, null, 2)}</pre>
      </div>
    </div>
  );
}
