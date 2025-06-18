import os
import yaml
import argparse
import logging
import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    precision_recall_curve,
    roc_curve,
    auc
)
import matplotlib.pyplot as plt
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from YAML file."""
    with open("configs/config.yaml") as f:
        return yaml.safe_load(f)

def load_test_data(config):
    """Load test dataset."""
    test_path = os.path.join(config["data"]["processed_path"], "test.parquet")
    logger.info(f"Loading test data from {test_path}")
    return pd.read_parquet(test_path)

def load_model(model_name, version):
    """Load model from MLflow registry."""
    logger.info(f"Loading model {model_name} version {version}")
    return mlflow.pyfunc.load_model(f"models:/{model_name}/{version}")

def calculate_metrics(y_true, y_pred):
    """Calculate regression metrics."""
    metrics = {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
        "r2": r2_score(y_true, y_pred),
        "mape": np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    }
    return metrics

def plot_prediction_error(y_true, y_pred, output_path):
    """Generate prediction error visualization."""
    plt.figure(figsize=(10, 6))
    plt.scatter(y_true, y_pred, alpha=0.5)
    plt.plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 'r--', lw=2)
    plt.xlabel('Actual Values')
    plt.ylabel('Predicted Values')
    plt.title('Prediction Error Analysis')
    plt.tight_layout()
    plt.savefig(os.path.join(output_path, 'prediction_error.png'))
    plt.close()

def plot_residuals(y_true, y_pred, output_path):
    """Generate residuals plot."""
    residuals = y_true - y_pred
    plt.figure(figsize=(10, 6))
    plt.scatter(y_pred, residuals, alpha=0.5)
    plt.axhline(y=0, color='r', linestyle='--')
    plt.xlabel('Predicted Values')
    plt.ylabel('Residuals')
    plt.title('Residuals Analysis')
    plt.tight_layout()
    plt.savefig(os.path.join(output_path, 'residuals.png'))
    plt.close()

def evaluate_model(config, model_version=None):
    """Main evaluation pipeline."""
    # Set up MLflow tracking
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    mlflow.set_experiment(f"{config['mlflow']['experiment_name']}_evaluation")

    with mlflow.start_run():
        # Load test data
        test_data = load_test_data(config)
        X_test = test_data.drop(config["model"]["target_column"], axis=1)
        y_test = test_data[config["model"]["target_column"]]

        # Load model
        model_version = model_version or config["model"]["version"]
        model = load_model(config["model"]["name"], model_version)

        # Make predictions
        logger.info("Making predictions on test data")
        y_pred = model.predict(X_test)

        # Calculate metrics
        metrics = calculate_metrics(y_test, y_pred)
        logger.info(f"Model metrics: {metrics}")

        # Create output directory for artifacts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            config["model"]["artifacts_path"],
            f"evaluation_{timestamp}"
        )
        os.makedirs(output_path, exist_ok=True)

        # Generate plots
        plot_prediction_error(y_test, y_pred, output_path)
        plot_residuals(y_test, y_pred, output_path)

        # Log metrics and artifacts to MLflow
        mlflow.log_metrics(metrics)
        mlflow.log_artifacts(output_path)

        # Check against thresholds
        threshold_checks = {}
        for metric, threshold in config["evaluation"]["threshold"].items():
            threshold_checks[metric] = metrics[metric] <= threshold

        if all(threshold_checks.values()):
            logger.info("Model meets all performance thresholds")
        else:
            logger.warning("Model fails to meet some performance thresholds:")
            for metric, passed in threshold_checks.items():
                if not passed:
                    logger.warning(
                        f"{metric}: {metrics[metric]} > {config['evaluation']['threshold'][metric]}"
                    )

        return metrics, threshold_checks

def main():
    parser = argparse.ArgumentParser(description="Evaluate transport prediction model")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config file")
    parser.add_argument("--model-version", help="Specific model version to evaluate")
    args = parser.parse_args()

    config = load_config()
    metrics, threshold_checks = evaluate_model(config, args.model_version)

    # Save evaluation results
    results = {
        "metrics": metrics,
        "threshold_checks": threshold_checks,
        "timestamp": datetime.now().isoformat(),
        "model_version": args.model_version or config["model"]["version"]
    }

    output_file = os.path.join(
        config["model"]["artifacts_path"],
        "evaluation_results.yaml"
    )
    with open(output_file, "w") as f:
        yaml.dump(results, f)

if __name__ == "__main__":
    main()
