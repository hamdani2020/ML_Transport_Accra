"""
Demand Prediction Module for Accra Public Transport
Uses ML models to predict passenger demand at stops and times
"""

import os
import logging
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import lightgbm as lgb
from datetime import datetime, timedelta
import yaml
import joblib
from typing import Dict, List, Tuple, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DemandPredictor:
    """Predicts passenger demand using machine learning models."""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        """Initialize the demand predictor with configuration."""
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.models = {}
        self.scalers = {}
        self.label_encoders = {}
        self.feature_columns = []
        
    def load_gtfs_data(self, data_path: str) -> pd.DataFrame:
        """Load and prepare GTFS data for demand prediction."""
        logger.info(f"Loading GTFS data from {data_path}")
        
        # Load GTFS files
        stops_df = pd.read_csv(os.path.join(data_path, "stops.txt"))
        routes_df = pd.read_csv(os.path.join(data_path, "routes.txt"))
        trips_df = pd.read_csv(os.path.join(data_path, "trips.txt"))
        stop_times_df = pd.read_csv(os.path.join(data_path, "stop_times.txt"))
        calendar_df = pd.read_csv(os.path.join(data_path, "calendar.txt"))
        
        # Merge data
        route_trips = trips_df.merge(routes_df, on='route_id', how='left')
        route_trips = route_trips.merge(calendar_df, on='service_id', how='left')
        
        # Merge with stop times
        stop_times_with_info = stop_times_df.merge(route_trips, on='trip_id', how='left')
        stop_times_with_info = stop_times_with_info.merge(stops_df, on='stop_id', how='left')
        
        logger.info(f"Loaded {len(stop_times_with_info)} stop time records")
        return stop_times_with_info
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features for demand prediction."""
        logger.info("Engineering features for demand prediction")
        
        # Convert time strings to datetime features
        df['arrival_time'] = pd.to_datetime(df['arrival_time'], format='%H:%M:%S', errors='coerce')
        df['departure_time'] = pd.to_datetime(df['departure_time'], format='%H:%M:%S', errors='coerce')
        
        # Extract time-based features
        df['hour'] = df['arrival_time'].dt.hour
        df['minute'] = df['arrival_time'].dt.minute
        df['time_of_day'] = df['hour'] + df['minute'] / 60
        
        # Create time period categories
        df['time_period'] = pd.cut(df['hour'], 
                                  bins=[0, 6, 9, 12, 17, 20, 24], 
                                  labels=['night', 'morning_peak', 'midday', 'afternoon_peak', 'evening', 'late_night'])
        
        # Day of week features
        df['monday'] = (df['monday'] == 1).astype(int)
        df['tuesday'] = (df['tuesday'] == 1).astype(int)
        df['wednesday'] = (df['wednesday'] == 1).astype(int)
        df['thursday'] = (df['thursday'] == 1).astype(int)
        df['friday'] = (df['friday'] == 1).astype(int)
        df['saturday'] = (df['saturday'] == 1).astype(int)
        df['sunday'] = (df['sunday'] == 1).astype(int)
        
        # Route type features
        df['route_type_encoded'] = df['route_type'].astype('category').cat.codes
        
        # Stop sequence features
        df['stop_sequence'] = df['stop_sequence'].astype(int)
        
        # Create demand target (simulated for now)
        np.random.seed(42)
        df['demand'] = self._generate_realistic_demand(df)
        
        logger.info(f"Engineered features. Final dataset shape: {df.shape}")
        return df
    
    def _generate_realistic_demand(self, df: pd.DataFrame) -> np.ndarray:
        """Generate realistic demand patterns based on time, day, and route characteristics."""
        demand = np.zeros(len(df))
        
        for idx, row in df.iterrows():
            base_demand = 20
            
            # Time-based demand patterns
            hour = row['hour']
            if 7 <= hour <= 9:  # Morning peak
                time_multiplier = 2.5
            elif 17 <= hour <= 19:  # Evening peak
                time_multiplier = 2.0
            elif 6 <= hour <= 22:  # Regular hours
                time_multiplier = 1.0
            else:  # Night hours
                time_multiplier = 0.3
            
            # Day of week patterns
            if row['monday'] or row['friday']:
                day_multiplier = 1.2
            elif row['saturday'] or row['sunday']:
                day_multiplier = 0.8
            else:
                day_multiplier = 1.0
            
            # Route type patterns
            route_type = row['route_type']
            if route_type == 3:  # Bus
                route_multiplier = 1.5
            elif route_type == 1:  # Metro
                route_multiplier = 2.0
            else:
                route_multiplier = 1.0
            
            # Stop sequence patterns (first/last stops have higher demand)
            stop_seq = row['stop_sequence']
            if stop_seq <= 3 or stop_seq >= 15:  # Major stops
                stop_multiplier = 1.5
            else:
                stop_multiplier = 1.0
            
            # Add some randomness
            noise = np.random.normal(1, 0.2)
            
            demand[idx] = base_demand * time_multiplier * day_multiplier * route_multiplier * stop_multiplier * noise
            demand[idx] = max(1, int(demand[idx]))  # Ensure minimum demand
        
        return demand
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features and target for training."""
        # Select feature columns
        feature_columns = [
            'hour', 'minute', 'time_of_day', 'time_period',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'route_type_encoded', 'stop_sequence',
            'stop_lat', 'stop_lon'
        ]
        
        # Only use columns that exist
        available_features = [col for col in feature_columns if col in df.columns]
        
        X = df[available_features].copy()
        y = df['demand']
        
        # Handle categorical features
        categorical_features = ['time_period']
        for feature in categorical_features:
            if feature in X.columns:
                le = LabelEncoder()
                X[feature] = le.fit_transform(X[feature].astype(str))
                self.label_encoders[feature] = le
        
        # Handle missing values
        X = X.fillna(X.mean())
        
        self.feature_columns = list(X.columns)
        logger.info(f"Prepared {len(self.feature_columns)} features for training")
        
        return X, y
    
    def train_models(self, X: pd.DataFrame, y: pd.Series) -> Dict:
        """Train multiple ML models for demand prediction."""
        logger.info("Training demand prediction models")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        self.scalers['demand'] = scaler
        
        # Define models
        models = {
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
            'gradient_boosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
            'xgboost': xgb.XGBRegressor(n_estimators=100, random_state=42),
            'lightgbm': lgb.LGBMRegressor(n_estimators=100, random_state=42)
        }
        
        results = {}
        
        for name, model in models.items():
            logger.info(f"Training {name} model")
            
            # Train model
            model.fit(X_train_scaled, y_train)
            
            # Make predictions
            y_pred = model.predict(X_test_scaled)
            
            # Calculate metrics
            metrics = {
                'mae': mean_absolute_error(y_test, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
                'r2': r2_score(y_test, y_pred)
            }
            
            # Cross-validation score
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='r2')
            metrics['cv_r2_mean'] = cv_scores.mean()
            metrics['cv_r2_std'] = cv_scores.std()
            
            results[name] = {
                'model': model,
                'metrics': metrics,
                'predictions': y_pred
            }
            
            logger.info(f"{name} - MAE: {metrics['mae']:.2f}, RMSE: {metrics['rmse']:.2f}, R²: {metrics['r2']:.3f}")
        
        # Store best model
        best_model_name = max(results.keys(), key=lambda k: results[k]['metrics']['r2'])
        self.models['demand'] = results[best_model_name]['model']
        
        logger.info(f"Best model: {best_model_name} with R²: {results[best_model_name]['metrics']['r2']:.3f}")
        
        return results
    
    def predict_demand(self, 
                      stop_id: str, 
                      route_id: str, 
                      time: str, 
                      day_of_week: str) -> Dict:
        """Predict demand for a specific stop, route, time, and day."""
        if 'demand' not in self.models:
            raise ValueError("Model not trained. Please train the model first.")
        
        # Create feature vector
        hour = int(time.split(':')[0])
        minute = int(time.split(':')[1])
        time_of_day = hour + minute / 60
        
        # Day encoding
        day_encoding = {
            'monday': [1, 0, 0, 0, 0, 0, 0],
            'tuesday': [0, 1, 0, 0, 0, 0, 0],
            'wednesday': [0, 0, 1, 0, 0, 0, 0],
            'thursday': [0, 0, 0, 1, 0, 0, 0],
            'friday': [0, 0, 0, 0, 1, 0, 0],
            'saturday': [0, 0, 0, 0, 0, 1, 0],
            'sunday': [0, 0, 0, 0, 0, 0, 1]
        }
        
        # Time period
        if 0 <= hour < 6:
            time_period = 'night'
        elif 6 <= hour < 9:
            time_period = 'morning_peak'
        elif 9 <= hour < 12:
            time_period = 'midday'
        elif 12 <= hour < 17:
            time_period = 'afternoon_peak'
        elif 17 <= hour < 20:
            time_period = 'evening'
        else:
            time_period = 'late_night'
        
        # Encode time_period
        le = self.label_encoders.get('time_period')
        if le:
            time_period_encoded = le.transform([time_period])[0]
        else:
            time_period_encoded = 0  # fallback if encoder missing
        
        features = np.array([
            hour, minute, time_of_day,
            time_period_encoded,
            *day_encoding[day_of_week.lower()],
            1,  # route_type_encoded (simplified)
            1,  # stop_sequence (simplified)
            5.5600,  # stop_lat (Accra coordinates)
            -0.2057   # stop_lon (Accra coordinates)
        ])
        
        # Scale features
        features_scaled = self.scalers['demand'].transform(features.reshape(1, -1))
        
        # Make prediction
        predicted_demand = self.models['demand'].predict(features_scaled)[0]
        
        return {
            'stop_id': stop_id,
            'route_id': route_id,
            'time': time,
            'day_of_week': day_of_week,
            'predicted_demand': max(1, int(predicted_demand)),
            'confidence': 0.85  # Simplified confidence score
        }
    
    def predict_network_demand(self, 
                             stops: List[str], 
                             routes: List[str], 
                             time_range: Tuple[str, str],
                             days: List[str]) -> pd.DataFrame:
        """Predict demand for multiple stops, routes, and times."""
        predictions = []
        
        start_time, end_time = time_range
        start_hour = int(start_time.split(':')[0])
        end_hour = int(end_time.split(':')[0])
        
        for day in days:
            for hour in range(start_hour, end_hour + 1):
                for minute in [0, 15, 30, 45]:  # 15-minute intervals
                    time = f"{hour:02d}:{minute:02d}:00"
                    
                    for stop_id in stops:
                        for route_id in routes:
                            pred = self.predict_demand(stop_id, route_id, time, day)
                            predictions.append(pred)
        
        return pd.DataFrame(predictions)
    
    def save_models(self, path: str = "models/"):
        """Save trained models and preprocessors."""
        os.makedirs(path, exist_ok=True)
        
        # Save models
        for name, model in self.models.items():
            joblib.dump(model, os.path.join(path, f"{name}_model.pkl"))
        
        # Save scalers
        for name, scaler in self.scalers.items():
            joblib.dump(scaler, os.path.join(path, f"{name}_scaler.pkl"))
        
        # Save label encoders
        for name, encoder in self.label_encoders.items():
            joblib.dump(encoder, os.path.join(path, f"{name}_encoder.pkl"))
        
        logger.info(f"Models saved to {path}")
    
    def load_models(self, path: str = "models/"):
        """Load trained models and preprocessors."""
        # Load models
        for name in ['demand']:
            model_path = os.path.join(path, f"{name}_model.pkl")
            if os.path.exists(model_path):
                self.models[name] = joblib.load(model_path)
        
        # Load scalers
        for name in ['demand']:
            scaler_path = os.path.join(path, f"{name}_scaler.pkl")
            if os.path.exists(scaler_path):
                self.scalers[name] = joblib.load(scaler_path)
        
        # Load label encoders
        for name in ['time_period']:
            encoder_path = os.path.join(path, f"{name}_encoder.pkl")
            if os.path.exists(encoder_path):
                self.label_encoders[name] = joblib.load(encoder_path)
        
        logger.info(f"Models loaded from {path}")

def main():
    """Main function to train demand prediction models."""
    predictor = DemandPredictor()
    
    # Load and prepare data
    df = predictor.load_gtfs_data("data/raw")
    df = predictor.engineer_features(df)
    
    # Prepare features
    X, y = predictor.prepare_features(df)
    
    # Train models
    results = predictor.train_models(X, y)
    
    # Save models
    predictor.save_models()
    
    # Example prediction
    pred = predictor.predict_demand("STOP001", "ROUTE001", "08:30:00", "monday")
    print(f"Predicted demand: {pred}")
    
    print("Demand prediction training complete!")

if __name__ == "__main__":
    main() 