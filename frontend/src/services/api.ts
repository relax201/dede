import type { MarketOverview, Recommendation } from "../types/market";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchMarketOverview(): Promise<MarketOverview> {
  try {
    return await getJson<MarketOverview>("/api/market/overview");
  } catch {
    // Dev fallback until market overview endpoint is wired
    return {
      tasi_index: 11842.35,
      tasi_change_pct: 0.42,
      advancers: 98,
      decliners: 71,
      volume_total: 3.2e9,
    };
  }
}

export async function fetchRecommendations(): Promise<Recommendation[]> {
  // Aggregated list endpoint can be added later; compose from known symbols for demo shell
  const symbols = ["2222.SR", "1120.SR", "2010.SR", "1180.SR", "1010.SR"];
  const results: Recommendation[] = [];
  for (const symbol of symbols) {
    try {
      const reco = await getJson<{
        symbol: string;
        action: Recommendation["action"];
        confidence: number;
        explanation_ar: string;
        entry_price: number;
        stop_loss: number;
        take_profit: number;
      }>(`/api/recommendation/${symbol}`);
      results.push({
        symbol: reco.symbol,
        sector: "غير محدد",
        action: reco.action,
        confidence: reco.confidence,
        explanation_ar: reco.explanation_ar,
        risk_level: reco.confidence > 0.75 ? "low" : reco.confidence > 0.55 ? "medium" : "high",
        entry_price: reco.entry_price,
        stop_loss: reco.stop_loss,
        take_profit: reco.take_profit,
      });
    } catch {
      // skip unavailable symbols in local shell
    }
  }
  return results.sort((a, b) => b.confidence - a.confidence);
}

export function liveSocketUrl(): string {
  const base = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
  return `${base}/ws/live`;
}
