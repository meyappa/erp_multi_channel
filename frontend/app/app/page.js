"use client";

import { useEffect, useState } from "react";
import Shell, { Money, Pill } from "../../components/Shell";
import { api } from "../../lib/api";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api("/api/dashboard")
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  const k = data?.kpis || {};
  const max = Math.max(...Object.values(data?.profit_by_channel || {}).map(Number), 1);

  return (
    <Shell title="Command center" eyebrow="Live operations">
      {err ? <p style={{ color: "var(--rose)" }}>{err}</p> : null}
      <div className="grid kpis">
        <div className="card">
          <div className="kpi-label">Revenue</div>
          <div className="kpi-value">
            <Money value={k.revenue} />
          </div>
          <div className="kpi-sub">{k.orders || 0} orders ingested</div>
        </div>
        <div className="card">
          <div className="kpi-label">Gross profit</div>
          <div className="kpi-value">
            <Money value={k.gross_profit} />
          </div>
          <div className="kpi-sub">{k.margin_pct || 0}% margin</div>
        </div>
        <div className="card">
          <div className="kpi-label">On-hand units</div>
          <div className="kpi-value">{k.units_on_hand || 0}</div>
          <div className="kpi-sub">{k.products || 0} SKUs · {k.listings || 0} listings</div>
        </div>
        <div className="card">
          <div className="kpi-label">Exceptions</div>
          <div className="kpi-value">{(k.open_discrepancies || 0) + (k.open_returns || 0)}</div>
          <div className="kpi-sub">
            {k.open_discrepancies || 0} payout gaps · {k.open_returns || 0} RMAs
          </div>
        </div>
      </div>
      <div className="grid two" style={{ marginTop: 16 }}>
        <div className="card">
          <h3>Profit by channel</h3>
          <div className="bars">
            {Object.entries(data?.profit_by_channel || {}).map(([ch, val]) => (
              <div className="bar-row" key={ch}>
                <span>{ch || "n/a"}</span>
                <div className="bar">
                  <span style={{ width: `${(Number(val) / max) * 100}%` }} />
                </div>
                <Money value={val} />
              </div>
            ))}
          </div>
          <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 14 }} className="mono">
            {data?.formula}
          </p>
        </div>
        <div className="card">
          <h3>Connected marketplaces</h3>
          <table>
            <thead>
              <tr>
                <th>Channel</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {(data?.channels || []).map((c) => (
                <tr key={c.id}>
                  <td>
                    {c.name}
                    <div style={{ color: "var(--muted)", fontSize: 11 }}>{c.marketplace}</div>
                  </td>
                  <td>
                    <Pill value={c.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
