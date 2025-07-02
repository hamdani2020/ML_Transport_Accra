# Dockerfile
FROM apache/airflow:2.8.1

# Install required ML libraries
RUN pip install --no-cache-dir \
    mlflow[extras] \
    scikit-learn \
    pandas \
    matplotlib \
    seaborn \
    pyyaml
