import pytest
import os
import yaml
from datetime import datetime, timedelta
from pipelines.rollback import (
    validate_metrics,
    rollback_model,
    get_model_metrics,
    check_alert_thresholds,
    load_previous_model,
)

@pytest.fixture
def mock_config():
    return {
        "rollback": {
            "enable_auto_rollback": True,
            "performance_window": "1h",
            "error_threshold": 0.05,
            "latency_threshold": 200,
            "min_requests": 100
        },
        "model": {
            "name": "transport_predictor",
            "version": "v1.0",
            "artifacts_path": "models"
        },
        "monitoring": {
            "metrics_port": 9090,
            "log_level": "INFO"
        }
    }

@pytest.fixture
def sample_metrics():
    return {
        "error_rate": 0.03,
        "latency_p95": 150,
        "request_count": 500,
        "timestamp": datetime.now()
    }

def test_validate_metrics():
    """Test metric validation logic."""
    # Valid metrics
    valid_metrics = {
        "error_rate": 0.03,
        "latency_p95": 150,
        "request_count": 500
    }
    assert validate_metrics(valid_metrics) == True

    # Invalid metrics (missing fields)
    invalid_metrics = {
        "error_rate": 0.03
    }
    assert validate_metrics(invalid_metrics) == False

def test_check_alert_thresholds(mock_config, sample_metrics):
    """Test alert threshold checking."""
    # Test normal conditions
    assert check_alert_thresholds(sample_metrics, mock_config) == False

    # Test error rate threshold breach
    high_error_metrics = sample_metrics.copy()
    high_error_metrics["error_rate"] = 0.06
    assert check_alert_thresholds(high_error_metrics, mock_config) == True

    # Test latency threshold breach
    high_latency_metrics = sample_metrics.copy()
    high_latency_metrics["latency_p95"] = 250
    assert check_alert_thresholds(high_latency_metrics, mock_config) == True

def test_get_model_metrics(mocker):
    """Test model metrics retrieval."""
    # Mock prometheus client response
    mock_metrics = {
        "error_rate": 0.03,
        "latency_p95": 150,
        "request_count": 500
    }
    mocker.patch("pipelines.rollback.get_model_metrics", return_value=mock_metrics)

    metrics = get_model_metrics()
    assert isinstance(metrics, dict)
    assert "error_rate" in metrics
    assert "latency_p95" in metrics
    assert "request_count" in metrics

def test_load_previous_model(mocker):
    """Test loading previous model version."""
    # Mock MLflow client responses
    mock_model_versions = [
        {"version": "2", "current_stage": "Production"},
        {"version": "1", "current_stage": "Archived"}
    ]
    mocker.patch("mlflow.tracking.MlflowClient.search_model_versions",
                 return_value=mock_model_versions)

    previous_version = load_previous_model("transport_predictor")
    assert previous_version == "1"

def test_rollback_model(mocker, mock_config):
    """Test model rollback process."""
    # Mock necessary dependencies
    mocker.patch("mlflow.tracking.MlflowClient")
    mocker.patch("pipelines.rollback.load_previous_model", return_value="1")
    mocker.patch("pipelines.rollback.update_model_stage")

    # Test successful rollback
    assert rollback_model(mock_config) == True

    # Test rollback with no previous version
    mocker.patch("pipelines.rollback.load_previous_model", return_value=None)
    assert rollback_model(mock_config) == False

def test_rollback_disabled(mock_config):
    """Test behavior when rollback is disabled."""
    mock_config["rollback"]["enable_auto_rollback"] = False
    result = rollback_model(mock_config)
    assert result == False

def test_insufficient_data(mock_config, sample_metrics):
    """Test behavior with insufficient data."""
    sample_metrics["request_count"] = 50  # Below min_requests threshold
    assert check_alert_thresholds(sample_metrics, mock_config) == False

def test_rollback_notification(mocker, mock_config):
    """Test rollback notification system."""
    mock_notify = mocker.patch("pipelines.rollback.send_notification")
    rollback_model(mock_config)
    mock_notify.assert_called_once()

def test_metrics_timestamp_validation(sample_metrics):
    """Test validation of metrics timestamp."""
    # Test current metrics
    assert validate_metrics(sample_metrics) == True

    # Test old metrics
    old_metrics = sample_metrics.copy()
    old_metrics["timestamp"] = datetime.now() - timedelta(hours=2)
    assert validate_metrics(old_metrics) == False

def test_rollback_idempotency(mocker, mock_config):
    """Test that rollback operation is idempotent."""
    mocker.patch("mlflow.tracking.MlflowClient")
    mocker.patch("pipelines.rollback.load_previous_model", return_value="1")

    # First rollback
    first_result = rollback_model(mock_config)
    assert first_result == True

    # Second rollback should be skipped
    second_result = rollback_model(mock_config)
    assert second_result == False

if __name__ == "__main__":
    pytest.main([__file__])
