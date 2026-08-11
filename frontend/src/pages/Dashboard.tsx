import { useEffect, useMemo, useState } from "react";
import { LegalDisclaimer } from "../components/LegalDisclaimer";
import { PriceChart } from "../components/PriceChart";
import { useLiveQuotes } from "../hooks/useLiveQuotes";
import { fetchCandles, fetchMarketOverview, fetchRecommendations } from "../services/api";
import type { Candle, MarketOverview, Recommendation } from "../types/market";

const SECTORS = ["الكل", "الطاقة", "البنوك", "المواد الأساسية", "الاتصالات", "الرعاية الصحية"];
const RISK_LEVELS = ["الكل", "low", "medium", "high"] as const;
const HORIZONS = [5, 10, 20] as const;

const DEMO_RECOS: Recommendation[] = [
  {
    symbol: "2222",
    name_ar: "أرامكو السعودية",
    sector: "الطاقة",
    action: "strong_buy",
    confidence: 0.84,
    explanation_ar: "زخم إيجابي مع RSI خارج التشبع وMACD صاعد.",
    risk_level: "low",
    entry_price: 28.4,
    stop_loss: 27.1,
    take_profit: 31.65,
  },
  {
    symbol: "1120",
    name_ar: "مصرف الراجحي",
    sector: "البنوك",
    action: "buy",
    confidence: 0.71,
    explanation_ar: "السعر فوق المتوسطات مع تقلب منخفض نسبياً.",
    risk_level: "medium",
    entry_price: 86.2,
    stop_loss: 83.0,
    take_profit: 94.2,
  },
  {
    symbol: "2010",
    name_ar: "سابك",
    sector: "المواد الأساسية",
    action: "hold",
    confidence: 0.52,
    explanation_ar: "إشارات متضاربة بين الزخم والمشاعر الإخبارية.",
    risk_level: "medium",
    entry_price: 72.5,
    stop_loss: 69.8,
    take_profit: 79.25,
  },
  {
    symbol: "1180",
    name_ar: "الأهلي السعودي",
    sector: "البنوك",
    action: "sell",
    confidence: 0.34,
    explanation_ar: "ضعف الزخم وارتفاع التقلب قصير الأجل.",
    risk_level: "high",
    entry_price: 38.1,
    stop_loss: 39.6,
    take_profit: 34.35,
  },
];

const actionLabel: Record<Recommendation["action"], string> = {
  strong_buy: "شراء قوي",
  buy: "شراء",
  hold: "محايد",
  sell: "بيع",
};

