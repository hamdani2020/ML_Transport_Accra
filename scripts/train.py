import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import yaml
import argparse
import logging
import mlflow
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import tensorflow as tf
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from YAML file."""
    with open("configs/config.yaml") as f:
        return yaml.safe_load(f)

def load_data(config):
    """Load and preprocess data from GTFS files."""
    data_path = config["data"]["raw_dir"]
    logger.info(f"Loading data from {data_path}")

    # Load GTFS files
    trips_df = pd.read_csv(os.path.join(data_path, "trips.txt"))
    stops_df = pd.read_csv(os.path.join(data_path, "stops.txt"))
    stop_times_df = pd.read_csv(os.path.join(data_path, "stop_times.txt"))
    routes_df = pd.read_csv(os.path.join(data_path, "routes.txt"))
    
    logger.info(f"Loaded {len(trips_df)} trips, {len(stops_df)} stops, {len(stop_times_df)} stop times")
    
    # Create a simple dataset for demonstration
    # Merge trips with routes to get route information
    trips_with_routes = trips_df.merge(routes_df, on='route_id', how='left')
    
    # Add some derived features for demonstration
    df = trips_with_routes.copy()
    
    # Create dummy target variable (trip duration in minutes) for demonstration
    # In a real scenario, this would be actual trip duration data
    np.random.seed(42)  # For reproducible results
    df['trip_duration_minutes'] = np.random.normal(30, 10, len(df))  # Dummy duration
    df['trip_duration_minutes'] = df['trip_duration_minutes'].clip(5, 60)  # Reasonable range
    
    # Add some dummy features
    df['distance_km'] = np.random.normal(15, 8, len(df)).clip(1, 50)
    df['passenger_count'] = np.random.poisson(20, len(df)).clip(1, 100)
    df['speed_kmh'] = df['distance_km'] / (df['trip_duration_minutes'] / 60)
    
    # Convert categorical columns to numeric (only if they exist)
    if 'route_type' in df.columns:
        df['route_type'] = pd.Categorical(df['route_type']).codes
    
    logger.info(f"Created dataset with {len(df)} records")
    return df

def preprocess_data(df, config):
    """Preprocess the data for training."""
    logger.info("Preprocessing data")

    # Use available features from the dataset
    feature_columns = ['distance_km', 'passenger_count', 'speed_kmh', 'route_type']
    target_column = 'trip_duration_minutes'
    
    # Ensure all columns exist
    available_columns = [col for col in feature_columns if col in df.columns]
    logger.info(f"Using features: {available_columns}")
    
    # Split features and target
    X = df[available_columns]
    y = df[target_column]

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,  # Use default 20% test split
        random_state=42
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

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

    config = load_config()
    train_model(config)

if __name__ == "__main__":
    main()
