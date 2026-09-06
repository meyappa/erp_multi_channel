"use client";

import { useEffect, useState } from "react";
import Shell, { Money, Pill } from "../../../components/Shell";
import { api } from "../../../lib/api";

export default function ReturnsPage() {
  const [rows, setRows] = useState([]);
  const [msg, setMsg] = useState("");

  async function load() {
    setRows(await api("/api/returns"));
  }

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
  }, []);

  async function decide(id, action, restock) {
    await api(`/api/returns/${id}/decide`, { method: "POST", body: JSON.stringify({ action, restock }) });
    setMsg(`${action} recorded`);
    load();
  }

  return (
    <Shell title="Returns / RMA" eyebrow="Reverse logistics">
      {msg ? <p style={{ color: "var(--mint)" }}>{msg}</p> : null}
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>RMA</th>
              <th>Order</th>
              <th>Reason</th>
              <th>AI</th>
              <th>Refund</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="mono">{r.rma_number}</td>
                <td>{r.order_number}</td>
                <td>{r.reason_code}</td>
                <td>
                  {r.ai_category}
                  <div style={{ color: "var(--muted)", fontSize: 11 }}>{r.suggested_resolution}</div>
                </td>
                <td>
                  <Money value={r.refund_amount} />
                </td>
                <td>
                  <Pill value={r.status} />
                </td>
                <td className="row-actions">
                  <button className="btn" onClick={() => decide(r.id, "approve", true)}>
                    Approve + restock
                  </button>
                  <button className="btn ghost" onClick={() => decide(r.id, "reject", false)}>
                    Reject
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
