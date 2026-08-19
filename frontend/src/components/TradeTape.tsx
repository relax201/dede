import type { TradesTape } from "../types/market";

interface Props {
  tape: TradesTape | null;
  loading?: boolean;
}

function fmtTime(raw?: string | null): string {
  if (!raw) return "—";
  try {
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return raw.slice(11, 19) || raw;
    return d.toLocaleTimeString("ar-SA", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return raw;
  }
}

export function TradeTape({ tape, loading }: Props) {
  return (
    <section className="tape-panel" aria-label="سجل الصفقات">
      <div className="panel-head">
        <h2>سجل الصفقات</h2>
        <p>
          شريط صفقات سهمك
          {tape?.summary?.trade_quantity != null
            ? ` · كمية ${tape.summary.trade_quantity.toLocaleString("ar-SA")}`
            : ""}
          {tape?.count != null ? ` · ${tape.count} صفقة` : ""}
        </p>
      </div>
      {!tape?.events?.length && (
        <p className="empty">{loading ? "جاري تحميل الصفقات…" : "لا توجد صفقات حديثة"}</p>
      )}
      {!!tape?.events?.length && (
        <div className="tape-table-wrap">
          <table className="tape-table">
            <thead>
              <tr>
                <th>الوقت</th>
                <th>السعر</th>
                <th>الكمية</th>
                <th>القيمة</th>
              </tr>
            </thead>
            <tbody>
              {tape.events.map((e, i) => (
                <tr
                  key={`${e.event_time ?? i}-${e.price}-${e.quantity}`}
                  className={e.side === "sell" ? "is-sell" : e.side === "buy" ? "is-buy" : undefined}
                >
                  <td>{fmtTime(e.event_time)}</td>
                  <td>{e.price != null ? e.price.toFixed(2) : "—"}</td>
                  <td>{e.quantity.toLocaleString("ar-SA")}</td>
                  <td>
                    {e.value != null
                      ? e.value.toLocaleString("ar-SA", { maximumFractionDigits: 0 })
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
