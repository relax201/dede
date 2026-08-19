import type { Candle, Company, MarketOverview, Recommendation } from "../types/market";

const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

function url(path: string): string {
  return `${API_URL}${path}`;
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url(path), init);
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
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

export async function fetchCandles(symbol: string, limit = 120): Promise<Candle[]> {
  try {
    const data = await getJson<{ candles: Candle[] }>(
      `/api/stock/${encodeURIComponent(symbol)}/candles?interval=1d&limit=${limit}`
    );
    return data.candles ?? [];
  } catch {
    return [];
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
    const q = query.trim() ? `&q=${encodeURIComponent(query.trim())}` : "";
    const data = await getJson<{ results: Company[] }>(`/api/companies?${q}`);
    return data.results ?? [];
  } catch {
    return [];
  }
}

export async function fetchRecommendations(horizon: number = 5): Promise<Recommendation[]> {
  try {
    const data = await getJson<{ results: Recommendation[] }>(
      `/api/recommendations?horizon=${horizon}&limit=8`
    );
    return (data.results ?? []).map((reco) => ({
      ...reco,
      sector: reco.sector ?? "غير محدد",
      risk_level:
        reco.risk_level ??
        (reco.confidence > 0.75 ? "low" : reco.confidence > 0.55 ? "medium" : "high"),
    }));
  } catch {
    return [];
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

export async function createPortfolio(token: string, name: string, capital: number, symbol: string) {
  return getJson("/api/portfolio", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      name,
      capital,
      holdings: symbol ? [{ symbol, quantity: 10, avg_cost: 1 }] : [],
    }),
  });
}

export async function listPortfolios(token: string) {
  return getJson<{ results: Array<{ id: string; name: string; capital: number; holdings_count: number }> }>(
    "/api/portfolio",
    { headers: { Authorization: `Bearer ${token}` } }
  );
}

export function liveSocketUrl(): string {
  const explicit = (import.meta.env.VITE_WS_URL ?? "").replace(/\/$/, "");
  if (explicit) return `${explicit}/ws/live`;
  if (typeof window === "undefined") return "ws://localhost:8000/ws/live";
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/live`;
}
