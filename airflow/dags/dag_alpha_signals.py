"""
DAG: Run ensemble Alpha Signals for all tickers.

Runs the 3-model ensemble (ep2+ep4+ep5) for every valid ticker, writes to
forecast.alpha_signals. Fuels the /alpha-signals Premium page.

Schedule: hourly during extended US market hours (ET), Mon-Fri.
Waits for dag_run_forecast to finish (same price/news freshness prereq).

Workflow:
  1. wait_for_forecast — soft-fail sensor on dag_run_forecast
  2. trigger_alpha — POST /admin/run-alpha-signals (returns 202, spawns bg task)
  3. wait_alpha_complete — polls /admin/alpha-signals-status until phase=done
     (the BackgroundTasks pattern alone didn't block Airflow — this sensor fixes it)
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.bash import BashSensor
from airflow.sensors.external_task import ExternalTaskSensor

default_args = {
    "owner": "predictamarket",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_alpha_signals",
    default_args=default_args,
    description="Ensemble (ep2+ep4+ep5) alpha signals — Premium feature",
    schedule="15 10-17 * * 1-5",  # 15 min past every hour, 10:15-17:15 ET
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,  # never overlap — ensemble batch is long
    tags=["forecast", "ml", "ensemble", "heavy"],
) as dag:

    wait_forecast = ExternalTaskSensor(
        task_id="wait_for_forecast",
        external_dag_id="dag_run_forecast",
        timeout=1800,
        mode="reschedule",
        poke_interval=120,
        soft_fail=True,
    )

    trigger_alpha = BashOperator(
        task_id="trigger_alpha_signals",
        bash_command=(
            'curl -sf -X POST http://forecast-service:8004/api/forecast/admin/run-alpha-signals '
            '-H "x-internal-key: $INTERNAL_API_KEY"'
        ),
        execution_timeout=timedelta(minutes=5),
        pool="forecast_pool",
    )

    # Poll status endpoint until phase=done. Timeout ~2h (346 tickers × ~18s ≈ 100 min).
    wait_alpha_complete = BashSensor(
        task_id="wait_alpha_complete",
        bash_command=(
            'phase=$(curl -sf '
            '-H "x-internal-key: $INTERNAL_API_KEY" '
            'http://forecast-service:8004/api/forecast/admin/alpha-signals-status '
            '| python3 -c "import json, sys; print(json.load(sys.stdin).get(\\"phase\\", \\"unknown\\"))"); '
            'test "$phase" = "done"'
        ),
        mode="reschedule",
        poke_interval=120,  # every 2 min
        timeout=7200,        # 2h hard cap
    )

    wait_forecast >> trigger_alpha >> wait_alpha_complete
