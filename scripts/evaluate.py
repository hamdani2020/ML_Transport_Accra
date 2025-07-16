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
from sklearn.preprocessing import LabelEncoder

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config(config_path=None):
    """Load configuration from YAML file."""
    if config_path is None:
        # Try to find the project root and config file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # Go up one level from scripts/
        config_path = os.path.join(project_root, "configs", "config.yaml")

    if not os.path.exists(config_path):
        # Fallback to relative path
        config_path = "configs/config.yaml"

    logger.info(f"Loading config from: {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)

def preprocess_data_eval(df):
    """Preprocess the data for evaluation with expanded feature set and encoding (matches train.py)."""
    feature_columns = [
        'distance_km',
        'passenger_count',
        'speed_kmh',
        'route_type',
        'fare_id',
        'fare_price',
        'agency_id',
        'service_id',
        'shape_id',
        'first_stop_id',
        'last_stop_id',
        'first_stop_name',
        'last_stop_name',
        'route_color',
        'route_short_name',
        'route_long_name',
        'agency_name',
        'first_arrival_time',
        'last_departure_time',
    ]
    available_columns = [col for col in feature_columns if col in df.columns]
    X = df[available_columns].copy()
    # Encode categorical features
    for col in X.select_dtypes(include=['object']).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
    # Convert time columns to minutes since midnight if present
    def time_to_minutes(t):
        try:
            h, m, s = map(int, t.split(':'))
            return h * 60 + m + s / 60
        except:
            return 0
    for col in ['first_arrival_time', 'last_departure_time']:
        if col in X.columns:
            X[col] = X[col].astype(str).apply(time_to_minutes)
    return X, available_columns

def load_test_data(config):
    """Load and prepare test dataset using the same approach as training."""
    data_path = config["data"]["raw_dir"]
    logger.info(f"Loading test data from {data_path}")
    # Load GTFS files (same as training script)
    agency_df = pd.read_csv(os.path.join(data_path, "agency.txt"))
    calendar_df = pd.read_csv(os.path.join(data_path, "calendar.txt"))
    fare_attributes_df = pd.read_csv(os.path.join(data_path, "fare_attributes.txt"))
    fare_rules_df = pd.read_csv(os.path.join(data_path, "fare_rules.txt"))
    routes_df = pd.read_csv(os.path.join(data_path, "routes.txt"))
    shapes_df = pd.read_csv(os.path.join(data_path, "shapes.txt"))
    stops_df = pd.read_csv(os.path.join(data_path, "stops.txt"))
    stop_times_df = pd.read_csv(os.path.join(data_path, "stop_times.txt"))
    trips_df = pd.read_csv(os.path.join(data_path, "trips.txt"))
    # Merge as in train.py
    trips_routes = trips_df.merge(routes_df, on='route_id', how='left', suffixes=('', '_route'))
    trips_routes = trips_routes.merge(agency_df, on='agency_id', how='left', suffixes=('', '_agency'))
    trips_routes = trips_routes.merge(calendar_df, on='service_id', how='left', suffixes=('', '_calendar'))
    trips_routes = trips_routes.merge(fare_rules_df, on='route_id', how='left', suffixes=('', '_fare_rule'))
    trips_routes = trips_routes.merge(fare_attributes_df, on='fare_id', how='left', suffixes=('', '_fare_attr'))
    trips_routes = trips_routes.merge(shapes_df, on='shape_id', how='left', suffixes=('', '_shape'))
    stop_times_grouped = stop_times_df.groupby('trip_id').agg({
        'arrival_time': 'first',
        'departure_time': 'last',
        'stop_id': ['first', 'last']
    })
    stop_times_grouped.columns = ['first_arrival_time', 'last_departure_time', 'first_stop_id', 'last_stop_id']
    stop_times_grouped = stop_times_grouped.reset_index()
    trips_routes = trips_routes.merge(stop_times_grouped, on='trip_id', how='left')
    stops_first = stops_df.rename(columns={col: f"first_{col}" for col in stops_df.columns if col != 'stop_id'})
    stops_last = stops_df.rename(columns={col: f"last_{col}" for col in stops_df.columns if col != 'stop_id'})
    trips_routes = trips_routes.merge(stops_first, left_on='first_stop_id', right_on='stop_id', how='left', suffixes=('', '_first'))
    trips_routes = trips_routes.merge(stops_last, left_on='last_stop_id', right_on='stop_id', how='left', suffixes=('', '_last'))
    # Dummy target and features (as in train.py)
    np.random.seed(42)
    trips_routes['trip_duration_minutes'] = np.random.normal(30, 10, len(trips_routes)).clip(5, 60)
    trips_routes['distance_km'] = np.random.normal(15, 8, len(trips_routes)).clip(1, 50)
    trips_routes['passenger_count'] = np.random.poisson(20, len(trips_routes)).clip(1, 100)
    trips_routes['speed_kmh'] = trips_routes['distance_km'] / (trips_routes['trip_duration_minutes'] / 60)
    # Preprocess features
    X, available_columns = preprocess_data_eval(trips_routes)
    y = trips_routes['trip_duration_minutes']
    return X, y

def load_model_and_scaler(model_name, version):
    """Load model and scaler from MLflow registry or local files."""
    logger.info(f"Loading model {model_name} version {version}")

    # Set up MLflow with proper artifact root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    artifact_root = os.path.join(project_root, "mlflow_shared")
    os.environ["MLFLOW_DEFAULT_ARTIFACT_ROOT"] = os.path.abspath(artifact_root)
    os.environ["MLFLOW_ARTIFACT_ROOT"] = os.path.abspath(artifact_root)

    try:
        model = mlflow.pyfunc.load_model(f"models:/{model_name}/{version}")
        # Try to load scaler from MLflow artifacts
        scaler = None  # MLflow pyfunc models don't easily expose scalers
        return model, scaler
    except Exception as e:
        logger.warning(f"Could not load from MLflow: {e}")

        # First, try to find the latest timestamped model and scaler
        models_dir = os.path.join(project_root, "models")
        if os.path.exists(models_dir):
            # Look for timestamped model files
            model_files = [f for f in os.listdir(models_dir) if f.startswith("model_") and f.endswith(".h5")]
            if model_files:
                # Sort by timestamp to get the latest
                latest_model = sorted(model_files)[-1]
                model_path = os.path.join(models_dir, latest_model)

                # Find corresponding scaler
                timestamp = latest_model.replace("model_", "").replace(".h5", "")
                scaler_path = os.path.join(models_dir, f"scaler_{timestamp}.pkl")

                logger.info(f"Loading latest local model from {model_path}")
                model = tf.keras.models.load_model(model_path, compile=False)
                # Recompile with the correct loss and optimizer
                model.compile(
                    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
                    loss='mse'
                )

                # Load scaler if available
                scaler = None
                if os.path.exists(scaler_path):
                    import pickle
                    with open(scaler_path, 'rb') as f:
                        scaler = pickle.load(f)
                    logger.info(f"Loaded scaler from {scaler_path}")
                else:
                    logger.warning(f"Scaler not found at {scaler_path}")

                return model, scaler

        # Fallback to generic model file
        model_path = os.path.join(models_dir, "model.h5")
        if os.path.exists(model_path):
            logger.info(f"Loading fallback model from {model_path}")
            model = tf.keras.models.load_model(model_path, compile=False)
            model.compile(
                optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
                loss='mse'
            )
            return model, None
        else:
            raise FileNotFoundError(f"No model found. Checked MLflow registry and local paths: {models_dir}")

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
    # Set up MLflow tracking with error handling
    try:
        tracking_uri = config["mlflow"]["tracking_uri"]
        mlflow.set_tracking_uri(tracking_uri)

        # Set up experiment
        experiment_name = f"{config['mlflow']['experiment_name']}_evaluation"
        try:
            mlflow.set_experiment(experiment_name)
        except Exception as e:
            logger.warning(f"Could not set experiment {experiment_name}, using Default: {e}")
            mlflow.set_experiment("Default")

        logger.info(f"MLflow tracking URI: {tracking_uri}")
    except Exception as e:
        logger.error(f"MLflow setup failed: {e}")
        config["_skip_mlflow"] = True

    # Load test data
    X_test, y_test = load_test_data(config)

    # Load model and scaler
    model_version = model_version or config["model"]["version"]
    model, scaler = load_model_and_scaler(config["model"]["name"], model_version)

    # Scale test data if scaler is available
    if scaler is not None:
        logger.info("Scaling test data using loaded scaler")
        X_test_scaled = scaler.transform(X_test)
    else:
        logger.warning("No scaler found, using unscaled data (may cause poor predictions)")
        X_test_scaled = X_test

    # Make predictions
    logger.info("Making predictions on test data")
    y_pred = model.predict(X_test_scaled)

    # Ensure y_pred is 1D
    if hasattr(y_pred, 'flatten'):
        y_pred = y_pred.flatten()
    else:
        y_pred = np.ravel(y_pred)

    # Create predictions DataFrame for A/B testing
    predictions_df = pd.DataFrame({
        'actual': y_test.values,
        'predicted': y_pred,
        'error': np.abs(y_test.values - y_pred)
    })

    # Calculate metrics
    metrics = calculate_metrics(y_test, y_pred)
    logger.info(f"Model metrics: {metrics}")

    # Create output directory for artifacts
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    models_dir = os.path.join(project_root, "models")
    os.makedirs(models_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(models_dir, f"evaluation_{timestamp}")
    os.makedirs(output_path, exist_ok=True)

    # Generate plots
    plot_prediction_error(y_test, y_pred, output_path)
    plot_residuals(y_test, y_pred, output_path)

    # Save predictions for A/B testing
    predictions_path = os.path.join(output_path, "predictions.parquet")
    predictions_df.to_parquet(predictions_path, index=False)

    # Log metrics and artifacts to MLflow if available
    if not config.get("_skip_mlflow", False):
        try:
            with mlflow.start_run():
                mlflow.log_metrics(metrics)

                # Log individual files instead of entire directory to avoid permission issues
                try:
                    mlflow.log_artifact(predictions_path)
                    if os.path.exists(os.path.join(output_path, 'prediction_error.png')):
                        mlflow.log_artifact(os.path.join(output_path, 'prediction_error.png'))
                    if os.path.exists(os.path.join(output_path, 'residuals.png')):
                        mlflow.log_artifact(os.path.join(output_path, 'residuals.png'))
                    logger.info("✅ Successfully logged evaluation artifacts to MLflow")
                except Exception as e:
                    logger.warning(f"Failed to log artifacts to MLflow: {e}")

                # Set tags for A/B testing
                try:
                    mlflow.set_tag("group", "treatment")  # Evaluation runs as treatment group
                    mlflow.set_tag("model_version", model_version)
                    mlflow.set_tag("experiment_type", "evaluation")
                    mlflow.set_tag("output_path", output_path)
                except Exception as e:
                    logger.warning(f"Failed to set MLflow tags: {e}")

                logger.info("✅ Successfully logged evaluation to MLflow")
        except Exception as e:
            logger.warning(f"Failed to log to MLflow: {e}")
    else:
        logger.info("MLflow logging skipped due to setup issues")

    # Check against thresholds (use reasonable defaults)
    thresholds = config.get("evaluation", {}).get("threshold", {
        "mae": 5.0,   # Mean absolute error of 5 minutes
        "rmse": 7.0,  # Root mean square error of 7 minutes
        "r2": 0.95    # R-squared of 0.95 (high-performance model)
    })

    threshold_checks = {}
    for metric, threshold in thresholds.items():
        if metric in metrics:
            if metric == "r2":
                # For R², higher is better
                threshold_checks[metric] = metrics[metric] >= threshold
            else:
                # For MAE, RMSE, MAPE, lower is better
                threshold_checks[metric] = metrics[metric] <= threshold

    if all(threshold_checks.values()):
        logger.info("✅ Model meets all performance thresholds")
    else:
        logger.warning("⚠️ Model fails to meet some performance thresholds:")
        for metric, passed in threshold_checks.items():
            if not passed:
                logger.warning(
                    f"{metric}: {metrics[metric]} > {thresholds[metric]}"
                )

    # Save evaluation results locally
    results = {
        "metrics": metrics,
        "threshold_checks": threshold_checks,
        "timestamp": datetime.now().isoformat(),
        "model_version": model_version,
        "output_path": output_path
    }

    results_file = os.path.join(output_path, "evaluation_results.yaml")
    with open(results_file, "w") as f:
        yaml.dump(results, f)
    logger.info(f"Evaluation results saved to: {results_file}")

    return metrics, threshold_checks

def main():
    parser = argparse.ArgumentParser(description="Evaluate transport prediction model")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config file")
    parser.add_argument("--model-version", help="Specific model version to evaluate")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        metrics, threshold_checks = evaluate_model(config, args.model_version)

        logger.info("✅ Evaluation completed successfully")
        logger.info(f"Metrics: {metrics}")
        logger.info(f"Threshold checks: {threshold_checks}")

    except Exception as e:
        logger.error(f"❌ Evaluation failed: {e}")
        raise

if __name__ == "__main__":
    main()
