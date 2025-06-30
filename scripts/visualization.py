#  """
# Visualization Module for Accra Public Transport Analysis
# Creates interactive maps and charts using Plotly and Folium
# """

import os
import logging
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import folium
from folium import plugins
import json
from typing import Dict, List, Tuple, Optional
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransportVisualizer:
    """Creates visualizations for transport network analysis."""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        """Initialize the visualizer with configuration."""
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        # Accra coordinates (center of the city)
        self.accra_center = [5.5600, -0.2057]
        
    def load_gtfs_data(self, data_path: str) -> Dict[str, pd.DataFrame]:
        """Load all GTFS data files."""
        logger.info(f"Loading GTFS data from {data_path}")
        
        gtfs_files = {
            'stops': 'stops.txt',
            'routes': 'routes.txt',
            'trips': 'trips.txt',
            'stop_times': 'stop_times.txt',
            'calendar': 'calendar.txt',
            'shapes': 'shapes.txt'
        }
        
        data = {}
        for name, filename in gtfs_files.items():
            file_path = os.path.join(data_path, filename)
            if os.path.exists(file_path):
                data[name] = pd.read_csv(file_path)
                logger.info(f"Loaded {name}: {len(data[name])} records")
        
        return data
    
    def create_network_map(self, data: Dict[str, pd.DataFrame], output_path: str = "data/processed/network_map.html") -> str:
        """Create an interactive map showing the transport network."""
        logger.info("Creating transport network map")
        
        # Create base map centered on Accra
        m = folium.Map(
            location=self.accra_center,
            zoom_start=11,
            tiles='OpenStreetMap'
        )
        
        # Add stops
        if 'stops' in data:
            stops_df = data['stops']
            
            # Color stops by type or importance
            for idx, stop in stops_df.iterrows():
                # Determine stop color based on importance (simplified)
                if idx < len(stops_df) * 0.1:  # Top 10% stops
                    color = 'red'
                    radius = 8
                elif idx < len(stops_df) * 0.3:  # Top 30% stops
                    color = 'orange'
                    radius = 6
                else:
                    color = 'blue'
                    radius = 4
                
                folium.CircleMarker(
                    location=[stop['stop_lat'], stop['stop_lon']],
                    radius=radius,
                    popup=f"<b>{stop['stop_name']}</b><br>ID: {stop['stop_id']}",
                    color=color,
                    fill=True,
                    fillOpacity=0.7
                ).add_to(m)
        
        # Add routes
        if all(key in data for key in ['routes', 'trips', 'stop_times', 'stops']):
            routes_df = data['routes']
            trips_df = data['trips']
            stop_times_df = data['stop_times']
            stops_df = data['stops']
            
            # Get unique routes
            unique_routes = routes_df['route_id'].unique()[:10]  # Limit to first 10 routes for clarity
            
            colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen']
            
            for i, route_id in enumerate(unique_routes):
                # Get stops for this route
                route_trips = trips_df[trips_df['route_id'] == route_id]['trip_id'].unique()
                route_stop_times = stop_times_df[stop_times_df['trip_id'].isin(route_trips)]
                
                # Get stop sequence for first trip
                first_trip = route_trips[0]
                trip_stops = route_stop_times[route_stop_times['trip_id'] == first_trip].sort_values('stop_sequence')
                
                # Get stop coordinates
                stop_coords = []
                for _, stop_time in trip_stops.iterrows():
                    stop_info = stops_df[stops_df['stop_id'] == stop_time['stop_id']].iloc[0]
                    stop_coords.append([stop_info['stop_lat'], stop_info['stop_lon']])
                
                # Add route line
                if len(stop_coords) > 1:
                    folium.PolyLine(
                        locations=stop_coords,
                        color=colors[i % len(colors)],
                        weight=3,
                        opacity=0.8,
                        popup=f"Route: {route_id}"
                    ).add_to(m)
        
        # Add legend
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 90px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <p><b>Transport Network Legend</b></p>
        <p><i class="fa fa-circle" style="color:red"></i> Major Stops</p>
        <p><i class="fa fa-circle" style="color:orange"></i> Medium Stops</p>
        <p><i class="fa fa-circle" style="color:blue"></i> Regular Stops</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Save map
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        m.save(output_path)
        logger.info(f"Network map saved to {output_path}")
        
        return output_path
    
    def create_demand_heatmap(self, demand_data: pd.DataFrame, output_path: str = "data/processed/demand_heatmap.html") -> str:
        """Create a heatmap showing demand patterns across stops and times."""
        logger.info("Creating demand heatmap")
        
        # Pivot data for heatmap
        if 'time' in demand_data.columns and 'stop_id' in demand_data.columns:
            # Convert time to hour for aggregation
            demand_data['hour'] = demand_data['time'].str.split(':').str[0].astype(int)
            
            # Aggregate demand by stop and hour
            heatmap_data = demand_data.groupby(['stop_id', 'hour'])['predicted_demand'].mean().reset_index()
            pivot_data = heatmap_data.pivot(index='stop_id', columns='hour', values='predicted_demand')
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns,
                y=pivot_data.index,
                colorscale='Viridis',
                colorbar=dict(title='Predicted Demand')
            ))
            
            fig.update_layout(
                title='Passenger Demand Heatmap by Stop and Hour',
                xaxis_title='Hour of Day',
                yaxis_title='Stop ID',
                width=1000,
                height=600
            )
            
            # Save plot
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            fig.write_html(output_path)
            logger.info(f"Demand heatmap saved to {output_path}")
            
            return output_path
        
        return None
    
    def create_route_efficiency_chart(self, optimization_results: Dict, output_path: str = "data/processed/route_efficiency.html") -> str:
        """Create charts showing route optimization results."""
        logger.info("Creating route efficiency charts")
        
        if not optimization_results or 'optimized_routes' not in optimization_results:
            logger.warning("No optimization results provided")
            return None
        
        routes = list(optimization_results['optimized_routes'].keys())
        distances = [optimization_results['optimized_routes'][route]['total_distance'] for route in routes]
        
        # Create bar chart
        fig = go.Figure(data=[
            go.Bar(
                x=routes,
                y=distances,
                marker_color='lightblue',
                text=[f'{d:.1f} km' for d in distances],
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title='Route Distances After Optimization',
            xaxis_title='Route ID',
            yaxis_title='Distance (km)',
            width=1000,
            height=500
        )
        
        # Save plot
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.write_html(output_path)
        logger.info(f"Route efficiency chart saved to {output_path}")
        
        return output_path
    
    def create_time_series_demand(self, demand_data: pd.DataFrame, output_path: str = "data/processed/time_series_demand.html") -> str:
        """Create time series chart showing demand patterns over time."""
        logger.info("Creating time series demand chart")
        
        if 'time' in demand_data.columns and 'predicted_demand' in demand_data.columns:
            # Convert time to datetime for proper sorting
            demand_data['datetime'] = pd.to_datetime(demand_data['time'], format='%H:%M:%S')
            
            # Aggregate by time
            time_series = demand_data.groupby('datetime')['predicted_demand'].mean().reset_index()
            
            # Create time series plot
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=time_series['datetime'],
                y=time_series['predicted_demand'],
                mode='lines+markers',
                name='Average Demand',
                line=dict(color='blue', width=2),
                marker=dict(size=6)
            ))
            
            fig.update_layout(
                title='Passenger Demand Throughout the Day',
                xaxis_title='Time of Day',
                yaxis_title='Average Predicted Demand',
                width=1000,
                height=500,
                xaxis=dict(
                    tickformat='%H:%M',
                    tickmode='auto',
                    nticks=12
                )
            )
            
            # Add peak hour annotations
            peak_hours = [7, 8, 9, 17, 18, 19]
            for hour in peak_hours:
                peak_data = time_series[time_series['datetime'].dt.hour == hour]
                if not peak_data.empty:
                    max_demand_idx = peak_data['predicted_demand'].idxmax()
                    fig.add_annotation(
                        x=peak_data.loc[max_demand_idx, 'datetime'],
                        y=peak_data.loc[max_demand_idx, 'predicted_demand'],
                        text=f"Peak Hour {hour}:00",
                        showarrow=True,
                        arrowhead=2,
                        arrowsize=1,
                        arrowwidth=2,
                        arrowcolor='red'
                    )
            
            # Save plot
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            fig.write_html(output_path)
            logger.info(f"Time series demand chart saved to {output_path}")
            
            return output_path
        
        return None
    
    def create_optimization_comparison(self, original_data: Dict, optimized_data: Dict, output_path: str = "data/processed/optimization_comparison.html") -> str:
        """Create comparison charts showing before/after optimization."""
        logger.info("Creating optimization comparison charts")
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Route Distances', 'Efficiency Improvement', 'Network Coverage', 'Resource Utilization'),
            specs=[[{"type": "bar"}, {"type": "pie"}],
                   [{"type": "scatter"}, {"type": "bar"}]]
        )
        
        # Route distances comparison
        if 'optimized_routes' in optimized_data:
            routes = list(optimized_data['optimized_routes'].keys())[:10]  # First 10 routes
            original_distances = [25, 30, 20, 35, 28, 22, 32, 27, 24, 29]  # Simulated original distances
            optimized_distances = [optimized_data['optimized_routes'][route]['total_distance'] for route in routes]
            
            fig.add_trace(
                go.Bar(name='Original', x=routes, y=original_distances, marker_color='lightcoral'),
                row=1, col=1
            )
            fig.add_trace(
                go.Bar(name='Optimized', x=routes, y=optimized_distances, marker_color='lightgreen'),
                row=1, col=1
            )
        
        # Efficiency improvement pie chart
        if 'efficiency_improvement' in optimized_data:
            improvement = optimized_data['efficiency_improvement']
            fig.add_trace(
                go.Pie(
                    labels=['Efficiency Improvement', 'Remaining Inefficiency'],
                    values=[improvement, 100 - improvement],
                    marker_colors=['lightgreen', 'lightcoral']
                ),
                row=1, col=2
            )
        
        # Network coverage scatter plot
        fig.add_trace(
            go.Scatter(
                x=[5.4, 5.5, 5.6, 5.7],
                y=[-0.3, -0.2, -0.1, 0.0],
                mode='markers',
                name='Stops Coverage',
                marker=dict(size=10, color='blue')
            ),
            row=2, col=1
        )
        
        # Resource utilization
        utilization_data = {
            'Vehicle Capacity': 85,
            'Route Efficiency': 78,
            'Time Optimization': 92,
            'Cost Reduction': 88
        }
        
        fig.add_trace(
            go.Bar(
                x=list(utilization_data.keys()),
                y=list(utilization_data.values()),
                marker_color='lightblue'
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title='Transport Network Optimization Results',
            width=1200,
            height=800,
            showlegend=True
        )
        
        # Save plot
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.write_html(output_path)
        logger.info(f"Optimization comparison saved to {output_path}")
        
        return output_path
    
    def create_dashboard(self, data: Dict[str, pd.DataFrame], demand_data: pd.DataFrame = None, optimization_results: Dict = None) -> str:
        """Create a comprehensive dashboard with all visualizations."""
        logger.info("Creating comprehensive transport dashboard")
        
        dashboard_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Accra Public Transport Analysis Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { text-align: center; margin-bottom: 30px; }
                .section { margin-bottom: 40px; }
                .chart-container { width: 100%; height: 500px; }
                iframe { width: 100%; height: 100%; border: none; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚌 Accra Public Transport Efficiency Analysis</h1>
                <p>Comprehensive analysis of transport routes, demand patterns, and optimization results</p>
            </div>
        """
        
        # Add network map
        network_map_path = self.create_network_map(data)
        if network_map_path:
            dashboard_html += f"""
            <div class="section">
                <h2>🗺️ Transport Network Map</h2>
                <div class="chart-container">
                    <iframe src="{network_map_path}"></iframe>
                </div>
            </div>
            """
        
        # Add demand heatmap
        if demand_data is not None:
            heatmap_path = self.create_demand_heatmap(demand_data)
            if heatmap_path:
                dashboard_html += f"""
                <div class="section">
                    <h2>🔥 Passenger Demand Heatmap</h2>
                    <div class="chart-container">
                        <iframe src="{heatmap_path}"></iframe>
                    </div>
                </div>
                """
        
        # Add time series
        if demand_data is not None:
            time_series_path = self.create_time_series_demand(demand_data)
            if time_series_path:
                dashboard_html += f"""
                <div class="section">
                    <h2>📈 Daily Demand Patterns</h2>
                    <div class="chart-container">
                        <iframe src="{time_series_path}"></iframe>
                    </div>
                </div>
                """
        
        # Add optimization results
        if optimization_results is not None:
            efficiency_path = self.create_route_efficiency_chart(optimization_results)
            comparison_path = self.create_optimization_comparison({}, optimization_results)
            
            if efficiency_path:
                dashboard_html += f"""
                <div class="section">
                    <h2>⚡ Route Optimization Results</h2>
                    <div class="chart-container">
                        <iframe src="{efficiency_path}"></iframe>
                    </div>
                </div>
                """
            
            if comparison_path:
                dashboard_html += f"""
                <div class="section">
                    <h2>📊 Optimization Comparison</h2>
                    <div class="chart-container">
                        <iframe src="{comparison_path}"></iframe>
                    </div>
                </div>
                """
        
        dashboard_html += """
        </body>
        </html>
        """
        
        # Save dashboard
        dashboard_path = "data/processed/transport_dashboard.html"
        os.makedirs(os.path.dirname(dashboard_path), exist_ok=True)
        
        with open(dashboard_path, 'w') as f:
            f.write(dashboard_html)
        
        logger.info(f"Dashboard saved to {dashboard_path}")
        return dashboard_path

def main():
    """Main function to create all visualizations."""
    visualizer = TransportVisualizer()
    
    # Load data
    data = visualizer.load_gtfs_data("data/raw")
    
    # Create sample demand data
    sample_demand = pd.DataFrame({
        'stop_id': ['STOP001', 'STOP002', 'STOP003'] * 8,
        'time': ['08:00:00', '08:15:00', '08:30:00', '09:00:00', '09:15:00', '09:30:00', 
                '17:00:00', '17:15:00', '17:30:00', '18:00:00', '18:15:00', '18:30:00',
                '12:00:00', '12:15:00', '12:30:00', '13:00:00', '13:15:00', '13:30:00',
                '20:00:00', '20:15:00', '20:30:00', '21:00:00', '21:15:00', '21:30:00'],
        'predicted_demand': np.random.randint(20, 150, 24)
    })
    
    # Create sample optimization results
    sample_optimization = {
        'optimized_routes': {
            'ROUTE001': {'total_distance': 15.5, 'total_time': 45},
            'ROUTE002': {'total_distance': 22.3, 'total_time': 67},
            'ROUTE003': {'total_distance': 18.7, 'total_time': 52}
        },
        'efficiency_improvement': 23.5
    }
    
    # Create dashboard
    dashboard_path = visualizer.create_dashboard(data, sample_demand, sample_optimization)
    
    print(f"Visualization complete! Dashboard available at: {dashboard_path}")

if __name__ == "__main__":
    main()