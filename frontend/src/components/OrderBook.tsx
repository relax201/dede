import type { MarketDepth } from "../types/market";

interface Props {
  depth: MarketDepth | null;
  loading?: boolean;
}

function fmtQty(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("ar-SA");
}

function fmtPx(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toFixed(2);
}

export function OrderBook({ depth, loading }: Props) {
  const maxQty = Math.max(
    1,
    ...(depth?.bids ?? []).map((l) => l.quantity || 0),
    ...(depth?.asks ?? []).map((l) => l.quantity || 0)
  );

  return (
    <section className="book-panel" aria-label="عمق السوق">
      <div className="panel-head">
        <h2>عمق السوق</h2>
        <p>
          دفتر أوامر سهمك
          {depth?.spread != null
            ? ` · سبريد ${fmtPx(depth.spread)}${
                depth.spread_bps != null ? ` (${depth.spread_bps.toFixed(0)} ن.أ)` : ""
              }`
            : ""}
          {depth?.session ? ` · ${depth.session}` : ""}
        </p>
      </div>
      {!depth && (
        <p className="empty">{loading ? "جاري تحميل عمق السوق…" : "لا يتوفر عمق السوق حالياً"}</p>
      )}
      {depth && (
        <>
          <div className="book-meta">
            <span>أفضل طلب {fmtPx(depth.best_bid)}</span>
            <span>أفضل عرض {fmtPx(depth.best_ask)}</span>
            {depth.level_imbalance != null && (
              <span>اختلال {(depth.level_imbalance * 100).toFixed(0)}%</span>
            )}
          </div>
          <div className="book-grid">
            <div className="book-col book-col--ask" aria-label="عروض">
              <div className="book-head">
                <span>كمية</span>
                <span>عرض</span>
              </div>
              {[...(depth.asks ?? [])]
                .slice()
                .reverse()
                .map((lvl, i) => (
                  <div
                    key={`a-${lvl.level ?? i}`}
                    className="book-row"
                    style={{ ["--fill" as string]: `${((lvl.quantity || 0) / maxQty) * 100}%` }}
                  >
                    <span>{fmtQty(lvl.quantity)}</span>
                    <strong>{fmtPx(lvl.price)}</strong>
                  </div>
                ))}
            </div>
            <div className="book-col book-col--bid" aria-label="طلبات">
              <div className="book-head">
                <span>طلب</span>
                <span>كمية</span>
              </div>
              {(depth.bids ?? []).map((lvl, i) => (
                <div
                  key={`b-${lvl.level ?? i}`}
                  className="book-row"
                  style={{ ["--fill" as string]: `${((lvl.quantity || 0) / maxQty) * 100}%` }}
                >
                  <strong>{fmtPx(lvl.price)}</strong>
                  <span>{fmtQty(lvl.quantity)}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
