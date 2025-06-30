"""
Schedule Optimization Module for Accra Public Transport
Uses PuLP to optimize bus schedules and frequencies
"""

import os
import logging
import pandas as pd
import numpy as np
from pulp import *
import yaml
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScheduleOptimizer:
    """Optimizes bus schedules using linear programming with PuLP."""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        """Initialize the schedule optimizer with configuration."""
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.problem = None
        self.variables = {}
        self.constraints = {}
        
    def load_gtfs_data(self, data_path: str) -> Dict[str, pd.DataFrame]:
        """Load GTFS data for schedule optimization."""
        logger.info(f"Loading GTFS data from {data_path}")
        
        gtfs_files = {
            'routes': 'routes.txt',
            'trips': 'trips.txt',
            'stop_times': 'stop_times.txt',
            'stops': 'stops.txt',
            'calendar': 'calendar.txt'
        }
        
        data = {}
        for name, filename in gtfs_files.items():
            file_path = os.path.join(data_path, filename)
            if os.path.exists(file_path):
                data[name] = pd.read_csv(file_path)
                logger.info(f"Loaded {name}: {len(data[name])} records")
        
        return data
    
    def prepare_schedule_data(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """Prepare data for schedule optimization."""
        logger.info("Preparing schedule optimization data")
        
        routes_df = data['routes']
        trips_df = data['trips']
        stop_times_df = data['stop_times']
        stops_df = data['stops']
        
        # Get unique routes
        unique_routes = routes_df['route_id'].unique()
        
        schedule_data = {
            'routes': unique_routes,
            'route_info': {},
            'demand_patterns': {},
            'vehicle_capacity': 100,
            'min_headway': 5,  # minutes
            'max_headway': 30,  # minutes
            'service_hours': (6, 22)  # 6 AM to 10 PM
        }
        
        # Process each route
        for route_id in unique_routes[:5]:  # Limit to first 5 routes for demonstration
            route_info = routes_df[routes_df['route_id'] == route_id].iloc[0]
            route_trips = trips_df[trips_df['route_id'] == route_id]
            
            # Get stops for this route
            route_stop_times = stop_times_df[stop_times_df['trip_id'].isin(route_trips['trip_id'])]
            first_trip = route_trips.iloc[0]['trip_id']
            route_stops = route_stop_times[route_stop_times['trip_id'] == first_trip].sort_values('stop_sequence')
            
            # Calculate route characteristics
            total_stops = len(route_stops)
            avg_trip_time = self._calculate_avg_trip_time(route_stop_times)
            
            schedule_data['route_info'][route_id] = {
                'route_name': route_info.get('route_short_name', route_id),
                'route_type': route_info.get('route_type', 3),
                'total_stops': total_stops,
                'avg_trip_time': avg_trip_time,
                'stops': route_stops[['stop_id', 'stop_sequence']].to_dict('records')
            }
            
            # Generate demand patterns (simplified)
            schedule_data['demand_patterns'][route_id] = self._generate_demand_pattern(route_id, total_stops)
        
        logger.info(f"Prepared schedule data for {len(schedule_data['routes'])} routes")
        return schedule_data
    
    def _calculate_avg_trip_time(self, stop_times_df: pd.DataFrame) -> float:
        """Calculate average trip time in minutes."""
        trip_times = []
        
        for trip_id in stop_times_df['trip_id'].unique():
            trip_data = stop_times_df[stop_times_df['trip_id'] == trip_id].sort_values('stop_sequence')
            
            if len(trip_data) > 1:
                first_time = pd.to_datetime(trip_data.iloc[0]['arrival_time'], format='%H:%M:%S')
                last_time = pd.to_datetime(trip_data.iloc[-1]['arrival_time'], format='%H:%M:%S')
                trip_duration = (last_time - first_time).total_seconds() / 60
                trip_times.append(trip_duration)
        
        return np.mean(trip_times) if trip_times else 30.0
    
    def _generate_demand_pattern(self, route_id: str, total_stops: int) -> Dict:
        """Generate demand patterns for a route."""
        # Time periods: morning_peak, midday, afternoon_peak, evening, night
        time_periods = ['morning_peak', 'midday', 'afternoon_peak', 'evening', 'night']
        
        demand_pattern = {}
        
        for period in time_periods:
            period_demand = {}
            
            for stop_seq in range(1, total_stops + 1):
                # Generate realistic demand based on time period and stop
                base_demand = 20
                
                if period == 'morning_peak':
                    multiplier = 2.5
                elif period == 'afternoon_peak':
                    multiplier = 2.0
                elif period == 'evening':
                    multiplier = 1.5
                elif period == 'midday':
                    multiplier = 1.0
                else:  # night
                    multiplier = 0.3
                
                # Major stops (first, last, middle) have higher demand
                if stop_seq <= 3 or stop_seq >= total_stops - 2:
                    stop_multiplier = 1.5
                else:
                    stop_multiplier = 1.0
                
                demand = int(base_demand * multiplier * stop_multiplier * np.random.uniform(0.8, 1.2))
                period_demand[stop_seq] = max(1, demand)
            
            demand_pattern[period] = period_demand
        
        return demand_pattern
    
    def optimize_schedules(self, schedule_data: Dict) -> Dict:
        """Optimize bus schedules using linear programming."""
        logger.info("Starting schedule optimization")
        
        # Create optimization problem
        prob = LpProblem("Bus_Schedule_Optimization", LpMinimize)
        
        # Decision variables
        # x[r,t] = number of buses on route r during time period t
        routes = schedule_data['routes']
        time_periods = ['morning_peak', 'midday', 'afternoon_peak', 'evening', 'night']
        
        x = LpVariable.dicts("buses",
                           [(r, t) for r in routes for t in time_periods],
                           lowBound=1, cat='Integer')
        
        # Objective function: minimize total number of buses
        prob += lpSum([x[r, t] for r in routes for t in time_periods])
        
        # Constraints
        constraints = []
        
        # 1. Demand satisfaction constraint
        for r in routes:
            for t in time_periods:
                max_demand = max(schedule_data['demand_patterns'][r][t].values())
                capacity = schedule_data['vehicle_capacity']
                min_buses_needed = max(1, int(np.ceil(max_demand / capacity)))
                
                prob += x[r, t] >= min_buses_needed, f"demand_{r}_{t}"
                constraints.append(f"demand_{r}_{t}")
        
        # 2. Headway constraints
        for r in routes:
            for t in time_periods:
                avg_trip_time = schedule_data['route_info'][r]['avg_trip_time']
                
                # Maximum headway constraint
                max_headway = schedule_data['max_headway']
                min_buses_for_headway = max(1, int(np.ceil(avg_trip_time / max_headway)))
                prob += x[r, t] >= min_buses_for_headway, f"headway_max_{r}_{t}"
                constraints.append(f"headway_max_{r}_{t}")
                
                # Minimum headway constraint
                min_headway = schedule_data['min_headway']
                max_buses_for_headway = int(avg_trip_time / min_headway)
                prob += x[r, t] <= max_buses_for_headway, f"headway_min_{r}_{t}"
                constraints.append(f"headway_min_{r}_{t}")
        
        # 3. Fleet size constraint (total buses available)
        max_fleet_size = 50  # Total buses available
        prob += lpSum([x[r, t] for r in routes for t in time_periods]) <= max_fleet_size, "fleet_size"
        constraints.append("fleet_size")
        
        # Solve the problem
        logger.info("Solving optimization problem...")
        prob.solve(PULP_CBC_CMD(msg=False))
        
        # Extract results
        results = {
            'status': LpStatus[prob.status],
            'objective_value': value(prob.objective),
            'route_schedules': {},
            'summary': {}
        }
        
        if prob.status == 1:  # Optimal solution found
            logger.info(f"Optimal solution found! Total buses needed: {value(prob.objective)}")
            
            # Extract schedule for each route
            for r in routes:
                route_schedule = {}
                for t in time_periods:
                    buses_needed = int(value(x[r, t]))
                    route_schedule[t] = {
                        'buses': buses_needed,
                        'headway': schedule_data['route_info'][r]['avg_trip_time'] / buses_needed if buses_needed > 0 else float('inf'),
                        'capacity': buses_needed * schedule_data['vehicle_capacity'],
                        'max_demand': max(schedule_data['demand_patterns'][r][t].values())
                    }
                
                results['route_schedules'][r] = route_schedule
            
            # Calculate summary statistics
            total_buses = sum(sum(schedule[t]['buses'] for t in time_periods) 
                            for schedule in results['route_schedules'].values())
            
            results['summary'] = {
                'total_buses': total_buses,
                'total_routes': len(routes),
                'avg_buses_per_route': total_buses / len(routes),
                'utilization_rate': self._calculate_utilization_rate(results, schedule_data)
            }
            
        else:
            logger.warning(f"Optimization failed with status: {LpStatus[prob.status]}")
        
        return results
    
    def _calculate_utilization_rate(self, results: Dict, schedule_data: Dict) -> float:
        """Calculate fleet utilization rate."""
        total_capacity = 0
        total_demand = 0
        
        for route_id, schedule in results['route_schedules'].items():
            for time_period, data in schedule.items():
                total_capacity += data['capacity']
                total_demand += data['max_demand']
        
        return (total_demand / total_capacity) * 100 if total_capacity > 0 else 0
    
    def generate_optimized_gtfs(self, original_data: Dict, optimization_results: Dict, output_path: str) -> str:
        """Generate optimized GTFS files based on optimization results."""
        logger.info("Generating optimized GTFS files")
        
        if optimization_results['status'] != 'Optimal':
            logger.warning("Cannot generate GTFS without optimal solution")
            return None
        
        # Create output directory
        os.makedirs(output_path, exist_ok=True)
        
        # Generate optimized trips and stop_times
        optimized_trips = []
        optimized_stop_times = []
        trip_id_counter = 1
        
        for route_id, schedule in optimization_results['route_schedules'].items():
            route_info = original_data['routes'][original_data['routes']['route_id'] == route_id].iloc[0]
            
            for time_period, data in schedule.items():
                buses_needed = data['buses']
                
                for bus_num in range(buses_needed):
                    # Create trip
                    trip_id = f"OPT_{route_id}_{time_period}_{bus_num:02d}"
                    
                    optimized_trips.append({
                        'trip_id': trip_id,
                        'route_id': route_id,
                        'service_id': f"OPT_SERVICE_{time_period}",
                        'trip_headsign': f"{route_info.get('route_short_name', route_id)} - {time_period}",
                        'direction_id': 0,
                        'shape_id': f"OPT_SHAPE_{route_id}"
                    })
                    
                    # Create stop times for this trip
                    base_time = self._get_base_time_for_period(time_period)
                    headway = data['headway']
                    
                    # Get original stop sequence for this route
                    route_trips = original_data['trips'][original_data['trips']['route_id'] == route_id]
                    if not route_trips.empty:
                        original_trip = route_trips.iloc[0]['trip_id']
                        original_stop_times = original_data['stop_times'][
                            original_data['stop_times']['trip_id'] == original_trip
                        ].sort_values('stop_sequence')
                        
                        for idx, stop_time in original_stop_times.iterrows():
                            # Calculate new arrival/departure times
                            time_offset = (bus_num * headway) + (idx * 2)  # 2 minutes between stops
                            new_time = base_time + timedelta(minutes=time_offset)
                            
                            optimized_stop_times.append({
                                'trip_id': trip_id,
                                'stop_id': stop_time['stop_id'],
                                'stop_sequence': stop_time['stop_sequence'],
                                'arrival_time': new_time.strftime('%H:%M:%S'),
                                'departure_time': (new_time + timedelta(minutes=1)).strftime('%H:%M:%S')
                            })
        
        # Create DataFrames
        trips_df = pd.DataFrame(optimized_trips)
        stop_times_df = pd.DataFrame(optimized_stop_times)
        
        # Save optimized GTFS files
        trips_df.to_csv(os.path.join(output_path, 'trips.txt'), index=False)
        stop_times_df.to_csv(os.path.join(output_path, 'stop_times.txt'), index=False)
        
        # Copy other necessary files
        for file_name in ['routes.txt', 'stops.txt', 'calendar.txt']:
            if file_name in original_data:
                original_data[file_name].to_csv(os.path.join(output_path, file_name), index=False)
        
        logger.info(f"Optimized GTFS files saved to {output_path}")
        return output_path
    
    def _get_base_time_for_period(self, time_period: str) -> datetime:
        """Get base time for a time period."""
        base_times = {
            'morning_peak': datetime.strptime('07:00:00', '%H:%M:%S'),
            'midday': datetime.strptime('12:00:00', '%H:%M:%S'),
            'afternoon_peak': datetime.strptime('17:00:00', '%H:%M:%S'),
            'evening': datetime.strptime('19:00:00', '%H:%M:%S'),
            'night': datetime.strptime('22:00:00', '%H:%M:%S')
        }
        return base_times.get(time_period, datetime.strptime('08:00:00', '%H:%M:%S'))
    
    def create_schedule_report(self, optimization_results: Dict, output_path: str = "data/processed/schedule_report.html") -> str:
        """Create a detailed report of the optimized schedules."""
        logger.info("Creating schedule optimization report")
        
        if optimization_results['status'] != 'Optimal':
            return None
        
        # Create HTML report
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Schedule Optimization Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .summary {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .route-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                .route-table th, .route-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .route-table th {{ background-color: #f2f2f2; }}
                .efficient {{ color: green; }}
                .warning {{ color: orange; }}
                .critical {{ color: red; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚌 Bus Schedule Optimization Report</h1>
                <p>Accra Public Transport System</p>
            </div>
            
            <div class="summary">
                <h2>📊 Optimization Summary</h2>
                <p><strong>Status:</strong> {optimization_results['status']}</p>
                <p><strong>Total Buses Required:</strong> {optimization_results['summary']['total_buses']}</p>
                <p><strong>Total Routes:</strong> {optimization_results['summary']['total_routes']}</p>
                <p><strong>Average Buses per Route:</strong> {optimization_results['summary']['avg_buses_per_route']:.1f}</p>
                <p><strong>Fleet Utilization Rate:</strong> {optimization_results['summary']['utilization_rate']:.1f}%</p>
            </div>
            
            <h2>🚏 Route-by-Route Schedule</h2>
            <table class="route-table">
                <tr>
                    <th>Route ID</th>
                    <th>Morning Peak</th>
                    <th>Midday</th>
                    <th>Afternoon Peak</th>
                    <th>Evening</th>
                    <th>Night</th>
                </tr>
        """
        
        for route_id, schedule in optimization_results['route_schedules'].items():
            html_content += f"<tr><td><strong>{route_id}</strong></td>"
            
            for period in ['morning_peak', 'midday', 'afternoon_peak', 'evening', 'night']:
                data = schedule[period]
                buses = data['buses']
                headway = data['headway']
                
                # Color coding based on efficiency
                if headway <= 10:
                    efficiency_class = "efficient"
                elif headway <= 20:
                    efficiency_class = "warning"
                else:
                    efficiency_class = "critical"
                
                html_content += f"""
                <td class="{efficiency_class}">
                    <strong>{buses} buses</strong><br>
                    Headway: {headway:.1f} min<br>
                    Capacity: {data['capacity']}<br>
                    Demand: {data['max_demand']}
                </td>
                """
            
            html_content += "</tr>"
        
        html_content += """
            </table>
            
            <h2>💡 Recommendations</h2>
            <ul>
                <li><strong>Green cells:</strong> Optimal service frequency</li>
                <li><strong>Orange cells:</strong> Consider increasing frequency</li>
                <li><strong>Red cells:</strong> Immediate attention needed</li>
            </ul>
            
            <h2>📈 Expected Improvements</h2>
            <ul>
                <li>Reduced waiting times for passengers</li>
                <li>Better resource utilization</li>
                <li>Improved service reliability</li>
                <li>Cost optimization through efficient fleet management</li>
            </ul>
        </body>
        </html>
        """
        
        # Save report
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Schedule report saved to {output_path}")
        return output_path

def main():
    """Main function to run schedule optimization."""
    optimizer = ScheduleOptimizer()
    
    # Load data
    data = optimizer.load_gtfs_data("data/raw")
    
    # Prepare schedule data
    schedule_data = optimizer.prepare_schedule_data(data)
    
    # Optimize schedules
    results = optimizer.optimize_schedules(schedule_data)
    
    # Generate optimized GTFS
    if results['status'] == 'Optimal':
        optimized_gtfs_path = optimizer.generate_optimized_gtfs(data, results, "data/processed/optimized_gtfs")
        
        # Create report
        report_path = optimizer.create_schedule_report(results)
        
        print(f"Schedule optimization complete!")
        print(f"Total buses needed: {results['summary']['total_buses']}")
        print(f"Utilization rate: {results['summary']['utilization_rate']:.1f}%")
        print(f"Optimized GTFS saved to: {optimized_gtfs_path}")
        print(f"Report saved to: {report_path}")
    else:
        print(f"Optimization failed: {results['status']}")

if __name__ == "__main__":
    main() 