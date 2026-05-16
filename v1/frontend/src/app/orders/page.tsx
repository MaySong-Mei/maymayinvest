"use client";

import { useEffect, useState } from "react";
import { call, type Order } from "@/lib/api";

export default function OrdersPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [qty, setQty] = useState("1");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [last, setLast] = useState<Order | null>(null);
  const [open, setOpen] = useState<Order[]>([]);

  const refresh = async () => {
    try {
      const o = await call<Order[]>("get_open_orders");
      setOpen(o);
    } catch (e) {
      setErr(String(e));
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const submit = async () => {
    setBusy(true);
    setErr(null);
    try {
      const o = await call<Order>("submit_order", {
        symbol,
        side,
        qty,
        type: "market",
      });
      setLast(o);
      await refresh();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-xl font-semibold">Orders (manual user)</h1>

      <section className="rounded border border-[var(--border)] bg-[var(--surface)] p-4 space-y-3">
        <h2 className="text-sm text-[var(--text-dim)]">New market order</h2>
        <div className="grid grid-cols-3 gap-3 items-end">
          <Field label="Symbol">
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm"
            />
          </Field>
          <Field label="Side">
            <select
              value={side}
              onChange={(e) => setSide(e.target.value as "buy" | "sell")}
              className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm"
            >
              <option value="buy">buy</option>
              <option value="sell">sell</option>
            </select>
          </Field>
          <Field label="Qty">
            <input
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm"
            />
          </Field>
        </div>
        <button
          disabled={busy}
          onClick={submit}
          className="text-sm px-4 py-2 rounded bg-[var(--accent)] hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "submitting…" : "Submit (user, immediate)"}
        </button>
      </section>

      {err && (
        <div className="rounded border border-[var(--negative)] bg-[var(--negative)]/10 text-[var(--negative)] p-3 text-sm whitespace-pre-wrap">
          {err}
        </div>
      )}

      {last && (
        <section>
          <h2 className="text-sm font-semibold mb-2 text-[var(--text-dim)]">Last result</h2>
          <pre className="text-xs bg-[var(--surface)] border border-[var(--border)] rounded p-3 overflow-auto">
            {JSON.stringify(last, null, 2)}
          </pre>
        </section>
      )}

      <section>
        <h2 className="text-sm font-semibold mb-2 text-[var(--text-dim)]">Open orders</h2>
        {open.length === 0 ? (
          <div className="text-sm text-[var(--text-dim)] italic">No open orders (paper fills market orders instantly)</div>
        ) : (
          <pre className="text-xs bg-[var(--surface)] border border-[var(--border)] rounded p-3 overflow-auto">
            {JSON.stringify(open, null, 2)}
          </pre>
        )}
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="space-y-1 block">
      <div className="text-xs text-[var(--text-dim)] uppercase tracking-wide">{label}</div>
      {children}
    </label>
  );
}
