"""
Comprehensive FastAPI Service for Accra Public Transport Analysis
Provides endpoints for route optimization, demand prediction, schedule optimization, and ML inference
"""

import os
import sys
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uvicorn
import json
import pandas as pd
import numpy as np
import mlflow
from datetime import datetime
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram, start_http_server

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.route_optimizer import RouteOptimizer
from scripts.demand_predictor import DemandPredictor
from scripts.schedule_optimizer import ScheduleOptimizer
from scripts.visualization import TransportVisualizer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Accra Public Transport Analysis API",
    description="AI-powered public transport efficiency analysis for Accra, Ghana",
    version="1.0.0"
)

# Mount static files for processed data
app.mount("/data/processed", StaticFiles(directory="data/processed"), name="processed")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Metrics
PREDICTION_COUNTER = Counter(
    'prediction_requests_total',
    'Total number of prediction requests'
)
OPTIMIZATION_COUNTER = Counter(
    'optimization_requests_total',
    'Total number of optimization requests'
)
PREDICTION_LATENCY = Histogram(
    'prediction_latency_seconds',
    'Time spent processing prediction requests'
)
OPTIMIZATION_LATENCY = Histogram(
    'optimization_latency_seconds',
    'Time spent processing optimization requests'
)

# Start Prometheus metrics server
try:
    start_http_server(9090)
    logger.info("Prometheus metrics server started on port 9090")
except Exception as e:
    logger.warning(f"Failed to start Prometheus server: {e}")

# Initialize components
route_optimizer = RouteOptimizer()
demand_predictor = DemandPredictor()
schedule_optimizer = ScheduleOptimizer()
visualizer = TransportVisualizer()

# Load GTFS lookup tables at startup
GTFS_LOOKUPS = {}
def load_gtfs_lookups():
    """Load GTFS data for lookups."""
    try:
        data_path = "data/raw"
        GTFS_LOOKUPS["routes"] = pd.read_csv(os.path.join(data_path, "routes.txt"))
        GTFS_LOOKUPS["fare_attributes"] = pd.read_csv(os.path.join(data_path, "fare_attributes.txt"))
        GTFS_LOOKUPS["fare_rules"] = pd.read_csv(os.path.join(data_path, "fare_rules.txt"))
        GTFS_LOOKUPS["agency"] = pd.read_csv(os.path.join(data_path, "agency.txt"))
        GTFS_LOOKUPS["stops"] = pd.read_csv(os.path.join(data_path, "stops.txt"))
        logger.info("GTFS lookup tables loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load GTFS lookups: {e}")

# Load GTFS data on startup
load_gtfs_lookups()

# Global model and version for ML inference
model = None
model_version = None
model_name = "transport_predictor"

# Helper to get current production version from MLflow
def get_production_model_version():
    """Get the current production model version from MLflow."""
    try:
        mlflow.set_tracking_uri("http://localhost:5000")
        client = mlflow.tracking.MlflowClient()
        versions = client.search_model_versions(f"name='{model_name}'")
        for v in versions:
            if v.current_stage == "Production":
                return v.version
        return None
    except Exception as e:
        logger.warning(f"Failed to get production model version: {e}")
        return None

def load_model_if_needed():
    """Load ML model if needed."""
    global model, model_version
    try:
        prod_version = get_production_model_version()
        if model is None or str(model_version) != str(prod_version):
            if prod_version:
                model = mlflow.pyfunc.load_model(model_uri=f"models:/{model_name}/Production")
                model_version = prod_version
                logger.info(f"Loaded model: {model_name}, version: {model_version}")
            else:
                logger.warning("No production model available")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")

def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    """Validate API key."""
    if api_key_header == os.environ.get("API_KEY", "default_key"):
        return api_key_header
    raise HTTPException(
        status_code=401,
        detail="Invalid API Key"
    )

# Pydantic models for API requests/responses
class RouteOptimizationRequest(BaseModel):
    vehicle_capacity: int = 100
    max_route_time: int = 120
    include_demand_estimation: bool = True

