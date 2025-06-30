"""
FastAPI Service for Accra Public Transport Analysis
Provides endpoints for route optimization, demand prediction, and schedule optimization
"""

import os
import sys
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uvicorn
import json
import pandas as pd
from datetime import datetime
from fastapi.staticfiles import StaticFiles

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

# Initialize components
route_optimizer = RouteOptimizer()
demand_predictor = DemandPredictor()
schedule_optimizer = ScheduleOptimizer()
visualizer = TransportVisualizer()

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

# Global storage for results
optimization_results = {}
demand_predictions = {}
schedule_results = {}

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API documentation."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Accra Public Transport Analysis API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { text-align: center; margin-bottom: 30px; }
            .endpoint { background-color: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }
            .method { font-weight: bold; color: #0066cc; }
            .url { font-family: monospace; background-color: #e0e0e0; padding: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚌 Accra Public Transport Analysis API</h1>
            <p>AI-powered transport efficiency analysis for Accra, Ghana</p>
        </div>
        
        <h2>Available Endpoints</h2>
        
        <div class="endpoint">
            <div class="method">GET</div>
            <div class="url">/docs</div>
            <p>Interactive API documentation (Swagger UI)</p>
        </div>
        
        <div class="endpoint">
            <div class="method">POST</div>
            <div class="url">/optimize/routes</div>
            <p>Optimize transport routes using OR-Tools</p>
        </div>
        
        <div class="endpoint">
            <div class="method">POST</div>
            <div class="url">/predict/demand</div>
            <p>Predict passenger demand for specific stops and times</p>
        </div>
        
        <div class="endpoint">
            <div class="method">POST</div>
            <div class="url">/optimize/schedules</div>
            <p>Optimize bus schedules using linear programming</p>
        </div>
        
        <div class="endpoint">
            <div class="method">GET</div>
            <div class="url">/visualize/network</div>
            <p>Generate interactive transport network map</p>
        </div>
        
        <div class="endpoint">
            <div class="method">GET</div>
            <div class="url">/dashboard</div>
            <p>Access comprehensive analysis dashboard</p>
        </div>
        
        <div class="endpoint">
            <div class="method">GET</div>
            <div class="url">/results/{result_type}</div>
            <p>Get optimization results (routes, schedules, demand)</p>
        </div>
    </body>
    </html>
    """

@app.post("/optimize/routes", response_model=OptimizationResponse)
async def optimize_routes(request: RouteOptimizationRequest, background_tasks: BackgroundTasks):
    """Optimize transport routes using OR-Tools."""
    try:
        logger.info("Starting route optimization")
        
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

@app.post("/predict/demand", response_model=DemandPredictionResponse)
async def predict_demand(request: DemandPredictionRequest):
    """Predict passenger demand for a specific stop, route, time, and day."""
    try:
        logger.info(f"Predicting demand for {request.stop_id} at {request.time}")
        
        # Load models if not already loaded
        if not demand_predictor.models:
            demand_predictor.load_models()
        
        # Make prediction
        prediction = demand_predictor.predict_demand(
            request.stop_id,
            request.route_id,
            request.time,
            request.day_of_week
        )
        
        return DemandPredictionResponse(**prediction)
    
    except Exception as e:
        logger.error(f"Demand prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Demand prediction failed: {str(e)}")

@app.post("/predict/network-demand")
async def predict_network_demand(request: NetworkDemandRequest):
    """Predict demand for multiple stops, routes, and times."""
    try:
        logger.info("Predicting network-wide demand")
        
        # Load models if not already loaded
        if not demand_predictor.models:
            demand_predictor.load_models()
        
        # Make predictions
        predictions_df = demand_predictor.predict_network_demand(
            request.stops,
            request.routes,
            tuple(request.time_range),
            request.days
        )
        
        # Store results
        global demand_predictions
        demand_predictions['network'] = predictions_df.to_dict('records')
        
        return {
            "status": "success",
            "message": f"Predicted demand for {len(predictions_df)} combinations",
            "data": predictions_df.to_dict('records'),
            "total_predictions": len(predictions_df)
        }
    
    except Exception as e:
        logger.error(f"Network demand prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Network demand prediction failed: {str(e)}")

@app.post("/optimize/schedules")
async def optimize_schedules(request: ScheduleOptimizationRequest, background_tasks: BackgroundTasks):
    """Optimize bus schedules using linear programming."""
    try:
        logger.info("Starting schedule optimization")
        
        # Run optimization in background
        def run_schedule_optimization():
            global schedule_results
            data = schedule_optimizer.load_gtfs_data("data/raw")
            schedule_data = schedule_optimizer.prepare_schedule_data(data)
            results = schedule_optimizer.optimize_schedules(schedule_data)
            schedule_results = results
            
            # Generate optimized GTFS and reports
            if results['status'] == 'Optimal':
                schedule_optimizer.generate_optimized_gtfs(data, results, "data/processed/optimized_gtfs")
                schedule_optimizer.create_schedule_report(results)
        
        background_tasks.add_task(run_schedule_optimization)
        
        return {
            "status": "success",
            "message": "Schedule optimization started. Check /results/schedules for results."
        }
    
    except Exception as e:
        logger.error(f"Schedule optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Schedule optimization failed: {str(e)}")

@app.get("/visualize/network")
async def create_network_visualization():
    """Generate interactive transport network map."""
    try:
        logger.info("Creating network visualization")
        
        # Load data and create map
        data = visualizer.load_gtfs_data("data/raw")
        map_path = visualizer.create_network_map(data)
        
        if map_path and os.path.exists(map_path):
            return FileResponse(map_path, media_type="text/html")
        else:
            raise HTTPException(status_code=500, detail="Failed to create network map")
    
    except Exception as e:
        logger.error(f"Network visualization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Network visualization failed: {str(e)}")

@app.get("/visualize/demand-heatmap")
async def create_demand_heatmap():
    """Generate demand heatmap visualization."""
    try:
        logger.info("Creating demand heatmap")
        
        # Create sample demand data if none exists
        if 'network' not in demand_predictions:
            sample_demand = pd.DataFrame({
                'stop_id': ['STOP001', 'STOP002', 'STOP003'] * 8,
                'time': ['08:00:00', '08:15:00', '08:30:00', '09:00:00', '09:15:00', '09:30:00', 
                        '17:00:00', '17:15:00', '17:30:00', '18:00:00', '18:15:00', '18:30:00',
                        '12:00:00', '12:15:00', '12:30:00', '13:00:00', '13:15:00', '13:30:00',
                        '20:00:00', '20:15:00', '20:30:00', '21:00:00', '21:15:00', '21:30:00'],
                'predicted_demand': [120, 85, 95, 110, 75, 90, 140, 130, 125, 115, 100, 105, 
                                   80, 70, 85, 90, 75, 80, 60, 50, 65, 70, 55, 60]
            })
        else:
            sample_demand = pd.DataFrame(demand_predictions['network'])
        
        heatmap_path = visualizer.create_demand_heatmap(sample_demand)
        
        if heatmap_path and os.path.exists(heatmap_path):
            return FileResponse(heatmap_path, media_type="text/html")
        else:
            raise HTTPException(status_code=500, detail="Failed to create demand heatmap")
    
    except Exception as e:
        logger.error(f"Demand heatmap creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Demand heatmap creation failed: {str(e)}")

@app.get("/dashboard")
async def get_dashboard():
    """Get comprehensive analysis dashboard."""
    try:
        logger.info("Creating comprehensive dashboard")
        
        # Load data
        data = visualizer.load_gtfs_data("data/raw")
        
        # Create sample data for demonstration
        sample_demand = pd.DataFrame({
            'stop_id': ['STOP001', 'STOP002', 'STOP003'] * 8,
            'time': ['08:00:00', '08:15:00', '08:30:00', '09:00:00', '09:15:00', '09:30:00', 
                    '17:00:00', '17:15:00', '17:30:00', '18:00:00', '18:15:00', '18:30:00',
                    '12:00:00', '12:15:00', '12:30:00', '13:00:00', '13:15:00', '13:30:00',
                    '20:00:00', '20:15:00', '20:30:00', '21:00:00', '21:15:00', '21:30:00'],
            'predicted_demand': [120, 85, 95, 110, 75, 90, 140, 130, 125, 115, 100, 105, 
                               80, 70, 85, 90, 75, 80, 60, 50, 65, 70, 55, 60]
        })
        
        sample_optimization = {
            'optimized_routes': {
                'ROUTE001': {'total_distance': 15.5, 'total_time': 45},
                'ROUTE002': {'total_distance': 22.3, 'total_time': 67},
                'ROUTE003': {'total_distance': 18.7, 'total_time': 52}
            },
            'efficiency_improvement': 23.5
        }
        
        # Create dashboard
        dashboard_path = visualizer.create_dashboard(data, sample_demand, sample_optimization)
        
        if dashboard_path and os.path.exists(dashboard_path):
            return FileResponse(dashboard_path, media_type="text/html")
        else:
            raise HTTPException(status_code=500, detail="Failed to create dashboard")
    
    except Exception as e:
        logger.error(f"Dashboard creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dashboard creation failed: {str(e)}")

@app.get("/results/{result_type}")
async def get_results(result_type: str):
    """Get optimization results by type."""
    try:
        if result_type == "routes":
            if 'routes' in optimization_results:
                return {
                    "status": "success",
                    "data": optimization_results['routes']
                }
            else:
                return {
                    "status": "pending",
                    "message": "Route optimization in progress or not started"
                }
        
        elif result_type == "schedules":
            if schedule_results:
                return {
                    "status": "success",
                    "data": schedule_results
                }
            else:
                return {
                    "status": "pending",
                    "message": "Schedule optimization in progress or not started"
                }
        
        elif result_type == "demand":
            if 'network' in demand_predictions:
                return {
                    "status": "success",
                    "data": demand_predictions['network']
                }
            else:
                return {
                    "status": "pending",
                    "message": "No demand predictions available"
                }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown result type: {result_type}")
    
    except Exception as e:
        logger.error(f"Failed to get results for {result_type}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Accra Public Transport Analysis API"
    }

@app.get("/metrics")
async def get_metrics():
    """Get system metrics and performance indicators."""
    try:
        # Calculate basic metrics
        metrics = {
            "total_routes_optimized": len(optimization_results.get('routes', {}).get('optimized_routes', {})),
            "total_demand_predictions": len(demand_predictions.get('network', [])),
            "schedule_optimization_status": schedule_results.get('status', 'not_started'),
            "efficiency_improvement": optimization_results.get('routes', {}).get('efficiency_improvement', 0),
            "api_uptime": "running",
            "last_optimization": datetime.now().isoformat()
        }
        
        return metrics
    
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 