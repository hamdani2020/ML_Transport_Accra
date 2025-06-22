#!/usr/bin/env python3
"""
Script to run A/B tests for model comparison.
This script trains a control model and evaluates a treatment model,
then runs the comparison analysis.
"""

import os
import sys
import subprocess
import logging
import yaml
import mlflow
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from YAML file."""
    with open("configs/config.yaml") as f:
        return yaml.safe_load(f)

def run_command(command, description):
    """Run a shell command and log the result."""
    logger.info(f"Running: {description}")
    logger.info(f"Command: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True
        )
        logger.info(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed with error: {e}")
        logger.error(f"Error output: {e.stderr}")
        raise

def get_experiment_id(experiment_name):
    """Get MLflow experiment ID by name."""
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment:
        return experiment.experiment_id
    else:
        # Create experiment if it doesn't exist
        experiment_id = client.create_experiment(experiment_name)
        logger.info(f"Created new experiment: {experiment_name} (ID: {experiment_id})")
        return experiment_id

def main():
    """Main A/B testing pipeline."""
    config = load_config()
    
    # Set up MLflow tracking
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    
    # Get experiment ID
    experiment_name = config["mlflow"]["experiment_name"]
    experiment_id = get_experiment_id(experiment_name)
    
    logger.info("🚀 Starting A/B Test Pipeline")
    logger.info(f"Experiment: {experiment_name} (ID: {experiment_id})")
    
    try:
        # Step 1: Train control model
        logger.info("📊 Step 1: Training control model...")
        run_command(
            "python scripts/train.py --config configs/config.yaml",
            "Training control model"
        )
        
        # Step 2: Evaluate treatment model (using latest model from registry)
        logger.info("🔬 Step 2: Evaluating treatment model...")
        run_command(
            "python scripts/evaluate.py --model-version latest",
            "Evaluating treatment model"
        )
        
        # Step 3: Run A/B comparison
        logger.info("📈 Step 3: Running A/B comparison...")
        output_path = f"models/ab_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        run_command(
            f"python scripts/compare_ab.py --experiment-id {experiment_id} --output-path {output_path}",
            "A/B comparison analysis"
        )
        
        logger.info("🎉 A/B Test Pipeline completed successfully!")
        logger.info(f"Results saved to: {output_path}")
        
        # Display summary
        logger.info("\n" + "="*50)
        logger.info("A/B TEST SUMMARY")
        logger.info("="*50)
        logger.info(f"Experiment ID: {experiment_id}")
        logger.info(f"Results Path: {output_path}")
        logger.info("Check the output directory for detailed results and visualizations.")
        
    except Exception as e:
        logger.error(f"❌ A/B Test Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 