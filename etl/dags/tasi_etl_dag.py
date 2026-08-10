"""
Airflow DAGs — TASI ETL
- SAHMK ticks every 5 seconds handled by Spark Streaming (not Airflow schedule)
- LSEG daily history @ 18:30 Asia/Riyadh
- MarketAux news/sentiment hourly
"""

from __future__ import annotations

from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
    from airflow.operators.python import PythonOperator
except ImportError:  # pragma: no cover — local package without Airflow installed
    DAG = None  # type: ignore[assignment]


def trigger_spark_daily_lseg(**_context) -> None:
    """Kick Spark batch job to load LSEG OHLCV into ClickHouse."""
    # Replace with spark-submit / KubernetesPodOperator in production
    print("Submitting Spark job: etl.spark.lseg_daily")


def trigger_news_sentiment(**_context) -> None:
    """Pull MarketAux news and score with AraBERT."""
    print("Submitting Spark/Python job: etl.spark.marketaux_sentiment")


if DAG is not None:
    default_args = {
        "owner": "tasi-data",
        "depends_on_past": False,
        "email_on_failure": True,
        "retries": 2,
        "retry_delay": timedelta(minutes=10),
    }

    with DAG(
        dag_id="tasi_lseg_daily",
        default_args=default_args,
        description="Daily LSEG historical OHLCV ingest",
        schedule_interval="30 18 * * 0-4",  # Sun–Thu Riyadh close window
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=["tasi", "lseg", "daily"],
    ) as dag_daily:
        PythonOperator(task_id="spark_lseg_daily", python_callable=trigger_spark_daily_lseg)
        BashOperator(
            task_id="validate_clickhouse_counts",
            bash_command="echo 'VALIDATE tasi.ohlcv_daily row counts'",
        )

    with DAG(
        dag_id="tasi_marketaux_hourly",
        default_args=default_args,
        description="Hourly news + AraBERT sentiment",
        schedule_interval="15 * * * *",
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=["tasi", "news", "nlp"],
    ) as dag_hourly:
        PythonOperator(task_id="news_sentiment", python_callable=trigger_news_sentiment)
