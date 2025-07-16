#!/usr/bin/env python3
"""
MLflow connectivity and configuration test script.
This script helps diagnose MLflow connection issues and ensures proper setup.
"""

import os
import sys
import tempfile
import mlflow
import mlflow.tensorflow
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from YAML file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    config_path = os.path.join(project_root, "configs", "config.yaml")

    if not os.path.exists(config_path):
        logger.error(f"Config file not found at: {config_path}")
        return None

    with open(config_path) as f:
        return yaml.safe_load(f)

def test_mlflow_connection(tracking_uri):
    """Test basic MLflow connection."""
    try:
        mlflow.set_tracking_uri(tracking_uri)
        client = mlflow.tracking.MlflowClient()

        # Try to get or create the default experiment
        try:
            experiment = client.get_experiment_by_name("Default")
            if experiment is None:
                experiment_id = client.create_experiment("Default")
                logger.info(f"Created default experiment with ID: {experiment_id}")
            else:
                logger.info(f"Found default experiment with ID: {experiment.experiment_id}")
        except Exception as e:
            logger.error(f"Failed to access/create experiment: {e}")
            return False

        logger.info(f"✅ Successfully connected to MLflow at: {tracking_uri}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to connect to MLflow: {e}")
        return False

def test_artifact_logging(tracking_uri):
    """Test artifact logging capability."""
    try:
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("mlflow_test")

        with mlflow.start_run(run_name="test_run"):
            # Create a simple test artifact
            test_data = pd.DataFrame({
                'x': np.random.randn(100),
                'y': np.random.randn(100)
            })

            # Test logging metrics
            mlflow.log_metric("test_metric", 0.85)
            mlflow.log_param("test_param", "test_value")

            # Test logging artifacts
            with tempfile.TemporaryDirectory() as temp_dir:
                artifact_path = os.path.join(temp_dir, "test_data.csv")
                test_data.to_csv(artifact_path, index=False)
                mlflow.log_artifact(artifact_path)

                logger.info("✅ Successfully logged test artifacts")
                return True

    except Exception as e:
        logger.error(f"❌ Failed to log artifacts: {e}")
        return False

def check_permissions():
    """Check if we have proper write permissions for MLflow directories."""
    try:
        # Check current working directory permissions
        cwd = os.getcwd()
        test_file = os.path.join(cwd, "test_write_permission.txt")

        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        logger.info(f"✅ Write permissions OK in current directory: {cwd}")

        # Check mlruns directory
        mlruns_dir = os.path.join(cwd, "mlruns")
        if not os.path.exists(mlruns_dir):
            os.makedirs(mlruns_dir, exist_ok=True)
            logger.info(f"Created mlruns directory: {mlruns_dir}")

        test_file = os.path.join(mlruns_dir, "test_write_permission.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        logger.info(f"✅ Write permissions OK in mlruns directory: {mlruns_dir}")

        return True

    except Exception as e:
        logger.error(f"❌ Permission check failed: {e}")
        return False

def fix_mlflow_environment():
    """Set proper MLflow environment variables to avoid permission issues."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    mlruns_path = os.path.join(project_root, "mlruns")

    # Ensure mlruns directory exists
    os.makedirs(mlruns_path, exist_ok=True)

    # Set environment variables
    os.environ["MLFLOW_DEFAULT_ARTIFACT_ROOT"] = mlruns_path
    os.environ["MLFLOW_ARTIFACT_ROOT"] = mlruns_path

    logger.info(f"Set MLFLOW_DEFAULT_ARTIFACT_ROOT to: {mlruns_path}")
    logger.info(f"Set MLFLOW_ARTIFACT_ROOT to: {mlruns_path}")

def main():
    """Main test function."""
    logger.info("🧪 Starting MLflow connectivity tests...")

    # Load configuration
    config = load_config()
    if config is None:
        logger.error("Failed to load configuration. Exiting.")
        sys.exit(1)

    tracking_uri = config.get("mlflow", {}).get("tracking_uri", "sqlite:///mlflow.db")
    logger.info(f"Testing MLflow with tracking URI: {tracking_uri}")

    # Fix environment variables
    fix_mlflow_environment()

    # Check permissions
    logger.info("\n📁 Checking file permissions...")
    permissions_ok = check_permissions()

    # Test basic connection
    logger.info("\n🔗 Testing MLflow connection...")
    connection_ok = test_mlflow_connection(tracking_uri)

    # Test artifact logging
    logger.info("\n📦 Testing artifact logging...")
    artifacts_ok = test_artifact_logging(tracking_uri)

    # Summary
    logger.info("\n📋 Test Summary:")
    logger.info(f"Permissions: {'✅ PASS' if permissions_ok else '❌ FAIL'}")
    logger.info(f"Connection: {'✅ PASS' if connection_ok else '❌ FAIL'}")
    logger.info(f"Artifacts: {'✅ PASS' if artifacts_ok else '❌ FAIL'}")

    if all([permissions_ok, connection_ok, artifacts_ok]):
        logger.info("\n🎉 All tests passed! MLflow is properly configured.")
        return 0
    else:
        logger.error("\n💥 Some tests failed. Please check the errors above.")
        logger.info("\n🔧 Troubleshooting tips:")
        if not permissions_ok:
            logger.info("- Check file permissions in your project directory")
            logger.info("- Ensure the user has write access to the mlruns directory")
        if not connection_ok:
            logger.info("- Verify MLflow server is running (docker-compose up mlflow)")
            logger.info("- Check the tracking URI in your config.yaml")
        if not artifacts_ok:
            logger.info("- Check MLflow artifact store configuration")
            logger.info("- Verify the MLFLOW_DEFAULT_ARTIFACT_ROOT environment variable")

        return 1

if __name__ == "__main__":
    sys.exit(main())
