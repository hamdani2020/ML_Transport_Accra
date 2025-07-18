import argparse
import logging
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

def load_config():
    """Load configuration from YAML file."""
    with open("configs/config.yaml") as f:
        return yaml.safe_load(f)

def load_experiment_data(experiment_id, config):
    """
    Load A/B test data from MLflow experiment.
    Returns DataFrame with predictions and actual values for both models.
    """
    client = mlflow.tracking.MlflowClient()
    runs = client.search_runs(
        experiment_id,
        filter_string="tags.group IN ('control', 'treatment')"
    )

    data = []
    for run in runs:
        predictions = pd.read_parquet(
            f"{run.info.artifact_uri}/predictions.parquet"
        )
        predictions['group'] = run.data.tags['group']
        predictions['model_version'] = run.data.tags['model_version']
        data.append(predictions)

    return pd.concat(data, ignore_index=True)

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
    args = parser.parse_args()

    # Load configuration
    config = load_config()

    # Create output directory
    import os
    os.makedirs(args.output_path, exist_ok=True)

    # Load experiment data
    data = load_experiment_data(args.experiment_id, config)

    # Calculate error metrics
    data['error'] = np.abs(data['actual'] - data['predicted'])

    # Split data by group
    control_data = data[data['group'] == 'control']
    treatment_data = data[data['group'] == 'treatment']

    # Calculate metrics for each group
    control_metrics = calculate_metrics(data, 'control')
    treatment_metrics = calculate_metrics(data, 'treatment')

    # Perform statistical tests
    stat_tests = perform_statistical_tests(control_data, treatment_data)

    # Generate visualizations
    plot_comparison(data, args.output_path)

    # Generate and save report
    generate_report(control_metrics, treatment_metrics, stat_tests, config, args.output_path)

    # Log results summary
    logger.info("A/B Test Results Summary:")
    logger.info(f"Control Model MAE: {control_metrics['mae']:.4f}")
    logger.info(f"Treatment Model MAE: {treatment_metrics['mae']:.4f}")
    logger.info(f"Improvement: {((control_metrics['mae'] - treatment_metrics['mae']) / control_metrics['mae'] * 100):.2f}%")
    logger.info(f"Statistical Significance (p-value): {stat_tests['p_value']:.4f}")
    logger.info(f"Effect Size (Cohen's d): {stat_tests['cohens_d']:.4f}")

    # Log results to MLflow
    with mlflow.start_run(experiment_id=args.experiment_id, run_name="ab_test_comparison"):
        mlflow.log_metrics({
            "control_mae": control_metrics['mae'],
            "treatment_mae": treatment_metrics['mae'],
            "p_value": stat_tests['p_value'],
            "cohens_d": stat_tests['cohens_d']
        })
        mlflow.log_artifacts(args.output_path)

if __name__ == "__main__":
    main()