class DemandPredictionRequest(BaseModel):
    stop_id: str
    route_id: str
    time: str
    day_of_week: str

class NetworkDemandRequest(BaseModel):
    stops: List[str]
    routes: List[str]
    time_range: List[str]  # ["08:00:00", "18:00:00"]
    days: List[str]

class ScheduleOptimizationRequest(BaseModel):
    vehicle_capacity: int = 100
    min_headway: int = 5
    max_headway: int = 30
    max_fleet_size: int = 50

class MLPredictionRequest(BaseModel):
    route_id: str
    stop_id: str
    timestamp: str
    features: Dict[str, float]
    additional_context: Optional[Dict] = None

class OptimizationResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    efficiency_improvement: Optional[float] = None
    total_distance_saved: Optional[float] = None

class DemandPredictionResponse(BaseModel):
    stop_id: str
    route_id: str
    time: str
    day_of_week: str
    predicted_demand: int
    confidence: float

class MLPredictionResponse(BaseModel):
    prediction: float
    confidence: float
    model_version: str
    processing_time: float
    route_id: Optional[str] = None
    route_name: Optional[str] = None
    route_color: Optional[str] = None
    fare_id: Optional[str] = None
    fare_price: Optional[float] = None
    agency_name: Optional[str] = None
    first_stop_name: Optional[str] = None
    last_stop_name: Optional[str] = None
    input_summary: Dict[str, Any]

# Global storage for results
optimization_results = {}
demand_predictions = {}
schedule_results = {}

