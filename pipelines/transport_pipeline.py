"""
End-to-End Transport Optimization Pipeline
Integrates demand prediction, route optimization, and schedule optimization
"""

import os
import sys
import logging
import pandas as pd
import yaml
import json
import numpy as np

# Add project root to path to allow importing modules from the 'scripts' directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.demand_predictor import DemandPredictor
from scripts.route_optimizer import RouteOptimizer
from scripts.schedule_optimizer import ScheduleOptimizer

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TransportPipeline:
    """Orchestrates the end-to-end transport optimization workflow."""

    def __init__(self, config_path="configs/config.yaml"):
        """Initialize the pipeline components."""
        logger.info("Initializing transport optimization pipeline...")
        self.config_path = config_path
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.demand_predictor = DemandPredictor(config_path)
        self.route_optimizer = RouteOptimizer(config_path)
        self.schedule_optimizer = ScheduleOptimizer(config_path)
        logger.info("Pipeline components initialized successfully.")

    def run_pipeline(self):
        """
        Execute the full transport optimization pipeline:
        1. Predict passenger demand.
        2. Optimize transport routes based on predicted demand.
        3. Optimize bus schedules based on demand and optimized routes.
        """
        logger.info("======================================================")
        logger.info("=== STARTING END-TO-END TRANSPORT OPTIMIZATION PIPELINE ===")
        logger.info("======================================================")

        # --- Step 1: Predict Passenger Demand ---
        logger.info("--- Step 1: Predicting Passenger Demand ---")
        full_data_with_demand = self._run_demand_prediction_step()
        if full_data_with_demand is None:
            logger.error("Demand prediction failed. Aborting pipeline.")
            return None

        # --- Step 2: Optimize Transport Routes ---
        logger.info("--- Step 2: Optimizing Transport Routes ---")
        # NOTE: This step requires modification of `RouteOptimizer` to accept demand data.
        route_results = self._run_route_optimization_step(full_data_with_demand)
        if not route_results or not route_results.get('optimized_routes'):
            logger.warning("Route optimization did not produce results. The pipeline will now terminate.")
            return None

        # --- Step 3: Optimize Bus Schedules ---
        logger.info("--- Step 3: Optimizing Bus Schedules ---")
        # NOTE: This step requires modification of `ScheduleOptimizer` to use predicted demand.
        schedule_results = self._run_schedule_optimization_step(full_data_with_demand)
        if not schedule_results:
            logger.error("Schedule optimization failed. Aborting pipeline.")
            return None

        logger.info("--- Pipeline execution completed successfully! ---")

        final_results = {
            "demand_summary": {
                "total_records": len(full_data_with_demand),
                "total_predicted_demand": int(full_data_with_demand['demand'].sum())
            },
            "route_optimization": route_results,
            "schedule_optimization": schedule_results
        }

        # Save the final results to a file
        self._save_results(final_results)

        return final_results

    def _run_demand_prediction_step(self) -> pd.DataFrame:
        """Runs the demand prediction module to get a dataframe with a 'demand' column."""
        try:
            # Load and prepare raw GTFS data
            df = self.demand_predictor.load_gtfs_data("data/raw")
            # The 'engineer_features' method currently simulates and adds a 'demand' column.
            # In a real-world scenario, you would train a model and then call a predict method.
            df_featured = self.demand_predictor.engineer_features(df)
            logger.info("Demand data generated with engineered features.")

            # Save the featured data for inspection
            output_dir = self.config['data']['processed_dir']
            os.makedirs(output_dir, exist_ok=True)
            df_featured.to_csv(os.path.join(output_dir, 'featured_demand_data.csv'), index=False)

            return df_featured
        except Exception as e:
            logger.error(f"An error occurred during the demand prediction step: {e}", exc_info=True)
            return None

    def _run_route_optimization_step(self, demand_data: pd.DataFrame) -> dict:
        """Runs the route optimization module, injecting predicted demand."""
        try:
            # TODO: Modify `RouteOptimizer` to use this injected demand data
            # instead of its internal `estimate_demand` method.
            # For now, we are monkey-patching the demand estimation method
            # to use our predicted demand. This is a temporary solution.
            def new_estimate_demand_for_route(stops: list[dict]) -> list[int]:
                stop_ids = [s['id'] for s in stops]
                route_demand = demand_data[demand_data['stop_id'].isin(stop_ids)]

                # Create a map of stop_id to demand
                demand_map = route_demand.groupby('stop_id')['demand'].mean().to_dict()

                # Return a list of demands in the same order as the input stops
                # Use a default demand of 10 if a stop is not in our prediction data
                return [int(demand_map.get(stop_id, 10)) for stop_id in stop_ids]

            self.route_optimizer.estimate_demand_for_route = new_estimate_demand_for_route

            logger.info("Injected predicted demand into route optimizer.")
            results = self.route_optimizer.optimize_network("data/raw")
            return results
        except Exception as e:
            logger.error(f"An error occurred during the route optimization step: {e}", exc_info=True)
            return None

    def _run_schedule_optimization_step(self, demand_data: pd.DataFrame) -> dict:
        """Runs the schedule optimization module, injecting predicted demand."""
        try:
            # Load base GTFS data
            gtfs_data = self.schedule_optimizer.load_gtfs_data("data/raw")

            # Aggregate demand by route and time period from our demand predictions
            demand_patterns = {}
            # Ensure 'time_period' column is of a consistent type
            demand_data['time_period'] = demand_data['time_period'].astype(str)

            # Limit to the same routes processed by the schedule optimizer for consistency
            processed_routes = [r for r in demand_data['route_id'].unique() if r in gtfs_data['routes']['route_id'].unique()][:5]

            for route_id in processed_routes:
                route_demand_data = demand_data[demand_data['route_id'] == route_id]
                demand_patterns[route_id] = {}
                for period, period_group in route_demand_data.groupby('time_period'):
                    # Aggregate demand per stop in the period (e.g., max demand)
                    demand_per_stop = period_group.groupby('stop_sequence')['demand'].max().to_dict()
                    # Ensure keys and values are native Python types for PuLP
                    demand_patterns[route_id][period] = {int(k): int(v) for k, v in demand_per_stop.items() if v > 0}

            # Prepare data for optimization
            schedule_data = self.schedule_optimizer.prepare_schedule_data(gtfs_data)

            # Override the simulated demand with our predicted demand
            schedule_data['demand_patterns'] = demand_patterns
            # Ensure the routes list is consistent
            schedule_data['routes'] = processed_routes

            logger.info("Injected predicted demand into schedule optimizer.")
            results = self.schedule_optimizer.optimize_schedules(schedule_data)

            # Generate reports and new GTFS files if optimization is successful
            if results and results.get('status') == 'Optimal':
                output_path = os.path.join(self.config['data']['processed_dir'], 'optimized_gtfs')
                self.schedule_optimizer.generate_optimized_gtfs(gtfs_data, results, output_path)
                report_path = os.path.join(self.config['data']['processed_dir'], 'schedule_report.html')
                self.schedule_optimizer.create_schedule_report(results, report_path)

            return results
        except Exception as e:
            logger.error(f"An error occurred during schedule optimization: {e}", exc_info=True)
            return None

    def _save_results(self, results: dict, filename: str = "pipeline_results.json"):
        """Saves the final pipeline results to a JSON file."""
        output_path = os.path.join(self.config['data']['processed_dir'], filename)
        logger.info(f"Saving final pipeline results to {output_path}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Custom JSON encoder to handle non-serializable types like numpy objects
        class CustomEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, pd.Timestamp):
                    return obj.isoformat()
                return super(CustomEncoder, self).default(obj)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=4, cls=CustomEncoder)
        logger.info(f"Results saved successfully to {output_path}")

def main():
    """Main function to instantiate and run the transport pipeline."""
    pipeline = TransportPipeline()
    results = pipeline.run_pipeline()

    if results:
        print("\n--- ✅ Pipeline Execution Finished ---")
        if "route_optimization" in results and results["route_optimization"]:
            improvement = results['route_optimization'].get('efficiency_improvement', 0)
            print(f"Route Optimization: Efficiency improvement of {improvement:.2f}%")
        if "schedule_optimization" in results and results["schedule_optimization"]:
            status = results['schedule_optimization'].get('status', 'Unknown')
            if status == 'Optimal':
                total_buses = results['schedule_optimization'].get('summary', {}).get('total_buses', 'N/A')
                print(f"Schedule Optimization: Status is {status}. Total buses needed: {total_buses}")
            else:
                print(f"Schedule Optimization: Status is {status}.")
        print(f"\nFull results saved to: data/processed/pipeline_results.json")
    else:
        print("\n--- ❌ Pipeline Execution Failed ---")

if __name__ == "__main__":
    main()
