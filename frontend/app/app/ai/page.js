"use client";

import Link from "next/link";
import { useState } from "react";
import Shell, { Pill } from "../../../components/Shell";
import { api } from "../../../lib/api";

export default function AiPage() {
  const [log, setLog] = useState([{ role: "bot", text: "Ask about profit, stock, payouts, or returns." }]);
  const [msg, setMsg] = useState("");
  const [alerts, setAlerts] = useState([]);

  async function send(e) {
    e.preventDefault();
    const text = msg.trim();
    if (!text) return;
    setMsg("");
    setLog((l) => [...l, { role: "me", text }]);
    const r = await api("/api/ai/chat", { method: "POST", body: JSON.stringify({ message: text }) });
    setLog((l) => [...l, { role: "bot", text: r.reply }]);
  }

  async function scan() {
    const r = await api("/api/ai/anomalies", { method: "POST" });
    setAlerts(r.alerts || []);
  }

  return (
    <Shell
      title="AI copilot"
      eyebrow="Automation layer"
      actions={
        <>
          <Link className="btn ghost" href="/app/ai-log">
            Open AI log
          </Link>
          <button className="btn" onClick={scan}>
            Scan anomalies
          </button>
        </>
      }
    >
      <div className="grid two">
        <div className="card chat">
          <div className="chat-log">
            {log.map((m, i) => (
              <div key={i} className={`bubble ${m.role}`}>
                {m.text}
              </div>
            ))}
          </div>
          <form onSubmit={send} className="row-actions">
            <input style={{ flex: 1 }} value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="What is our margin this period?" />
            <button className="btn">Send</button>
          </form>
        </div>
        <div className="card">
          <h3>Background monitors</h3>
          {alerts.length === 0 ? <p style={{ color: "var(--muted)" }}>No alerts yet. Run a scan.</p> : null}
          {alerts.map((a) => (
            <div key={a.id} style={{ borderBottom: "1px solid var(--line)", padding: "10px 0" }}>
              <Pill value={a.severity} /> <strong>{a.title}</strong>
              <p style={{ color: "var(--muted)", fontSize: 13 }}>{a.detail}</p>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
