"""
XGBoost classifier for TASI directional prediction
نموذج XGBoost مع Hyperparameter Tuning و SHAP و MLflow
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

from ml.features.technical_indicators import (
    FEATURE_COLUMNS,
    build_feature_frame,
    temporal_train_test_split,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClassificationMetrics:
    auc_roc: float
    precision: float
    recall: float
    hit_rate: float
    accuracy: float

    def as_dict(self) -> dict[str, float]:
        return {
            "auc_roc": self.auc_roc,
            "precision": self.precision,
            "recall": self.recall,
            "hit_rate": self.hit_rate,
            "accuracy": self.accuracy,
        }


def compute_metrics(y_true: np.ndarray, y_proba: np.ndarray, threshold: float = 0.5) -> ClassificationMetrics:
    """Compute AUC-ROC, Precision, Recall, Hit Rate."""
    y_pred = (y_proba >= threshold).astype(int)
    try:
        auc = float(roc_auc_score(y_true, y_proba))
    except ValueError:
        auc = float("nan")
    return ClassificationMetrics(
        auc_roc=auc,
        precision=float(precision_score(y_true, y_pred, zero_division=0)),
        recall=float(recall_score(y_true, y_pred, zero_division=0)),
        hit_rate=float(accuracy_score(y_true, y_pred)),  # Hit Rate ≈ correct direction rate
        accuracy=float(accuracy_score(y_true, y_pred)),
    )


class TasiXGBoostTrainer:
    """Production-ready XGBoost training pipeline with temporal CV + SHAP."""

    def __init__(
        self,
        experiment_name: str = "tasi-xgboost",
        random_state: int = 42,
        n_splits: int = 5,
    ) -> None:
        self.experiment_name = experiment_name
        self.random_state = random_state
        self.n_splits = n_splits
        self.model: XGBClassifier | None = None
        self.feature_columns: list[str] = list(FEATURE_COLUMNS)

    def _base_estimator(self, **overrides: Any) -> XGBClassifier:
        params: dict[str, Any] = {
            "objective": "binary:logistic",
            "eval_metric": "auc",
            "tree_method": "hist",
            "n_estimators": 400,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "reg_lambda": 1.0,
            "random_state": self.random_state,
            "n_jobs": -1,
        }
        params.update(overrides)
        return XGBClassifier(**params)

    def tune_hyperparameters(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> dict[str, Any]:
        """
        Grid search with TimeSeriesSplit (no random KFold).
        ضبط المعاملات باستخدام تقسيم زمني فقط.
        """
        grid = [
            {"max_depth": 3, "learning_rate": 0.05, "n_estimators": 300, "min_child_weight": 3},
            {"max_depth": 5, "learning_rate": 0.05, "n_estimators": 400, "min_child_weight": 3},
            {"max_depth": 5, "learning_rate": 0.03, "n_estimators": 600, "min_child_weight": 5},
            {"max_depth": 7, "learning_rate": 0.03, "n_estimators": 500, "min_child_weight": 5},
        ]
        tscv = TimeSeriesSplit(n_splits=self.n_splits)
        best_auc = -np.inf
        best_params: dict[str, Any] = grid[0]

        for params in grid:
            fold_aucs: list[float] = []
            for train_idx, val_idx in tscv.split(X):
                model = self._base_estimator(**params)
                model.fit(
                    X.iloc[train_idx],
                    y.iloc[train_idx],
                    eval_set=[(X.iloc[val_idx], y.iloc[val_idx])],
                    verbose=False,
                )
                proba = model.predict_proba(X.iloc[val_idx])[:, 1]
                try:
                    fold_aucs.append(float(roc_auc_score(y.iloc[val_idx], proba)))
                except ValueError:
                    continue
            mean_auc = float(np.mean(fold_aucs)) if fold_aucs else -np.inf
            logger.info("Params %s → mean AUC=%.4f", params, mean_auc)
            if mean_auc > best_auc:
                best_auc = mean_auc
                best_params = params

        logger.info("Best params: %s (AUC=%.4f)", best_params, best_auc)
        return best_params

    def train(
        self,
        ohlcv: pd.DataFrame,
        forward_horizon: int = 5,
        test_ratio: float = 0.2,
        mlflow_tracking_uri: str | None = None,
        register_model_name: str = "tasi_xgboost",
    ) -> tuple[XGBClassifier, ClassificationMetrics, dict[str, Any]]:
        """Full train → evaluate → MLflow log → SHAP summary."""
        features = build_feature_frame(ohlcv, forward_horizon=forward_horizon)
        train_df, test_df = temporal_train_test_split(features, test_ratio=test_ratio)

        X_train = train_df[self.feature_columns]
        y_train = train_df["target"].astype(int)
        X_test = test_df[self.feature_columns]
        y_test = test_df["target"].astype(int)

        best_params = self.tune_hyperparameters(X_train, y_train)
        model = self._base_estimator(**best_params)
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )
        self.model = model

        y_proba = model.predict_proba(X_test)[:, 1]
        metrics = compute_metrics(y_test.to_numpy(), y_proba)
        shap_summary = self.explain(X_test)

        if mlflow_tracking_uri:
            mlflow.set_tracking_uri(mlflow_tracking_uri)
        mlflow.set_experiment(self.experiment_name)

        with mlflow.start_run(run_name="xgboost-temporal"):
            mlflow.log_params({**best_params, "forward_horizon": forward_horizon})
            mlflow.log_metrics(metrics.as_dict())
            mlflow.log_dict(shap_summary, "shap_summary.json")
            mlflow.xgboost.log_model(
                model,
                artifact_path="model",
                registered_model_name=register_model_name,
            )

        return model, metrics, shap_summary

    def explain(self, X: pd.DataFrame, max_samples: int = 500) -> dict[str, Any]:
        """SHAP TreeExplainer — تفسير مساهمة الميزات."""
        if self.model is None:
            raise RuntimeError("Model is not trained")

        sample = X.iloc[:max_samples]
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values(sample)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        mean_abs = np.abs(shap_values).mean(axis=0)
        ranking = sorted(
            zip(self.feature_columns, mean_abs.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )
        return {
            "top_features": [
                {"feature": name, "mean_abs_shap": float(score)} for name, score in ranking[:10]
            ],
            "n_samples": int(len(sample)),
        }

    def explain_instance(self, row: pd.Series) -> dict[str, Any]:
        """Per-recommendation SHAP explanation + Arabic summary helper payload."""
        if self.model is None:
            raise RuntimeError("Model is not trained")
        frame = row[self.feature_columns].to_frame().T
        explainer = shap.TreeExplainer(self.model)
        values = explainer.shap_values(frame)
        if isinstance(values, list):
            values = values[1]
        contributions = sorted(
            [
                {"feature": f, "shap_value": float(v)}
                for f, v in zip(self.feature_columns, values[0])
            ],
            key=lambda x: abs(x["shap_value"]),
            reverse=True,
        )
        return {"contributions": contributions[:8]}

    def save(self, path: str | Path) -> None:
        if self.model is None:
            raise RuntimeError("Model is not trained")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(path))
        meta = {"feature_columns": self.feature_columns}
        path.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    def load(self, path: str | Path) -> XGBClassifier:
        path = Path(path)
        model = XGBClassifier()
        model.load_model(str(path))
        meta_path = path.with_suffix(".meta.json")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            self.feature_columns = list(meta.get("feature_columns", FEATURE_COLUMNS))
        self.model = model
        return model
