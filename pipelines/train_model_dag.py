from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import yaml
import os

# Hardcode the project root path since this DAG will be copied to Airflow's dags directory
project_root = "/home/lusitech/AmaliTech/ML_Transport_Accra"

# Load configuration
config_path = os.path.join(project_root, "configs", "config.yaml")
print(f"Loading config from: {config_path}")
print(f"Project root: {project_root}")

with open(config_path) as f:
    config = yaml.safe_load(f)

default_args = {
    'owner': 'ml_team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
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
    schedule=timedelta(days=1),  # Daily training
    catchup=False,
    tags=['ml', 'transport']
)

# Check if new data is available
def check_data_availability():
    """Check if new data flag file exists."""
    flag_file = os.path.join(project_root, config['data']['raw_dir'], "new_data_flag.txt")
    if not os.path.exists(flag_file):
        raise ValueError(f"Data flag file not found: {flag_file}")
    print(f"Data flag file found: {flag_file}")
    return True

check_data = PythonOperator(
    task_id='check_new_data',
    python_callable=check_data_availability,
    dag=dag
)

# Data preprocessing and validation
def preprocess_data():
    """Preprocess and validate new data."""
    print("Preprocessing data...")
    # Implementation here
    pass

preprocess = PythonOperator(
    task_id='preprocess_data',
    python_callable=preprocess_data,
    dag=dag
)

# Model training using script
training = BashOperator(
    task_id='train_model',
    bash_command=f'cd {project_root} && python scripts/train.py --config configs/config.yaml',
    dag=dag
)

# Model evaluation using script
evaluation = BashOperator(
    task_id='evaluate_model',
    bash_command=f'cd {project_root} && python scripts/evaluate.py --model-version {config["model"]["version"]}',
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
    bash_command=f'rm -f {config["data"]["raw_dir"]}/new_data_flag.txt',
    dag=dag
)

# Define task dependencies
check_data >> preprocess >> training >> evaluation >> promote_staging >> cleanup
