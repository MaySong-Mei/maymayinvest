// All operator calls go through one helper so headers (actor, reasoning, execute)
// stay consistent. Same surface used by humans and (later) by agent tools.

export type ActorType = "user" | "agent";

export interface CallOptions {
  actorType?: ActorType;
  actorId?: string;
  reasoning?: string;
  execute?: boolean;
}

export async function call<T>(
  capability: string,
  body?: unknown,
  opts: CallOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Actor-Type": opts.actorType ?? "user",
    "X-Actor-Id": opts.actorId ?? "me",
  };
  if (opts.reasoning) headers["X-Reasoning"] = opts.reasoning;
  if (opts.execute != null) headers["X-Execute"] = opts.execute ? "true" : "false";

  const res = await fetch(`/api/v1/op/${capability}`, {
    method: "POST",
    headers,
    body: body !== undefined ? JSON.stringify(body) : "{}",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${capability} [${res.status}]: ${text}`);
  }
  return res.json();
}

export interface Portfolio {
  account_id: string;
  base_currency: string;
  cash: string;
  equity: string | null;
  positions: Position[];
}

export interface Position {
  symbol: string;
  qty: string;
  avg_cost: string;
  sub_portfolio_id: string;
}

export interface Order {
  client_order_id: string;
  broker_order_id: string | null;
  symbol: string;
  side: "buy" | "sell";
  qty: string;
  type: string;
  state: string;
  limit_price: string | null;
  tif: string;
  created_at: string;
}
