import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

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
    """Load the latest production model from MLflow and return (model, version)"""
    try:
        mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
        model_name = config["model"]["name"]
        client = mlflow.tracking.MlflowClient()
        # Find the production version
        versions = client.search_model_versions(f"name='{model_name}'")
        prod_version = None
        for v in versions:
            if v.current_stage == "Production":
                prod_version = v.version
                break
        if prod_version is None:
            logger.error("No model in Production stage found.")
            raise HTTPException(status_code=500, detail="No model in Production stage.")
        model = mlflow.pyfunc.load_model(model_uri=f"models:/{model_name}/Production")
        logger.info(f"Loaded model: {model_name}, version: {prod_version}")
        return model, prod_version
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Model loading failed"
        )

# Global model and version
model = None
model_version = None

@app.on_event("startup")
async def startup_event():
    """Initialize the model and other resources on startup"""
    global model, model_version
    try:
        model, model_version = load_model()
        logger.info("API startup complete")
    except Exception as e:
        logger.error(f"Failed to load model on startup: {str(e)}")
        # Set model to None so the API can still start
        model = None
        model_version = None
        logger.warning("API starting without model - predictions will fail")

@app.get("/")
async def root():
    """Root endpoint showing model details."""
    if model is None:
        return {"status": "unhealthy", "error": "Model not loaded"}
    return {
        "status": "healthy",
        "model_name": config["model"]["name"],
        "model_version": model_version,
        "features": list(config["features"]["numerical_columns"] + config["features"]["categorical_columns"]),
        "description": "ML Transport Accra Prediction API"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if model is None:
        return {"status": "unhealthy", "error": "Model not loaded"}
    return {"status": "healthy", "model_version": model_version}

@app.post("/predict", response_model=PredictionResponse)
async def predict(
    request: PredictionRequest,
    api_key: str = Depends(get_api_key)
):
    """Make predictions using the loaded model. Uses features: distance, speed, passenger_count, day_of_week (or hour_of_day)."""
    try:
        with PREDICTION_LATENCY.time():
            # Extract required features
            features_dict = request.features
            try:
                distance = features_dict["distance"]
                speed = features_dict["speed"]
                passenger_count = features_dict["passenger_count"]
                # Prefer day_of_week, fallback to hour_of_day
                if "day_of_week" in features_dict:
                    fourth_feature = features_dict["day_of_week"]
                elif "hour_of_day" in features_dict:
                    fourth_feature = features_dict["hour_of_day"]
                else:
                    raise ValueError("Missing required feature: day_of_week or hour_of_day")
            except KeyError as e:
                logger.error(f"Missing required feature: {e}")
                raise HTTPException(status_code=400, detail=f"Missing required feature: {e}")
            except ValueError as e:
                logger.error(str(e))
                raise HTTPException(status_code=400, detail=str(e))

            # Prepare input for model
            input_array = np.array([[distance, speed, passenger_count, fourth_feature]])

            # Make prediction
            prediction = model.predict(input_array)

            # Calculate confidence (example implementation)
            confidence = calculate_confidence(prediction)

            PREDICTION_COUNTER.inc()

            return PredictionResponse(
                prediction=float(prediction[0]),
                confidence=confidence,
                model_version=str(model_version),
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
        "model_version": model_version,
        "features": list(config["features"]["numerical_columns"] +
                       config["features"]["categorical_columns"]),
        "last_trained": None,  # Could be added if tracked in model metadata
        "performance_metrics": None  # Could be added if tracked in model metadata
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
