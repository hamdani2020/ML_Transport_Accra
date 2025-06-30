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
logging.basicConfig(level=logging.INFO)
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
        
        logger.info(f"Calculated distance matrix for {n_stops} stops")
        return distance_matrix
    
    def estimate_demand(self, route_stops: pd.DataFrame) -> List[int]:
        """Estimate passenger demand for each stop based on population density and historical data."""
        # This is a simplified demand estimation
        # In practice, this would use real passenger count data
        demands = []
        
        for _, route in route_stops.iterrows():
            route_demands = []
            n_stops = len(route['stop_id'])
            
            # Generate realistic demand pattern (higher at major stops)
            for i in range(n_stops):
                # Major stops (first, last, middle) have higher demand
                if i == 0 or i == n_stops - 1 or i == n_stops // 2:
                    demand = np.random.randint(50, 150)
                else:
                    demand = np.random.randint(10, 50)
                route_demands.append(demand)
            
            demands.extend(route_demands)
        
        logger.info(f"Estimated demand for {len(demands)} stops")
        return demands
    
    def optimize_route(self, 
                      route_id: str, 
                      stops: List[Dict], 
                      vehicle_capacity: int = 500,
                      max_route_time: int = 600) -> Dict:
        """Optimize a single route using OR-Tools VRP solver."""
        
        # Prepare data for OR-Tools
        n_stops = len(stops)
        print(f"[DEBUG] n_stops: {n_stops}")
        distance_matrix = self.calculate_distance_matrix(pd.DataFrame(stops))
        print(f"[DEBUG] distance_matrix shape: {distance_matrix.shape}")
        demands = self.estimate_demand_for_route(stops)
        print(f"[DEBUG] demands length: {len(demands)}")
        
        # Create the routing index manager
        print(f"[DEBUG] Creating RoutingIndexManager with {n_stops} stops")
        manager = pywrapcp.RoutingIndexManager(n_stops, 1, 0)
        
        # Create Routing Model
        routing = pywrapcp.RoutingModel(manager)
        print(f"[DEBUG] Routing model created with {n_stops} stops")
        
        # Create and register a transit callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            # Convert km to meters and cast to int for OR-Tools
            return int(distance_matrix[from_node][to_node] * 1000)
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        
        # Define cost of each arc
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Add Capacity constraint
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
        
        # Add time constraint
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            max_route_time,  # maximum time per vehicle
            False,  # Don't force start cumul to zero
            'Time')
        time_dimension = routing.GetDimensionOrDie('Time')
        time_dimension.SetGlobalSpanCostCoefficient(100)
        
        # Setting first solution heuristic
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        search_parameters.time_limit.seconds = 30
        
        # Solve the problem
        print(f"[DEBUG] Calling SolveWithParameters for route {route_id}")
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            return self._extract_solution(manager, routing, solution, stops)
        else:
            logger.warning(f"No solution found for route {route_id}")
            return None
    
    def _extract_solution(self, manager, routing, solution, stops):
        """Extract the optimized route from the OR-Tools solution."""
        index = routing.Start(0)
        route_distance = 0
        route_stops = []
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_stops.append(stops[node_index])
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
        
        # Add the last stop
        node_index = manager.IndexToNode(index)
        route_stops.append(stops[node_index])
        
        return {
            'route_stops': route_stops,
            'total_distance': route_distance,
            'total_time': solution.ObjectiveValue()
        }
    
    def optimize_network(self, data_path: str) -> Dict:
        """Optimize the entire transport network."""
        logger.info("Starting network-wide route optimization")
        
        # Load GTFS data
        route_stops = self.load_gtfs_data(data_path)
        
        optimized_routes = {}
        total_distance_saved = 0
        original_distance = 0
        
        for _, route in route_stops.iterrows():
            route_id = route['route_id']
            stops = []
            
            # Prepare stops data
            for i in range(len(route['stop_id'])):
                stops.append({
                    'id': route['stop_id'][i],
                    'name': route['stop_name'][i],
                    'stop_lat': route['stop_lat'][i],
                    'stop_lon': route['stop_lon'][i]
                })
            
            # Calculate original distance
            original_dist = self._calculate_route_distance(stops)
            original_distance += original_dist
            
            # Optimize route
            optimized_route = self.optimize_route(route_id, stops)
            
            if optimized_route:
                optimized_routes[route_id] = optimized_route
                distance_saved = original_dist - optimized_route['total_distance']
                total_distance_saved += distance_saved
                
                logger.info(f"Route {route_id}: Saved {distance_saved:.2f} km")
        
        optimization_results = {
            'optimized_routes': optimized_routes,
            'total_distance_saved': total_distance_saved,
            'original_total_distance': original_distance,
            'efficiency_improvement': (total_distance_saved / original_distance) * 100 if original_distance > 0 else 0
        }
        
        logger.info(f"Network optimization complete. Efficiency improvement: {optimization_results['efficiency_improvement']:.2f}%")
        return optimization_results
    
    def _calculate_route_distance(self, stops: List[Dict]) -> float:
        """Calculate the total distance of a route."""
        total_distance = 0
        for i in range(len(stops) - 1):
            coord1 = (stops[i]['stop_lat'], stops[i]['stop_lon'])
            coord2 = (stops[i+1]['stop_lat'], stops[i+1]['stop_lon'])
            total_distance += geodesic(coord1, coord2).kilometers
        
        return total_distance
    
    def estimate_demand_for_route(self, stops: List[Dict]) -> List[int]:
        """Estimate demand for stops in a single route."""
        demands = []
        n_stops = len(stops)
        
        for i in range(n_stops):
            # Major stops (first, last, middle) have higher demand
            if i == 0 or i == n_stops - 1 or i == n_stops // 2:
                demand = np.random.randint(50, 150)
            else:
                demand = np.random.randint(10, 50)
            demands.append(demand)
        
        return demands

def main():
    """Main function to run route optimization."""
    optimizer = RouteOptimizer()
    
    # Optimize the network
    results = optimizer.optimize_network("data/raw")
    
    # Save results
    import json
    with open("data/processed/optimization_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Optimization complete! Efficiency improvement: {results['efficiency_improvement']:.2f}%")

if __name__ == "__main__":
    main() 