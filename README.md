# ML Transport Accra

A machine learning system for analyzing and optimizing public transportation in Accra using GTFS data.

## Project Overview

This project implements a machine learning pipeline for processing GTFS (General Transit Feed Specification) data from Accra's public transportation system. The system aims to provide insights and predictions to improve transit efficiency and reliability.

## Directory Structure

```
├── data/
│   ├── raw/                  # Original GTFS data (e.g., .zip files)
│   └── processed/            # Cleaned and feature-engineered data
├── models/                   # Trained and versioned models (artifacts)
├── pipelines/               
│   ├── train_model_dag.py    # Airflow/Prefect DAG for training
│   └── rollback.py           # Rollback logic for simulations/model promotion
├── inference/
│   ├── inference_api.py      # FastAPI serving logic
│   └── Dockerfile            # Dockerfile for the inference API
├── scripts/
│   ├── train.py              # Data preprocessing and model training script
│   ├── evaluate.py           # Model evaluation script
│   ├── compare_ab.py         # A/B simulation analysis
│   └── track_experiments.py  # MLflow experiment tracking
├── tests/                    # Unit and integration tests
├── configs/                  # Configuration files
└── .github/workflows/        # CI/CD pipeline definitions
```

## Setup and Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Data Processing
```bash
python scripts/train.py --config configs/config.yaml
```

### Model Training
```bash
python scripts/train.py --config configs/config.yaml
```

### Model Evaluation
```bash
python scripts/evaluate.py --model-version v1.0
```

## Inference API

The inference API provides a RESTful interface for making predictions using trained models. It's built with FastAPI and includes monitoring, authentication, and comprehensive documentation.

### Quick Start

#### Option 1: Development Mode (Recommended for Development)
```bash
# From the project root directory
python -m uvicorn inference.inference_api:app --host 0.0.0.0 --port 8000 --reload
```

#### Option 2: Production Mode (Single Process)
```bash
# From the project root directory
python -m uvicorn inference.inference_api:app --host 0.0.0.0 --port 8000
```

#### Option 3: Production Mode with Gunicorn (Multiple Workers)
```bash
# Install gunicorn first
pip install gunicorn

# Run with multiple workers
gunicorn inference.inference_api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### Option 4: Docker Deployment (Production)
```bash
# Build the Docker image
docker build -f inference/Dockerfile -t ml-transport-api .

# Run the container
docker run -p 8000:8000 -e API_KEY=your_secret_key ml-transport-api
```

### API Configuration

#### Environment Variables
- `API_KEY`: Secret key for API authentication (required for protected endpoints)
- `MLFLOW_TRACKING_URI`: MLflow tracking server URI (defaults to local SQLite)

#### Example Setup
```bash
export API_KEY=your_secret_key_here
export MLFLOW_TRACKING_URI=sqlite:///mlflow.db
```

### API Endpoints

#### 1. Root Endpoint (Model Details)
```http
GET /
```
**Response:**
```json
{
  "status": "healthy",
  "model_name": "transport_predictor",
  "model_version": 7,
  "features": [
    "distance",
    "speed", 
    "passenger_count",
    "route_id",
    "stop_id",
    "direction_id"
  ],
  "description": "ML Transport Accra Prediction API"
}
```

#### 2. Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "model_version": 7
}
```

#### 3. API Documentation
```http
GET /docs
```
Interactive Swagger UI documentation with all endpoints and schemas.

#### 4. Make Predictions
```http
POST /predict
```
**Headers:**
```
X-API-Key: your_secret_key
Content-Type: application/json
```

**Request Body:**
```json
{
  "route_id": "route_001",
  "stop_id": "stop_001",
  "timestamp": "2024-01-01T10:00:00Z",
  "features": {
    "distance": 5.2,
    "speed": 25.0,
    "passenger_count": 15
  },
  "additional_context": {
    "weather_condition": "sunny",
    "special_event": null
  }
}
```

**Response:**
```json
{
  "prediction": 12.5,
  "confidence": 0.95,
  "model_version": 7,
  "processing_time": 0.023
}
```

#### 5. Model Metadata
```http
GET /metadata
```
**Headers:**
```
X-API-Key: your_secret_key
```

**Response:**
```json
{
  "model_name": "transport_predictor",
  "model_version": 7,
  "features": [
    "distance",
    "speed",
    "passenger_count", 
    "route_id",
    "stop_id",
    "direction_id"
  ],
  "last_trained": null,
  "performance_metrics": null
}
```

#### 6. Record Feedback
```http
POST /feedback
```
**Headers:**
```
X-API-Key: your_secret_key
Content-Type: application/json
```

**Request Body:**
```json
{
  "prediction_id": "pred_12345",
  "actual_value": 15.2
}
```

**Response:**
```json
{
  "status": "feedback recorded"
}
```

### Testing the API

