"""
Airflow DAGs — TASI Vision ETL

الجداول المعتمدة:
- SAHMK WebSocket/ticks: كل 3 ثوانٍ عبر Spark Streaming (خارج Airflow)
- LSEG يومي بعد الإغلاق
- MarketAux أخبار كل ساعة
- توليد التحليلات: 06:00 و 12:00 Asia/Riyadh (أحد–خميس)
- تحديث قائمة الـ 120 سهماً المتقدمة: شهرياً
"""

from __future__ import annotations

from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
    from airflow.operators.python import PythonOperator
except ImportError:  # pragma: no cover
    DAG = None  # type: ignore[assignment]


def trigger_spark_daily_lseg(**_context) -> None:
    print("Submitting Spark job: etl.spark.lseg_daily → tasi.ohlcv_daily")


def trigger_news_sentiment(**_context) -> None:
    print("Submitting job: etl.spark.marketaux_sentiment (symbols bare e.g. 2222)")


def trigger_recommendation_batch(horizon_days: int = 5, **_context) -> None:
    print(
        f"Running ensemble inference for advanced universe (120) "
        f"horizon={horizon_days} → PostgreSQL recommendations"
    )


def refresh_advanced_universe(**_context) -> None:
    """تحديث شهري لقائمة الـ 120 سهماً ذات النماذج المتقدمة."""
    print("Refreshing coverage_tier=advanced list (target 120 symbols)")


if DAG is not None:
    default_args = {
        "owner": "tasi-vision-data",
        "depends_on_past": False,
        "email_on_failure": True,
        "retries": 2,
        "retry_delay": timedelta(minutes=10),
    }

    with DAG(
        dag_id="tasi_lseg_daily",
        default_args=default_args,
        description="Daily LSEG historical OHLCV (symbols as 2222.SR)",
        schedule_interval="30 15 * * 0-4",  # بعد إغلاق تقريبي
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=["tasi-vision", "lseg", "daily"],
    ) as dag_daily:
        PythonOperator(task_id="spark_lseg_daily", python_callable=trigger_spark_daily_lseg)
        BashOperator(
            task_id="validate_clickhouse_counts",
            bash_command="echo 'VALIDATE tasi.ohlcv_daily row counts'",
        )

    with DAG(
        dag_id="tasi_marketaux_hourly",
        default_args=default_args,
        description="Hourly MarketAux news + AraBERT sentiment",
        schedule_interval="15 * * * *",
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=["tasi-vision", "news", "nlp"],
    ) as dag_hourly:
        PythonOperator(task_id="news_sentiment", python_callable=trigger_news_sentiment)

    with DAG(
        dag_id="tasi_recommendations_morning",
        default_args=default_args,
        description="تحليلات يومية 06:00 — آفاق 5/10/20",
        schedule_interval="0 6 * * 0-4",
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=["tasi-vision", "ml", "recommendations"],
    ) as dag_reco_am:
        for h in (5, 10, 20):
            PythonOperator(
                task_id=f"ensemble_h{h}",
                python_callable=trigger_recommendation_batch,
                op_kwargs={"horizon_days": h},
            )

    with DAG(
        dag_id="tasi_recommendations_midday",
        default_args=default_args,
        description="تحديث منتصف النهار 12:00 — أفق أساسي 5 (+اختياري)",
        schedule_interval="0 12 * * 0-4",
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=["tasi-vision", "ml", "recommendations"],
    ) as dag_reco_noon:
        PythonOperator(
            task_id="ensemble_h5_midday",
            python_callable=trigger_recommendation_batch,
            op_kwargs={"horizon_days": 5},
        )

    with DAG(
        dag_id="tasi_advanced_universe_monthly",
        default_args=default_args,
        description="تحديث شهري لقائمة 120 سهماً للنماذج المتقدمة",
        schedule_interval="@monthly",
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=["tasi-vision", "coverage"],
    ) as dag_universe:
        PythonOperator(task_id="refresh_advanced_120", python_callable=refresh_advanced_universe)
