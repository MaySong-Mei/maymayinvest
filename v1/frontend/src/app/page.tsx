"use client";

import { useEffect, useState } from "react";
import { call, type Portfolio, type Order } from "@/lib/api";

export default function Dashboard() {
  const [pf, setPf] = useState<Portfolio | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setErr(null);
    try {
      const [p, o] = await Promise.all([
        call<Portfolio>("get_portfolio"),
        call<Order[]>("get_open_orders"),
      ]);
      setPf(p);
      setOrders(o);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-6 max-w-4xl">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <button
          onClick={refresh}
          className="text-sm px-3 py-1 rounded border border-[var(--border)] hover:bg-[var(--surface)]"
        >
          Refresh
        </button>
      </header>

      {err && (
        <div className="rounded border border-[var(--negative)] bg-[var(--negative)]/10 text-[var(--negative)] p-3 text-sm">
          {err}
        </div>
      )}

      <section className="grid grid-cols-3 gap-4">
        <Card label="Account">
          <div className="text-lg">{pf?.account_id ?? (loading ? "…" : "—")}</div>
        </Card>
        <Card label="Cash">
          <div className="text-lg">{pf ? `$${Number(pf.cash).toLocaleString()}` : "…"}</div>
        </Card>
        <Card label="Equity">
          <div className="text-lg">
            {pf?.equity ? `$${Number(pf.equity).toLocaleString()}` : "…"}
          </div>
        </Card>
      </section>

      <section>
        <h2 className="text-sm font-semibold mb-2 text-[var(--text-dim)]">Positions</h2>
        <Table
          cols={["Symbol", "Qty", "Avg cost", "Sub-portfolio"]}
          rows={
            pf?.positions.length
              ? pf.positions.map((p) => [p.symbol, p.qty, p.avg_cost, p.sub_portfolio_id])
              : []
          }
          empty="No open positions"
        />
      </section>

      <section>
        <h2 className="text-sm font-semibold mb-2 text-[var(--text-dim)]">Open orders</h2>
        <Table
          cols={["Symbol", "Side", "Qty", "Type", "State"]}
          rows={orders.map((o) => [o.symbol, o.side, o.qty, o.type, o.state])}
          empty="No open orders"
        />
      </section>
    </div>
  );
}

function Card({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="text-xs uppercase tracking-wide text-[var(--text-dim)] mb-1">{label}</div>
      {children}
    </div>
  );
}

function Table({
  cols,
  rows,
  empty,
}: {
  cols: string[];
  rows: (string | number)[][];
  empty: string;
}) {
  if (rows.length === 0)
    return <div className="text-sm text-[var(--text-dim)] italic">{empty}</div>;
  return (
    <div className="rounded border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      <table className="w-full text-sm">
        <thead className="text-[var(--text-dim)] text-xs uppercase">
          <tr>
            {cols.map((c) => (
              <th key={c} className="text-left px-4 py-2 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-[var(--border)]">
              {r.map((cell, j) => (
                <td key={j} className="px-4 py-2">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
