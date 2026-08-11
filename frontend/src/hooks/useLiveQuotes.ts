import { useEffect, useRef, useState } from "react";
import { liveSocketUrl } from "../services/api";

export interface LiveQuote {
  symbol: string;
  price: number;
  change_pct?: number | null;
  bid?: number | null;
  ask?: number | null;
  ts?: string;
  source?: string;
}

/**
 * Connect to /ws/live and keep a map of latest quotes.
 * يعيد الاتصال تلقائياً عند الانقطاع.
 */
export function useLiveQuotes(symbols: string[]) {
  const [quotes, setQuotes] = useState<Record<string, LiveQuote>>({});
  const [status, setStatus] = useState<"connecting" | "open" | "closed">("connecting");
  const symbolsKey = symbols.join(",");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let closed = false;
    let retry: ReturnType<typeof setTimeout> | undefined;
    const wanted = symbolsKey.split(",").filter(Boolean);

    const connect = () => {
      if (closed) return;
      setStatus("connecting");
      const ws = new WebSocket(liveSocketUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("open");
        if (wanted.length) {
          ws.send(JSON.stringify({ action: "subscribe", symbols: wanted }));
        }
      };

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg?.type === "quote" && msg.symbol) {
            setQuotes((prev) => ({
              ...prev,
              [msg.symbol]: {
                symbol: msg.symbol,
                price: Number(msg.price),
                change_pct: msg.change_pct ?? null,
                bid: msg.bid ?? null,
                ask: msg.ask ?? null,
                ts: msg.ts,
                source: msg.source,
              },
            }));
          }
        } catch {
          // ignore malformed frames
        }
      };

      ws.onclose = () => {
        setStatus("closed");
        if (!closed) retry = setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      wsRef.current?.close();
    };
  }, [symbolsKey]);

  return { quotes, status };
}
