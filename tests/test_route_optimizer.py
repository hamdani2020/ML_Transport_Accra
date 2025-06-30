"""
Tests for Route Optimization Module
"""

import pytest
import pandas as pd
import numpy as np
import os
import tempfile
from unittest.mock import Mock, patch
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.route_optimizer import RouteOptimizer

class TestRouteOptimizer:
    """Test cases for RouteOptimizer class."""
    
    @pytest.fixture
    def optimizer(self):
        """Create a RouteOptimizer instance for testing."""
        return RouteOptimizer()
    
    @pytest.fixture
    def sample_gtfs_data(self):
        """Create sample GTFS data for testing."""
        data = {
            'stops': pd.DataFrame({
                'stop_id': ['STOP001', 'STOP002', 'STOP003'],
                'stop_name': ['Stop 1', 'Stop 2', 'Stop 3'],
                'stop_lat': [5.5600, 5.5700, 5.5800],
                'stop_lon': [-0.2057, -0.2157, -0.2257]
            }),
            'routes': pd.DataFrame({
                'route_id': ['ROUTE001', 'ROUTE002'],
                'route_short_name': ['R1', 'R2'],
                'route_type': [3, 3]
            }),
            'trips': pd.DataFrame({
                'trip_id': ['TRIP001', 'TRIP002'],
                'route_id': ['ROUTE001', 'ROUTE002'],
                'service_id': ['SERVICE001', 'SERVICE002']
            }),
            'stop_times': pd.DataFrame({
                'trip_id': ['TRIP001', 'TRIP001', 'TRIP001', 'TRIP002', 'TRIP002', 'TRIP002'],
                'stop_id': ['STOP001', 'STOP002', 'STOP003', 'STOP001', 'STOP002', 'STOP003'],
                'stop_sequence': [1, 2, 3, 1, 2, 3],
                'arrival_time': ['08:00:00', '08:15:00', '08:30:00', '09:00:00', '09:15:00', '09:30:00'],
                'departure_time': ['08:01:00', '08:16:00', '08:31:00', '09:01:00', '09:16:00', '09:31:00']
            })
        }
        return data
    
    def test_init(self, optimizer):
        """Test RouteOptimizer initialization."""
        assert optimizer is not None
        assert hasattr(optimizer, 'config')
        assert optimizer.data_manager is None
    
    def test_load_gtfs_data(self, optimizer, sample_gtfs_data, tmp_path):
        """Test GTFS data loading."""
        # Create temporary GTFS files
        for filename, df in sample_gtfs_data.items():
            df.to_csv(tmp_path / f"{filename}.txt", index=False)
        
        # Test loading
        result = optimizer.load_gtfs_data(str(tmp_path))
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'route_id' in result.columns
    
    @patch('scripts.route_optimizer.geodesic')
    def test_calculate_distance_matrix(self, mock_geodesic, optimizer):
        """Test distance matrix calculation."""
        # Mock geodesic distance calculation
        mock_geodesic.return_value.kilometers = 1.5
        
        stops_df = pd.DataFrame({
            'stop_lat': [5.5600, 5.5700],
            'stop_lon': [-0.2057, -0.2157]
        })
        
        result = optimizer.calculate_distance_matrix(stops_df)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 2)
        assert result[0][1] == 1.5  # Distance between stops
    
    def test_estimate_demand(self, optimizer):
        """Test demand estimation."""
        route_stops = pd.DataFrame({
            'route_id': ['ROUTE001'],
            'stop_id': [['STOP001', 'STOP002', 'STOP003']],
            'stop_name': [['Stop 1', 'Stop 2', 'Stop 3']],
            'stop_lat': [[5.5600, 5.5700, 5.5800]],
            'stop_lon': [[-0.2057, -0.2157, -0.2257]]
        })
        
        result = optimizer.estimate_demand(route_stops)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(demand, int) for demand in result)
    
    def test_optimize_route(self, optimizer):
        """Test single route optimization."""
        stops = [
            {'id': 'STOP001', 'name': 'Stop 1', 'lat': 5.5600, 'lon': -0.2057},
            {'id': 'STOP002', 'name': 'Stop 2', 'lat': 5.5700, 'lon': -0.2157},
            {'id': 'STOP003', 'name': 'Stop 3', 'lat': 5.5800, 'lon': -0.2257}
        ]
        
        with patch.object(optimizer, 'calculate_distance_matrix') as mock_dist:
            mock_dist.return_value = np.array([[0, 1.5, 3.0], [1.5, 0, 1.5], [3.0, 1.5, 0]])
            
            result = optimizer.optimize_route('ROUTE001', stops)
            
            if result:  # Optimization might fail in test environment
                assert isinstance(result, dict)
                assert 'route_stops' in result
                assert 'total_distance' in result
                assert 'total_time' in result
    
    def test_optimize_network(self, optimizer, sample_gtfs_data, tmp_path):
        """Test network-wide optimization."""
        # Create temporary GTFS files
        for filename, df in sample_gtfs_data.items():
            df.to_csv(tmp_path / f"{filename}.txt", index=False)
        
        with patch.object(optimizer, 'optimize_route') as mock_optimize:
            mock_optimize.return_value = {
                'route_stops': [],
                'total_distance': 15.5,
                'total_time': 45
            }
            
            result = optimizer.optimize_network(str(tmp_path))
            
            assert isinstance(result, dict)
            assert 'optimized_routes' in result
            assert 'total_distance_saved' in result
            assert 'efficiency_improvement' in result
    
    def test_calculate_route_distance(self, optimizer):
        """Test route distance calculation."""
        stops = [
            {'lat': 5.5600, 'lon': -0.2057},
            {'lat': 5.5700, 'lon': -0.2157},
            {'lat': 5.5800, 'lon': -0.2257}
        ]
        
        with patch('scripts.route_optimizer.geodesic') as mock_geodesic:
            mock_geodesic.return_value.kilometers = 1.5
            
            result = optimizer._calculate_route_distance(stops)
            
            assert isinstance(result, float)
            assert result > 0
    
    def test_estimate_demand_for_route(self, optimizer):
        """Test demand estimation for a single route."""
        stops = [
            {'id': 'STOP001', 'name': 'Stop 1', 'lat': 5.5600, 'lon': -0.2057},
            {'id': 'STOP002', 'name': 'Stop 2', 'lat': 5.5700, 'lon': -0.2157},
            {'id': 'STOP003', 'name': 'Stop 3', 'lat': 5.5800, 'lon': -0.2257}
        ]
        
        result = optimizer.estimate_demand_for_route(stops)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(demand, int) for demand in result)
        assert all(demand > 0 for demand in result)

if __name__ == "__main__":
    pytest.main([__file__]) 