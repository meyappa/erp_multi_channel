"use client";

import { useEffect, useState } from "react";
import Shell, { Pill } from "../../../components/Shell";
import { api } from "../../../lib/api";

export default function InventoryPage() {
  const [balances, setBalances] = useState([]);
  const [events, setEvents] = useState([]);
  const [forecasts, setForecasts] = useState([]);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const [b, e] = await Promise.all([api("/api/inventory/balances"), api("/api/inventory/sync-events")]);
    setBalances(b);
    setEvents(e);
  }

  useEffect(() => {
    load().catch((err) => setMsg(err.message));
  }, []);

  async function sync() {
    setBusy(true);
    try {
      const r = await api("/api/inventory/sync", { method: "POST" });
      setMsg(`Synced ${r.results.length} channels`);
      await load();
    } catch (err) {
      setMsg(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function forecast() {
    const r = await api("/api/inventory/forecast", { method: "POST" });
    setForecasts(r.forecasts || []);
  }

  return (
    <Shell
      title="Inventory mesh"
      eyebrow="Multi-warehouse sync"
      actions={
        <>
          <button className="btn ghost" onClick={forecast}>
            Forecast 30d
          </button>
          <button className="btn" disabled={busy} onClick={sync}>
            {busy ? "Syncing…" : "Sync all channels"}
          </button>
        </>
      }
    >
      {msg ? <p style={{ color: "var(--mint)" }}>{msg}</p> : null}
      <div className="card" style={{ marginBottom: 16 }}>
        <h3>Balances</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Warehouse</th>
                <th>On hand</th>
                <th>Reserved</th>
                <th>Available</th>
                <th>Safety</th>
              </tr>
            </thead>
            <tbody>
              {balances.map((b) => (
                <tr key={b.id}>
                  <td className="mono">{b.sku}</td>
                  <td>{b.warehouse}</td>
                  <td>{b.on_hand}</td>
                  <td>{b.reserved}</td>
                  <td>{b.available}</td>
                  <td>{b.safety_stock}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="grid two">
        <div className="card">
          <h3>Sync audit</h3>
          <table>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Dir</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {events.slice(0, 12).map((e) => (
                <tr key={e.id}>
                  <td className="mono">{e.entity_id}</td>
                  <td>{e.direction}</td>
                  <td>
                    <Pill value={e.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3>Replenishment suggestions</h3>
          {forecasts.length === 0 ? (
            <p style={{ color: "var(--muted)" }}>Run a 30-day forecast to see suggested PO quantities.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Variant</th>
                  <th>Demand</th>
                  <th>Buy</th>
                </tr>
              </thead>
              <tbody>
                {forecasts.slice(0, 10).map((f) => (
                  <tr key={`${f.variant_id}-${f.predicted_demand_30d}`}>
                    <td>{f.variant_id}</td>
                    <td>{f.predicted_demand_30d}</td>
                    <td>{f.suggested_replenish}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </Shell>
  );
}
