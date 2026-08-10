"""
Unified training entrypoint for XGBoost + LSTM
نقطة تشغيل موحّدة للتدريب وتسجيل MLflow
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from ml.models.lstm_model import TasiLSTMTrainer
from ml.models.xgboost_model import TasiXGBoostTrainer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("train_pipeline")


def load_ohlcv_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalize column names
    rename = {c: c.lower().strip() for c in df.columns}
    df = df.rename(columns=rename)
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        raise ValueError(f"CSV must contain columns: {sorted(required)}")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Train TASI ML models")
    parser.add_argument("--data", required=True, help="Path to OHLCV CSV")
    parser.add_argument("--model", choices=["xgboost", "lstm", "both"], default="both")
    parser.add_argument("--mlflow-uri", default=None)
    parser.add_argument("--out-dir", default="artifacts/models")
    args = parser.parse_args()

    ohlcv = load_ohlcv_csv(args.data)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if args.model in ("xgboost", "both"):
        xgb = TasiXGBoostTrainer()
        model, metrics, shap_summary = xgb.train(ohlcv, mlflow_tracking_uri=args.mlflow_uri)
        xgb.save(out / "xgboost_model.json")
        logger.info("XGBoost metrics: %s", metrics.as_dict())
        logger.info("SHAP top: %s", shap_summary.get("top_features", [])[:5])

    if args.model in ("lstm", "both"):
        lstm = TasiLSTMTrainer()
        model, metrics, stats = lstm.train(ohlcv, mlflow_tracking_uri=args.mlflow_uri)
        lstm.save(out / "lstm_model.keras")
        logger.info("LSTM metrics: %s", metrics.as_dict())
        logger.info("Scaler stats keys: %s", list(stats.keys()))


if __name__ == "__main__":
    main()
