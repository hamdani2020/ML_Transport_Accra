# Accra Public Transport Efficiency Analysis

An AI-powered system for analyzing and optimizing public transport routes in Accra, Ghana. This project provides actionable insights for route optimization, demand prediction, and schedule optimization to improve transport efficiency and accessibility.

## Project Objectives

- **Route Optimization**: Optimize transport routes using OR-Tools to reduce travel time and distance
- **Demand Prediction**: Predict passenger demand using machine learning models
- **Schedule Optimization**: Optimize bus schedules using linear programming
- **Resource Allocation**: Efficiently allocate vehicles and resources
- **Visualization**: Interactive maps and dashboards for analysis

##  Architecture

```
ML_Transport_Accra/
├── api/                    # FastAPI service
│   └── main.py            # API endpoints
├── scripts/               # Core analysis modules
│   ├── train.py           # ML model training
│   ├── route_optimizer.py # Route optimization
│   ├── demand_predictor.py # Demand prediction
│   ├── schedule_optimizer.py # Schedule optimization
│   └── visualization.py   # Data visualization
├── pipelines/             # ML pipelines
│   └── train_model_dag.py # Training pipeline
├── configs/               # Configuration files
│   └── config.yaml        # Main configuration
├── data/                  # Data storage
│   ├── raw/               # GTFS data files
│   └── processed/         # Processed data and results
├── models/                # Trained ML models
├── dags/                  # Airflow DAGs
├── logs/                  # Airflow logs
├── plugins/               # Airflow plugins
├── mlruns/                # MLflow artifacts
├── docker-compose.yml     # Docker services configuration
└── requirements.txt       # Python dependencies
```

## Features

### 1. Route Optimization
- **OR-Tools Integration**: Uses Google's OR-Tools for vehicle routing problems
- **Distance Matrix Calculation**: Haversine formula for accurate distance calculations
- **Demand-Based Optimization**: Considers passenger demand patterns
- **Constraint Handling**: Vehicle capacity, time windows, and route constraints

### 2. Demand Prediction
- **Multiple ML Models**: Random Forest, XGBoost, LightGBM, Gradient Boosting
- **Feature Engineering**: Time-based features, day-of-week patterns, route characteristics
- **Real-time Prediction**: Predict demand for specific stops, routes, and times
- **Network-wide Analysis**: Predict demand across the entire transport network

### 3. Schedule Optimization
- **Linear Programming**: Uses PuLP for schedule optimization
- **Headway Optimization**: Optimize bus frequencies based on demand
- **Fleet Management**: Efficient vehicle allocation and utilization
- **GTFS Generation**: Generate optimized GTFS files for deployment

### 4. Data Visualization
- **Interactive Maps**: Folium-based network visualization
- **Demand Heatmaps**: Plotly-based demand pattern visualization
- **Time Series Analysis**: Daily and hourly demand patterns
- **Optimization Reports**: Comprehensive HTML reports with recommendations

### 5. API Service
- **RESTful API**: FastAPI-based service with automatic documentation
- **Background Processing**: Asynchronous optimization tasks
- **Real-time Results**: Live access to optimization results
- **Comprehensive Dashboard**: Web-based analysis interface

### 6. Workflow Orchestration
- **Apache Airflow**: Automated pipeline orchestration and scheduling
- **MLflow**: Machine learning experiment tracking and model management
- **Docker Integration**: Containerized services for easy deployment

## Dataset

The project uses the **GTFS (General Transit Feed Specification)** dataset for Accra, Ghana, collected in May and June 2015. The dataset includes:

- **agency.txt**: Transport agency information
- **routes.txt**: Route definitions and characteristics
- **stops.txt**: Stop locations and information
- **trips.txt**: Trip definitions
- **stop_times.txt**: Stop arrival and departure times
- **calendar.txt**: Service schedules
- **shapes.txt**: Route geometries
- **fare_attributes.txt**: Fare information

## Installation

### Prerequisites
- Python 3.8+
- pip
- Git
- Docker and Docker Compose (for containerized setup)

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd ML_Transport_Accra
```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify GTFS data**
Ensure the GTFS files are present in `data/raw/`:
```bash
ls data/raw/
# Should show: agency.txt, routes.txt, stops.txt, trips.txt, stop_times.txt, etc.
```

## Docker Setup with Airflow and MLflow

This project includes Docker Compose configuration to run Apache Airflow and MLflow services for workflow orchestration and ML experiment tracking.

### Services Overview

- **Apache Airflow**: Workflow orchestration and scheduling
  - Web UI: http://localhost:8080
  - Scheduler for automated pipeline execution
  - PostgreSQL backend for metadata storage

- **MLflow**: Machine learning experiment tracking
  - Tracking UI: http://localhost:5000
  - Model registry and artifact storage
  - SQLite backend for experiment tracking

### Quick Start

1. **Initialize Airflow database**
```bash
docker-compose run airflow-webserver airflow db init
```

2. **Create Airflow admin user (optional)**
```bash
docker-compose run airflow-webserver airflow users create \
  --username admin --password admin --firstname Admin --lastname User \
  --role Admin --email admin@example.com
