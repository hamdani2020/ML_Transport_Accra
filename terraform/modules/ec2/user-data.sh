#!/bin/bash
# User Data Script for ML Transport Accra EC2 Instances
# This script initializes the instance with all required software and configurations

set -e

# Variables passed from Terraform
S3_DATA_BUCKET="${s3_data_bucket}"
S3_MODELS_BUCKET="${s3_models_bucket}"
S3_LOGS_BUCKET="${s3_logs_bucket}"
AWS_REGION="${aws_region}"
ENVIRONMENT="${environment}"
PROJECT_NAME="${project_name}"
APPLICATION_PORT="${application_port}"
AIRFLOW_PORT="${airflow_port}"
MLFLOW_PORT="${mlflow_port}"
DOCKER_COMPOSE_VERSION="${docker_compose_version}"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a /var/log/user-data.log
}

log "Starting ML Transport Accra instance initialization..."

# Update system packages
log "Updating system packages..."
apt-get update -y
apt-get upgrade -y

# Install essential packages
log "Installing essential packages..."
apt-get install -y \
    awscli \
    curl \
    wget \
    git \
    unzip \
    htop \
    tree \
    jq \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    supervisor \
    nginx \
    fail2ban

# Install Docker
log "Installing Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Install Docker Compose
log "Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# CloudWatch agent installation removed to reduce costs and complexity
log_info "Skipping CloudWatch agent installation..."

# CloudWatch agent configuration removed to reduce costs and complexity
log_info "CloudWatch agent configuration skipped - using local logging only"

# Mount and format additional data volume
log "Setting up additional data volume..."
if lsblk | grep -q nvme1n1; then
    DEVICE="/dev/nvme1n1"
elif lsblk | grep -q xvdf; then
    DEVICE="/dev/xvdf"
else
    log "No additional volume found, skipping data volume setup"
    DEVICE=""
fi

if [ ! -z "$DEVICE" ]; then
    # Check if device is already formatted
    if ! blkid $DEVICE; then
        log "Formatting data volume..."
        mkfs.ext4 $DEVICE
    fi

    # Create mount point and mount
    mkdir -p /data
    mount $DEVICE /data

    # Add to fstab for persistent mounting
    echo "$DEVICE /data ext4 defaults,nofail 0 2" >> /etc/fstab

    # Set ownership and permissions
    chown ubuntu:ubuntu /data
    chmod 755 /data
fi

# Create application directories
log "Creating application directories..."
mkdir -p /home/ubuntu/ml-transport-accra
mkdir -p /home/ubuntu/ml-transport-accra/data
mkdir -p /home/ubuntu/ml-transport-accra/logs
mkdir -p /home/ubuntu/ml-transport-accra/models
mkdir -p /home/ubuntu/ml-transport-accra/config
mkdir -p /data/mlruns
mkdir -p /data/airflow-logs

# Set up symlinks for data storage
ln -sf /data/mlruns /home/ubuntu/ml-transport-accra/mlruns
ln -sf /data/airflow-logs /home/ubuntu/ml-transport-accra/logs/airflow-logs

# Set ownership
chown -R ubuntu:ubuntu /home/ubuntu/ml-transport-accra
chown -R ubuntu:ubuntu /data

# Download application package from S3
log "Downloading application package from S3..."
cd /home/ubuntu/ml-transport-accra
aws s3 cp s3://$S3_DATA_BUCKET/deployments/app-package.zip . --region $AWS_REGION
unzip -o app-package.zip
rm app-package.zip

# Download GTFS data from S3
log "Downloading GTFS data from S3..."
mkdir -p data/raw
aws s3 sync s3://$S3_DATA_BUCKET/gtfs/ data/raw/ --region $AWS_REGION

# Download configuration from S3
log "Downloading configuration from S3..."
aws s3 cp s3://$S3_DATA_BUCKET/config/config.yaml configs/config.yaml --region $AWS_REGION

# Update configuration with S3 bucket names and environment variables
log "Updating configuration..."
cat > configs/config-override.yaml << EOF
# Environment-specific configuration overrides
data:
  raw_dir: "data/raw"
  processed_dir: "data/processed"
  s3_data_bucket: "$S3_DATA_BUCKET"
  s3_models_bucket: "$S3_MODELS_BUCKET"
  s3_logs_bucket: "$S3_LOGS_BUCKET"

mlflow:
  tracking_uri: "http://localhost:5000"
  backend_store_uri: "sqlite:///mlflow.db"
  default_artifact_root: "s3://$S3_MODELS_BUCKET/mlflow-artifacts"

