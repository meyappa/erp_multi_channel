"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearSession, getUser } from "../lib/api";

const LINKS = [
  ["Dashboard", "/app"],
  ["Catalog", "/app/catalog"],
  ["Inventory", "/app/inventory"],
  ["Orders", "/app/orders"],
  ["Reconciliation", "/app/reconciliation"],
  ["Profit", "/app/profit"],
  ["Returns", "/app/returns"],
  ["Accounting", "/app/accounting"],
  ["AI Copilot", "/app/ai"],
  ["AI Log", "/app/ai-log"],
];

export default function Shell({ title, eyebrow, actions, children }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState(null);

  useEffect(() => {
    const u = getUser();
    if (!u) {
      router.replace("/");
      return;
    }
    setUser(u);
  }, [router]);

  if (!user) return null;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="mark">CF</div>
          <div>
            <h1>ChannelForge</h1>
            <small>Multi-channel ERP</small>
          </div>
        </div>
        <nav className="nav">
          {LINKS.map(([label, href]) => (
            <Link key={href} href={href} className={pathname === href ? "active" : ""}>
              {label}
            </Link>
          ))}
        </nav>
        <div className="user-card">
          <strong>{user.full_name}</strong>
          <span>
            {user.role} · {user.tenant}
          </span>
          <div style={{ marginTop: 10 }}>
            <button
              className="btn ghost"
              onClick={() => {
                clearSession();
                router.replace("/");
              }}
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>
      <main className="main">
        <div className="topbar">
          <div>
            <div className="eyebrow">{eyebrow || "Operations"}</div>
            <h2 style={{ fontSize: 34 }}>{title}</h2>
          </div>
          <div className="row-actions">{actions}</div>
        </div>
        {children}
      </main>
    </div>
  );
}

export function Pill({ value }) {
  const v = String(value || "").toLowerCase();
  let cls = "idle";
  if (["active", "connected", "paid", "success", "approved", "posted", "ok"].includes(v)) cls = "ok";
  if (["paused", "pending", "requested", "draft", "medium"].includes(v)) cls = "warn";
  if (["failed", "rejected", "open", "high", "missing_payout", "out-of-stock"].includes(v)) cls = "bad";
  return <span className={`pill ${cls}`}>{value}</span>;
}

export function Money({ value }) {
  const n = Number(value || 0);
  return <span className="mono">${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>;
}
