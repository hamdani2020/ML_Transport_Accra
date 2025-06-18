import pytest
import os
import pandas as pd
import numpy as np
from scripts.train import (
    load_config,
    load_data,
    preprocess_data,
    build_model,
    evaluate_model
)

@pytest.fixture
def mock_config():
    return {
        "data": {
            "raw_path": "tests/fixtures/data/raw",
            "processed_path": "tests/fixtures/data/processed"
        },
        "model": {
            "name": "test_model",
            "target_column": "travel_time",
            "hyperparameters": {
                "learning_rate": 0.001,
                "batch_size": 32,
                "epochs": 2
            }
        },
        "features": {
            "numerical_columns": ["distance", "speed"],
            "categorical_columns": ["route_id", "stop_id"]
        },
        "evaluation": {
            "train_test_split": 0.2,
            "metrics": ["mae", "rmse", "r2"],
            "threshold": {
                "mae": 5.0,
                "rmse": 7.0
            }
        }
    }

@pytest.fixture
def sample_data():
    # Create sample dataset
    n_samples = 100
    data = {
        "route_id": np.random.randint(1, 5, n_samples),
        "stop_id": np.random.randint(1, 10, n_samples),
        "distance": np.random.uniform(0, 10, n_samples),
        "speed": np.random.uniform(20, 60, n_samples),
        "travel_time": np.random.uniform(10, 30, n_samples)
    }
    return pd.DataFrame(data)

def test_load_config(tmp_path):
    # Create temporary config file
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("""
        data:
            raw_path: "data/raw"
            processed_path: "data/processed"
        model:
            name: "test_model"
    """)

    # Test config loading
    os.chdir(tmp_path)
    config = load_config()
    assert isinstance(config, dict)
    assert "data" in config
    assert "model" in config

def test_load_data(mock_config, sample_data, tmp_path):
    # Setup test data
    data_dir = tmp_path / "data" / "raw"
    data_dir.mkdir(parents=True)
    sample_data.to_parquet(data_dir / "transport_data.parquet")

    # Test data loading
    mock_config["data"]["raw_path"] = str(data_dir)
    df = load_data(mock_config)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == len(sample_data)
    assert all(col in df.columns for col in sample_data.columns)

def test_preprocess_data(mock_config, sample_data):
    # Test data preprocessing
    X_train, X_test, y_train, y_test, scaler = preprocess_data(sample_data, mock_config)

    assert isinstance(X_train, np.ndarray)
    assert isinstance(X_test, np.ndarray)
    assert isinstance(y_train, pd.Series)
    assert isinstance(y_test, pd.Series)

    # Check shapes
    total_features = len(mock_config["features"]["numerical_columns"] +
                        mock_config["features"]["categorical_columns"])
    assert X_train.shape[1] == total_features

    # Check train-test split ratio
    expected_test_size = int(len(sample_data) * mock_config["evaluation"]["train_test_split"])
    assert len(X_test) == expected_test_size

def test_build_model(mock_config):
    # Test model building
    input_dim = len(mock_config["features"]["numerical_columns"] +
                   mock_config["features"]["categorical_columns"])
    model = build_model(input_dim, mock_config)

    # Check model structure
    assert model.input_shape[1] == input_dim
    assert isinstance(model.optimizer.learning_rate, float)

def test_evaluate_model(mock_config):
    # Create test predictions
    y_true = np.array([1, 2, 3, 4, 5])
    y_pred = np.array([1.1, 2.1, 3.1, 4.1, 5.1])

    # Test model evaluation
    metrics = evaluate_model({"actual": y_true, "predicted": y_pred})

    assert isinstance(metrics, dict)
    assert "mae" in metrics
    assert "rmse" in metrics
    assert "r2" in metrics
    assert all(isinstance(v, float) for v in metrics.values())

if __name__ == "__main__":
    pytest.main([__file__])
