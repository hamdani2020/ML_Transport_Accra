#!/bin/bash
# Application Installation Script Template for ML Transport Accra
# This template is processed by Terraform and injected into EC2 user data

set -e

# Template variables (will be replaced by Terraform)
S3_DATA_BUCKET="${s3_data_bucket}"
S3_MODELS_BUCKET="${s3_models_bucket}"
S3_LOGS_BUCKET="${s3_logs_bucket}"
AWS_REGION="${aws_region}"
ENVIRONMENT="${environment}"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a /var/log/app-install.log
}

log "Starting ML Transport Accra application installation..."

# Create application directory structure
log "Creating application directories..."
mkdir -p /opt/ml-transport-accra/{data,logs,models,configs,scripts}
mkdir -p /opt/ml-transport-accra/data/{raw,processed}

# Download application code from S3
log "Downloading application code..."
cd /opt/ml-transport-accra
aws s3 sync s3://$S3_DATA_BUCKET/application/ . --region $AWS_REGION || log "No application code found in S3"

# Download GTFS data
log "Downloading GTFS data..."
aws s3 sync s3://$S3_DATA_BUCKET/gtfs/ data/raw/ --region $AWS_REGION || log "No GTFS data found in S3"

# Set up Python virtual environment
log "Setting up Python environment..."
python3 -m venv /opt/ml-transport-accra/venv
source /opt/ml-transport-accra/venv/bin/activate

# Install Python dependencies
log "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt || log "No requirements.txt found, installing basic dependencies"

# Install core ML dependencies
pip install \
    fastapi[all] \
    uvicorn \
    pandas \
    numpy \
    scikit-learn \
    mlflow \
    apache-airflow \
    ortools \
    pulp \
    plotly \
    folium \
    xgboost \
    lightgbm

# Set up environment variables
log "Configuring environment..."
cat > /opt/ml-transport-accra/.env << EOF
AWS_DEFAULT_REGION=$AWS_REGION
S3_DATA_BUCKET=$S3_DATA_BUCKET
S3_MODELS_BUCKET=$S3_MODELS_BUCKET
S3_LOGS_BUCKET=$S3_LOGS_BUCKET
ENVIRONMENT=$ENVIRONMENT
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_S3_ENDPOINT_URL=https://s3.$AWS_REGION.amazonaws.com
EOF

# Set up systemd service
log "Creating systemd service..."
cat > /etc/systemd/system/ml-transport-accra.service << EOF
[Unit]
Description=ML Transport Accra Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/ml-transport-accra
Environment=PATH=/opt/ml-transport-accra/venv/bin
EnvironmentFile=/opt/ml-transport-accra/.env
ExecStart=/opt/ml-transport-accra/venv/bin/python api/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Set permissions
chown -R ubuntu:ubuntu /opt/ml-transport-accra
chmod +x /opt/ml-transport-accra/scripts/* || true

# Enable and start service
systemctl daemon-reload
systemctl enable ml-transport-accra
systemctl start ml-transport-accra

log "ML Transport Accra application installation completed."