api:
  host: "0.0.0.0"
  port: $APPLICATION_PORT

airflow:
  webserver_port: $AIRFLOW_PORT
  executor: "LocalExecutor"

environment:
  name: "$ENVIRONMENT"
  aws_region: "$AWS_REGION"
  project_name: "$PROJECT_NAME"
EOF

# Set up environment variables
log "Setting up environment variables..."
cat > /home/ubuntu/.env << EOF
AWS_DEFAULT_REGION=$AWS_REGION
S3_DATA_BUCKET=$S3_DATA_BUCKET
S3_MODELS_BUCKET=$S3_MODELS_BUCKET
S3_LOGS_BUCKET=$S3_LOGS_BUCKET
ENVIRONMENT=$ENVIRONMENT
PROJECT_NAME=$PROJECT_NAME
APPLICATION_PORT=$APPLICATION_PORT
AIRFLOW_PORT=$AIRFLOW_PORT
MLFLOW_PORT=$MLFLOW_PORT
MLFLOW_BACKEND_STORE_URI=sqlite:///mlflow.db
MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://$S3_MODELS_BUCKET/mlflow-artifacts
AIRFLOW__CORE__LOAD_EXAMPLES=False
AIRFLOW__WEBSERVER__EXPOSE_CONFIG=True
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=sqlite:///airflow.db
EOF

# Source environment variables
source /home/ubuntu/.env

# Set ownership of all files
chown -R ubuntu:ubuntu /home/ubuntu/ml-transport-accra
chown ubuntu:ubuntu /home/ubuntu/.env

# Install Python dependencies
log "Installing Python dependencies..."
cd /home/ubuntu/ml-transport-accra
sudo -u ubuntu pip3 install --user -r requirements.txt

# Install additional ML dependencies
sudo -u ubuntu pip3 install --user \
    ortools \
    pulp \
    folium \
    plotly \
    xgboost \
    lightgbm \
    geopy \
    gtfs-realtime-bindings

# Configure Nginx as reverse proxy
log "Configuring Nginx..."
cat > /etc/nginx/sites-available/ml-transport-accra << EOF
server {
    listen 80;
    server_name _;

    # Main application
    location / {
        proxy_pass http://localhost:$APPLICATION_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:$APPLICATION_PORT/health;
        access_log off;
    }
}

