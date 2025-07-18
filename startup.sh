#!/bin/bash

# startup.sh - Script to properly initialize volumes and permissions

set -e

echo "Starting MLflow and Airflow initialization..."

# Create necessary directories
echo " Creating directories..."
mkdir -p ./dags ./logs ./plugins ./configs ./data ./scripts ./mlruns
mkdir -p ./mlflow_data

# Set proper permissions
echo "Setting up permissions..."
export AIRFLOW_UID=$(id -u)
export AIRFLOW_GID=0

# Fix MLflow data permissions
sudo chown -R $AIRFLOW_UID:$AIRFLOW_GID ./mlflow_data
chmod -R 777 ./mlflow_data

# Fix other directories
sudo chown -R $AIRFLOW_UID:$AIRFLOW_GID ./logs ./dags ./plugins ./mlruns
chmod -R 755 ./logs ./dags ./plugins ./mlruns

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOL
AIRFLOW_UID=$AIRFLOW_UID
AIRFLOW_GID=$AIRFLOW_GID
AIRFLOW__CORE__FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
EOL
fi

# Create .env.mlflow file if it doesn't exist
if [ ! -f .env.mlflow ]; then
    echo "Creating .env.mlflow file..."
    cat > .env.mlflow << EOL
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_DEFAULT_ARTIFACT_ROOT=/data/artifacts
GIT_PYTHON_REFRESH=quiet
EOL
fi

echo "Initialization complete!"
echo "Starting Docker Compose..."

# Start the services
docker compose up -d

echo "Services started successfully!"
echo "Airflow UI: http://localhost:8082 (admin/admin)"
echo "MLflow UI: http://localhost:5000"
echo ""
echo "To check logs: docker-compose logs -f [service-name]"
echo "To stop: docker-compose down"
