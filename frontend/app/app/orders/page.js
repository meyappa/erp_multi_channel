"use client";

import { useEffect, useState } from "react";
import Shell, { Money, Pill } from "../../../components/Shell";
import { api } from "../../../lib/api";

export default function OrdersPage() {
  const [orders, setOrders] = useState([]);
  const [detail, setDetail] = useState(null);
  const [msg, setMsg] = useState("");

  async function load() {
    setOrders(await api("/api/orders"));
  }

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
  }, []);

  async function ingest() {
    const r = await api("/api/orders/ingest", { method: "POST" });
    setMsg(`Ingested from ${r.results.length} channels`);
    load();
  }

  async function open(id) {
    setDetail(await api(`/api/orders/${id}`));
  }

  return (
    <Shell
      title="Orders"
      eyebrow="Marketplace ingestion"
      actions={
        <button className="btn" onClick={ingest}>
          Pull latest orders
        </button>
      }
    >
      {msg ? <p style={{ color: "var(--mint)" }}>{msg}</p> : null}
      <div className="grid two">
        <div className="card">
          <h3>Inbox</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Channel</th>
                  <th>Total</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.id} onClick={() => open(o.id)} style={{ cursor: "pointer" }}>
                    <td className="mono">{o.order_number}</td>
                    <td>{o.channel}</td>
                    <td>
                      <Money value={o.total} />
                    </td>
                    <td>
                      <Pill value={o.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <h3>Gross profit snapshot</h3>
          {!detail ? (
            <p style={{ color: "var(--muted)" }}>Select an order to inspect auditable profit.</p>
          ) : (
            <>
              <p>
                {detail.order_number} · {detail.customer_name}
              </p>
              <table>
                <tbody>
                  {["selling_price", "cogs", "marketplace_fees", "shipping_cost", "returns_refunds", "ads", "gross_profit"].map(
                    (k) => (
                      <tr key={k}>
                        <td>{k.replaceAll("_", " ")}</td>
                        <td>
                          <Money value={detail.profit?.[k]} />
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
              <p className="mono" style={{ color: "var(--muted)", fontSize: 12 }}>
                {detail.profit?.formula}
              </p>
            </>
          )}
        </div>
      </div>
    </Shell>
  );
}
