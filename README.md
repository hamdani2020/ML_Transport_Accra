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

### Inference API
```bash
cd inference
docker build -t ml-transport-accra .
docker run -p 8000:8000 ml-transport-accra
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