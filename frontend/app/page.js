"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getToken, setSession } from "../lib/api";

const DEMOS = [
  ["Admin", "ava.chen@forge.example", "admin123"],
  ["Manager", "marco.lee@forge.example", "manager123"],
  ["Accountant", "sofia.ng@forge.example", "account123"],
  ["Warehouse", "diego.ruiz@forge.example", "warehouse123"],
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("ava.chen@forge.example");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (getToken()) router.replace("/app");
  }, [router]);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setSession(data.access_token, {
        full_name: data.full_name,
        role: data.role,
        tenant: data.tenant,
      });
      router.replace("/app");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <div className="login-card">
        <div className="login-art">
          <div className="eyebrow">ChannelForge</div>
          <h2>One ledger for every marketplace.</h2>
          <p style={{ color: "var(--muted)", maxWidth: 420 }}>
            Sync inventory, ingest orders, reconcile payouts, and compute auditable gross profit across Amazon, Shopee,
            Lazada, TikTok Shop, Shopify, and eBay.
          </p>
        </div>
        <form className="login-form" onSubmit={submit}>
          <h3>Sign in</h3>
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} />
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          {error ? <div style={{ color: "var(--rose)" }}>{error}</div> : null}
          <button className="btn" disabled={busy}>
            {busy ? "Signing in…" : "Enter workspace"}
          </button>
          <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>Demo users</div>
          <div className="row-actions">
            {DEMOS.map(([label, em, pw]) => (
              <button
                type="button"
                key={label}
                className="btn ghost"
                onClick={() => {
                  setEmail(em);
                  setPassword(pw);
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </form>
      </div>
    </div>
  );
}
