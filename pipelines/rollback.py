import logging
import mlflow
import yaml
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import requests
from prometheus_client.parser import text_string_to_metric_families

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelRollbackManager:
    def __init__(self, config_path: str = "configs/config.yaml"):
        """Initialize the rollback manager.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.mlflow_client = mlflow.tracking.MlflowClient(
            tracking_uri=self.config["mlflow"]["tracking_uri"]
        )
        self.model_name = self.config["model"]["name"]

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        with open(config_path) as f:
            return yaml.safe_load(f)

    def get_current_metrics(self) -> Dict[str, float]:
        """Fetch current model performance metrics from Prometheus."""
        try:
            response = requests.get(
                f'http://localhost:{self.config["monitoring"]["metrics_port"]}/metrics'
            )
            response.raise_for_status()

            metrics = {}
            for family in text_string_to_metric_families(response.text):
                if family.name in ["prediction_error", "prediction_latency_seconds"]:
                    metrics[family.name] = family.samples[0].value

            return metrics
        except Exception as e:
            logger.error(f"Failed to fetch metrics: {str(e)}")
            return {}

    def check_rollback_conditions(self, metrics: Dict[str, float]) -> Tuple[bool, str]:
        """Check if rollback conditions are met.

        Args:
            metrics: Dictionary of current metrics

        Returns:
            Tuple of (should_rollback, reason)
        """
        if not metrics:
            return False, "No metrics available"

        thresholds = self.config["rollback"]

        # Check error rate
        if metrics.get("prediction_error", 0) > thresholds["error_threshold"]:
            return True, f"Error rate {metrics['prediction_error']} exceeds threshold {thresholds['error_threshold']}"

        # Check latency
        if metrics.get("prediction_latency_seconds", 0) > thresholds["latency_threshold"]:
            return True, f"Latency {metrics['prediction_latency_seconds']} exceeds threshold {thresholds['latency_threshold']}"

        return False, "All metrics within acceptable ranges"

    def get_previous_production_version(self) -> Optional[str]:
        """Get the previous production version of the model."""
        versions = self.mlflow_client.search_model_versions(f"name='{self.model_name}'")
        production_versions = [
            v for v in versions
            if v.current_stage == "Production" or v.current_stage == "Archived"
        ]

        if len(production_versions) < 2:
            return None

        # Sort by version number (descending)
        production_versions.sort(key=lambda x: int(x.version), reverse=True)
        return production_versions[1].version

    def rollback_model(self) -> bool:
        """Execute model rollback to previous version.

        Returns:
            bool: True if rollback was successful, False otherwise
        """
        try:
            # Get current and previous versions
            current_version = self.mlflow_client.search_model_versions(
                f"name='{self.model_name}' AND stage='Production'"
            )[0].version

            previous_version = self.get_previous_production_version()
            if not previous_version:
                logger.error("No previous version available for rollback")
                return False

            # Archive current version
            self.mlflow_client.transition_model_version_stage(
                name=self.model_name,
                version=current_version,
                stage="Archived",
                archive_existing_versions=False
            )

            # Promote previous version to production
            self.mlflow_client.transition_model_version_stage(
                name=self.model_name,
                version=previous_version,
                stage="Production",
                archive_existing_versions=False
            )

            logger.info(
                f"Successfully rolled back from version {current_version} "
                f"to version {previous_version}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to execute rollback: {str(e)}")
            return False

    def notify_rollback(self, reason: str) -> None:
        """Send notification about rollback event."""
        # Implementation depends on notification system (e.g., email, Slack)
        logger.info(f"Model rollback notification: {reason}")

    def monitor_and_rollback(self, check_interval: int = 300) -> None:
        """Continuously monitor metrics and trigger rollback if needed.

        Args:
            check_interval: Time between checks in seconds (default: 5 minutes)
        """
        while True:
            try:
                # Get current metrics
                metrics = self.get_current_metrics()

                # Check if rollback is needed
                should_rollback, reason = self.check_rollback_conditions(metrics)

                if should_rollback:
                    logger.warning(f"Initiating rollback: {reason}")

                    # Execute rollback
                    if self.rollback_model():
                        self.notify_rollback(reason)
                    else:
                        logger.error("Rollback failed")

                time.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(check_interval)

def main():
    """Main entry point for rollback manager."""
    try:
        manager = ModelRollbackManager()
        manager.monitor_and_rollback()
    except KeyboardInterrupt:
        logger.info("Stopping rollback manager")
    except Exception as e:
        logger.error(f"Error running rollback manager: {str(e)}")

if __name__ == "__main__":
    main()
