import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import yaml
import argparse
import logging
import tempfile
import mlflow
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import tensorflow as tf
from datetime import datetime
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

def load_data(config):
    """Load and preprocess data from all GTFS files."""
    data_path = config["data"]["raw_dir"]
    logger.info(f"Loading data from {data_path}")

    # Load all GTFS files
    agency_df = pd.read_csv(os.path.join(data_path, "agency.txt"))
    calendar_df = pd.read_csv(os.path.join(data_path, "calendar.txt"))
    fare_attributes_df = pd.read_csv(os.path.join(data_path, "fare_attributes.txt"))
    fare_rules_df = pd.read_csv(os.path.join(data_path, "fare_rules.txt"))
    routes_df = pd.read_csv(os.path.join(data_path, "routes.txt"))
    shapes_df = pd.read_csv(os.path.join(data_path, "shapes.txt"))
    stops_df = pd.read_csv(os.path.join(data_path, "stops.txt"))
    stop_times_df = pd.read_csv(os.path.join(data_path, "stop_times.txt"))
    trips_df = pd.read_csv(os.path.join(data_path, "trips.txt"))

    logger.info(f"Loaded GTFS files: agency({len(agency_df)}), calendar({len(calendar_df)}), fare_attributes({len(fare_attributes_df)}), fare_rules({len(fare_rules_df)}), routes({len(routes_df)}), shapes({len(shapes_df)}), stops({len(stops_df)}), stop_times({len(stop_times_df)}), trips({len(trips_df)})")

    # Merge trips with routes to get route and agency info
    trips_routes = trips_df.merge(routes_df, on='route_id', how='left', suffixes=('', '_route'))
    trips_routes = trips_routes.merge(agency_df, on='agency_id', how='left', suffixes=('', '_agency'))

    # Merge with calendar to get service info
    trips_routes = trips_routes.merge(calendar_df, on='service_id', how='left', suffixes=('', '_calendar'))

    # Merge with fare_rules to get fare_id for each route
    trips_routes = trips_routes.merge(fare_rules_df, on='route_id', how='left', suffixes=('', '_fare_rule'))
    # Merge with fare_attributes to get fare price
    trips_routes = trips_routes.merge(fare_attributes_df, on='fare_id', how='left', suffixes=('', '_fare_attr'))

    # Merge with shapes to get shape info (e.g., shape_dist_traveled)
    trips_routes = trips_routes.merge(shapes_df, on='shape_id', how='left', suffixes=('', '_shape'))

    # Example: For each trip, get the first and last stop times
    stop_times_grouped = stop_times_df.groupby('trip_id').agg({
        'arrival_time': 'first',
        'departure_time': 'last',
        'stop_id': ['first', 'last']
    })
    stop_times_grouped.columns = ['first_arrival_time', 'last_departure_time', 'first_stop_id', 'last_stop_id']
    stop_times_grouped = stop_times_grouped.reset_index()
    trips_routes = trips_routes.merge(stop_times_grouped, on='trip_id', how='left')

    # Merge with stops to get info about the first and last stops
    stops_first = stops_df.rename(columns={col: f"first_{col}" for col in stops_df.columns if col != 'stop_id'})
    stops_last = stops_df.rename(columns={col: f"last_{col}" for col in stops_df.columns if col != 'stop_id'})
    trips_routes = trips_routes.merge(stops_first, left_on='first_stop_id', right_on='stop_id', how='left', suffixes=('', '_first'))
    trips_routes = trips_routes.merge(stops_last, left_on='last_stop_id', right_on='stop_id', how='left', suffixes=('', '_last'))

    # Example feature engineering: add dummy target variable (trip duration in minutes)
    np.random.seed(42)
    trips_routes['trip_duration_minutes'] = np.random.normal(30, 10, len(trips_routes)).clip(5, 60)
    trips_routes['distance_km'] = np.random.normal(15, 8, len(trips_routes)).clip(1, 50)
    trips_routes['passenger_count'] = np.random.poisson(20, len(trips_routes)).clip(1, 100)
    trips_routes['speed_kmh'] = trips_routes['distance_km'] / (trips_routes['trip_duration_minutes'] / 60)

    # Example: add agency_name, fare_price, service_days, shape_dist_traveled, first/last stop names
    # (already included by merge above)

    logger.info(f"Created dataset with {len(trips_routes)} records and columns: {list(trips_routes.columns)}")
    return trips_routes

