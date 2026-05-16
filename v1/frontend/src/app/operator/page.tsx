"use client";

import { useState } from "react";
import { call } from "@/lib/api";

/**
 * Operator console — same surface, agent identity + reasoning + dry-run toggle.
 * Use this to see what an agent's call to the system looks like end-to-end.
 */
export default function OperatorConsole() {
  const [capability, setCapability] = useState("submit_order");
  const [actorType, setActorType] = useState<"user" | "agent">("agent");
  const [actorId, setActorId] = useState("claude");
  const [reasoning, setReasoning] = useState("ma_cross_confirmed long entry");
  const [execute, setExecute] = useState(false);
  const [body, setBody] = useState(
    JSON.stringify({ symbol: "AAPL", side: "buy", qty: "1", type: "market" }, null, 2),
  );
  const [result, setResult] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const send = async () => {
    setBusy(true);
    setResult("");
    try {
      const parsed = body.trim() ? JSON.parse(body) : undefined;
      const r = await call(capability, parsed, {
        actorType,
        actorId,
        reasoning,
        execute,
      });
      setResult(JSON.stringify(r, null, 2));
    } catch (e) {
      setResult(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-xl font-semibold">Operator Console</h1>
      <p className="text-xs text-[var(--text-dim)]">
        Same /api/v1/op/* surface a human uses. Agent + missing reasoning ⇒ 403. Agent + reasoning
        + execute=off ⇒ <code>dry_run</code>. Toggle <code>execute</code> to actually submit.
      </p>

      <div className="grid grid-cols-2 gap-3">
        <Labeled label="Capability">
          <select
            value={capability}
            onChange={(e) => setCapability(e.target.value)}
            className="bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm w-full"
          >
            {[
              "get_portfolio",
              "get_open_orders",
              "get_last_price",
              "submit_order",
              "cancel_order",
              "kill_switch",
            ].map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </Labeled>
        <Labeled label="Actor Type">
          <select
            value={actorType}
            onChange={(e) => setActorType(e.target.value as "user" | "agent")}
            className="bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm w-full"
          >
            <option value="user">user</option>
            <option value="agent">agent</option>
          </select>
        </Labeled>
        <Labeled label="Actor ID">
          <input
            value={actorId}
            onChange={(e) => setActorId(e.target.value)}
            className="bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm w-full"
          />
        </Labeled>
        <Labeled label="Reasoning (required for agent + act)">
          <input
            value={reasoning}
            onChange={(e) => setReasoning(e.target.value)}
            className="bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm w-full"
          />
        </Labeled>
      </div>

      <Labeled label="Request body (JSON; omitted for no-input capabilities)">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={8}
          className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-2 text-xs font-mono"
        />
      </Labeled>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={execute}
          onChange={(e) => setExecute(e.target.checked)}
        />
        execute (uncheck = dry-run for agents)
      </label>

      <button
        disabled={busy}
        onClick={send}
        className="text-sm px-4 py-2 rounded bg-[var(--accent)] hover:opacity-90 disabled:opacity-50"
      >
        {busy ? "sending…" : "Send"}
      </button>

      {result && (
        <pre className="text-xs bg-[var(--surface)] border border-[var(--border)] rounded p-3 overflow-auto whitespace-pre-wrap">
          {result}
        </pre>
      )}
    </div>
  );
}

function Labeled({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="space-y-1 block">
      <div className="text-xs text-[var(--text-dim)] uppercase tracking-wide">{label}</div>
      {children}
    </label>
  );
}
