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
  time: string | number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface DepthLevel {
  level?: number | null;
  price: number | null;
  quantity: number;
  order_count?: number | null;
}

export interface MarketDepth {
  symbol: string;
  updated_at?: string | null;
  session?: string | null;
  book_state?: string | null;
  levels?: number | null;
  entitled_levels?: number | null;
  best_bid?: number | null;
  best_ask?: number | null;
  spread?: number | null;
  spread_bps?: number | null;
  level_imbalance?: number | null;
  bids: DepthLevel[];
  asks: DepthLevel[];
}

export interface TradeEvent {
  event_time?: string | null;
  price: number | null;
  quantity: number;
  value?: number | null;
  side?: string | null;
}

export interface TradesTape {
  symbol: string;
  updated_at?: string | null;
  count: number;
  summary?: {
    event_count?: number | null;
    trade_quantity?: number | null;
    trade_value?: number | null;
    latest_event_time?: string | null;
  };
  events: TradeEvent[];
}
