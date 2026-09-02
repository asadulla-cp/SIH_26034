import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";

const links = [
  ["/", "Dashboard"],
  ["/scan", "Scan Product"],
  ["/history", "Inspection History"],
  ["/reports", "Reports"],
  ["/rules", "Rule Library"],
  ["/settings", "Settings"],
] as const;

export default function Layout({ online }: { online: boolean | null }) {
  const [clock, setClock] = useState(() => new Date().toLocaleString());
  useEffect(() => {
    const t = setInterval(() => setClock(new Date().toLocaleString()), 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="min-h-full flex">
      <aside className="w-60 shrink-0 bg-[#101a2c] border-r border-white/10 flex flex-col">
        <div className="px-5 py-5 border-b border-white/10">
          <div className="text-gold font-semibold tracking-[0.2em] text-xs">SIH PROTOTYPE</div>
          <div className="text-2xl font-bold mt-1">MetaLex</div>
          <div className="text-xs text-white/50 mt-1 leading-snug">Packaged Commodities · LM(PC) Rules, 2011</div>
        </div>
        <nav className="p-3 flex-1 space-y-1">
          {links.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-lg text-sm ${isActive ? "bg-gold/15 text-gold" : "text-white/75 hover:bg-white/5"}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 text-[11px] text-white/40 border-t border-white/10">
          AI extracts · Rules decide · Evidence explains
        </div>
      </aside>
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-white/10 flex items-center justify-between px-6 bg-[#0f1728]">
          <div className="text-sm text-white/60">Legal Metrology Officer Console</div>
          <div className="flex items-center gap-3 text-xs">
            <span className={`px-2 py-1 rounded-full border ${online ? "border-emerald-400/40 text-emerald-300" : "border-amber-400/40 text-amber-300"}`}>
              {online ? "Local / Online backend" : "Offline / Local mode"}
            </span>
            <span className="font-mono text-white/50">{clock}</span>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
