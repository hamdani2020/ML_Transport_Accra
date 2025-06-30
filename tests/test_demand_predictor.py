"""
Tests for Demand Prediction Module
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

from scripts.demand_predictor import DemandPredictor

class TestDemandPredictor:
    """Test cases for DemandPredictor class."""
    
    @pytest.fixture
    def predictor(self):
        """Create a DemandPredictor instance for testing."""
        return DemandPredictor()
    
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
            }),
            'calendar': pd.DataFrame({
                'service_id': ['SERVICE001', 'SERVICE002'],
                'monday': [1, 1],
                'tuesday': [1, 1],
                'wednesday': [1, 1],
                'thursday': [1, 1],
                'friday': [1, 1],
                'saturday': [0, 0],
                'sunday': [0, 0]
            })
        }
        return data
    
    def test_init(self, predictor):
        """Test DemandPredictor initialization."""
        assert predictor is not None
        assert hasattr(predictor, 'config')
        assert predictor.models == {}
        assert predictor.scalers == {}
        assert predictor.label_encoders == {}
    
    def test_load_gtfs_data(self, predictor, sample_gtfs_data, tmp_path):
        """Test GTFS data loading."""
        # Create temporary GTFS files
        for filename, df in sample_gtfs_data.items():
            df.to_csv(tmp_path / f"{filename}.txt", index=False)
        
        # Test loading
        result = predictor.load_gtfs_data(str(tmp_path))
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'trip_id' in result.columns
        assert 'route_id' in result.columns
        assert 'stop_id' in result.columns
    
    def test_engineer_features(self, predictor):
        """Test feature engineering."""
        # Create sample data
        df = pd.DataFrame({
            'arrival_time': ['08:00:00', '09:00:00', '17:00:00'],
            'departure_time': ['08:01:00', '09:01:00', '17:01:00'],
            'monday': [1, 1, 1],
            'tuesday': [0, 0, 0],
            'wednesday': [0, 0, 0],
            'thursday': [0, 0, 0],
            'friday': [0, 0, 0],
            'saturday': [0, 0, 0],
            'sunday': [0, 0, 0],
            'route_type': [3, 3, 3],
            'stop_sequence': [1, 2, 3],
            'stop_lat': [5.5600, 5.5700, 5.5800],
            'stop_lon': [-0.2057, -0.2157, -0.2257]
        })
        
        result = predictor.engineer_features(df)
        
        assert isinstance(result, pd.DataFrame)
        assert 'hour' in result.columns
        assert 'minute' in result.columns
        assert 'time_of_day' in result.columns
        assert 'time_period' in result.columns
        assert 'demand' in result.columns
        assert len(result) == 3
    
    def test_generate_realistic_demand(self, predictor):
        """Test realistic demand generation."""
        df = pd.DataFrame({
            'hour': [7, 12, 17, 22],
            'monday': [1, 1, 1, 1],
            'friday': [0, 0, 0, 0],
            'saturday': [0, 0, 0, 0],
            'sunday': [0, 0, 0, 0],
            'route_type': [3, 3, 3, 3],
            'stop_sequence': [1, 5, 10, 15]
        })
        
        result = predictor._generate_realistic_demand(df)
        
        assert isinstance(result, np.ndarray)
        assert len(result) == 4
        assert all(demand > 0 for demand in result)
        
        # Morning peak should have higher demand
        assert result[0] > result[1]  # 7 AM > 12 PM
        assert result[2] > result[1]  # 5 PM > 12 PM
    
    def test_prepare_features(self, predictor):
        """Test feature preparation."""
        df = pd.DataFrame({
            'hour': [7, 8, 9],
            'minute': [0, 15, 30],
            'time_of_day': [7.0, 8.25, 9.5],
            'time_period': ['morning_peak', 'morning_peak', 'midday'],
            'monday': [1, 1, 1],
            'tuesday': [0, 0, 0],
            'wednesday': [0, 0, 0],
            'thursday': [0, 0, 0],
            'friday': [0, 0, 0],
            'saturday': [0, 0, 0],
            'sunday': [0, 0, 0],
            'route_type_encoded': [1, 1, 1],
            'stop_sequence': [1, 2, 3],
            'stop_lat': [5.5600, 5.5700, 5.5800],
            'stop_lon': [-0.2057, -0.2157, -0.2257],
            'demand': [50, 60, 40]
        })
        
        X, y = predictor.prepare_features(df)
        
        assert isinstance(X, pd.DataFrame)
        assert isinstance(y, pd.Series)
        assert len(X) == len(y)
        assert len(X) == 3
        assert 'demand' not in X.columns
        assert all(col in X.columns for col in ['hour', 'minute', 'time_of_day'])
    
    @patch('scripts.demand_predictor.RandomForestRegressor')
    @patch('scripts.demand_predictor.GradientBoostingRegressor')
    @patch('scripts.demand_predictor.xgb.XGBRegressor')
    @patch('scripts.demand_predictor.lgb.LGBMRegressor')
    def test_train_models(self, mock_lgb, mock_xgb, mock_gb, mock_rf, predictor):
        """Test model training."""
        # Mock models
        mock_rf.return_value.fit.return_value = None
        mock_rf.return_value.predict.return_value = np.array([45, 55, 35])
        mock_gb.return_value.fit.return_value = None
        mock_gb.return_value.predict.return_value = np.array([47, 53, 37])
        mock_xgb.return_value.fit.return_value = None
        mock_xgb.return_value.predict.return_value = np.array([46, 54, 36])
        mock_lgb.return_value.fit.return_value = None
        mock_lgb.return_value.predict.return_value = np.array([48, 52, 38])
        
        # Create sample data
        X = pd.DataFrame({
            'hour': [7, 8, 9],
            'minute': [0, 15, 30],
            'time_of_day': [7.0, 8.25, 9.5],
            'monday': [1, 1, 1],
            'tuesday': [0, 0, 0],
            'wednesday': [0, 0, 0],
            'thursday': [0, 0, 0],
            'friday': [0, 0, 0],
            'saturday': [0, 0, 0],
            'sunday': [0, 0, 0],
            'route_type_encoded': [1, 1, 1],
            'stop_sequence': [1, 2, 3],
            'stop_lat': [5.5600, 5.5700, 5.5800],
            'stop_lon': [-0.2057, -0.2157, -0.2257]
        })
        y = pd.Series([50, 60, 40])
        
        result = predictor.train_models(X, y)
        
        assert isinstance(result, dict)
        assert 'random_forest' in result
        assert 'gradient_boosting' in result
        assert 'xgboost' in result
        assert 'lightgbm' in result
        
        # Check that models were trained
        mock_rf.return_value.fit.assert_called_once()
        mock_gb.return_value.fit.assert_called_once()
        mock_xgb.return_value.fit.assert_called_once()
        mock_lgb.return_value.fit.assert_called_once()
    
    def test_predict_demand(self, predictor):
        """Test demand prediction."""
        # Mock trained model and scaler
        predictor.models['demand'] = Mock()
        predictor.models['demand'].predict.return_value = np.array([45])
        predictor.scalers['demand'] = Mock()
        predictor.scalers['demand'].transform.return_value = np.array([[7, 30, 7.5, 1, 0, 0, 0, 0, 0, 0, 1, 1, 5.5600, -0.2057]])
        
        result = predictor.predict_demand('STOP001', 'ROUTE001', '07:30:00', 'monday')
        
        assert isinstance(result, dict)
        assert 'stop_id' in result
        assert 'route_id' in result
        assert 'time' in result
        assert 'day_of_week' in result
        assert 'predicted_demand' in result
        assert 'confidence' in result
        assert result['stop_id'] == 'STOP001'
        assert result['route_id'] == 'ROUTE001'
        assert result['time'] == '07:30:00'
        assert result['day_of_week'] == 'monday'
        assert result['predicted_demand'] > 0
    
    def test_predict_network_demand(self, predictor):
        """Test network-wide demand prediction."""
        # Mock predict_demand method
        predictor.predict_demand = Mock()
        predictor.predict_demand.return_value = {
            'stop_id': 'STOP001',
            'route_id': 'ROUTE001',
            'time': '08:00:00',
            'day_of_week': 'monday',
            'predicted_demand': 50,
            'confidence': 0.85
        }
        
        stops = ['STOP001', 'STOP002']
        routes = ['ROUTE001']
        time_range = ('08:00:00', '09:00:00')
        days = ['monday']
        
        result = predictor.predict_network_demand(stops, routes, time_range, days)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'stop_id' in result.columns
        assert 'route_id' in result.columns
        assert 'time' in result.columns
        assert 'predicted_demand' in result.columns
    
    def test_save_models(self, predictor, tmp_path):
        """Test model saving."""
        # Mock models and scalers
        predictor.models['demand'] = Mock()
        predictor.scalers['demand'] = Mock()
        predictor.label_encoders['time_period'] = Mock()
        
        # Test saving
        predictor.save_models(str(tmp_path))
        
        # Check that files were created
        assert (tmp_path / 'demand_model.pkl').exists()
        assert (tmp_path / 'demand_scaler.pkl').exists()
        assert (tmp_path / 'time_period_encoder.pkl').exists()
    
    def test_load_models(self, predictor, tmp_path):
        """Test model loading."""
        # Create mock model files
        (tmp_path / 'demand_model.pkl').touch()
        (tmp_path / 'demand_scaler.pkl').touch()
        (tmp_path / 'time_period_encoder.pkl').touch()
        
        with patch('scripts.demand_predictor.joblib.load') as mock_load:
            mock_load.return_value = Mock()
            
            predictor.load_models(str(tmp_path))
            
            # Check that load was called
            assert mock_load.call_count >= 3

if __name__ == "__main__":
    pytest.main([__file__]) 