@app.on_event("startup")
async def startup_event():
    """Initialize the API on startup."""
    try:
        load_model_if_needed()
        logger.info("API startup complete")
    except Exception as e:
        logger.error(f"Failed to load model on startup: {str(e)}")
        global model, model_version
        model = None
        model_version = None
        logger.warning("API starting without ML model - ML predictions will fail")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with comprehensive API documentation."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Accra Public Transport Analysis API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { text-align: center; margin-bottom: 30px; }
            .section { margin: 30px 0; }
            .endpoint { background-color: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }
            .method { font-weight: bold; color: #0066cc; }
            .url { font-family: monospace; background-color: #e0e0e0; padding: 5px; }
            .category { color: #28a745; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚌 Accra Public Transport Analysis API</h1>
            <p>Comprehensive AI-powered transport efficiency analysis for Accra, Ghana</p>
        </div>
        
        <div class="section">
            <h2>🛣️ Route Optimization</h2>
            <div class="endpoint">
                <div class="method">POST</div>
                <div class="url">/optimize/routes</div>
                <p>Optimize transport routes using OR-Tools with vehicle capacity and time constraints</p>
            </div>
        </div>
        
        <div class="section">
            <h2>⏰ Schedule Optimization</h2>
            <div class="endpoint">
                <div class="method">POST</div>
                <div class="url">/optimize/schedules</div>
                <p>Optimize bus schedules using linear programming (PuLP)</p>
            </div>
        </div>
        
        <div class="section">
            <h2>📈 Demand Prediction</h2>
            <div class="endpoint">
                <div class="method">POST</div>
                <div class="url">/predict/demand</div>
                <p>Predict passenger demand for specific stops, routes, and times</p>
            </div>
            <div class="endpoint">
                <div class="method">POST</div>
                <div class="url">/predict/network-demand</div>
                <p>Predict demand across the entire transport network</p>
            </div>
            <div class="endpoint">
                <div class="method">POST</div>
                <div class="url">/predict/ml</div>
                <p>ML-based prediction with advanced features and model versioning</p>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Visualization & Analytics</h2>
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="url">/visualize/network</div>
                <p>Generate interactive transport network map</p>
            </div>
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="url">/visualize/demand-heatmap</div>
                <p>Generate demand heatmap visualization</p>
            </div>
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="url">/dashboard</div>
                <p>Access comprehensive analysis dashboard</p>
            </div>
        </div>
        
        <div class="section">
            <h2>🔧 System & Monitoring</h2>
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="url">/docs</div>
                <p>Interactive API documentation (Swagger UI)</p>
            </div>
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="url">/health</div>
                <p>System health check</p>
            </div>
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="url">/metrics</div>
                <p>Prometheus metrics</p>
            </div>
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="url">/results/{result_type}</div>
                <p>Get optimization results (routes, schedules, demand)</p>
            </div>
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="url">/metadata</div>
                <p>Get ML model metadata and version information</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/optimize/routes", response_model=OptimizationResponse)
async def optimize_routes(request: RouteOptimizationRequest, background_tasks: BackgroundTasks):
    """Optimize transport routes using OR-Tools."""
    try:
        logger.info("Starting route optimization")
        OPTIMIZATION_COUNTER.inc()
        
        with OPTIMIZATION_LATENCY.time():
            # Run optimization in background
            def run_optimization():
                global optimization_results
                results = route_optimizer.optimize_network("data/raw")
                optimization_results['routes'] = results
            
            background_tasks.add_task(run_optimization)
            
            return OptimizationResponse(
                status="success",
                message="Route optimization started. Check /results/routes for results.",
                efficiency_improvement=0.0  # Will be updated when complete
            )
    
    except Exception as e:
        logger.error(f"Route optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Route optimization failed: {str(e)}")

@app.post("/optimize/schedules", response_model=OptimizationResponse)
async def optimize_schedules(request: ScheduleOptimizationRequest, background_tasks: BackgroundTasks):
    """Optimize bus schedules using linear programming."""
    try:
        logger.info("Starting schedule optimization")
        OPTIMIZATION_COUNTER.inc()
        
        with OPTIMIZATION_LATENCY.time():
            # Run optimization in background
            def run_schedule_optimization():
                global schedule_results
                results = schedule_optimizer.optimize_schedules("data/raw", request.dict())
                schedule_results = results
            
            background_tasks.add_task(run_schedule_optimization)
            
            return OptimizationResponse(
                status="success",
                message="Schedule optimization started. Check /results/schedules for results.",
                efficiency_improvement=0.0
            )
    
    except Exception as e:
        logger.error(f"Schedule optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Schedule optimization failed: {str(e)}")

@app.post("/predict/demand", response_model=DemandPredictionResponse)
async def predict_demand(request: DemandPredictionRequest):
    """Predict passenger demand for a specific stop, route, time, and day."""
    try:
        logger.info(f"Predicting demand for {request.stop_id} at {request.time}")
        PREDICTION_COUNTER.inc()
        
        with PREDICTION_LATENCY.time():
            # Load models if not already loaded
            if not hasattr(demand_predictor, 'models') or not demand_predictor.models:
                demand_predictor.load_models()
            
            # Predict demand
            prediction = demand_predictor.predict_demand(
                request.stop_id, 
                request.route_id, 
                request.time, 
                request.day_of_week
            )
            
            return DemandPredictionResponse(
                stop_id=request.stop_id,
                route_id=request.route_id,
                time=request.time,
                day_of_week=request.day_of_week,
                predicted_demand=prediction['predicted_demand'],
                confidence=prediction['confidence']
            )
    
    except Exception as e:
        logger.error(f"Demand prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Demand prediction failed: {str(e)}")

@app.post("/predict/network-demand")
async def predict_network_demand(request: NetworkDemandRequest):
    """Predict demand across the entire transport network."""
    try:
        logger.info("Predicting network-wide demand")
        PREDICTION_COUNTER.inc()
        
        with PREDICTION_LATENCY.time():
            # Load models if not already loaded
            if not hasattr(demand_predictor, 'models') or not demand_predictor.models:
                demand_predictor.load_models()
            
            # Predict network demand
            predictions = demand_predictor.predict_network_demand(
                request.stops,
                request.routes,
                request.time_range,
                request.days
            )
            
            return {
                "status": "success",
                "predictions": predictions.to_dict('records'),
                "total_stops": len(request.stops),
                "total_routes": len(request.routes)
            }
    
    except Exception as e:
        logger.error(f"Network demand prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Network demand prediction failed: {str(e)}")

@app.post("/predict/ml", response_model=MLPredictionResponse)
async def predict_ml(request: MLPredictionRequest, api_key: str = Depends(get_api_key)):
    """Make ML-based predictions using the loaded model."""
    try:
        # Hot-reload model if needed
        load_model_if_needed()
        
        with PREDICTION_LATENCY.time():
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

            if model is None:
                raise HTTPException(status_code=503, detail="ML model not available")

            # Prepare input for model
            input_array = np.array([[distance, speed, passenger_count, fourth_feature]])

            # Make prediction
            prediction = model.predict(input_array)

            # Calculate confidence
            confidence = calculate_confidence(prediction)

            PREDICTION_COUNTER.inc()

            # Get route and stop information
            route_id = request.route_id
            stop_id = request.stop_id
            route_name = route_color = agency_name = fare_id = fare_price = first_stop_name = last_stop_name = None

            # Route info
            if route_id and "routes" in GTFS_LOOKUPS:
                route_row = GTFS_LOOKUPS["routes"][GTFS_LOOKUPS["routes"]["route_id"] == route_id]
                if not route_row.empty:
                    route_name = route_row.iloc[0].get("route_long_name") or route_row.iloc[0].get("route_short_name")
                    route_color = route_row.iloc[0].get("route_color")
                    agency_id = route_row.iloc[0].get("agency_id")
                    # Agency info
                    if "agency" in GTFS_LOOKUPS:
                        agency_row = GTFS_LOOKUPS["agency"][GTFS_LOOKUPS["agency"]["agency_id"] == agency_id]
                        if not agency_row.empty:
                            agency_name = agency_row.iloc[0].get("agency_name")
                # Fare info via fare_rules
                if "fare_rules" in GTFS_LOOKUPS:
                    fare_rule_row = GTFS_LOOKUPS["fare_rules"][GTFS_LOOKUPS["fare_rules"]["route_id"] == route_id]
                    if not fare_rule_row.empty:
                        fare_id = fare_rule_row.iloc[0].get("fare_id")
                        if "fare_attributes" in GTFS_LOOKUPS:
                            fare_attr_row = GTFS_LOOKUPS["fare_attributes"][GTFS_LOOKUPS["fare_attributes"]["fare_id"] == fare_id]
                            if not fare_attr_row.empty:
                                fare_price = fare_attr_row.iloc[0].get("price")
            # Stop info
            if stop_id and "stops" in GTFS_LOOKUPS:
                stop_row = GTFS_LOOKUPS["stops"][GTFS_LOOKUPS["stops"]["stop_id"] == stop_id]
                if not stop_row.empty:
                    first_stop_name = stop_row.iloc[0].get("stop_name")
                    last_stop_name = stop_row.iloc[0].get("stop_name")

            return MLPredictionResponse(
                prediction=float(prediction[0]),
                confidence=confidence,
                model_version=str(model_version) if model_version else "unknown",
                processing_time=PREDICTION_LATENCY._sum.get(),
                route_id=route_id,
                route_name=route_name,
                route_color=route_color,
                fare_id=fare_id,
                fare_price=float(fare_price) if fare_price is not None else None,
                agency_name=agency_name,
                first_stop_name=first_stop_name,
                last_stop_name=last_stop_name,
                input_summary=features_dict
            )

    except Exception as e:
        logger.error(f"ML prediction error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"ML prediction failed: {str(e)}"
        )

def calculate_confidence(prediction: np.ndarray) -> float:
    """Calculate confidence score for the prediction."""
    # Example: return a fixed confidence or implement actual confidence calculation
    return 0.95

@app.get("/visualize/network")
async def create_network_visualization():
    """Generate interactive transport network map."""
    try:
        logger.info("Creating network visualization")
        
        # Generate network map
        map_html = visualizer.create_network_map("data/raw")
        
        return FileResponse(
            path="data/processed/network_map.html",
            media_type="text/html",
            filename="network_map.html"
        )
    
    except Exception as e:
        logger.error(f"Network visualization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Network visualization failed: {str(e)}")

@app.get("/visualize/demand-heatmap")
async def create_demand_heatmap():
    """Generate demand heatmap visualization."""
    try:
        logger.info("Creating demand heatmap")
        
        # Generate demand heatmap
        heatmap_html = visualizer.create_demand_heatmap("data/raw")
        
        return FileResponse(
            path="data/processed/demand_heatmap.html",
            media_type="text/html",
            filename="demand_heatmap.html"
        )
    
    except Exception as e:
        logger.error(f"Demand heatmap failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Demand heatmap failed: {str(e)}")

@app.get("/dashboard")
async def get_dashboard():
    """Access comprehensive analysis dashboard."""
    try:
        logger.info("Generating comprehensive dashboard")
        
        # Generate all visualizations
        dashboard_html = visualizer.create_comprehensive_dashboard("data/raw")
        
        return FileResponse(
            path="data/processed/transport_dashboard.html",
            media_type="text/html",
            filename="transport_dashboard.html"
        )
    
    except Exception as e:
        logger.error(f"Dashboard generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")

@app.get("/results/{result_type}")
async def get_results(result_type: str):
    """Get optimization results by type."""
    try:
        if result_type == "routes":
            if 'routes' in optimization_results:
                return {
                    "status": "success",
                    "type": "route_optimization",
                    "data": optimization_results['routes']
                }
            else:
                return {"status": "pending", "message": "Route optimization in progress"}
        
        elif result_type == "schedules":
            if schedule_results:
                return {
                    "status": "success",
                    "type": "schedule_optimization",
                    "data": schedule_results
                }
            else:
                return {"status": "pending", "message": "Schedule optimization in progress"}
        
        elif result_type == "demand":
            if demand_predictions:
                return {
                    "status": "success",
                    "type": "demand_prediction",
                    "data": demand_predictions
                }
            else:
                return {"status": "no_data", "message": "No demand predictions available"}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown result type: {result_type}")
    
    except Exception as e:
        logger.error(f"Failed to get results for {result_type}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "route_optimizer": True,
                "demand_predictor": True,
                "schedule_optimizer": True,
                "visualizer": True,
                "ml_model": model is not None
            }
        }
        
        if model is not None:
            health_status["ml_model_version"] = str(model_version)
        
        return health_status
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/metrics")
async def get_metrics():
    """Get Prometheus metrics."""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response
        
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Metrics generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metrics generation failed: {str(e)}")

@app.get("/metadata")
async def get_metadata(api_key: str = Depends(get_api_key)):
    """Return ML model metadata and system information."""
    try:
        return {
            "model_name": model_name,
            "model_version": str(model_version) if model_version else "unknown",
            "model_status": "loaded" if model is not None else "not_loaded",
            "features": ["distance", "speed", "passenger_count", "day_of_week"],
            "system_info": {
                "api_version": "1.0.0",
                "gtfs_data_loaded": len(GTFS_LOOKUPS) > 0,
                "optimization_components": ["route_optimizer", "schedule_optimizer", "demand_predictor"],
                "visualization_components": ["network_map", "demand_heatmap", "dashboard"]
            }
        }
    except Exception as e:
        logger.error(f"Metadata generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metadata generation failed: {str(e)}")

@app.post("/feedback")
async def record_feedback(
    prediction_id: str,
    actual_value: float,
    api_key: str = Depends(get_api_key)
):
    """Record feedback for a prediction."""
    try:
        # Log feedback to MLflow
        mlflow.log_metric(
            f"feedback_{prediction_id}",
            actual_value
        )
        return {"status": "feedback recorded", "prediction_id": prediction_id}
    except Exception as e:
        logger.error(f"Error recording feedback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to record feedback"
        )

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=4
    ) 