"""
Data management for GTFS data loading and preprocessing.
"""

import os
import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .exceptions import DataLoadError, ValidationError
from .config import Config


logger = logging.getLogger(__name__)


class DataManager:
    """Manages GTFS data loading and preprocessing."""
    
    def __init__(self, config: Config):
        """Initialize data manager with configuration."""
        self.config = config
        self._data_cache = {}
        
    def load_gtfs_data(self, data_path: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """Load all GTFS files from the specified path."""
        if data_path is None:
            data_path = self.config.data_paths['raw_dir']
            
        logger.info(f"Loading GTFS data from {data_path}")
        
        required_files = self.config.get('gtfs.required_files', [
            'agency.txt', 'routes.txt', 'stops.txt', 'trips.txt', 
            'stop_times.txt', 'calendar.txt'
        ])
        
        optional_files = self.config.get('gtfs.optional_files', [
            'shapes.txt', 'fare_attributes.txt', 'fare_rules.txt'
        ])
        
        data = {}
        
        # Load required files
        for filename in required_files:
            file_path = os.path.join(data_path, filename)
            if not os.path.exists(file_path):
                raise DataLoadError(f"Required GTFS file not found: {filename}")
            
            try:
                data[filename.replace('.txt', '')] = pd.read_csv(file_path)
                logger.info(f"Loaded {filename}: {len(data[filename.replace('.txt', '')])} records")
            except Exception as e:
                raise DataLoadError(f"Failed to load {filename}: {str(e)}")
        
        # Load optional files
        for filename in optional_files:
            file_path = os.path.join(data_path, filename)
            if os.path.exists(file_path):
                try:
                    data[filename.replace('.txt', '')] = pd.read_csv(file_path)
                    logger.info(f"Loaded {filename}: {len(data[filename.replace('.txt', '')])} records")
                except Exception as e:
                    logger.warning(f"Failed to load optional file {filename}: {str(e)}")
        
        self._data_cache = data
        return data
    
    def validate_gtfs_data(self, data: Dict[str, pd.DataFrame]) -> bool:
        """Validate GTFS data integrity."""
        logger.info("Validating GTFS data")
        
        # Check for required files
        required_files = ['agency', 'routes', 'stops', 'trips', 'stop_times', 'calendar']
        for file_key in required_files:
            if file_key not in data:
                raise ValidationError(f"Missing required GTFS file: {file_key}")
        
        # Validate relationships
        try:
            # Check route_id consistency
            routes_ids = set(data['routes']['route_id'])
            trips_route_ids = set(data['trips']['route_id'])
            if not trips_route_ids.issubset(routes_ids):
                raise ValidationError("Some trips reference non-existent routes")
            
            # Check stop_id consistency
            stops_ids = set(data['stops']['stop_id'])
            stop_times_stop_ids = set(data['stop_times']['stop_id'])
            if not stop_times_stop_ids.issubset(stops_ids):
                raise ValidationError("Some stop_times reference non-existent stops")
            
            # Check trip_id consistency
            trips_ids = set(data['trips']['trip_id'])
            stop_times_trip_ids = set(data['stop_times']['trip_id'])
            if not stop_times_trip_ids.issubset(trips_ids):
                raise ValidationError("Some stop_times reference non-existent trips")
            
            logger.info("GTFS data validation passed")
            return True
            
        except Exception as e:
            raise ValidationError(f"GTFS data validation failed: {str(e)}")
    
    def merge_gtfs_data(self, data: Optional[Dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
        """Merge GTFS data into a comprehensive dataset."""
        if data is None:
            data = self._data_cache
            
        if not data:
            raise DataLoadError("No GTFS data loaded. Call load_gtfs_data() first.")
        
        logger.info("Merging GTFS data")
        
        # Start with trips and merge with routes
        merged = data['trips'].merge(
            data['routes'], on='route_id', how='left', suffixes=('', '_route')
        )
        
        # Merge with agency
        merged = merged.merge(
            data['agency'], on='agency_id', how='left', suffixes=('', '_agency')
        )
        
        # Merge with calendar
        merged = merged.merge(
            data['calendar'], on='service_id', how='left', suffixes=('', '_calendar')
        )
        
        # Add stop information
        stop_times_with_info = data['stop_times'].merge(
            data['stops'], on='stop_id', how='left', suffixes=('', '_stop')
        )
        
        # Merge with trips
        stop_times_with_info = stop_times_with_info.merge(
            merged, on='trip_id', how='left', suffixes=('', '_trip')
        )
        
        logger.info(f"Merged dataset shape: {stop_times_with_info.shape}")
        return stop_times_with_info
    
    def get_route_stops(self, data: Optional[Dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
        """Get route-stop mapping for optimization."""
        if data is None:
            data = self._data_cache
            
        if not data:
            raise DataLoadError("No GTFS data loaded. Call load_gtfs_data() first.")
        
        # Create route-stop mapping
        route_stops = data['stop_times'].merge(
            data['trips'][['trip_id', 'route_id']], on='trip_id'
        )
        route_stops = route_stops.merge(
            data['stops'][['stop_id', 'stop_name', 'stop_lat', 'stop_lon']], on='stop_id'
        )
        
        # Get unique stops per route
        route_stop_sequences = route_stops.groupby('route_id').agg({
            'stop_id': list,
            'stop_name': list,
            'stop_lat': list,
            'stop_lon': list
        }).reset_index()
        
        return route_stop_sequences
    
    def save_processed_data(self, data: pd.DataFrame, filename: str):
        """Save processed data to the processed directory."""
        output_path = self.config.data_paths['processed_dir'] / filename
        data.to_csv(output_path, index=False)
        logger.info(f"Saved processed data to {output_path}")
    
    def load_processed_data(self, filename: str) -> pd.DataFrame:
        """Load processed data from the processed directory."""
        input_path = self.config.data_paths['processed_dir'] / filename
        if not input_path.exists():
            raise DataLoadError(f"Processed data file not found: {filename}")
        
        return pd.read_csv(input_path) 