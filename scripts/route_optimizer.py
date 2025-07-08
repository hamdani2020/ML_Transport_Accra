"""
Route Optimization Module for Accra Public Transport
Uses OR-Tools to optimize routes, schedules, and resource allocation
"""

import os
import logging
import pandas as pd
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import Dict, List, Tuple, Optional
import yaml
from geopy.distance import geodesic

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RouteOptimizer:
    """Optimizes public transport routes using OR-Tools Vehicle Routing Problem solver."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        """Initialize the route optimizer with configuration."""
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.data_manager = None
        self.distance_matrix = None
        self.demands = None
        self.vehicle_capacities = None
        # Average speed for converting distance to time, crucial for time constraints.
        self.average_speed_kmh = self.config.get('route_optimization', {}).get('average_speed_kmh', 30.0)


    def load_gtfs_data(self, data_path: str) -> pd.DataFrame:
        """Load and prepare GTFS data for optimization."""
        logger.info(f"Loading GTFS data from {data_path}")

        # Load GTFS files
        stops_df = pd.read_csv(os.path.join(data_path, "stops.txt"))
        routes_df = pd.read_csv(os.path.join(data_path, "routes.txt"))
        trips_df = pd.read_csv(os.path.join(data_path, "trips.txt"))
        stop_times_df = pd.read_csv(os.path.join(data_path, "stop_times.txt"))

        # Create route-stop mapping
        route_stops = stop_times_df.merge(trips_df[['trip_id', 'route_id']], on='trip_id')
        route_stops = route_stops.merge(stops_df[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']], on='stop_id')

        # Get unique stops per route
        route_stop_sequences = route_stops.groupby('route_id').agg({
            'stop_id': list,
            'stop_name': list,
            'stop_lat': list,
            'stop_lon': list
        }).reset_index()

        logger.info(f"Loaded {len(route_stop_sequences)} routes with stops")
        return route_stop_sequences

    def calculate_distance_matrix(self, stops_df: pd.DataFrame) -> np.ndarray:
        """Calculate distance matrix between all stops using Haversine formula."""
        n_stops = len(stops_df)
        distance_matrix = np.zeros((n_stops, n_stops))

        for i in range(n_stops):
            for j in range(n_stops):
                if i != j:
                    coord1 = (stops_df.iloc[i]['stop_lat'], stops_df.iloc[i]['stop_lon'])
                    coord2 = (stops_df.iloc[j]['stop_lat'], stops_df.iloc[j]['stop_lon'])
                    distance_matrix[i][j] = geodesic(coord1, coord2).kilometers

        return distance_matrix

    def optimize_route(self,
                      route_id: str,
                      stops: List[Dict],
                      demands: List[int],
                      vehicle_capacity: int = 500,
                      max_route_time: int = 600) -> Optional[Dict]:
        """Optimize a single route using OR-Tools VRP solver."""
        if not stops:
            logger.warning(f"Route {route_id} has no stops, skipping optimization.")
            return None

        n_stops = len(stops)
        distance_matrix = self.calculate_distance_matrix(pd.DataFrame(stops))

        # Create the routing index manager.
        manager = pywrapcp.RoutingIndexManager(n_stops, 1, 0) # 1 vehicle, start/end at depot (stop 0)

        # Create Routing Model.
        routing = pywrapcp.RoutingModel(manager)

        # --- Define Callbacks ---

        # 1. Distance callback (for arc costs)
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(distance_matrix[from_node][to_node] * 1000) # Use meters for precision

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # 2. Demand callback (for capacity constraints)
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return demands[from_node]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            [vehicle_capacity],  # vehicle maximum capacities
            True,  # start cumul to zero
            'Capacity')

        # 3. Time callback (for time constraints) - THE CRITICAL FIX
        def time_callback(from_index, to_index):
            """Calculates travel time between two nodes based on distance and average speed."""
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            distance_km = distance_matrix[from_node][to_node]
            # Convert time to integer minutes for the solver
            time_minutes = int((distance_km / self.average_speed_kmh) * 60)
            return time_minutes

        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            30,  # allow 30 minutes of slack
            max_route_time,
            True, # force start cumul to zero
            'Time')

        # --- Configure Solver ---
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        search_parameters.time_limit.seconds = 30
        search_parameters.log_search = False # Quieter logs

        # --- Solve the problem ---
        logger.info(f"Solving optimization for route {route_id} with {n_stops} stops.")
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            logger.info(f"Solution found for route {route_id}.")
            return self._extract_solution(manager, routing, solution, stops, distance_matrix)
        else:
            logger.warning(f"No solution found for route {route_id}")
            return None

    def _extract_solution(self, manager, routing, solution, stops, distance_matrix):
        """Extract the optimized route from the OR-Tools solution."""
        index = routing.Start(0)
        route_distance_km = 0
        optimized_route_stops = []

        time_dimension = routing.GetDimensionOrDie('Time')

        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            optimized_route_stops.append(stops[node_index])

            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance_km += distance_matrix[manager.IndexToNode(previous_index)][manager.IndexToNode(index)]

        # Get total time from the time dimension at the final node
        total_time_minutes = solution.Min(time_dimension.CumulVar(index))

        return {
            'route_stops': optimized_route_stops,
            'total_distance_km': round(route_distance_km, 2),
            'total_time_minutes': total_time_minutes
        }

    def optimize_network(self, data_path: str, demand_data: Optional[pd.DataFrame] = None) -> Dict:
        """Optimize the entire transport network, optionally using predicted demand."""
        logger.info("Starting network-wide route optimization")
        route_stops_df = self.load_gtfs_data(data_path)

        optimized_routes = {}
        total_distance_saved = 0
        original_total_distance = 0

        for _, route in route_stops_df.iterrows():
            route_id = route['route_id']
            stops = []
            for i in range(len(route['stop_id'])):
                stops.append({
                    'id': route['stop_id'][i],
                    'name': route['stop_name'][i],
                    'stop_lat': route['stop_lat'][i],
                    'stop_lon': route['stop_lon'][i]
                })

            if not stops:
                continue

            original_dist = self._calculate_route_distance(stops)
            original_total_distance += original_dist

            # Prepare demands for the current route
            if demand_data is not None:
                stop_ids = [s['id'] for s in stops]
                route_demand_df = demand_data[demand_data['stop_id'].isin(stop_ids)]
                demand_map = route_demand_df.groupby('stop_id')['demand'].mean().to_dict()
                demands = [int(demand_map.get(s_id, 10)) for s_id in stop_ids] # Default demand of 10
            else:
                demands = self._estimate_demand_for_route(stops)

            # Optimize the route
            optimized_route = self.optimize_route(route_id, stops, demands)

            if optimized_route:
                optimized_routes[route_id] = optimized_route
                distance_saved = original_dist - optimized_route['total_distance_km']
                total_distance_saved += distance_saved
                logger.info(f"Route {route_id}: Original: {original_dist:.2f} km, Optimized: {optimized_route['total_distance_km']:.2f} km, Saved: {distance_saved:.2f} km")

        efficiency_improvement = (total_distance_saved / original_total_distance) * 100 if original_total_distance > 0 else 0

        optimization_results = {
            'optimized_routes': optimized_routes,
            'total_distance_saved_km': round(total_distance_saved, 2),
            'original_total_distance_km': round(original_total_distance, 2),
            'efficiency_improvement': round(efficiency_improvement, 2)
        }

        logger.info(f"Network optimization complete. Efficiency improvement: {efficiency_improvement:.2f}%")
        return optimization_results

    def _calculate_route_distance(self, stops: List[Dict]) -> float:
        """Calculate the total distance of a route."""
        total_distance = 0
        for i in range(len(stops) - 1):
            coord1 = (stops[i]['stop_lat'], stops[i]['stop_lon'])
            coord2 = (stops[i+1]['stop_lat'], stops[i+1]['stop_lon'])
            total_distance += geodesic(coord1, coord2).kilometers
        return total_distance

    def _estimate_demand_for_route(self, stops: List[Dict]) -> List[int]:
        """(Fallback) Estimate demand for stops in a single route."""
        demands = []
        n_stops = len(stops)
        for i in range(n_stops):
            if i == 0 or i == n_stops - 1 or i == n_stops // 2:
                demand = np.random.randint(20, 40)
            else:
                demand = np.random.randint(5, 15)
            demands.append(demand)
        return demands

def main():
    """Main function to run route optimization as a standalone script."""
    optimizer = RouteOptimizer()
    results = optimizer.optimize_network("data/raw")

    # Save results to a file
    output_path = "data/processed/route_optimization_results.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Optimization complete! Efficiency improvement: {results.get('efficiency_improvement', 0):.2f}%")
    print(f"Results saved to {output_path}")

if __name__ == "__main__":
    main()
