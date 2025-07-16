import argparse
import logging
import os
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
import yaml
from datetime import datetime, timedelta
import mlflow

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config(config_path=None):
    """Load configuration from YAML file."""
    if config_path is None:
        # Try to find the project root and config file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # Go up one level from scripts/
        config_path = os.path.join(project_root, "configs", "config.yaml")

    if not os.path.exists(config_path):
        # Fallback to relative path
        config_path = "configs/config.yaml"

    logger.info(f"Loading config from: {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)

def load_experiment_data(experiment_id, config):
    """
    Load A/B test data from MLflow experiment.
    Returns DataFrame with predictions and actual values for both models.
    """
    try:
        # Set the tracking URI from config
        tracking_uri = config['mlflow']['tracking_uri']
        mlflow.set_tracking_uri(tracking_uri)
        client = mlflow.tracking.MlflowClient()
        logger.info(f"Connected to MLflow at: {tracking_uri}")

        # Set up environment for artifact access
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        artifact_root = os.path.join(project_root, "mlflow_shared")
        os.environ["MLFLOW_DEFAULT_ARTIFACT_ROOT"] = os.path.abspath(artifact_root)
        os.environ["MLFLOW_ARTIFACT_ROOT"] = os.path.abspath(artifact_root)

        # Search in multiple experiments for control and treatment runs
        all_runs = []
        valid_experiment_ids = ["0", "1"]  # Default and Default_evaluation

        for exp_id in valid_experiment_ids:
            try:
                # Get all runs from the experiment
                runs = client.search_runs([exp_id])
                logger.info(f"Found {len(runs)} total runs in experiment {exp_id}")

                # Filter by group tags
                control_runs = [r for r in runs if r.data.tags.get('group') == 'control']
                treatment_runs = [r for r in runs if r.data.tags.get('group') == 'treatment']

                all_runs.extend(control_runs)
                all_runs.extend(treatment_runs)
                logger.info(f"Experiment {exp_id}: {len(control_runs)} control, {len(treatment_runs)} treatment runs")

            except Exception as e:
                logger.warning(f"Could not search experiment {exp_id}: {e}")
                continue

        logger.info(f"Total runs found: {len(all_runs)}")

        # Try to load data from local files first, then MLflow artifacts
        data = []
        models_dir = os.path.join(project_root, "models")

        for run in all_runs:
            try:
                group = run.data.tags.get('group', 'unknown')
                run_id = run.info.run_id
                logger.info(f"Processing run {run_id} with group {group}")

                predictions_df = None

                # Try to load from local models directory first
                if group == 'training' or group == 'control':
                    # Look for training predictions files
                    prediction_files = [f for f in os.listdir(models_dir)
                                      if f.startswith("predictions_") and f.endswith(".parquet")]
                    if prediction_files:
                        latest_file = sorted(prediction_files)[-1]
                        local_path = os.path.join(models_dir, latest_file)
                        try:
                            predictions_df = pd.read_parquet(local_path)
                            logger.info(f"Loaded control data from local file: {local_path}")
                        except Exception as e:
                            logger.warning(f"Failed to load from local file {local_path}: {e}")

                elif group == 'evaluation' or group == 'treatment':
                    # Look for evaluation results
                    eval_dirs = [d for d in os.listdir(models_dir)
                               if d.startswith("evaluation_") and os.path.isdir(os.path.join(models_dir, d))]
                    if eval_dirs:
                        latest_eval_dir = sorted(eval_dirs)[-1]
                        eval_predictions_path = os.path.join(models_dir, latest_eval_dir, "predictions.parquet")
                        if os.path.exists(eval_predictions_path):
                            try:
                                predictions_df = pd.read_parquet(eval_predictions_path)
                                logger.info(f"Loaded treatment data from: {eval_predictions_path}")
                            except Exception as e:
                                logger.warning(f"Failed to load from {eval_predictions_path}: {e}")

                # If local loading failed, try MLflow artifacts
                if predictions_df is None:
                    try:
                        artifacts = client.list_artifacts(run_id)
                        prediction_artifacts = [a for a in artifacts if 'predictions' in a.path.lower()]
                        if prediction_artifacts:
                            artifact_path = prediction_artifacts[0].path
                            local_artifact_path = client.download_artifacts(run_id, artifact_path)
                            predictions_df = pd.read_parquet(local_artifact_path)
                            logger.info(f"Loaded from MLflow artifact: {artifact_path}")
                    except Exception as e:
                        logger.warning(f"Failed to load from MLflow artifacts for run {run_id}: {e}")

                # Add to dataset if we successfully loaded predictions
                if predictions_df is not None and not predictions_df.empty:
                    predictions_df['group'] = group
                    predictions_df['model_version'] = run.data.tags.get('model_version', '1.0.0')
                    predictions_df['run_id'] = run_id
                    data.append(predictions_df)
                    logger.info(f"Added {len(predictions_df)} rows from run {run_id}")
                else:
                    logger.warning(f"No predictions found for run {run_id}")

            except Exception as e:
                logger.warning(f"Failed to process run {run.info.run_id}: {e}")
                continue

        logger.info(f"Final data list has {len(data)} dataframes")
        if len(data) == 0:
            logger.error("No A/B test data found! Cannot perform comparison.")
            return pd.DataFrame()

        combined_data = pd.concat(data, ignore_index=True)
        logger.info(f"Combined dataset has {len(combined_data)} rows")
        logger.info(f"Groups found: {combined_data['group'].value_counts().to_dict()}")
        return combined_data

    except Exception as e:
        logger.error(f"Failed to load experiment data: {e}")
        return pd.DataFrame()

def calculate_metrics(data, group):
    """Calculate key metrics for a specific group."""
    group_data = data[data['group'] == group]

    metrics = {
        'mae': np.mean(np.abs(group_data['actual'] - group_data['predicted'])),
        'rmse': np.sqrt(np.mean((group_data['actual'] - group_data['predicted'])**2)),
        'mape': np.mean(np.abs((group_data['actual'] - group_data['predicted']) / group_data['actual'])) * 100,
        'r2': 1 - (np.sum((group_data['actual'] - group_data['predicted'])**2) /
                   np.sum((group_data['actual'] - group_data['actual'].mean())**2))
    }

    return metrics

def perform_statistical_tests(control_data, treatment_data):
    """Perform statistical significance tests between control and treatment groups."""
    # Calculate absolute errors for both groups
    control_errors = np.abs(control_data['actual'] - control_data['predicted'])
    treatment_errors = np.abs(treatment_data['actual'] - treatment_data['predicted'])

    # Perform t-test
    t_stat, p_value = stats.ttest_ind(control_errors, treatment_errors)

    # Effect size (Cohen's d)
    pooled_std = np.sqrt((control_errors.var() + treatment_errors.var()) / 2)
    cohens_d = (treatment_errors.mean() - control_errors.mean()) / pooled_std

    return {
        't_statistic': t_stat,
        'p_value': p_value,
        'cohens_d': cohens_d
    }

def plot_comparison(data, output_path):
    """Generate comparison visualizations."""
    # Error distribution plot
    plt.figure(figsize=(12, 6))
    sns.boxplot(x='group', y='error', data=data)
    plt.title('Error Distribution by Group')
    plt.savefig(f"{output_path}/error_distribution.png")
    plt.close()

    # Scatter plot of predictions vs actuals
    plt.figure(figsize=(12, 6))
    sns.scatterplot(data=data, x='actual', y='predicted', hue='group', alpha=0.5)
    plt.plot([data['actual'].min(), data['actual'].max()],
             [data['actual'].min(), data['actual'].max()],
             'r--', label='Perfect Prediction')
    plt.title('Predictions vs Actuals by Group')
    plt.legend()
    plt.savefig(f"{output_path}/predictions_vs_actuals.png")
    plt.close()

def convert_numpy_to_python(obj):
    """Convert NumPy types to native Python types for YAML serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_python(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(item) for item in obj]
    else:
        return obj

def generate_report(control_metrics, treatment_metrics, stat_tests, config, output_path):
    """Generate a detailed comparison report."""
    report = {
        'timestamp': datetime.now().isoformat(),
        'experiment_config': config['ab_testing'],
        'metrics': {
            'control': control_metrics,
            'treatment': treatment_metrics
        },
        'statistical_tests': stat_tests,
        'conclusions': {
            'significant_difference': stat_tests['p_value'] < config['ab_testing']['significance_level'],
            'effect_size_interpretation': interpret_effect_size(stat_tests['cohens_d'])
        }
    }

    # Convert all NumPy values to native Python types
    report = convert_numpy_to_python(report)

    # Save report
    with open(f"{output_path}/ab_test_report.yaml", 'w') as f:
        yaml.dump(report, f)

def interpret_effect_size(cohens_d):
    """Interpret Cohen's d effect size."""
    abs_d = abs(cohens_d)
    if abs_d < 0.2:
        return "negligible"
    elif abs_d < 0.5:
        return "small"
    elif abs_d < 0.8:
        return "medium"
    else:
        return "large"

def main():
    parser = argparse.ArgumentParser(description="Compare A/B test results")
    parser.add_argument("--experiment-id", required=True, help="MLflow experiment ID")
    parser.add_argument("--output-path", default="models/ab_test_results",
                       help="Path to save comparison results")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config file")
    args = parser.parse_args()

    try:
        # Load configuration
        config = load_config(args.config)

        # Create output directory
        import os
        os.makedirs(args.output_path, exist_ok=True)

        # Load experiment data
        data = load_experiment_data(args.experiment_id, config)

        # Check if we have enough data for A/B testing
        if data.empty:
            logger.error("No data found for A/B testing. Exiting.")
            # Create a minimal report indicating no data
            minimal_report = {
                'timestamp': datetime.now().isoformat(),
                'status': 'failed',
                'reason': 'no_data_found',
                'metrics': {'control': {}, 'treatment': {}},
                'statistical_tests': {'p_value': 1.0, 'cohens_d': 0.0},
                'conclusions': {'significant_difference': False}
            }
            with open(f"{args.output_path}/ab_test_report.yaml", 'w') as f:
                yaml.dump(minimal_report, f)
            return

        # Calculate error metrics
        data['error'] = np.abs(data['actual'] - data['predicted'])

        # Split data by group
        control_data = data[data['group'] == 'control']
        treatment_data = data[data['group'] == 'treatment']

        # Check if we have both groups
        if control_data.empty:
            logger.warning("No control group data found, using training data as control")
            control_data = data[data['group'].isin(['control', 'training'])]

        if treatment_data.empty:
            logger.warning("No treatment group data found, using evaluation data as treatment")
            treatment_data = data[data['group'].isin(['treatment', 'evaluation'])]

        if control_data.empty or treatment_data.empty:
            logger.error("Insufficient data for A/B testing (missing control or treatment group)")
            # Create a report indicating insufficient data
            insufficient_report = {
                'timestamp': datetime.now().isoformat(),
                'status': 'failed',
                'reason': 'insufficient_data',
                'data_summary': {
                    'total_rows': len(data),
                    'control_rows': len(control_data),
                    'treatment_rows': len(treatment_data),
                    'groups_found': data['group'].unique().tolist()
                },
                'conclusions': {'significant_difference': False}
            }
            with open(f"{args.output_path}/ab_test_report.yaml", 'w') as f:
                yaml.dump(insufficient_report, f)
            return

        # Calculate metrics for each group
        control_metrics = calculate_metrics(data, control_data['group'].iloc[0])
        treatment_metrics = calculate_metrics(data, treatment_data['group'].iloc[0])

        # Perform statistical tests
        stat_tests = perform_statistical_tests(control_data, treatment_data)

        # Generate visualizations
        try:
            plot_comparison(data, args.output_path)
        except Exception as e:
            logger.warning(f"Failed to generate plots: {e}")

        # Generate and save report
        generate_report(control_metrics, treatment_metrics, stat_tests, config, args.output_path)

        # Log results summary
        logger.info("A/B Test Results Summary:")
        logger.info(f"Control Model MAE: {control_metrics['mae']:.4f}")
        logger.info(f"Treatment Model MAE: {treatment_metrics['mae']:.4f}")
        improvement = ((control_metrics['mae'] - treatment_metrics['mae']) / control_metrics['mae'] * 100)
        logger.info(f"Improvement: {improvement:.2f}%")
        logger.info(f"Statistical Significance (p-value): {stat_tests['p_value']:.4f}")
        logger.info(f"Effect Size (Cohen's d): {stat_tests['cohens_d']:.4f}")

        # Log results to MLflow with error handling
        try:
            with mlflow.start_run(experiment_id=args.experiment_id, run_name="ab_test_comparison"):
                mlflow.log_metrics({
                    "control_mae": control_metrics['mae'],
                    "treatment_mae": treatment_metrics['mae'],
                    "improvement_percent": improvement,
                    "p_value": stat_tests['p_value'],
                    "cohens_d": stat_tests['cohens_d']
                })
                try:
                    mlflow.log_artifacts(args.output_path)
                except Exception as e:
                    logger.warning(f"Failed to log artifacts to MLflow: {e}")
        except Exception as e:
            logger.warning(f"Failed to log results to MLflow: {e}")

        logger.info("✅ A/B test comparison completed successfully")

    except Exception as e:
        logger.error(f"❌ A/B test comparison failed: {e}")
        # Create error report
        error_report = {
            'timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error': str(e),
            'conclusions': {'significant_difference': False}
        }
        import os
        os.makedirs(args.output_path, exist_ok=True)
        with open(f"{args.output_path}/ab_test_report.yaml", 'w') as f:
            yaml.dump(error_report, f)
        raise

if __name__ == "__main__":
    main()