export function Dashboard() {
  const [overview, setOverview] = useState<MarketOverview | null>(null);
  const [recos, setRecos] = useState<Recommendation[]>(DEMO_RECOS);
  const [sector, setSector] = useState("الكل");
  const [risk, setRisk] = useState<(typeof RISK_LEVELS)[number]>("الكل");
  const [horizon, setHorizon] = useState<(typeof HORIZONS)[number]>(5);
  const [selected, setSelected] = useState("2222");
  const [candles, setCandles] = useState<Candle[]>([]);

  const watchSymbols = useMemo(() => {
    const fromRecos = recos.map((r) => r.symbol);
    return Array.from(new Set([selected, ...fromRecos]));
  }, [recos, selected]);

  const { quotes, status: wsStatus } = useLiveQuotes(watchSymbols);
  const live = quotes[selected];

  useEffect(() => {
    let alive = true;
    (async () => {
      const mkt = await fetchMarketOverview();
      if (!alive) return;
      setOverview(mkt);
      const liveRecos = await fetchRecommendations(horizon);
      if (!alive) return;
      if (liveRecos.length) setRecos(liveRecos);
    })();
    return () => {
      alive = false;
    };
  }, [horizon]);

  useEffect(() => {
    let alive = true;
    (async () => {
      const bars = await fetchCandles(selected, 120);
      if (!alive) return;
      setCandles(bars);
    })();
    return () => {
      alive = false;
    };
  }, [selected]);

  const filtered = useMemo(() => {
    return recos
      .filter((r) => (sector === "الكل" ? true : r.sector === sector))
      .filter((r) => (risk === "الكل" ? true : r.risk_level === risk))
      .sort((a, b) => b.confidence - a.confidence);
  }, [recos, sector, risk]);

  return (
    <div className="dash">
      <header className="dash__brand">
        <div>
          <p className="dash__eyebrow">أدوات تحليل سوق الأسهم السعودي</p>
          <h1 className="dash__logo">تاسي فيجن</h1>
          <p className="dash__logo-en">TASI Vision</p>
          <p className="dash__tag">
            بث سهمك الحي · أفق {horizon} أيام · حالة الاتصال:{" "}
            {wsStatus === "open" ? "متصل" : wsStatus === "connecting" ? "يتصل…" : "منقطع"}
          </p>
        </div>
        <div className="dash__pulse" aria-hidden />
      </header>

      <LegalDisclaimer />

      <section className="dash__overview" aria-label="مؤشرات السوق">
        <div className="metric">
          <span>مؤشر تاسي</span>
          <strong>{overview?.tasi_index ? overview.tasi_index.toLocaleString("ar-SA") : "—"}</strong>
          <em className={(overview?.tasi_change_pct ?? 0) >= 0 ? "up" : "down"}>
            {(overview?.tasi_change_pct ?? 0) >= 0 ? "+" : ""}
            {overview?.tasi_change_pct?.toFixed(2) ?? "0.00"}%
          </em>
        </div>
        <div className="metric">
          <span>رابحون</span>
          <strong>{overview?.advancers ?? "—"}</strong>
        </div>
        <div className="metric">
          <span>خاسرون</span>
          <strong>{overview?.decliners ?? "—"}</strong>
        </div>
        <div className="metric">
          <span>السهم المحدد</span>
          <strong>{live?.price?.toFixed(2) ?? "—"}</strong>
          <em className={(live?.change_pct ?? 0) >= 0 ? "up" : "down"}>
            {live?.change_pct != null
              ? `${live.change_pct >= 0 ? "+" : ""}${live.change_pct.toFixed(2)}%`
              : "بانتظار البث"}
          </em>
        </div>
      </section>

      <section className="dash__filters" aria-label="تصفية التوصيات">
        <label>
          القطاع
          <select value={sector} onChange={(e) => setSector(e.target.value)}>
            {SECTORS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          مستوى المخاطرة
          <select value={risk} onChange={(e) => setRisk(e.target.value as typeof risk)}>
            <option value="الكل">الكل</option>
            <option value="low">منخفض</option>
            <option value="medium">متوسط</option>
            <option value="high">مرتفع</option>
          </select>
        </label>
        <label>
          أفق التوصية
          <select
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value) as (typeof HORIZONS)[number])}
          >
            <option value={5}>5 أيام (أساسي)</option>
            <option value={10}>10 أيام</option>
            <option value={20}>20 يوم</option>
          </select>
        </label>
      </section>

      <div className="dash__grid">
        <section className="dash__chart-panel" aria-label="الرسم البياني">
          <div className="panel-head">
            <h2>
              {selected}
              {live?.price != null ? ` · ${live.price.toFixed(2)}` : ""}
            </h2>
            <p>
              شموع سهمك التاريخية
              {candles.length ? ` (${candles.length})` : " — جاري التحميل"}
              {live?.bid != null && live?.ask != null
                ? ` · عرض ${live.bid} / طلب ${live.ask}`
                : ""}
            </p>
          </div>
          {candles.length ? (
            <PriceChart candles={candles} />
          ) : (
            <p className="empty">لا تتوفر شموع حالياً لهذا الرمز</p>
          )}
        </section>

        <section className="dash__reco-panel" aria-label="قائمة التوصيات">
          <div className="panel-head">
            <h2>التحليلات</h2>
            <p>مرتبة حسب الثقة · أفق {horizon} أيام</p>
          </div>
          <ul className="reco-list">
            {filtered.map((r) => {
              const q = quotes[r.symbol];
              return (
                <li key={r.symbol}>
                  <button
                    type="button"
                    className={`reco ${selected === r.symbol ? "is-active" : ""}`}
                    onClick={() => setSelected(r.symbol)}
                  >
                    <div className="reco__top">
                      <strong>
                        {r.symbol}
                        {q?.price != null ? ` · ${q.price.toFixed(2)}` : ""}
                      </strong>
                      <span className={`badge badge--${r.action}`}>{actionLabel[r.action]}</span>
                    </div>
                    <p>{r.name_ar ?? r.sector}</p>
                    <div className="reco__meta">
                      <span>ثقة {(r.confidence * 100).toFixed(0)}%</span>
                      <span>
                        {r.entry_price} → TP {r.take_profit}
                      </span>
                    </div>
                    <small>{r.explanation_ar}</small>
                  </button>
                </li>
              );
            })}
            {!filtered.length && <li className="empty">لا توجد نتائج مطابقة للفلتر</li>}
          </ul>
        </section>
      </div>
    </div>
  );
}
