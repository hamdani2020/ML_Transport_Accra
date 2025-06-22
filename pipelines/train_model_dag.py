from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.dates import days_ago
import yaml
import sys
import os
from pathlib import Path

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

# A/B Testing
def run_ab_test(**context):
    """Run A/B test comparison between control and treatment models."""
    try:
        import mlflow
        import subprocess
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Set up MLflow tracking
        mlflow.set_tracking_uri(config['mlflow']['tracking_uri'])
        client = mlflow.tracking.MlflowClient()
        
        # Get experiment ID for the Default experiment
        experiment = client.get_experiment_by_name("Default")
        if not experiment:
            logger.warning("Default experiment not found, creating it")
            experiment_id = client.create_experiment("Default")
        else:
            experiment_id = experiment.experiment_id
        
        logger.info(f"Running A/B test on experiment ID: {experiment_id}")
        
        # Create output directory for A/B test results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"models/ab_test_results_{timestamp}"
        os.makedirs(output_path, exist_ok=True)
        
        # Run the A/B comparison script
        cmd = [
            "python", "scripts/compare_ab.py",
            "--experiment-id", str(experiment_id),
            "--output-path", output_path
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        logger.info("A/B test completed successfully")
        logger.info(f"Results saved to: {output_path}")
        
        # Log the results to MLflow
        with mlflow.start_run(experiment_id=experiment_id, run_name="ab_test_comparison"):
            mlflow.log_artifacts(output_path)
            mlflow.set_tag("experiment_type", "ab_test")
            mlflow.set_tag("output_path", output_path)
        
        return {
            "status": "success",
            "output_path": output_path,
            "experiment_id": experiment_id
        }
        
    except subprocess.CalledProcessError as e:
        logger.error(f"A/B test failed with error: {e}")
        logger.error(f"Error output: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"A/B test failed: {str(e)}")
        raise

ab_test = PythonOperator(
    task_id='run_ab_test',
    python_callable=run_ab_test,
    dag=dag
)

# Model promotion to staging (conditional on A/B test results)
def promote_to_staging(**context):
    """Promote latest model to staging if A/B test shows significant improvement."""
    try:
        import mlflow
        import json
        import yaml
        from pathlib import Path
        
        mlflow.set_tracking_uri(config['mlflow']['tracking_uri'])
        client = mlflow.tracking.MlflowClient()
        model_name = config['model']['name']

        # Get A/B test results from previous task
        ab_test_result = context['task_instance'].xcom_pull(task_ids='run_ab_test')
        output_path = ab_test_result['output_path']
        
        # Read A/B test report
        report_path = Path(output_path) / "ab_test_report.yaml"
        if not report_path.exists():
            print(f"A/B test report not found at {report_path}")
            return False
            
        with open(report_path, 'r') as f:
            ab_report = yaml.safe_load(f)
        
        # Check if treatment is significantly better than control
        significant_improvement = ab_report['conclusions']['significant_difference']
        p_value = ab_report['statistical_tests']['p_value']
        significance_level = config['ab_testing']['significance_level']
        
        print(f"A/B Test Results:")
        print(f"  P-value: {p_value}")
        print(f"  Significance level: {significance_level}")
        print(f"  Significant improvement: {significant_improvement}")
        
        # Only promote if there's significant improvement
        if not significant_improvement:
            print("A/B test shows no significant improvement. Model will not be promoted.")
            return False
        
        # Get the latest version number
        versions = client.search_model_versions(f"name='{model_name}'")
        if not versions:
            print(f"No versions found for model: {model_name}")
            return False
        latest_version = max([int(m.version) for m in versions])
        print(f"Promoting model {model_name} version {latest_version} to Staging")

        # Transition model to staging
        client.transition_model_version_stage(
            name=model_name,
            version=latest_version,
            stage="Staging"
        )
        
        print("Model successfully promoted to Staging")
        return True
        
    except Exception as e:
        print(f"Failed to promote model: {str(e)}")
        return False

promote_staging = PythonOperator(
    task_id='promote_to_staging',
    python_callable=promote_to_staging,
    dag=dag
)

# Notification task
def send_notification(**context):
    """Send notification with A/B test results and promotion decision."""
    try:
        import yaml
        from pathlib import Path
        
        # Get A/B test results
        ab_test_result = context['task_instance'].xcom_pull(task_ids='run_ab_test')
        output_path = ab_test_result['output_path']
        
        # Get promotion decision
        promotion_result = context['task_instance'].xcom_pull(task_ids='promote_to_staging')
        
        # Read A/B test report
        report_path = Path(output_path) / "ab_test_report.yaml"
        if report_path.exists():
            with open(report_path, 'r') as f:
                ab_report = yaml.safe_load(f)
            
            # Extract key metrics
            control_mae = ab_report['metrics']['control']['mae']
            treatment_mae = ab_report['metrics']['treatment']['mae']
            p_value = ab_report['statistical_tests']['p_value']
            significant = ab_report['conclusions']['significant_difference']
            
            # Create notification message
            message = f"""
🚀 ML Pipeline A/B Test Results

📊 Performance Comparison:
  • Control Model MAE: {control_mae:.4f}
  • Treatment Model MAE: {treatment_mae:.4f}
  • Improvement: {((control_mae - treatment_mae) / control_mae * 100):.2f}%

📈 Statistical Results:
  • P-value: {p_value:.4f}
  • Significant Improvement: {significant}
  • Model Promoted: {promotion_result}

📁 Results saved to: {output_path}
            """
            
            print(message)
            
            # In a real implementation, you would send this via email, Slack, etc.
            # For now, we just print it to the logs
            
        return {
            "status": "notification_sent",
            "ab_test_results": ab_report if report_path.exists() else None,
            "promotion_decision": promotion_result
        }
        
    except Exception as e:
        print(f"Failed to send notification: {str(e)}")
        return {"status": "notification_failed", "error": str(e)}

notification = PythonOperator(
    task_id='send_notification',
    python_callable=send_notification,
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
check_data >> preprocess >> training >> evaluation >> ab_test >> promote_staging >> notification >> cleanup
