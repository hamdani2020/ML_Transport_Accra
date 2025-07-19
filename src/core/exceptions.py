"""
Custom exceptions for the transport optimization system.
"""


class TransportOptimizationError(Exception):
    """Base exception for transport optimization errors."""
    pass


class DataLoadError(TransportOptimizationError):
    """Raised when data loading fails."""
    pass


class ModelTrainingError(TransportOptimizationError):
    """Raised when model training fails."""
    pass


class OptimizationError(TransportOptimizationError):
    """Raised when optimization fails."""
    pass


class ConfigurationError(TransportOptimizationError):
    """Raised when configuration is invalid."""
    pass


class ValidationError(TransportOptimizationError):
    """Raised when data validation fails."""
    pass 