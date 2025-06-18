import os
import logging
import mlflow
import yaml
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExperimentTracker:
    def __init__(self, config_path: str = "configs/config.yaml"):
        """Initialize the experiment tracker.

        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        self.tracking_uri = self.config["mlflow"]["tracking_uri"]
        self.experiment_name = self.config["mlflow"]["experiment_name"]

        # Set up MLflow
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        with open(config_path) as f:
            return yaml.safe_load(f)

    def start_run(self, run_name: Optional[str] = None) -> None:
        """Start a new MLflow run.

        Args:
            run_name: Optional name for the run
        """
        run_name = run_name or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        mlflow.start_run(run_name=run_name)
        logger.info(f"Started MLflow run: {run_name}")

    def end_run(self) -> None:
        """End the current MLflow run."""
        mlflow.end_run()
        logger.info("Ended MLflow run")

    def log_params(self, params: Dict[str, Any]) -> None:
        """Log parameters to MLflow.

        Args:
            params: Dictionary of parameters to log
        """
        mlflow.log_params(params)
        logger.info(f"Logged parameters: {params}")

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        """Log metrics to MLflow.

        Args:
            metrics: Dictionary of metrics to log
            step: Optional step number for the metrics
        """
        mlflow.log_metrics(metrics, step=step)
        logger.info(f"Logged metrics: {metrics}")

    def log_model(self, model: Any, artifact_path: str, registered_model_name: Optional[str] = None) -> None:
        """Log a model to MLflow.

        Args:
            model: The model to log
            artifact_path: Path where the model will be saved
            registered_model_name: Optional name to register the model under
        """
        mlflow.sklearn.log_model(
            model,
            artifact_path,
            registered_model_name=registered_model_name
        )
        logger.info(f"Logged model to {artifact_path}")

    def log_artifact(self, local_path: str) -> None:
        """Log an artifact to MLflow.

        Args:
            local_path: Path to the artifact to log
        """
        mlflow.log_artifact(local_path)
        logger.info(f"Logged artifact: {local_path}")

    def log_artifacts(self, local_dir: str) -> None:
        """Log a directory of artifacts to MLflow.

        Args:
            local_dir: Path to the directory to log
        """
        mlflow.log_artifacts(local_dir)
        logger.info(f"Logged artifacts from directory: {local_dir}")

    def log_figure(self, figure: Any, artifact_path: str) -> None:
        """Log a matplotlib/plotly figure to MLflow.

        Args:
            figure: The figure to log
            artifact_path: Path where the figure will be saved
        """
        try:
            # Handle both matplotlib and plotly figures
            if 'matplotlib' in str(type(figure)):
                figure.savefig(artifact_path)
                mlflow.log_artifact(artifact_path)
            else:  # plotly figure
                figure.write_html(artifact_path)
                mlflow.log_artifact(artifact_path)
            logger.info(f"Logged figure to {artifact_path}")
        except Exception as e:
            logger.error(f"Failed to log figure: {str(e)}")

    def set_tags(self, tags: Dict[str, str]) -> None:
        """Set tags for the current run.

        Args:
            tags: Dictionary of tags to set
        """
        mlflow.set_tags(tags)
        logger.info(f"Set tags: {tags}")

    def get_run_info(self, run_id: str) -> Dict:
        """Get information about a specific run.

        Args:
            run_id: The ID of the run to get information about

        Returns:
            Dictionary containing run information
        """
        client = mlflow.tracking.MlflowClient()
        run = client.get_run(run_id)
        return {
            "run_id": run.info.run_id,
            "experiment_id": run.info.experiment_id,
            "status": run.info.status,
            "start_time": run.info.start_time,
            "end_time": run.info.end_time,
            "params": run.data.params,
            "metrics": run.data.metrics,
            "tags": run.data.tags
        }

    def load_model(self, model_name: str, stage: str = "Production") -> Any:
        """Load a model from the MLflow model registry.

        Args:
            model_name: Name of the registered model
            stage: Stage of the model to load (e.g., "Production", "Staging")

        Returns:
            The loaded model
        """
        model = mlflow.pyfunc.load_model(f"models:/{model_name}/{stage}")
        logger.info(f"Loaded model {model_name} from stage {stage}")
        return model

    def compare_runs(self, run_ids: List[str], metric_key: str) -> Dict:
        """Compare multiple runs based on a specific metric.

        Args:
            run_ids: List of run IDs to compare
            metric_key: The metric to compare

        Returns:
            Dictionary containing comparison results
        """
        client = mlflow.tracking.MlflowClient()
        results = {}

        for run_id in run_ids:
            run = client.get_run(run_id)
            results[run_id] = {
                "value": run.data.metrics.get(metric_key),
                "params": run.data.params,
                "tags": run.data.tags
            }

        return results

    def create_experiment(self, experiment_name: str, artifact_location: Optional[str] = None) -> str:
        """Create a new MLflow experiment.

        Args:
            experiment_name: Name of the new experiment
            artifact_location: Optional location for experiment artifacts

        Returns:
            ID of the created experiment
        """
        experiment_id = mlflow.create_experiment(
            experiment_name,
            artifact_location=artifact_location
        )
        logger.info(f"Created experiment {experiment_name} with ID {experiment_id}")
        return experiment_id

if __name__ == "__main__":
    # Example usage
    tracker = ExperimentTracker()

    # Start a new run
    tracker.start_run("example_run")

    # Log some parameters and metrics
    tracker.log_params({
        "learning_rate": 0.001,
        "batch_size": 32
    })

    tracker.log_metrics({
        "accuracy": 0.95,
        "loss": 0.1
    })

    # Set some tags
    tracker.set_tags({
        "model_type": "transformer",
        "dataset_version": "v1.0"
    })

    # End the run
    tracker.end_run()
