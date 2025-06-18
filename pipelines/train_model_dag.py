from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.dates import days_ago
import yaml
import sys
import os

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Import project modules
from scripts.train import train_model
from scripts.evaluate import evaluate_model
from scripts.track_experiments import ExperimentTracker

# Load configuration
with open("configs/config.yaml") as f:
    config = yaml.safe_load(f)

default_args = {
    'owner': 'ml_team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email': ['ml-team@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'transport_model_training',
    default_args=default_args,
    description='End-to-end training pipeline for transport prediction model',
    schedule_interval=timedelta(days=1),  # Daily training
    catchup=False,
    tags=['ml', 'transport']
)

# Check if new data is available
check_data = FileSensor(
    task_id='check_new_data',
    filepath=f"{config['data']['raw_path']}/new_data_flag.txt",
    poke_interval=300,  # Check every 5 minutes
    timeout=3600,  # Timeout after 1 hour
    dag=dag
)

# Data preprocessing and validation
def preprocess_data():
    """Preprocess and validate new data."""
    # Implementation here
    pass

preprocess = PythonOperator(
    task_id='preprocess_data',
    python_callable=preprocess_data,
    dag=dag
)

# Model training
def train():
    """Train the model using preprocessed data."""
    tracker = ExperimentTracker()
    with tracker.start_run():
        train_model(config)

training = PythonOperator(
    task_id='train_model',
    python_callable=train,
    dag=dag
)

# Model evaluation
def evaluate():
    """Evaluate the trained model."""
    model_version = config['model']['version']
    metrics = evaluate_model(model_version, None, config)

    # Check if metrics meet thresholds
    for metric, threshold in config['evaluation']['threshold'].items():
        if metrics[metric] > threshold:
            raise ValueError(f"Model failed {metric} threshold: {metrics[metric]} > {threshold}")

    return metrics

evaluation = PythonOperator(
    task_id='evaluate_model',
    python_callable=evaluate,
    dag=dag
)

# Model promotion to staging
def promote_to_staging(**context):
    """Promote model to staging if evaluation passes."""
    try:
        import mlflow
        mlflow.set_tracking_uri(config['mlflow']['tracking_uri'])

        client = mlflow.tracking.MlflowClient()
        model_name = config['model']['name']
        version = config['model']['version']

        # Transition model to staging
        client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage="Staging"
        )

        return True
    except Exception as e:
        print(f"Failed to promote model: {str(e)}")
        return False

promote_staging = PythonOperator(
    task_id='promote_to_staging',
    python_callable=promote_to_staging,
    dag=dag
)

# Cleanup task
cleanup = BashOperator(
    task_id='cleanup',
    bash_command='rm -f {{ params.data_path }}/new_data_flag.txt',
    params={'data_path': config['data']['raw_path']},
    dag=dag
)

# Define task dependencies
check_data >> preprocess >> training >> evaluation >> promote_staging >> cleanup
