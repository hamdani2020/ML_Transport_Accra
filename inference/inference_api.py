from typing import Dict, List, Optional
import os
import yaml
import mlflow
import numpy as np
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
import logging
from prometheus_client import Counter, Histogram, start_http_server

# Load configuration
with open("configs/config.yaml") as f:
    config = yaml.safe_load(f)

# Setup logging
logging.basicConfig(level=config["monitoring"]["log_level"])
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ML Transport Accra Prediction API",
    description="API for predicting transport metrics in Accra",
    version="1.0.0"
)

# Security
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Metrics
PREDICTION_COUNTER = Counter(
    'prediction_requests_total',
    'Total number of prediction requests'
)
PREDICTION_LATENCY = Histogram(
    'prediction_latency_seconds',
    'Time spent processing prediction requests'
)

# Start Prometheus metrics server
start_http_server(config["monitoring"]["prometheus_port"])

class PredictionRequest(BaseModel):
    route_id: str
    stop_id: str
    timestamp: str
    features: Dict[str, float]
    additional_context: Optional[Dict] = None

class PredictionResponse(BaseModel):
    prediction: float
    confidence: float
    model_version: str
    processing_time: float

def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    if api_key_header == os.environ.get("API_KEY"):
        return api_key_header
    raise HTTPException(
        status_code=401,
        detail="Invalid API Key"
    )

def load_model():
    """Load the latest production model from MLflow"""
    try:
        mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
        model = mlflow.pyfunc.load_model(
            model_uri=f"models:/{config['model']['name']}/Production"
        )
        logger.info(f"Loaded model version: {model.version}")
        return model
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Model loading failed"
        )

@app.on_event("startup")
async def startup_event():
    """Initialize the model and other resources on startup"""
    global model
    model = load_model()
    logger.info("API startup complete")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model_version": model.version}

@app.post("/predict", response_model=PredictionResponse)
async def predict(
    request: PredictionRequest,
    api_key: str = Depends(get_api_key)
):
    """Make predictions using the loaded model"""
    try:
        with PREDICTION_LATENCY.time():
            # Preprocess input
            features = {
                **request.features,
                "route_id": request.route_id,
                "stop_id": request.stop_id,
                "timestamp": request.timestamp
            }

            # Make prediction
            prediction = model.predict(features)

            # Calculate confidence (example implementation)
            confidence = calculate_confidence(prediction)

            PREDICTION_COUNTER.inc()

            return PredictionResponse(
                prediction=float(prediction[0]),
                confidence=confidence,
                model_version=model.version,
                processing_time=PREDICTION_LATENCY._sum.get()
            )

    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )

def calculate_confidence(prediction: np.ndarray) -> float:
    """
    Calculate confidence score for the prediction
    This is a placeholder implementation
    """
    # Example: return a fixed confidence or implement actual confidence calculation
    return 0.95

@app.get("/metadata")
async def get_metadata(api_key: str = Depends(get_api_key)):
    """Return model metadata"""
    return {
        "model_name": config["model"]["name"],
        "model_version": model.version,
        "features": list(config["features"]["numerical_columns"] +
                       config["features"]["categorical_columns"]),
        "last_trained": model.metadata.get("training_timestamp"),
        "performance_metrics": model.metadata.get("performance_metrics")
    }

@app.post("/feedback")
async def record_feedback(
    prediction_id: str,
    actual_value: float,
    api_key: str = Depends(get_api_key)
):
    """Record feedback for a prediction"""
    try:
        # Log feedback to MLflow
        mlflow.log_metric(
            f"feedback_{prediction_id}",
            actual_value
        )
        return {"status": "feedback recorded"}
    except Exception as e:
        logger.error(f"Error recording feedback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to record feedback"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config["api"]["host"],
        port=config["api"]["port"],
        workers=config["api"]["workers"]
    )