#### Using curl
```bash
# Health check (no API key required)
curl http://localhost:8000/health

# Get model details (no API key required)
curl http://localhost:8000/

# Get model metadata (requires API key)
curl -H "X-API-Key: your_secret_key" http://localhost:8000/metadata

# Make a prediction
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: your_secret_key" \
  -H "Content-Type: application/json" \
  -d '{
    "route_id": "route_001",
    "stop_id": "stop_001",
    "timestamp": "2024-01-01T10:00:00Z",
    "features": {
      "distance": 5.2,
      "speed": 25.0,
      "passenger_count": 15
    }
  }'
```

#### Using Python requests
```python
import requests

# Set API key
headers = {"X-API-Key": "your_secret_key"}

# Health check (no API key required)
response = requests.get("http://localhost:8000/health")
print(response.json())

# Get model details (no API key required)
response = requests.get("http://localhost:8000/")
print(response.json())

# Make prediction
prediction_data = {
    "route_id": "route_001",
    "stop_id": "stop_001",
    "timestamp": "2024-01-01T10:00:00Z",
    "features": {
        "distance": 5.2,
        "speed": 25.0,
        "passenger_count": 15
    }
}

response = requests.post(
    "http://localhost:8000/predict",
    headers=headers,
    json=prediction_data
)
print(response.json())
```

### API Key Authentication

The API uses API key authentication for protected endpoints. Here's how to set it up:

#### 1. Set the API Key Environment Variable
```bash
export API_KEY="your-secret-api-key-here"
```

#### 2. Start the Server with API Key
```bash
API_KEY="your-secret-api-key-here" python -m uvicorn inference.inference_api:app --host 0.0.0.0 --port 8000
```

#### 3. Include API Key in Requests
For protected endpoints, include the API key in the request headers:
```
X-API-Key: your-secret-api-key-here
```

#### Protected vs Public Endpoints

**Protected Endpoints (require API key):**
- `POST /predict` - Make predictions
- `GET /metadata` - Get model metadata
- `POST /feedback` - Record feedback

**Public Endpoints (no API key required):**
- `GET /` - Root endpoint with model details
- `GET /health` - Health check
- `GET /docs` - API documentation

#### Testing API Key Authentication
```bash
# Test with correct API key
curl -H "X-API-Key: your-secret-key" http://localhost:8000/metadata

# Test with wrong API key (should return 401)
curl -H "X-API-Key: wrong-key" http://localhost:8000/metadata

# Test without API key (should return 401)
curl http://localhost:8000/metadata
```

### Monitoring and Observability

#### Prometheus Metrics
The API exposes Prometheus metrics on port 9090:
- `prediction_requests_total`: Total number of prediction requests
- `prediction_latency_seconds`: Prediction processing time

#### Health Checks
- Endpoint: `/health`
- Returns model status and version
- Useful for load balancers and monitoring systems

#### Logging
- Structured logging with configurable levels
- Logs include request IDs, processing times, and errors
- Configured via `config.yaml` under `monitoring.log_level`

### Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid input)
- `401`: Unauthorized (invalid API key)
- `500`: Internal Server Error (model loading/prediction failures)

### Security Features

- **API Key Authentication**: All prediction endpoints require a valid API key
- **Input Validation**: Automatic validation of request schemas
- **Rate Limiting**: Configurable rate limiting (can be added via middleware)
- **CORS**: Configurable Cross-Origin Resource Sharing

### Deployment Considerations

#### Production Checklist
- [ ] Set secure API key
- [ ] Configure MLflow tracking URI
- [ ] Set up monitoring and alerting
- [ ] Configure reverse proxy (nginx)
- [ ] Set up SSL/TLS certificates
- [ ] Configure log aggregation
- [ ] Set up backup and recovery procedures

#### Docker Deployment
```bash
# Build optimized image
docker build -f inference/Dockerfile -t ml-transport-api .

# Run with environment variables
docker run -d \
  -p 8000:8000 \
  -e API_KEY=your_production_key \
  -e MLFLOW_TRACKING_URI=your_mlflow_uri \
  --name ml-transport-api \
  ml-transport-api
```

#### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-transport-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ml-transport-api
  template:
    metadata:
      labels:
        app: ml-transport-api
    spec:
      containers:
      - name: api
        image: ml-transport-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: api-key
```

### Troubleshooting

#### Common Issues

1. **Model Not Loaded**
   - Ensure a model is trained and available in MLflow
   - Check MLflow tracking URI configuration
   - Verify model name and stage in config

2. **API Key Issues**
   - Set the `API_KEY` environment variable
   - Include `X-API-Key` header in requests
   - Check for typos in the API key

3. **Port Already in Use**
   - Change the port: `--port 8001`
   - Kill existing processes: `pkill -f uvicorn`

4. **Import Errors**
   - Ensure you're running from the project root
   - Check virtual environment activation
   - Verify all dependencies are installed

#### Debug Mode
```bash
# Run with debug logging
python -m uvicorn inference.inference_api:app --host 0.0.0.0 --port 8000 --log-level debug
```

## MLflow Experiment Tracking

Access the MLflow UI to view experiment results:
```bash
mlflow ui
```

## Testing

Run the test suite:
```bash
pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions or feedback, please open an issue in the repository.

mlflow ui --backend-store-uri sqlite:///$(pwd)/mlflow.db