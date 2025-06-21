#!/usr/bin/env python3

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import yaml
import mlflow
import pandas as pd
import numpy as np
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
with open("configs/config.yaml") as f:
    config = yaml.safe_load(f)

def test_model_input_formats():
    """Test different input formats to see what the model expects"""
    try:
        # Set tracking URI
        tracking_uri = config["mlflow"]["tracking_uri"]
        logger.info(f"Setting MLflow tracking URI: {tracking_uri}")
        mlflow.set_tracking_uri(tracking_uri)
        
        # Get the model name
        model_name = config["model"]["name"]
        logger.info(f"Model name: {model_name}")
        
        # Load the model
        logger.info("Loading model from Production stage...")
        model = mlflow.pyfunc.load_model(f"models:/{model_name}/Production")
        logger.info(f"Model loaded successfully")
        
        logger.info("Testing different input formats...")
        
        # Test 1: Numpy array with exactly 4 features
        logger.info("Test 1: Numpy array with 4 numerical features")
        try:
            # Try different combinations of 4 features
            test_arrays = [
                np.array([[5.2, 25.0, 15.0, 1.0]]),  # distance, speed, passenger_count, route_encoded
                np.array([[5.2, 25.0, 15.0, 0.0]]),  # distance, speed, passenger_count, direction_encoded
                np.array([[5.2, 25.0, 15.0, 8.0]]),  # distance, speed, passenger_count, hour
                np.array([[5.2, 25.0, 15.0, 2.0]]),  # distance, speed, passenger_count, day_of_week
            ]
            
            for i, arr in enumerate(test_arrays):
                try:
                    result = model.predict(arr)
                    logger.info(f"✅ Numpy array {i+1} works! Result: {result}")
                    logger.info(f"   Features used: {arr[0]}")
                    return f"numpy_array_{i+1}"
                except Exception as e:
                    logger.error(f"❌ Numpy array {i+1} failed: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Numpy array test failed: {str(e)}")
        
        # Test 2: DataFrame with numerical features only
        logger.info("Test 2: DataFrame with numerical features only")
        try:
            # Try different numerical feature combinations
            numerical_features = [
                ["distance", "speed", "passenger_count", "hour"],
                ["distance", "speed", "passenger_count", "day_of_week"],
                ["distance", "speed", "passenger_count", "route_encoded"],
                ["distance", "speed", "passenger_count", "stop_encoded"]
            ]
            
            for i, features in enumerate(numerical_features):
                try:
                    # Create sample data
                    data = {
                        "distance": [5.2],
                        "speed": [25.0],
                        "passenger_count": [15.0],
                        "hour": [8.0],
                        "day_of_week": [1.0],
                        "route_encoded": [1.0],
                        "stop_encoded": [1.0]
                    }
                    
                    df = pd.DataFrame(data)
                    df_subset = df[features]
                    result = model.predict(df_subset)
                    logger.info(f"✅ DataFrame {i+1} works! Result: {result}")
                    logger.info(f"   Features used: {features}")
                    return f"dataframe_{i+1}"
                except Exception as e:
                    logger.error(f"❌ DataFrame {i+1} failed: {str(e)}")
        except Exception as e:
            logger.error(f"❌ DataFrame test failed: {str(e)}")
        
        # Test 3: Try with the original model's predict method directly
        logger.info("Test 3: Direct model predict method")
        try:
            # Get the underlying model
            if hasattr(model, '_model_impl'):
                underlying_model = model._model_impl
                logger.info(f"Underlying model type: {type(underlying_model)}")
                
                # Try to call predict directly
                test_input = np.array([[5.2, 25.0, 15.0, 1.0]], dtype=np.float32)
                result = underlying_model.predict(test_input)
                logger.info(f"✅ Direct model predict works! Result: {result}")
                return "direct_model_predict"
        except Exception as e:
            logger.error(f"❌ Direct model predict failed: {str(e)}")
        
        # Test 4: Try with different data types
        logger.info("Test 4: Different data types")
        try:
            test_inputs = [
                np.array([[5.2, 25.0, 15.0, 1.0]], dtype=np.float32),
                np.array([[5.2, 25.0, 15.0, 1.0]], dtype=np.float64),
                np.array([[5.2, 25.0, 15.0, 1.0]], dtype=np.int32),
            ]
            
            for i, test_input in enumerate(test_inputs):
                try:
                    result = model.predict(test_input)
                    logger.info(f"✅ Data type {i+1} works! Result: {result}")
                    logger.info(f"   Data type: {test_input.dtype}")
                    return f"data_type_{i+1}"
                except Exception as e:
                    logger.error(f"❌ Data type {i+1} failed: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Data type test failed: {str(e)}")
        
        logger.error("❌ None of the input formats worked!")
        return None
            
    except Exception as e:
        logger.error(f"Error in model input test: {str(e)}")
        return None

def examine_model_info():
    """Examine the model to understand its structure"""
    try:
        tracking_uri = config["mlflow"]["tracking_uri"]
        mlflow.set_tracking_uri(tracking_uri)
        model_name = config["model"]["name"]
        
        model = mlflow.pyfunc.load_model(f"models:/{model_name}/Production")
        
        logger.info("=== Model Information ===")
        logger.info(f"Model type: {type(model)}")
        
        # Try to get model signature
        try:
            signature = model.metadata.signature
            logger.info(f"Model signature: {signature}")
            if signature:
                logger.info(f"Input schema: {signature.inputs}")
                logger.info(f"Output schema: {signature.outputs}")
        except Exception as e:
            logger.info(f"Could not get model signature: {e}")
        
        # Try to get the underlying model
        try:
            if hasattr(model, '_model_impl'):
                underlying_model = model._model_impl
                logger.info(f"Underlying model type: {type(underlying_model)}")
                
                # If it's a TensorFlow model, get more info
                if hasattr(underlying_model, 'summary'):
                    logger.info("Model summary:")
                    underlying_model.summary()
                
                if hasattr(underlying_model, 'input_shape'):
                    logger.info(f"Input shape: {underlying_model.input_shape}")
                
                if hasattr(underlying_model, 'output_shape'):
                    logger.info(f"Output shape: {underlying_model.output_shape}")
        except Exception as e:
            logger.info(f"Could not examine underlying model: {e}")
        
    except Exception as e:
        logger.error(f"Error examining model: {str(e)}")

if __name__ == "__main__":
    logger.info("=== Model Input Format Investigation ===")
    
    # First examine the model
    examine_model_info()
    
    # Then test different input formats
    working_format = test_model_input_formats()
    
    if working_format:
        print(f"\n✅ SUCCESS: Model expects {working_format} format")
    else:
        print(f"\n❌ FAILED: Could not determine working input format") 