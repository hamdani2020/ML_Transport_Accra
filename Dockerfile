# Dockerfile
FROM apache/airflow:2.8.1

COPY requirements.txt .

# Install required ML libraries
RUN pip install --no-cache-dir -r requirements.txt