def preprocess_data(df, config):
    """Preprocess the data for training with more features and encoding."""
    logger.info("Preprocessing data with expanded feature set")

    # Expanded feature columns from all GTFS files
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
    # Only keep columns that exist
    available_columns = [col for col in feature_columns if col in df.columns]
    logger.info(f"Using features: {available_columns}")

    # Select features and target
    X = df[available_columns].copy()
    target_column = 'trip_duration_minutes'
    y = df[target_column]

    # Encode categorical features
    for col in X.select_dtypes(include=['object']).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
        logger.info(f"Encoded categorical feature: {col}")

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

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    logger.info(f"Final features used for training: {list(X.columns)}")
    return X_train_scaled, X_test_scaled, y_train, y_test, scaler

def build_model(input_dim, config):
    """Build the neural network model."""
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation='relu', input_dim=input_dim),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dropout(0.1),
        tf.keras.layers.Dense(1)
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='mse'
    )

    return model

def evaluate_model(model, X_test, y_test):
    """Evaluate the model and return metrics."""
    predictions = model.predict(X_test)

    metrics = {
        "mae": mean_absolute_error(y_test, predictions),
        "rmse": np.sqrt(mean_squared_error(y_test, predictions)),
        "r2": r2_score(y_test, predictions)
    }

    return metrics

def train_model(config):
    """Main training pipeline."""
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    mlflow.set_experiment(config["mlflow"]["experiment_name"])

    with mlflow.start_run():
        # Load and preprocess data
        df = load_data(config)
        X_train, X_test, y_train, y_test, scaler = preprocess_data(df, config)

        # Build and train model
        model = build_model(X_train.shape[1], config)

        history = model.fit(
            X_train, y_train,
            epochs=50,  # Reduced epochs for faster training
            batch_size=32,
            validation_split=0.2,
            callbacks=[
                tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True)
            ]
        )

        # Evaluate model
        metrics = evaluate_model(model, X_test, y_test)
        logger.info(f"Model metrics: {metrics}")

        # Make predictions on test set for A/B testing
        y_pred = model.predict(X_test)
        if hasattr(y_pred, 'flatten'):
            y_pred = y_pred.flatten()

        # Create predictions DataFrame for A/B testing
        predictions_df = pd.DataFrame({
            'actual': y_test,
            'predicted': y_pred,
            'error': np.abs(y_test - y_pred)
        })

        # Log metrics and artifacts
        mlflow.log_metrics(metrics)
        mlflow.log_params({
            "learning_rate": 0.001,
            "epochs": 50,
            "batch_size": 32
        })

        # Create models directory if it doesn't exist
        os.makedirs("models", exist_ok=True)

        # Save model
        model_path = os.path.join("models", "model.h5")
        model.save(model_path)
        mlflow.log_artifact(model_path)

        # Save scaler
        scaler_path = os.path.join("models", "scaler.pkl")
        with open(scaler_path, "wb") as f:
            import pickle
            pickle.dump(scaler, f)
        mlflow.log_artifact(scaler_path)

        # Save predictions for A/B testing
        predictions_path = os.path.join("models", "predictions.parquet")
        predictions_df.to_parquet(predictions_path, index=False)
        mlflow.log_artifact(predictions_path)

        # Set tags for A/B testing
        mlflow.set_tag("group", "control")  # Default to control group
        mlflow.set_tag("model_version", config["model"]["version"])
        mlflow.set_tag("experiment_type", "training")

        # Register model in MLflow
        mlflow.tensorflow.log_model(
            model,
            "model",
            registered_model_name=config["model"]["name"]
        )

def main():
    parser = argparse.ArgumentParser(description="Train transport prediction model")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config file")
    args = parser.parse_args()

    config = load_config(args.config)
    train_model(config)

if __name__ == "__main__":
    main()
