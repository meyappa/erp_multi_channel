"use client";

import { useEffect, useMemo, useState } from "react";
import Shell, { Pill } from "../../../components/Shell";
import { api } from "../../../lib/api";

export default function AiLogPage() {
  const [data, setData] = useState({ items: [], counts: {}, labels: {}, total: 0 });
  const [jobType, setJobType] = useState("");
  const [trigger, setTrigger] = useState("");
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState(null);
  const [err, setErr] = useState("");

  async function load(nextJob, nextTrigger, nextStatus) {
    const params = new URLSearchParams();
    if (nextJob) params.set("job_type", nextJob);
    if (nextTrigger) params.set("trigger", nextTrigger);
    if (nextStatus) params.set("status", nextStatus);
    params.set("limit", "200");
    const qs = params.toString();
    setData(await api(`/api/ai/logs${qs ? `?${qs}` : ""}`));
  }

  useEffect(() => {
    load(jobType, trigger, status).catch((e) => setErr(e.message));
  }, []);

  const types = useMemo(() => Object.keys(data.labels || {}), [data.labels]);

  function apply(next) {
    const j = next.jobType !== undefined ? next.jobType : jobType;
    const t = next.trigger !== undefined ? next.trigger : trigger;
    const s = next.status !== undefined ? next.status : status;
    setJobType(j);
    setTrigger(t);
    setStatus(s);
    load(j, t, s).catch((e) => setErr(e.message));
  }

  function exportCsv() {
    const rows = [["id", "time", "job", "trigger", "actor", "status", "summary", "model", "ms"]];
    for (const r of data.items || []) {
      rows.push([r.id, r.created_at, r.job_type, r.trigger, r.actor, r.status, `"${(r.summary || "").replaceAll('"', "'")}"`, r.model, r.duration_ms]);
    }
    const blob = new Blob([rows.map((r) => r.join(",")).join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ai-automation-log.csv";
    a.click();
  }

  return (
    <Shell
      title="AI automation log"
      eyebrow="Audit trail"
      actions={
        <button className="btn ghost" onClick={exportCsv}>
          Export CSV
        </button>
      }
    >
      {err ? <p style={{ color: "var(--rose)" }}>{err}</p> : null}
      <div className="grid kpis" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="kpi-label">Events</div>
          <div className="kpi-value">{data.total || 0}</div>
        </div>
        {["forecast", "anomaly_scan", "listing_optimize", "chat"].map((k) => (
          <div className="card" key={k} style={{ cursor: "pointer" }} onClick={() => apply({ jobType: jobType === k ? "" : k })}>
            <div className="kpi-label">{data.labels?.[k] || k}</div>
            <div className="kpi-value">{data.counts?.[k] || 0}</div>
          </div>
        ))}
      </div>
      <div className="filters">
        <select value={jobType} onChange={(e) => apply({ jobType: e.target.value })}>
          <option value="">All automations</option>
          {types.map((t) => (
            <option key={t} value={t}>
              {data.labels[t] || t}
            </option>
          ))}
        </select>
        <select value={trigger} onChange={(e) => apply({ trigger: e.target.value })}>
          <option value="">All triggers</option>
          <option value="user">User</option>
          <option value="agent">Background agent</option>
        </select>
        <select value={status} onChange={(e) => apply({ status: e.target.value })}>
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
        </select>
      </div>
      <div className="grid two">
        <div className="card">
          <h3>Timeline</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>Automation</th>
                  <th>Trigger</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {(data.items || []).map((r) => (
                  <tr key={r.id} onClick={() => setSelected(r)} style={{ cursor: "pointer" }}>
                    <td className="mono">{r.created_at ? r.created_at.replace("T", " ").slice(0, 19) : ""}</td>
                    <td>
                      {r.label}
                      <div style={{ color: "var(--muted)", fontSize: 11, maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis" }}>
                        {r.summary}
                      </div>
                    </td>
                    <td>
                      <Pill value={r.trigger} />
                    </td>
                    <td>
                      <Pill value={r.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <h3>Event detail</h3>
          {!selected ? (
            <p style={{ color: "var(--muted)" }}>Select a log row to inspect input, output, model, and actor.</p>
          ) : (
            <>
              <p>
                <strong>{selected.label}</strong> · <Pill value={selected.status} />
              </p>
              <p style={{ color: "var(--muted)" }}>{selected.summary}</p>
              <table>
                <tbody>
                  <tr>
                    <td>Actor</td>
                    <td className="mono">{selected.actor}</td>
                  </tr>
                  <tr>
                    <td>Trigger</td>
                    <td>{selected.trigger}</td>
                  </tr>
                  <tr>
                    <td>Model</td>
                    <td className="mono">{selected.model}</td>
                  </tr>
                  <tr>
                    <td>Tokens</td>
                    <td>{selected.tokens_used}</td>
                  </tr>
                  <tr>
                    <td>Duration</td>
                    <td>{selected.duration_ms} ms</td>
                  </tr>
                  <tr>
                    <td>Entity</td>
                    <td className="mono">
                      {selected.entity_type} {selected.entity_id}
                    </td>
                  </tr>
                </tbody>
              </table>
              {selected.error ? <p style={{ color: "var(--rose)" }}>{selected.error}</p> : null}
              <h3 style={{ marginTop: 16 }}>Input</h3>
              <pre className="mono log-json">{pretty(selected.input_json)}</pre>
              <h3>Output</h3>
              <pre className="mono log-json">{pretty(selected.output_json)}</pre>
            </>
          )}
        </div>
      </div>
    </Shell>
  );
}

function pretty(raw) {
  try {
    return JSON.stringify(JSON.parse(raw || "{}"), null, 2);
  } catch {
    return raw || "{}";
  }
}
