import { FormEvent, useEffect, useMemo, useState } from "react";
import { LegalDisclaimer } from "../components/LegalDisclaimer";
import { PriceChart } from "../components/PriceChart";
import { useLiveQuotes } from "../hooks/useLiveQuotes";
import {
  createPortfolio,
  fetchCandles,
  fetchCompanies,
  fetchMarketOverview,
  fetchRecommendations,
  fetchStock,
  listPortfolios,
  loginAccount,
  registerAccount,
} from "../services/api";
import type { Candle, Company, MarketOverview, Recommendation } from "../types/market";

const RISK_LEVELS = ["الكل", "low", "medium", "high"] as const;
const HORIZONS = [5, 10, 20] as const;
const TOKEN_KEY = "tasi.token";

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
  const [companies, setCompanies] = useState<Company[]>([]);
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState<(typeof RISK_LEVELS)[number]>("الكل");
  const [horizon, setHorizon] = useState<(typeof HORIZONS)[number]>(5);
  const [selected, setSelected] = useState("2222");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [stockName, setStockName] = useState("2222");
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) ?? "");
  const [authMsg, setAuthMsg] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [portfolios, setPortfolios] = useState<Array<{ id: string; name: string; capital: number }>>([]);

  const watchSymbols = useMemo(() => {
    const fromRecos = recos.map((r) => r.symbol);
    return Array.from(new Set([selected, ...fromRecos]));
  }, [recos, selected]);

  const { quotes, status: wsStatus } = useLiveQuotes(watchSymbols);
  const live = quotes[selected];
  const sectors = useMemo(() => {
    const set = new Set(recos.map((r) => r.sector).filter(Boolean));
    return ["الكل", ...Array.from(set)];
  }, [recos]);
  const [sector, setSector] = useState("الكل");

  useEffect(() => {
    let alive = true;
    (async () => {
      const mkt = await fetchMarketOverview();
      if (!alive) return;
      setOverview(mkt);
      const liveRecos = await fetchRecommendations(horizon);
      if (!alive) return;
      if (liveRecos.length) setRecos(liveRecos);
      const universe = await fetchCompanies();
      if (!alive) return;
      if (universe.length) setCompanies(universe);
    })();
    return () => {
      alive = false;
    };
  }, [horizon]);

  useEffect(() => {
    let alive = true;
    (async () => {
      const bars = await fetchCandles(selected, 120);
      if (alive) setCandles(bars);
      try {
        const quote = await fetchStock(selected);
        if (alive) setStockName(quote.name_ar || quote.symbol);
      } catch {
        if (alive) setStockName(selected);
      }
    })();
    return () => {
      alive = false;
    };
  }, [selected]);

  useEffect(() => {
    if (!token) return;
    listPortfolios(token)
      .then((data) => setPortfolios(data.results ?? []))
      .catch(() => setPortfolios([]));
  }, [token]);

  const filtered = useMemo(() => {
    return recos
      .filter((r) => (sector === "الكل" ? true : r.sector === sector))
      .filter((r) => (risk === "الكل" ? true : r.risk_level === risk))
      .sort((a, b) => b.confidence - a.confidence);
  }, [recos, sector, risk]);

  const companyHits = useMemo(() => {
    const q = query.trim();
    if (!q) return companies.slice(0, 12);
    const qq = q.toLowerCase();
    return companies
      .filter(
        (c) =>
          c.symbol.includes(q) ||
          (c.name_ar ?? "").includes(q) ||
          (c.name_en ?? "").toLowerCase().includes(qq)
      )
      .slice(0, 12);
  }, [companies, query]);

  async function onAuth(mode: "login" | "register", ev: FormEvent) {
    ev.preventDefault();
    setAuthMsg("");
    try {
      const res =
        mode === "login"
          ? await loginAccount(email, password)
          : await registerAccount(email, password, fullName);
      localStorage.setItem(TOKEN_KEY, res.access_token);
      setToken(res.access_token);
      setAuthMsg("تم الدخول");
    } catch (err) {
      setAuthMsg(err instanceof Error ? err.message : "تعذر الدخول — اربط Postgres في Railway");
    }
  }

  async function onCreatePortfolio() {
    if (!token) {
      setAuthMsg("سجّل الدخول أولاً");
      return;
    }
    try {
      await createPortfolio(token, `محفظة ${selected}`, 10000, selected);
      const data = await listPortfolios(token);
      setPortfolios(data.results ?? []);
      setAuthMsg("تم إنشاء المحفظة");
    } catch (err) {
      setAuthMsg(err instanceof Error ? err.message : "تعذر إنشاء المحفظة");
    }
  }

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
          <span>{stockName}</span>
          <strong>{live?.price?.toFixed(2) ?? "—"}</strong>
          <em className={(live?.change_pct ?? 0) >= 0 ? "up" : "down"}>
            {live?.change_pct != null
              ? `${live.change_pct >= 0 ? "+" : ""}${live.change_pct.toFixed(2)}%`
              : "بانتظار البث"}
          </em>
        </div>
      </section>

      <section className="dash__filters" aria-label="بحث وتصفية">
        <label>
          بحث عن شركة
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="رمز أو اسم — مثال 2222"
          />
        </label>
        <label>
          القطاع
          <select value={sector} onChange={(e) => setSector(e.target.value)}>
            {sectors.map((s) => (
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

      {!!companyHits.length && (
        <ul className="company-chips" aria-label="نتائج البحث">
          {companyHits.map((c) => (
            <li key={c.symbol}>
              <button type="button" onClick={() => setSelected(c.symbol)}>
                {c.symbol} · {c.name_ar ?? c.name_en}
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="dash__grid">
        <section className="dash__chart-panel" aria-label="الرسم البياني">
          <div className="panel-head">
            <h2>
              {selected}
              {live?.price != null ? ` · ${live.price.toFixed(2)}` : ""}
            </h2>
            <p>
              {stockName} · شموع سهمك
              {candles.length ? ` (${candles.length})` : " — جاري التحميل"}
            </p>
          </div>
          {candles.length ? (
            <PriceChart candles={candles} />
          ) : (
            <p className="empty">لا تتوفر شموع حالياً لهذا الرمز</p>
          )}
        </section>

        <section className="dash__reco-panel" aria-label="قائمة التحليلات">
          <div className="panel-head">
            <h2>التحليلات</h2>
            <p>إشارات فنية من الشموع الحية · أفق {horizon} أيام</p>
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

      <section className="account-panel" aria-label="الحساب والمحفظة">
        <div className="panel-head">
          <h2>الحساب والمحفظة</h2>
          <p>يتطلب PostgreSQL في Railway لتسجيل الدخول</p>
        </div>
        {!token ? (
          <form className="auth-form" onSubmit={(e) => onAuth("login", e)}>
            <input
              type="email"
              required
              placeholder="البريد"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <input
              placeholder="الاسم (للتسجيل)"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
            <input
              type="password"
              required
              minLength={8}
              placeholder="كلمة المرور ≥ 8"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <div className="auth-actions">
              <button type="submit">دخول</button>
              <button type="button" onClick={(e) => onAuth("register", e)}>
                إنشاء حساب
              </button>
            </div>
          </form>
        ) : (
          <div className="auth-form">
            <p>مسجّل الدخول</p>
            <button type="button" onClick={onCreatePortfolio}>
              إنشاء محفظة بالسهم المحدد
            </button>
            <button
              type="button"
              onClick={() => {
                localStorage.removeItem(TOKEN_KEY);
                setToken("");
              }}
            >
              خروج
            </button>
            <ul>
              {portfolios.map((p) => (
                <li key={p.id}>
                  {p.name} · {p.capital} ر.س
                </li>
              ))}
            </ul>
          </div>
        )}
        {authMsg && <p className="empty">{authMsg}</p>}
      </section>
    </div>
  );
}
