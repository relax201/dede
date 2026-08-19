export type RecAction = "strong_buy" | "buy" | "hold" | "sell";

export interface Company {
  symbol: string;
  name_ar?: string;
  name_en?: string;
  sector?: string;
}

export interface Recommendation {
  symbol: string;
  name_ar?: string;
  sector: string;
  action: RecAction;
  confidence: number;
  explanation_ar: string;
  risk_level: "low" | "medium" | "high";
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  shap?: Array<{ feature: string; shap_value: number }>;
}

export interface MarketOverview {
  tasi_index: number;
  tasi_change_pct: number;
  advancers: number;
  decliners: number;
  volume_total: number;
}

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}
