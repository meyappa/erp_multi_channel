"use client";

import { useEffect, useState } from "react";
import Shell, { Money } from "../../../components/Shell";
import { api } from "../../../lib/api";

export default function ProfitPage() {
  const [report, setReport] = useState(null);
  const [sku, setSku] = useState("");

  async function load(nextSku) {
    const qs = nextSku ? `?sku=${encodeURIComponent(nextSku)}` : "";
    setReport(await api(`/api/finance/profit${qs}`));
  }

  useEffect(() => {
    load().catch(() => {});
  }, []);

  function exportCsv() {
    if (!report) return;
    const rows = [["order", "channel", "sku", "selling", "cogs", "fees", "ship", "refunds", "ads", "gp"]];
    for (const o of report.orders || []) {
      rows.push([o.order_number, o.channel, o.sku, o.selling_price, o.cogs, o.marketplace_fees, o.shipping_cost, o.returns_refunds, o.ads, o.gross_profit]);
    }
    const blob = new Blob([rows.map((r) => r.join(",")).join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "gross-profit.csv";
    a.click();
  }

  const t = report?.totals || {};

  return (
    <Shell
      title="Gross profit"
      eyebrow="Auditable P&L"
      actions={
        <button className="btn ghost" onClick={exportCsv}>
          Export CSV
        </button>
      }
    >
      <div className="filters">
        <input placeholder="Filter SKU" value={sku} onChange={(e) => setSku(e.target.value)} />
        <button className="btn ghost" onClick={() => load(sku)}>
          Apply
        </button>
      </div>
      <div className="grid kpis">
        {[
          ["Selling", t.selling_price],
          ["COGS", t.cogs],
          ["Fees", t.marketplace_fees],
          ["Gross profit", t.gross_profit],
        ].map(([label, val]) => (
          <div className="card" key={label}>
            <div className="kpi-label">{label}</div>
            <div className="kpi-value">
              <Money value={val} />
            </div>
          </div>
        ))}
      </div>
      <p className="mono" style={{ color: "var(--muted)", margin: "16px 0" }}>
        {report?.formula} · margin {report?.margin_pct}%
      </p>
      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Order</th>
                <th>Channel</th>
                <th>SKU</th>
                <th>GP</th>
                <th>Margin</th>
              </tr>
            </thead>
            <tbody>
              {(report?.orders || []).map((o) => (
                <tr key={o.order_id}>
                  <td className="mono">{o.order_number}</td>
                  <td>{o.channel}</td>
                  <td>{o.sku}</td>
                  <td>
                    <Money value={o.gross_profit} />
                  </td>
                  <td>{o.margin_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