server {
    listen $AIRFLOW_PORT;
    server_name _;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

server {
    listen $MLFLOW_PORT;
    server_name _;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable the site
ln -sf /etc/nginx/sites-available/ml-transport-accra /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and restart Nginx
nginx -t
systemctl restart nginx
systemctl enable nginx

# Configure fail2ban for security
log "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-noscript]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 6
EOF

systemctl restart fail2ban
systemctl enable fail2ban

# Set up log rotation
log "Setting up log rotation..."
cat > /etc/logrotate.d/ml-transport-accra << EOF
/home/ubuntu/ml-transport-accra/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        /usr/bin/aws s3 sync /home/ubuntu/ml-transport-accra/logs/ s3://$S3_LOGS_BUCKET/logs/\$(hostname)/ --region $AWS_REGION --exclude "*.log"
    endscript
}
EOF

# Create systemd service for the application
log "Creating systemd service..."
cat > /etc/systemd/system/ml-transport-accra.service << EOF
[Unit]
Description=ML Transport Accra Application
After=network.target docker.service
Requires=docker.service

[Service]
Type=forking
User=ubuntu
WorkingDirectory=/home/ubuntu/ml-transport-accra
Environment=DOCKER_HOST=unix:///var/run/docker.sock
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=300
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Update Docker Compose file with environment-specific settings
log "Updating Docker Compose configuration..."
cd /home/ubuntu/ml-transport-accra
cat > docker-compose.override.yml << EOF
version: '3.8'
services:
  postgres:
    volumes:
      - /data/postgres:/var/lib/postgresql/data

  airflow-webserver:
    ports:
      - "8080:8080"
    environment:
      - AIRFLOW__WEBSERVER__BASE_URL=http://localhost:$AIRFLOW_PORT
    volumes:
      - /data/airflow-logs:/opt/airflow/logs
      - ./data:/opt/airflow/data
      - ./configs:/opt/airflow/configs

  airflow-scheduler:
    volumes:
      - /data/airflow-logs:/opt/airflow/logs
      - ./data:/opt/airflow/data
      - ./configs:/opt/airflow/configs

  mlflow:
    ports:
      - "5000:5000"
    environment:
      - MLFLOW_S3_ENDPOINT_URL=https://s3.$AWS_REGION.amazonaws.com
      - AWS_DEFAULT_REGION=$AWS_REGION
    volumes:
      - /data/mlruns:/mlruns
EOF

# Start Docker Compose services
log "Starting Docker Compose services..."
sudo -u ubuntu docker-compose up -d

# Enable and start the systemd service
systemctl enable ml-transport-accra
systemctl start ml-transport-accra

# Wait for services to be ready
log "Waiting for services to start..."
sleep 60

# Initialize Airflow database and create admin user
log "Initializing Airflow..."
sudo -u ubuntu docker-compose exec -T airflow-webserver airflow db init || true
sudo -u ubuntu docker-compose exec -T airflow-webserver airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --email admin@example.com \
    --role Admin \
    --password admin || true

# Create a simple health check script
log "Creating health check script..."
cat > /home/ubuntu/health-check.sh << EOF
#!/bin/bash
# Health check script for ML Transport Accra

check_service() {
    local service=\$1
    local port=\$2
    local path=\$3

    if curl -f -s http://localhost:\$port\$path > /dev/null; then
        echo "\$service: OK"
        return 0
    else
        echo "\$service: FAILED"
        return 1
    fi
}

echo "=== ML Transport Accra Health Check ==="
echo "Time: \$(date)"

# Check main application
check_service "Main Application" "$APPLICATION_PORT" "/health"

# Check Airflow
check_service "Airflow" "8080" "/health"

# Check MLflow
check_service "MLflow" "5000" "/"

# Check Docker containers
echo ""
echo "=== Docker Container Status ==="
docker ps --format "table {{.Names}}\t{{.Status}}"

# Check disk space
echo ""
echo "=== Disk Usage ==="
df -h

# Check memory usage
echo ""
echo "=== Memory Usage ==="
free -h
EOF

chmod +x /home/ubuntu/health-check.sh
chown ubuntu:ubuntu /home/ubuntu/health-check.sh

# Set up cron job for regular health checks and log uploads (no CloudWatch)
log "Setting up cron jobs..."
sudo -u ubuntu crontab -l > /tmp/crontab.tmp 2>/dev/null || true
echo "*/5 * * * * /home/ubuntu/health-check.sh >> /home/ubuntu/ml-transport-accra/logs/health-check.log 2>&1" >> /tmp/crontab.tmp
echo "0 */6 * * * /usr/bin/aws s3 sync /home/ubuntu/ml-transport-accra/logs/ s3://$S3_LOGS_BUCKET/logs/\$(hostname)/ --region $AWS_REGION" >> /tmp/crontab.tmp
echo "0 1 * * * /usr/bin/aws s3 sync /data/mlruns/ s3://$S3_MODELS_BUCKET/mlruns/ --region $AWS_REGION" >> /tmp/crontab.tmp
echo "0 2 * * * find /home/ubuntu/ml-transport-accra/logs/ -name '*.log' -mtime +7 -delete" >> /tmp/crontab.tmp
sudo -u ubuntu crontab /tmp/crontab.tmp
rm /tmp/crontab.tmp

# Send completion notification
log "Sending completion notification..."
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
INSTANCE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)

# Create completion marker
echo "ML Transport Accra instance initialization completed successfully" > /home/ubuntu/ml-transport-accra/DEPLOYMENT_COMPLETE
echo "Instance ID: $INSTANCE_ID" >> /home/ubuntu/ml-transport-accra/DEPLOYMENT_COMPLETE
echo "Instance IP: $INSTANCE_IP" >> /home/ubuntu/ml-transport-accra/DEPLOYMENT_COMPLETE
echo "Deployment Time: $(date)" >> /home/ubuntu/ml-transport-accra/DEPLOYMENT_COMPLETE

# Upload completion marker to S3
aws s3 cp /home/ubuntu/ml-transport-accra/DEPLOYMENT_COMPLETE s3://$S3_DATA_BUCKET/deployments/completion-markers/$INSTANCE_ID.txt --region $AWS_REGION

# Final health check
log "Running final health check..."
/home/ubuntu/health-check.sh

log "ML Transport Accra instance initialization completed successfully!"
log "Access the application at:"
log "  - Main Application: http://$INSTANCE_IP:$APPLICATION_PORT"
log "  - Airflow: http://$INSTANCE_IP:$AIRFLOW_PORT (admin/admin)"
log "  - MLflow: http://$INSTANCE_IP:$MLFLOW_PORT"

# Clean up
apt-get autoremove -y
apt-get autoclean

log "Instance initialization script finished."
