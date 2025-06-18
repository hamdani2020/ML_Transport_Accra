import pytest
from fastapi.testclient import TestClient
import json
import os
import yaml
import mlflow
import numpy as np
from inference.inference_api import app, PredictionRequest, PredictionResponse

# Create test client
client = TestClient(app)

@pytest.fixture
def mock_model(monkeypatch):
    """Mock MLflow model for testing."""
    class MockModel:
        def predict(self, features):
            # Return deterministic predictions for testing
            return np.array([25.0])  # Example prediction

        @property
        def version(self):
            return "v1.0"

    def mock_load_model(*args, **kwargs):
        return MockModel()

    # Patch mlflow.pyfunc.load_model
    monkeypatch.setattr(mlflow.pyfunc, "load_model", mock_load_model)
    return MockModel()

@pytest.fixture
def valid_prediction_request():
    """Create a valid prediction request."""
    return {
        "route_id": "route_1",
        "stop_id": "stop_1",
        "timestamp": "2023-01-01T12:00:00Z",
        "features": {
            "distance": 5.0,
            "speed": 40.0,
            "passenger_count": 30
        }
    }

def test_health_check(mock_model):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "model_version" in response.json()

def test_predict_valid_input(mock_model, valid_prediction_request):
    """Test prediction endpoint with valid input."""
    # Set API key in header
    headers = {"X-API-Key": os.getenv("API_KEY", "test_key")}

    response = client.post(
        "/predict",
        json=valid_prediction_request,
        headers=headers
    )

    assert response.status_code == 200
    assert "prediction" in response.json()
    assert "confidence" in response.json()
    assert "model_version" in response.json()
    assert "processing_time" in response.json()

    # Check response structure
    response_data = response.json()
    assert isinstance(response_data["prediction"], float)
    assert isinstance(response_data["confidence"], float)
    assert isinstance(response_data["processing_time"], float)

def test_predict_missing_features(mock_model):
    """Test prediction endpoint with missing features."""
    invalid_request = {
        "route_id": "route_1",
        "stop_id": "stop_1",
        "timestamp": "2023-01-01T12:00:00Z",
        "features": {}  # Empty features
    }

    headers = {"X-API-Key": os.getenv("API_KEY", "test_key")}
    response = client.post("/predict", json=invalid_request, headers=headers)

    assert response.status_code == 422  # Unprocessable Entity

def test_predict_invalid_feature_values(mock_model):
    """Test prediction endpoint with invalid feature values."""
    invalid_request = {
        "route_id": "route_1",
        "stop_id": "stop_1",
        "timestamp": "2023-01-01T12:00:00Z",
        "features": {
            "distance": "invalid",  # String instead of float
            "speed": 40.0
        }
    }

    headers = {"X-API-Key": os.getenv("API_KEY", "test_key")}
    response = client.post("/predict", json=invalid_request, headers=headers)

    assert response.status_code == 422

def test_predict_missing_api_key(mock_model, valid_prediction_request):
    """Test prediction endpoint without API key."""
    response = client.post("/predict", json=valid_prediction_request)
    assert response.status_code == 401

def test_predict_invalid_api_key(mock_model, valid_prediction_request):
    """Test prediction endpoint with invalid API key."""
    headers = {"X-API-Key": "invalid_key"}
    response = client.post(
        "/predict",
        json=valid_prediction_request,
        headers=headers
    )
    assert response.status_code == 401

def test_metadata_endpoint(mock_model):
    """Test the metadata endpoint."""
    headers = {"X-API-Key": os.getenv("API_KEY", "test_key")}
    response = client.get("/metadata", headers=headers)

    assert response.status_code == 200
    metadata = response.json()
    assert "model_name" in metadata
    assert "model_version" in metadata
    assert "features" in metadata
    assert isinstance(metadata["features"], list)

def test_feedback_endpoint(mock_model):
    """Test the feedback endpoint."""
    feedback_data = {
        "prediction_id": "test_pred_1",
        "actual_value": 27.5
    }

    headers = {"X-API-Key": os.getenv("API_KEY", "test_key")}
    response = client.post(
        "/feedback",
        json=feedback_data,
        headers=headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "feedback recorded"

def test_error_handling(mock_model, monkeypatch):
    """Test error handling when model prediction fails."""
    def mock_predict(*args, **kwargs):
        raise Exception("Prediction failed")

    # Patch the predict method to raise an exception
    monkeypatch.setattr(mock_model, "predict", mock_predict)

    headers = {"X-API-Key": os.getenv("API_KEY", "test_key")}
    response = client.post(
        "/predict",
        json=valid_prediction_request(),
        headers=headers
    )

    assert response.status_code == 500
    assert "error" in response.json() or "detail" in response.json()

@pytest.mark.asyncio
async def test_startup_event(mock_model):
    """Test application startup event."""
    # This should already be handled by the mock_model fixture
    # but we can add additional startup-specific tests here
    assert app.state.model is not None

def test_prometheus_metrics():
    """Test that Prometheus metrics are being recorded."""
    headers = {"X-API-Key": os.getenv("API_KEY", "test_key")}

    # Make a few predictions
    for _ in range(3):
        client.post(
            "/predict",
            json=valid_prediction_request(),
            headers=headers
        )

    # Get metrics
    response = client.get("/metrics")
    assert response.status_code == 200
    metrics_text = response.text

    # Check for specific metrics
    assert "prediction_requests_total" in metrics_text
    assert "prediction_latency_seconds" in metrics_text

if __name__ == "__main__":
    pytest.main([__file__])