```

3. **Start all services**
```bash
docker-compose up -d
```

4. **Access the services**
   - **Airflow UI**: http://localhost:8080 (admin/admin)
   - **MLflow UI**: http://localhost:5000

### Service Management

```bash
# Start services in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart specific service
docker-compose restart airflow-webserver

# Remove all containers and volumes
docker-compose down -v
```

### Airflow DAGs

Place your Airflow DAGs in the `dags/` directory. They will be automatically loaded by the Airflow scheduler.

Example DAG structure:
```
dags/
├── transport_optimization_dag.py
├── model_training_dag.py
└── data_processing_dag.py
```

### MLflow Integration

The MLflow service is configured with:
- **Backend Store**: SQLite database (`mlflow.db`)
- **Artifact Store**: Local file system (`mlruns/`)
- **Port**: 5000

Use MLflow in your Python scripts:
```python
import mlflow

# Set tracking URI
mlflow.set_tracking_uri("http://localhost:5000")

# Start experiment
with mlflow.start_run():
    # Your ML code here
    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_model(model, "model")
```

### Customization

Edit `docker-compose.yml` to customize:
- Service ports
- Environment variables
- Volume mounts
- Resource limits

## 🚀 Usage

### 1. Start the API Service

```bash
cd api
python main.py
```

The API will be available at `http://localhost:8000`

### 2. Access the Dashboard

Visit `http://localhost:8000/dashboard` for the comprehensive analysis dashboard.

### 3. API Endpoints

#### Route Optimization
```bash
curl -X POST "http://localhost:8000/optimize/routes" \
     -H "Content-Type: application/json" \
     -d '{"vehicle_capacity": 100, "max_route_time": 120}'
```

#### Demand Prediction
```bash
curl -X POST "http://localhost:8000/predict/demand" \
     -H "Content-Type: application/json" \
     -d '{"stop_id": "STOP001", "route_id": "ROUTE001", "time": "08:30:00", "day_of_week": "monday"}'
```

#### Schedule Optimization
```bash
curl -X POST "http://localhost:8000/optimize/schedules" \
     -H "Content-Type: application/json" \
     -d '{"vehicle_capacity": 100, "min_headway": 5, "max_headway": 30}'
```

#### Get Results
```bash
# Route optimization results
curl "http://localhost:8000/results/routes"

# Schedule optimization results
curl "http://localhost:8000/results/schedules"

# Demand prediction results
curl "http://localhost:8000/results/demand"
```

### 4. Individual Scripts

#### Train ML Models
```bash
python scripts/train.py
```

#### Run Route Optimization
```bash
python scripts/route_optimizer.py
```

#### Run Demand Prediction
```bash
python scripts/demand_predictor.py
```

#### Run Schedule Optimization
```bash
python scripts/schedule_optimizer.py
```

#### Generate Visualizations
```bash
python scripts/visualization.py
```

## 📈 Expected Improvements

### Efficiency Gains
- **Route Optimization**: 15-25% reduction in total route distance
- **Schedule Optimization**: 20-30% improvement in fleet utilization
- **Demand Prediction**: 85-90% accuracy in passenger demand forecasting

### Operational Benefits
- **Reduced Congestion**: Optimized routes reduce traffic bottlenecks
- **Lower Emissions**: Efficient routes reduce fuel consumption
- **Better Service**: Improved schedules reduce waiting times
- **Cost Savings**: Optimized resource allocation reduces operational costs

## 🔧 Configuration

Edit `configs/config.yaml` to customize:

```yaml
data:
  raw_dir: "data/raw"
  processed_dir: "data/processed"

mlflow:
  tracking_uri: "sqlite:///mlflow.db"
  experiment_name: "transport_optimization"

optimization:
  vehicle_capacity: 100
  max_route_time: 120
  min_headway: 5
  max_headway: 30
  max_fleet_size: 50

api:
  host: "0.0.0.0"
  port: 8000
```

## 📊 Monitoring and Metrics

### API Metrics
- **Health Check**: `GET /health`
- **System Metrics**: `GET /metrics`
- **Optimization Status**: `GET /results/{type}`

### Performance Indicators
- Route efficiency improvement percentage
- Fleet utilization rate
- Demand prediction accuracy
- API response times
- Optimization completion status

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=scripts tests/

# Run specific test
pytest tests/test_route_optimizer.py
```

## 📝 API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **GTFS Data**: Accra transport data from 2015
- **OR-Tools**: Google's optimization library
- **FastAPI**: Modern web framework for APIs
- **Plotly & Folium**: Interactive visualization libraries

## 📞 Support

For questions and support:
- Create an issue in the repository
- Contact the development team
- Check the API documentation at `/docs`

---

**Note**: This is a demonstration project for the Accra Public Transport Efficiency Analysis challenge. The system is designed to be scalable and can be adapted for real-world deployment with additional data sources and integration requirements.
