"use client";

import { useEffect, useState } from "react";
import Shell, { Money, Pill } from "../../../components/Shell";
import { api } from "../../../lib/api";

export default function ReconciliationPage() {
  const [payouts, setPayouts] = useState([]);
  const [gaps, setGaps] = useState([]);
  const [msg, setMsg] = useState("");

  async function load() {
    const [p, d] = await Promise.all([api("/api/finance/payouts"), api("/api/finance/discrepancies")]);
    setPayouts(p);
    setGaps(d);
  }

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
  }, []);

  async function reconcile() {
    await api("/api/finance/reconcile", { method: "POST" });
    setMsg("Reconciliation pass complete");
    load();
  }

  async function resolve(id) {
    await api(`/api/finance/discrepancies/${id}/resolve`, { method: "POST" });
    load();
  }

  return (
    <Shell
      title="Payment reconciliation"
      eyebrow="Finance control"
      actions={
        <button className="btn" onClick={reconcile}>
          Match payouts
        </button>
      }
    >
      {msg ? <p style={{ color: "var(--mint)" }}>{msg}</p> : null}
      <div className="grid two">
        <div className="card">
          <h3>Payouts</h3>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Channel</th>
                <th>Received</th>
                <th>Expected</th>
                <th>Matches</th>
              </tr>
            </thead>
            <tbody>
              {payouts.map((p) => (
                <tr key={p.id}>
                  <td className="mono">{p.external_id}</td>
                  <td>{p.channel}</td>
                  <td>
                    <Money value={p.amount} />
                  </td>
                  <td>
                    <Money value={p.expected_amount} />
                  </td>
                  <td>{p.matches}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3>Discrepancies</h3>
          {gaps.length === 0 ? <p style={{ color: "var(--muted)" }}>No open gaps.</p> : null}
          {gaps.map((g) => (
            <div key={g.id} style={{ borderBottom: "1px solid var(--line)", padding: "10px 0" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <Pill value={g.kind} />
                <Money value={g.amount} />
              </div>
              <p style={{ margin: "8px 0 4px" }}>{g.description}</p>
              <p style={{ color: "var(--muted)", fontSize: 12 }}>{g.suggested_action}</p>
              <button className="btn ghost" onClick={() => resolve(g.id)}>
                Mark resolved
              </button>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
