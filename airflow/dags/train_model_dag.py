from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.sensors.filesystem import FileSensor
import yaml
import sys
import os
from pathlib import Path

# Load configuration
config_path = "/home/lusitech/AmaliTech/ML_Transport_Accra/configs/config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

default_args = {
    'owner': 'ml_team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),  # Use direct datetime instead of days_ago
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
    schedule=timedelta(days=1),  # Daily training - use 'schedule' instead of 'schedule_interval'
    catchup=False,
    tags=['ml', 'transport']
)

# Check if new data is available
check_data = FileSensor(
    task_id='check_new_data',
    filepath='/home/lusitech/AmaliTech/ML_Transport_Accra/data/raw/new_data_flag.txt',
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
    import subprocess
    import logging

    logger = logging.getLogger(__name__)
    project_root = "/home/lusitech/AmaliTech/ML_Transport_Accra"

    try:
        cmd = ["python", f"{project_root}/scripts/train.py", "--config", f"{project_root}/configs/config.yaml"]
        logger.info(f"Running training command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=project_root)
        logger.info("Training completed successfully")
        logger.info(f"Training output: {result.stdout}")

        return {"status": "success", "output": result.stdout}

    except subprocess.CalledProcessError as e:
        logger.error(f"Training failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Training failed: {str(e)}")
        raise

training = PythonOperator(
    task_id='train_model',
    python_callable=train,
    dag=dag
)

# Model evaluation
def evaluate():
    """Evaluate the trained model."""
    import subprocess
    import logging

    logger = logging.getLogger(__name__)
    project_root = "/home/lusitech/AmaliTech/ML_Transport_Accra"

    try:
        # Get the latest model version
        import mlflow
        mlflow.set_tracking_uri(config['mlflow']['tracking_uri'])
        client = mlflow.tracking.MlflowClient()

        model_name = config['model']['name']
        versions = client.search_model_versions(f"name='{model_name}'")
        if versions:
            latest_version = max([int(m.version) for m in versions])
        else:
            latest_version = "latest"

        cmd = ["python", f"{project_root}/scripts/evaluate.py", "--model-version", str(latest_version)]
        logger.info(f"Running evaluation command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=project_root)
        logger.info("Evaluation completed successfully")
        logger.info(f"Evaluation output: {result.stdout}")

        return {"status": "success", "output": result.stdout, "model_version": latest_version}

    except subprocess.CalledProcessError as e:
        logger.error(f"Evaluation failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        raise

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
        project_root = "/home/lusitech/AmaliTech/ML_Transport_Accra"

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
        output_path = f"{project_root}/models/ab_test_results_{timestamp}"
        os.makedirs(output_path, exist_ok=True)

        # Run the A/B comparison script
        cmd = [
            "python", f"{project_root}/scripts/compare_ab.py",
            "--experiment-id", str(experiment_id),
            "--output-path", output_path
        ]

        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=project_root)

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
        from airflow.utils.email import send_email

        # Get A/B test results
        ab_test_result = context['task_instance'].xcom_pull(task_ids='run_ab_test')
        output_path = ab_test_result['output_path']

        # Get promotion decision
        promotion_result = context['task_instance'].xcom_pull(task_ids='promote_to_staging')

        # Read A/B test report
        report_path = Path(output_path) / "ab_test_report.yaml"
        ab_report = None

        if report_path.exists():
            try:
                with open(report_path, 'r') as f:
                    ab_report = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"Warning: Could not parse YAML report: {e}")
                # Try to read the file as text and extract basic info
                try:
                    with open(report_path, 'r') as f:
                        content = f.read()
                        print(f"Report file content (first 500 chars): {content[:500]}")
                except Exception as read_error:
                    print(f"Could not read report file: {read_error}")

        if ab_report:
            # Extract key metrics
            try:
                control_mae = ab_report['metrics']['control']['mae']
                treatment_mae = ab_report['metrics']['treatment']['mae']
                p_value = ab_report['statistical_tests']['p_value']
                significant = ab_report['conclusions']['significant_difference']

                # Create notification message
                subject = f"ML Pipeline A/B Test Results - {'PROMOTED' if promotion_result else 'NOT PROMOTED'}"

                html_content = f"""
                <html>
                <body>
                <h2>🚀 ML Pipeline A/B Test Results</h2>

                <h3>📊 Performance Comparison:</h3>
                <ul>
                    <li><strong>Control Model MAE:</strong> {control_mae:.4f}</li>
                    <li><strong>Treatment Model MAE:</strong> {treatment_mae:.4f}</li>
                    <li><strong>Improvement:</strong> {((control_mae - treatment_mae) / control_mae * 100):.2f}%</li>
                </ul>

                <h3>📈 Statistical Results:</h3>
                <ul>
                    <li><strong>P-value:</strong> {p_value:.4f}</li>
                    <li><strong>Significant Improvement:</strong> {'✅ Yes' if significant else '❌ No'}</li>
                    <li><strong>Model Promoted:</strong> {'✅ Yes' if promotion_result else '❌ No'}</li>
                </ul>

                <h3>📁 Results Location:</h3>
                <p>{output_path}</p>

                <hr>
                <p><em>This is an automated notification from your ML Transport Accra pipeline.</em></p>
                </body>
                </html>
                """

                # Send email
                send_email(
                    to=context['dag'].default_args['email'],
                    subject=subject,
                    html_content=html_content
                )

                print(f"Email notification sent to: {context['dag'].default_args['email']}")

            except KeyError as e:
                error_subject = "ML Pipeline A/B Test Results - ERROR"
                error_content = f"""
                <html>
                <body>
                <h2>⚠️ ML Pipeline A/B Test Results - ERROR</h2>
                <p>Could not extract all metrics from report: {e}</p>
                <p><strong>Model Promoted:</strong> {'Yes' if promotion_result else 'No'}</p>
                <p><strong>Results saved to:</strong> {output_path}</p>
                </body>
                </html>
                """

                send_email(
                    to=context['dag'].default_args['email'],
                    subject=error_subject,
                    html_content=error_content
                )

                print(f"Error notification email sent to: {context['dag'].default_args['email']}")
        else:
            error_subject = "ML Pipeline A/B Test Results - ERROR"
            error_content = f"""
            <html>
            <body>
            <h2>⚠️ ML Pipeline A/B Test Results - ERROR</h2>
            <p>Could not read A/B test report</p>
            <p><strong>Model Promoted:</strong> {'Yes' if promotion_result else 'No'}</p>
            <p><strong>Results saved to:</strong> {output_path}</p>
            </body>
            </html>
            """

            send_email(
                to=context['dag'].default_args['email'],
                subject=error_subject,
                html_content=error_content
            )

            print(f"Error notification email sent to: {context['dag'].default_args['email']}")

        return {
            "status": "notification_sent",
            "ab_test_results": ab_report,
            "promotion_decision": promotion_result,
            "email_sent": True
        }

    except Exception as e:
        error_message = f"Failed to send notification: {str(e)}"
        print(error_message)

        # Try to send error notification email
        try:
            from airflow.utils.email import send_email
            send_email(
                to=context['dag'].default_args['email'],
                subject="ML Pipeline - Notification Error",
                html_content=f"""
                <html>
                <body>
                <h2>❌ ML Pipeline Notification Error</h2>
                <p>Error: {str(e)}</p>
                <p>Please check the Airflow logs for more details.</p>
                </body>
                </html>
                """
            )
            print(f"Error notification email sent to: {context['dag'].default_args['email']}")
        except Exception as email_error:
            print(f"Failed to send error notification email: {email_error}")

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
    params={'data_path': '/home/lusitech/AmaliTech/ML_Transport_Accra/data/raw'},
    dag=dag
)

# Define task dependencies
check_data >> preprocess >> training >> evaluation >> ab_test >> promote_staging >> notification >> cleanup
