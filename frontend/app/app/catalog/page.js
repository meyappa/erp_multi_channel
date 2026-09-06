"use client";

import { useEffect, useState } from "react";
import Shell, { Money, Pill } from "../../../components/Shell";
import { api } from "../../../lib/api";

export default function CatalogPage() {
  const [products, setProducts] = useState([]);
  const [listings, setListings] = useState([]);
  const [q, setQ] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    const [p, l] = await Promise.all([api(`/api/catalog/products${q ? `?q=${encodeURIComponent(q)}` : ""}`), api("/api/catalog/listings")]);
    setProducts(p);
    setListings(l);
  }

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
  }, []);

  async function bulk(status) {
    const ids = listings.filter((x) => x.status !== status).slice(0, 5).map((x) => x.id);
    await api("/api/catalog/listings/bulk-status", { method: "POST", body: JSON.stringify({ listing_ids: ids, status }) });
    setMsg(`Updated ${ids.length} listings to ${status}`);
    load();
  }

  async function optimize(id) {
    const out = await api(`/api/ai/listings/${id}/optimize`, { method: "POST" });
    setMsg(`Suggested title: ${out.title}`);
  }

  return (
    <Shell
      title="Catalog & listings"
      eyebrow="Listing management"
      actions={
        <>
          <button className="btn ghost" onClick={() => bulk("paused")}>
            Pause sample
          </button>
          <button className="btn" onClick={() => bulk("active")}>
            Activate sample
          </button>
        </>
      }
    >
      {msg ? <p style={{ color: "var(--mint)" }}>{msg}</p> : null}
      <div className="filters">
        <input placeholder="Search SKU or title" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn ghost" onClick={load}>
          Search
        </button>
      </div>
      <div className="grid two">
        <div className="card">
          <h3>Central catalog</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Title</th>
                  <th>Type</th>
                  <th>COGS</th>
                  <th>Listings</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id}>
                    <td className="mono">{p.sku}</td>
                    <td>{p.title}</td>
                    <td>
                      <Pill value={p.product_type} />
                    </td>
                    <td>
                      <Money value={p.cogs} />
                    </td>
                    <td>{p.listings_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <h3>Channel listings</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Channel</th>
                  <th>SKU</th>
                  <th>Price</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {listings.map((l) => (
                  <tr key={l.id}>
                    <td>{l.channel}</td>
                    <td className="mono">{l.sku}</td>
                    <td>
                      <Money value={l.price} />
                    </td>
                    <td>
                      <Pill value={l.status} />
                    </td>
                    <td>
                      <button className="btn ghost" onClick={() => optimize(l.id)}>
                        AI copy
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Shell>
  );
}
