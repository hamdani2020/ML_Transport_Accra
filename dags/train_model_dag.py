from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor
import yaml
import subprocess
import logging
import os
from pathlib import Path

# Find project root by looking for a known marker (e.g., 'configs/config.yaml')
def find_project_root(marker='configs/config.yaml', start=Path(__file__).resolve()):
    for parent in [start] + list(start.parents):
        if (parent / marker).exists():
            return parent
    raise FileNotFoundError(f"Could not find project root with marker: {marker}")

PROJECT_ROOT = find_project_root()
CONFIG_PATH = PROJECT_ROOT / 'configs' / 'config.yaml'

# Load configuration
with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

default_args = {
    'owner': 'ml_team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email': ['hamdanialhassangandi2020@gmail.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'transport_model_training',
    default_args=default_args,
    description='End-to-end training pipeline for transport prediction model',
    schedule=timedelta(days=1),
    catchup=False,
    tags=['ml', 'transport']
)

# Task: Check for new data
check_data = FileSensor(
    task_id='check_new_data',
    filepath=str(PROJECT_ROOT / 'data' / 'raw' / 'new_data_flag.txt'),
    poke_interval=300,
    timeout=3600,
    dag=dag
)

# Task: Preprocess data
def preprocess_data():
    # Implement your logic here
    pass

preprocess = PythonOperator(
    task_id='preprocess_data',
    python_callable=preprocess_data,
    dag=dag
)

# Task: Train model
def train():
    logger = logging.getLogger(__name__)
    try:
        cmd = [
            "python", str(PROJECT_ROOT / 'scripts' / 'train.py'),
            "--config", str(CONFIG_PATH)
        ]
        logger.info(f"Running training command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=str(PROJECT_ROOT))
        logger.info(f"Training output: {result.stdout}")
        return {"status": "success", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        logger.error(f"Training failed: {e.stderr}")
        raise

training = PythonOperator(
    task_id='train_model',
    python_callable=train,
    dag=dag
)

# Task: Evaluate model
def evaluate():
    import mlflow
    mlflow.set_tracking_uri(config['mlflow']['tracking_uri'])
    client = mlflow.tracking.MlflowClient()
    model_name = config['model']['name']

    try:
        versions = client.search_model_versions(f"name='{model_name}'")
        latest_version = max([int(m.version) for m in versions]) if versions else "latest"

        cmd = [
            "python", str(PROJECT_ROOT / 'scripts' / 'evaluate.py'),
            "--model-version", str(latest_version)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=str(PROJECT_ROOT))
        return {"status": "success", "output": result.stdout, "model_version": latest_version}
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Evaluation failed: {e.stderr}")

evaluation = PythonOperator(
    task_id='evaluate_model',
    python_callable=evaluate,
    dag=dag
)

# Task: Run A/B test
def run_ab_test(**context):
    import mlflow

    mlflow.set_tracking_uri(config['mlflow']['tracking_uri'])
    client = mlflow.tracking.MlflowClient()

    experiment = client.get_experiment_by_name("Default")
    experiment_id = experiment.experiment_id if experiment else client.create_experiment("Default")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = PROJECT_ROOT / 'models' / f"ab_test_results_{timestamp}"
    output_path.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python", str(PROJECT_ROOT / 'scripts' / 'compare_ab.py'),
        "--experiment-id", str(experiment_id),
        "--output-path", str(output_path),
        "--config", str(CONFIG_PATH)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=str(PROJECT_ROOT))

    # Log to MLflow with comprehensive error handling
    try:
        with mlflow.start_run(experiment_id=experiment_id, run_name="ab_test_comparison"):
            # Try to log individual files instead of entire directory
            try:
                report_file = output_path / "ab_test_report.yaml"
                if report_file.exists():
                    mlflow.log_artifact(str(report_file))

                # Try to log any plots if they exist
                for plot_file in output_path.glob("*.png"):
                    try:
                        mlflow.log_artifact(str(plot_file))
                    except Exception as e:
                        import logging
                        logging.warning(f"Failed to log plot {plot_file}: {e}")

            except Exception as e:
                import logging
                logging.warning(f"Failed to log A/B test artifacts to MLflow: {e}")

            # Set tags with error handling
            try:
                mlflow.set_tag("experiment_type", "ab_test")
                mlflow.set_tag("output_path", str(output_path))
                mlflow.set_tag("status", "completed")
            except Exception as e:
                import logging
                logging.warning(f"Failed to set MLflow tags: {e}")

    except Exception as e:
        import logging
        logging.warning(f"Failed to create MLflow run for A/B test: {e}")

    return {"status": "success", "output_path": str(output_path), "experiment_id": experiment_id}

ab_test = PythonOperator(
    task_id='run_ab_test',
    python_callable=run_ab_test,
    dag=dag
)

# Task: Promote model to staging
def promote_to_staging(**context):
    import mlflow

    mlflow.set_tracking_uri(config['mlflow']['tracking_uri'])
    client = mlflow.tracking.MlflowClient()
    model_name = config['model']['name']

    ab_test_result = context['task_instance'].xcom_pull(task_ids='run_ab_test')
    output_path = Path(ab_test_result['output_path'])
    report_path = output_path / 'ab_test_report.yaml'

    if not report_path.exists():
        return False

    with open(report_path) as f:
        ab_report = yaml.safe_load(f)

    if not ab_report['conclusions']['significant_difference']:
        return False

    latest_version = max([int(m.version) for m in client.search_model_versions(f"name='{model_name}'")])
    client.transition_model_version_stage(name=model_name, version=latest_version, stage="Staging")
    return True

promote_staging = PythonOperator(
    task_id='promote_to_staging',
    python_callable=promote_to_staging,
    dag=dag
)

# Task: Send notification
def send_notification(**context):
    from airflow.utils.email import send_email

    ab_test_result = context['task_instance'].xcom_pull(task_ids='run_ab_test')
    promotion_result = context['task_instance'].xcom_pull(task_ids='promote_to_staging')
    report_path = Path(ab_test_result['output_path']) / 'ab_test_report.yaml'

    if report_path.exists():
        with open(report_path) as f:
            ab_report = yaml.safe_load(f)

        control_mae = ab_report['metrics']['control']['mae']
        treatment_mae = ab_report['metrics']['treatment']['mae']
        p_value = ab_report['statistical_tests']['p_value']
        significant = ab_report['conclusions']['significant_difference']

        subject = f"ML Pipeline A/B Test Results - {'PROMOTED' if promotion_result else 'NOT PROMOTED'}"
        html_content = f"""
        <h2>ML A/B Test Summary</h2>
        <ul>
            <li>Control MAE: {control_mae:.4f}</li>
            <li>Treatment MAE: {treatment_mae:.4f}</li>
            <li>Improvement: {(control_mae - treatment_mae) / control_mae * 100:.2f}%</li>
            <li>P-value: {p_value:.4f}</li>
            <li>Significant: {'✅' if significant else '❌'}</li>
            <li>Promoted to Staging: {'✅' if promotion_result else '❌'}</li>
        </ul>
        <p>Results Path: {ab_test_result['output_path']}</p>
        """
    else:
        subject = "ML Pipeline A/B Test Report Missing"
        html_content = "<p>A/B test report not found. Promotion may not have occurred.</p>"

    send_email(to=context['dag'].default_args['email'], subject=subject, html_content=html_content)
    return {"status": "notification_sent"}

notification = PythonOperator(
    task_id='send_notification',
    python_callable=send_notification,
    dag=dag
)

# Task: Cleanup
cleanup = BashOperator(
    task_id='cleanup',
    bash_command='rm -f {{ params.data_path }}/new_data_flag.txt',
    params={'data_path': str(PROJECT_ROOT / 'data' / 'raw')},
    dag=dag
)

# Task dependencies
check_data >> preprocess >> training >> evaluation >> ab_test >> promote_staging >> notification >> cleanup
