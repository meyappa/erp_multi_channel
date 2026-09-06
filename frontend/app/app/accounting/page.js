"use client";

import { useEffect, useState } from "react";
import Shell, { Money, Pill } from "../../../components/Shell";
import { api } from "../../../lib/api";

export default function AccountingPage() {
  const [conns, setConns] = useState([]);
  const [maps, setMaps] = useState([]);
  const [journals, setJournals] = useState([]);
  const [msg, setMsg] = useState("");

  async function load() {
    const [c, m, j] = await Promise.all([
      api("/api/accounting/connections"),
      api("/api/accounting/mappings"),
      api("/api/accounting/journals"),
    ]);
    setConns(c);
    setMaps(m);
    setJournals(j);
  }

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
  }, []);

  async function sync(id) {
    const r = await api(`/api/accounting/sync/${id}`, { method: "POST" });
    setMsg(`Posted ${r.posted} journal lines to ${r.provider}`);
    load();
  }

  return (
    <Shell title="Accounting sync" eyebrow="Xero / QuickBooks / Wave">
      {msg ? <p style={{ color: "var(--mint)" }}>{msg}</p> : null}
      <div className="grid two">
        <div className="card">
          <h3>Connections</h3>
          {conns.map((c) => (
            <div key={c.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <div>
                <strong>{c.name}</strong>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>{c.provider}</div>
              </div>
              <button className="btn" onClick={() => sync(c.id)}>
                Push journals
              </button>
            </div>
          ))}
          <h3 style={{ marginTop: 18 }}>Mapping rules</h3>
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Account</th>
              </tr>
            </thead>
            <tbody>
              {maps.map((m) => (
                <tr key={m.id}>
                  <td>{m.source_code}</td>
                  <td>
                    {m.target_account} {m.target_account_name}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3>Journal entries</h3>
          <table>
            <thead>
              <tr>
                <th>Memo</th>
                <th>Dr</th>
                <th>Cr</th>
                <th>Amt</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {journals.map((j) => (
                <tr key={j.id}>
                  <td>{j.memo}</td>
                  <td className="mono">{j.debit_account}</td>
                  <td className="mono">{j.credit_account}</td>
                  <td>
                    <Money value={j.amount} />
                  </td>
                  <td>
                    <Pill value={j.status} />
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
