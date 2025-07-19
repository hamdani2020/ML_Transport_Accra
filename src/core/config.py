"""
Configuration management for the transport optimization system.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """Centralized configuration management."""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        """Initialize configuration from YAML file."""
        self.config_path = config_path
        self._config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def get_path(self, key: str) -> Path:
        """Get configuration path and ensure it exists."""
        path_str = self.get(key)
        if not path_str:
            raise ValueError(f"Path configuration not found: {key}")
            
        path = Path(path_str)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def reload(self):
        """Reload configuration from file."""
        self._config = self._load_config()
    
    @property
    def data_paths(self) -> Dict[str, Path]:
        """Get data-related paths."""
        return {
            'raw_dir': self.get_path('data.raw_dir'),
            'processed_dir': self.get_path('data.processed_dir'),
            'models_dir': self.get_path('data.models_dir'),
        }
    
    @property
    def model_config(self) -> Dict[str, Any]:
        """Get model configuration."""
        return self.get('model', {})
    
    @property
    def api_config(self) -> Dict[str, Any]:
        """Get API configuration."""
        return self.get('api', {})
    
    @property
    def mlflow_config(self) -> Dict[str, Any]:
        """Get MLflow configuration."""
        return self.get('mlflow', {}) 