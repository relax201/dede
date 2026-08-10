"""
LSTM model for TASI price direction — TensorFlow/Keras
نافذة 60 يوم، Dropout، EarlyStopping، ReduceLROnPlateau، دعم CUDA GPU
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow
import mlflow.tensorflow
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from tensorflow.keras import Model, Sequential
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.optimizers import Adam

from ml.features.technical_indicators import (
    FEATURE_COLUMNS,
    build_feature_frame,
    temporal_train_test_split,
)

logger = logging.getLogger(__name__)


def configure_gpu() -> str:
    """Enable memory growth on CUDA GPUs when available."""
    gpus = tf.config.list_physical_devices("GPU")
    if not gpus:
        logger.warning("No GPU detected — training on CPU")
        return "CPU"
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        logger.info("Configured %d CUDA GPU(s)", len(gpus))
        return f"GPU x{len(gpus)}"
    except RuntimeError as exc:
        logger.error("GPU configuration failed: %s", exc)
        return "CPU"


@dataclass(frozen=True)
class LSTMMetrics:
    auc_roc: float
    precision: float
    recall: float
    hit_rate: float

    def as_dict(self) -> dict[str, float]:
        return {
            "auc_roc": self.auc_roc,
            "precision": self.precision,
            "recall": self.recall,
            "hit_rate": self.hit_rate,
        }


def create_sequences(
    features: np.ndarray,
    targets: np.ndarray,
    window: int = 60,
) -> tuple[np.ndarray, np.ndarray]:
    """Build sliding windows of length `window` (no shuffle)."""
    if len(features) <= window:
        raise ValueError(f"Need more than {window} rows to build sequences")
    xs: list[np.ndarray] = []
    ys: list[float] = []
    for i in range(window, len(features)):
        xs.append(features[i - window : i])
        ys.append(float(targets[i]))
    return np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.float32)


class TasiLSTMTrainer:
    """LSTM binary classifier with production callbacks and MLflow logging."""

    def __init__(
        self,
        window: int = 60,
        units: int = 64,
        dropout: float = 0.3,
        learning_rate: float = 1e-3,
        experiment_name: str = "tasi-lstm",
    ) -> None:
        self.window = window
        self.units = units
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.experiment_name = experiment_name
        self.model: Model | None = None
        self.feature_columns: list[str] = list(FEATURE_COLUMNS)
        self.device: str = configure_gpu()

    def build_model(self, n_features: int) -> Model:
        """
        Architecture:
          Input(window, features) → LSTM → Dropout → LSTM → Dropout → Dense(sigmoid)
        """
        model = Sequential(
            [
                Input(shape=(self.window, n_features)),
                LSTM(self.units, return_sequences=True),
                Dropout(self.dropout),
                LSTM(self.units // 2, return_sequences=False),
                Dropout(self.dropout),
                Dense(32, activation="relu"),
                Dropout(self.dropout / 2),
                Dense(1, activation="sigmoid"),
            ]
        )
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss="binary_crossentropy",
            metrics=[tf.keras.metrics.AUC(name="auc"), "accuracy"],
        )
        return model

    def _normalize_fit(self, train: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
        mean = train[self.feature_columns].mean()
        std = train[self.feature_columns].std().replace(0, 1.0)
        norm = (train[self.feature_columns] - mean) / std
        stats = {"mean": mean.to_dict(), "std": std.to_dict()}
        return norm.to_numpy(dtype=np.float32), train["target"].to_numpy(dtype=np.float32), stats

    def _normalize_apply(self, df: pd.DataFrame, stats: dict[str, Any]) -> np.ndarray:
        mean = pd.Series(stats["mean"])
        std = pd.Series(stats["std"]).replace(0, 1.0)
        return ((df[self.feature_columns] - mean) / std).to_numpy(dtype=np.float32)

    def train(
        self,
        ohlcv: pd.DataFrame,
        forward_horizon: int = 5,
        test_ratio: float = 0.2,
        epochs: int = 50,
        batch_size: int = 64,
        mlflow_tracking_uri: str | None = None,
        register_model_name: str = "tasi_lstm",
    ) -> tuple[Model, LSTMMetrics, dict[str, Any]]:
        features = build_feature_frame(ohlcv, forward_horizon=forward_horizon)
        train_df, test_df = temporal_train_test_split(features, test_ratio=test_ratio)

        # Avoid leakage: fit scaler on train only / منع تسرب المقاييس
        x_train_raw, y_train_raw, stats = self._normalize_fit(train_df)
        x_test_raw = self._normalize_apply(test_df, stats)
        y_test_raw = test_df["target"].to_numpy(dtype=np.float32)

        # Use a small validation tail from train (still temporal)
        val_split = int(len(x_train_raw) * 0.85)
        x_tr, y_tr = x_train_raw[:val_split], y_train_raw[:val_split]
        x_val, y_val = x_train_raw[val_split:], y_train_raw[val_split:]

        X_tr, Y_tr = create_sequences(x_tr, y_tr, self.window)
        X_val, Y_val = create_sequences(x_val, y_val, self.window)
        X_te, Y_te = create_sequences(x_test_raw, y_test_raw, self.window)

        self.model = self.build_model(n_features=len(self.feature_columns))

        callbacks = [
            EarlyStopping(
                monitor="val_auc",
                mode="max",
                patience=8,
                restore_best_weights=True,
                verbose=1,
            ),
            ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=4,
                min_lr=1e-6,
                verbose=1,
            ),
        ]

        if mlflow_tracking_uri:
            mlflow.set_tracking_uri(mlflow_tracking_uri)
        mlflow.set_experiment(self.experiment_name)

        with mlflow.start_run(run_name="lstm-60d"):
            mlflow.log_params(
                {
                    "window": self.window,
                    "units": self.units,
                    "dropout": self.dropout,
                    "learning_rate": self.learning_rate,
                    "device": self.device,
                    "epochs": epochs,
                    "batch_size": batch_size,
                }
            )

            history = self.model.fit(
                X_tr,
                Y_tr,
                validation_data=(X_val, Y_val),
                epochs=epochs,
                batch_size=batch_size,
                callbacks=callbacks,
                shuffle=False,  # مهم: لا تخلط التسلسل الزمني
                verbose=1,
            )

            y_proba = self.model.predict(X_te, verbose=0).reshape(-1)
            metrics = self._metrics(Y_te, y_proba)
            mlflow.log_metrics(metrics.as_dict())
            for key, values in history.history.items():
                for epoch_i, val in enumerate(values):
                    mlflow.log_metric(key, float(val), step=epoch_i)

            mlflow.tensorflow.log_model(
                self.model,
                artifact_path="model",
                registered_model_name=register_model_name,
            )
            mlflow.log_dict(stats, "scaler_stats.json")

        return self.model, metrics, stats

    @staticmethod
    def _metrics(y_true: np.ndarray, y_proba: np.ndarray, threshold: float = 0.5) -> LSTMMetrics:
        y_pred = (y_proba >= threshold).astype(int)
        try:
            auc = float(roc_auc_score(y_true, y_proba))
        except ValueError:
            auc = float("nan")
        return LSTMMetrics(
            auc_roc=auc,
            precision=float(precision_score(y_true, y_pred, zero_division=0)),
            recall=float(recall_score(y_true, y_pred, zero_division=0)),
            hit_rate=float(accuracy_score(y_true, y_pred)),
        )

    def save(self, path: str | Path) -> None:
        if self.model is None:
            raise RuntimeError("Model is not trained")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(path)

    def load(self, path: str | Path) -> Model:
        self.model = tf.keras.models.load_model(path)
        return self.model
