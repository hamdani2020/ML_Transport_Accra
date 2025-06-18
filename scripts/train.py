import os
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
    """Load and preprocess data from raw files."""
    data_path = config["data"]["raw_path"]
    logger.info(f"Loading data from {data_path}")

    # Load raw data (implement specific loading logic)
    df = pd.read_parquet(os.path.join(data_path, "transport_data.parquet"))

    return df

def preprocess_data(df, config):
    """Preprocess the data for training."""
    logger.info("Preprocessing data")

    # Extract features defined in config
    numeric_features = config["features"]["numerical_columns"]
    categorical_features = config["features"]["categorical_columns"]

    # Handle categorical features
    for col in categorical_features:
        df[col] = pd.Categorical(df[col]).codes

    # Split features and target
    X = df[numeric_features + categorical_features]
    y = df[config["model"]["target_column"]]

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=config["evaluation"]["train_test_split"],
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
        optimizer=tf.keras.optimizers.Adam(config["model"]["hyperparameters"]["learning_rate"]),
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
            epochs=config["model"]["hyperparameters"]["epochs"],
            batch_size=config["model"]["hyperparameters"]["batch_size"],
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
        mlflow.log_params(config["model"]["hyperparameters"])

        # Save model
        model_path = os.path.join(config["model"]["artifacts_path"], "model.h5")
        model.save(model_path)
        mlflow.log_artifact(model_path)

        # Save scaler
        scaler_path = os.path.join(config["model"]["artifacts_path"], "scaler.pkl")
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
