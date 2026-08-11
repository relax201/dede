import { createChart, type IChartApi, type ISeriesApi } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { Candle } from "../types/market";

interface Props {
  candles: Candle[];
}

export function PriceChart({ candles }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "transparent" },
        textColor: "#c5d0c8",
      },
      grid: {
        vertLines: { color: "rgba(197, 208, 200, 0.08)" },
        horzLines: { color: "rgba(197, 208, 200, 0.08)" },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
      width: containerRef.current.clientWidth,
      height: 360,
    });

    const series = chart.addCandlestickSeries({
      upColor: "#1A7A4E",
      downColor: "#e85d4c",
      borderVisible: false,
      wickUpColor: "#1A7A4E",
      wickDownColor: "#e85d4c",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const onResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current) return;
    seriesRef.current.setData(
      candles.map((c) => ({
        time: c.time as unknown as string,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );
    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  return <div className="chart-shell" ref={containerRef} aria-label="رسم بياني للسعر" />;
}
