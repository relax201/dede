import type {
  Candle,
  Company,
  MarketDepth,
  MarketOverview,
  Recommendation,
  TradesTape,
} from "../types/market";

const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

function url(path: string): string {
  return `${API_URL}${path}`;
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url(path), init);
  if (!res.ok) {
    let detail = `API ${path} failed: ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function fetchHealthDetail(): Promise<{
  status: string;
  postgres: boolean;
  redis: boolean;
}> {
  try {
    return await getJson("/api/health/detail");
  } catch {
    return { status: "error", postgres: false, redis: false };
  }
}

export async function fetchMarketOverview(): Promise<MarketOverview> {
  try {
    return await getJson<MarketOverview>("/api/market/overview");
  } catch {
    return {
      tasi_index: 0,
      tasi_change_pct: 0,
      advancers: 0,
      decliners: 0,
      volume_total: 0,
    };
  }
}

export async function fetchCandles(
  symbol: string,
  limit = 120,
  interval = "1d"
): Promise<Candle[]> {
  try {
    const data = await getJson<{ candles: Candle[] }>(
      `/api/stock/${encodeURIComponent(symbol)}/candles?interval=${encodeURIComponent(interval)}&limit=${limit}`
    );
    return data.candles ?? [];
  } catch {
    return [];
  }
}

export async function fetchDepth(symbol: string, levels = 10): Promise<MarketDepth | null> {
  try {
    return await getJson<MarketDepth>(
      `/api/stock/${encodeURIComponent(symbol)}/depth?levels=${levels}`
    );
  } catch {
    return null;
  }
}

export async function fetchTrades(symbol: string, limit = 40): Promise<TradesTape | null> {
  try {
    return await getJson<TradesTape>(
      `/api/stock/${encodeURIComponent(symbol)}/trades?limit=${limit}`
    );
  } catch {
    return null;
  }
}

export async function fetchStock(symbol: string) {
  return getJson<{
    symbol: string;
    name_ar: string;
    name_en: string;
    sector: string;
    price: number;
    change_pct: number;
    volume: number;
    high?: number | null;
    low?: number | null;
    stale?: boolean;
  }>(`/api/stock/${encodeURIComponent(symbol)}`);
}

export async function fetchCompanies(query = ""): Promise<Company[]> {
  try {
    const q = query.trim() ? `q=${encodeURIComponent(query.trim())}` : "";
    const data = await getJson<{ results: Company[] }>(`/api/companies?${q}`);
    return data.results ?? [];
  } catch {
    return [];
  }
}

export async function fetchRecommendations(horizon: number = 5): Promise<Recommendation[]> {
  try {
    const data = await getJson<{ results: Recommendation[] }>(
      `/api/recommendations?horizon=${horizon}&limit=5`
    );
    return (data.results ?? []).map((reco) => ({
      ...reco,
      sector: reco.sector ?? "غير محدد",
      risk_level:
        reco.risk_level ??
        (reco.confidence > 0.75 ? "low" : reco.confidence > 0.55 ? "medium" : "high"),
    }));
  } catch {
    // Fallback: fetch a few known symbols individually
    const symbols = ["2222", "1120", "1180", "1010", "2010"];
    const results: Recommendation[] = [];
    for (const symbol of symbols) {
      try {
        const reco = await fetchRecommendation(symbol, horizon);
        if (reco) results.push(reco);
      } catch {
        // skip
      }
    }
    return results.sort((a, b) => b.confidence - a.confidence);
  }
}

export async function fetchRecommendation(symbol: string, horizon = 5): Promise<Recommendation | null> {
  try {
    const reco = await getJson<Recommendation & { shap?: Array<{ feature: string; shap_value: number }> }>(
      `/api/recommendation/${encodeURIComponent(symbol)}?horizon=${horizon}`
    );
    return {
      ...reco,
      sector: reco.sector ?? "غير محدد",
      risk_level:
        reco.risk_level ??
        (reco.confidence > 0.75 ? "low" : reco.confidence > 0.55 ? "medium" : "high"),
    };
  } catch {
    return null;
  }
}

export async function registerAccount(email: string, password: string, fullName: string) {
  return getJson<{ access_token: string; email: string; role: string }>("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
}

export async function loginAccount(email: string, password: string) {
  return getJson<{ access_token: string; email: string; role: string }>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function createPortfolio(
  token: string,
  name: string,
  capital: number,
  symbol: string,
  avgCost: number
) {
  return getJson("/api/portfolio", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      name,
      capital,
      holdings: symbol
        ? [{ symbol, quantity: 10, avg_cost: Math.max(avgCost, 0.01) }]
        : [],
    }),
  });
}

export async function listPortfolios(token: string) {
  return getJson<{
    results: Array<{ id: string; name: string; capital: number; holdings_count: number }>;
  }>("/api/portfolio", { headers: { Authorization: `Bearer ${token}` } });
}

export async function fetchPortfolioPerformance(token: string, id: string) {
  return getJson<{
    return_pct: number;
    market_value: number;
    unrealized_pnl: number;
    holdings: Array<{ symbol: string; last_price: number; unrealized_pnl: number }>;
  }>(`/api/portfolio/${id}/performance`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function liveSocketUrl(): string {
  const explicit = (import.meta.env.VITE_WS_URL ?? "").replace(/\/$/, "");
  if (explicit) return `${explicit}/ws/live`;
  if (typeof window === "undefined") return "ws://localhost:8000/ws/live";
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/live`;
}
