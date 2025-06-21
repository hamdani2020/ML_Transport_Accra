import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import yaml
import argparse
import logging
import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)
import matplotlib.pyplot as plt
from datetime import datetime
import tensorflow as tf

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from YAML file."""
    with open("configs/config.yaml") as f:
        return yaml.safe_load(f)

def load_test_data(config):
    """Load and prepare test dataset using the same approach as training."""
    data_path = config["data"]["raw_dir"]
    logger.info(f"Loading test data from {data_path}")

    # Load GTFS files (same as training script)
    trips_df = pd.read_csv(os.path.join(data_path, "trips.txt"))
    routes_df = pd.read_csv(os.path.join(data_path, "routes.txt"))
    
    # Create dataset (same as training script)
    trips_with_routes = trips_df.merge(routes_df, on='route_id', how='left')
    df = trips_with_routes.copy()
    
    # Create dummy target variable (same as training script)
    np.random.seed(42)
    df['trip_duration_minutes'] = np.random.normal(30, 10, len(df))
    df['trip_duration_minutes'] = df['trip_duration_minutes'].clip(5, 60)
    
    # Add dummy features (same as training script)
    df['distance_km'] = np.random.normal(15, 8, len(df)).clip(1, 50)
    df['passenger_count'] = np.random.poisson(20, len(df)).clip(1, 100)
    df['speed_kmh'] = df['distance_km'] / (df['trip_duration_minutes'] / 60)
    
    # Convert categorical columns (only if they exist)
    if 'route_type' in df.columns:
        df['route_type'] = pd.Categorical(df['route_type']).codes
    
    # Use same features as training
    feature_columns = ['distance_km', 'passenger_count', 'speed_kmh', 'route_type']
    target_column = 'trip_duration_minutes'
    
    # Split for evaluation (use a different random seed for test set)
    from sklearn.model_selection import train_test_split
    X = df[feature_columns]
    y = df[target_column]
    
    # Create test set (20% of data)
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=123)
    
    # Load and apply scaler
    scaler_path = os.path.join("models", "scaler.pkl")
    if os.path.exists(scaler_path):
        with open(scaler_path, "rb") as f:
            import pickle
            scaler = pickle.load(f)
        X_test_scaled = scaler.transform(X_test)
        return X_test_scaled, y_test
    else:
        logger.warning("Scaler not found, using unscaled data")
        return X_test, y_test

def load_model(model_name, version):
    """Load model from MLflow registry or local file."""
    logger.info(f"Loading model {model_name} version {version}")
    try:
        return mlflow.pyfunc.load_model(f"models:/{model_name}/{version}")
    except Exception as e:
        logger.warning(f"Could not load from MLflow: {e}")
        # Fallback to local model file
        model_path = os.path.join("models", "model.h5")
        if os.path.exists(model_path):
            logger.info(f"Loading local model from {model_path}")
            model = tf.keras.models.load_model(model_path, compile=False)
            # Recompile with the correct loss and optimizer
            model.compile(
                optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
                loss='mse'
            )
            return model
        else:
            raise FileNotFoundError(f"Model not found at {model_path}")

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
        X_test, y_test = load_test_data(config)

        # Load model
        model_version = model_version or config["model"]["version"]
        model = load_model(config["model"]["name"], model_version)

        # Make predictions
        logger.info("Making predictions on test data")
        if hasattr(model, 'predict'):
            y_pred = model.predict(X_test)
        else:
            y_pred = model.predict(X_test)
        # Flatten predictions if needed
        if hasattr(y_pred, 'flatten'):
            y_pred = y_pred.flatten()

        # Calculate metrics
        metrics = calculate_metrics(y_test, y_pred)
        logger.info(f"Model metrics: {metrics}")

        # Create output directory for artifacts
        os.makedirs("models", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join("models", f"evaluation_{timestamp}")
        os.makedirs(output_path, exist_ok=True)

        # Generate plots
        plot_prediction_error(y_test, y_pred, output_path)
        plot_residuals(y_test, y_pred, output_path)

        # Log metrics and artifacts to MLflow
        mlflow.log_metrics(metrics)
        mlflow.log_artifacts(output_path)

        # Check against thresholds (use reasonable defaults)
        thresholds = {
            "mae": 10.0,  # Mean absolute error of 10 minutes
            "rmse": 15.0,  # Root mean square error of 15 minutes
            "r2": 0.3      # R-squared of 0.3 (reasonable for dummy data)
        }
        
        threshold_checks = {}
        for metric, threshold in thresholds.items():
            if metric in metrics:
                threshold_checks[metric] = metrics[metric] <= threshold

        if all(threshold_checks.values()):
            logger.info("Model meets all performance thresholds")
        else:
            logger.warning("Model fails to meet some performance thresholds:")
            for metric, passed in threshold_checks.items():
                if not passed:
                    logger.warning(
                        f"{metric}: {metrics[metric]} > {thresholds[metric]}"
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

    output_file = os.path.join("models", "evaluation_results.yaml")
    with open(output_file, "w") as f:
        yaml.dump(results, f)

if __name__ == "__main__":
    main()
