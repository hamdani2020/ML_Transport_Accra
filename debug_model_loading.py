#!/usr/bin/env python3

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import yaml
import mlflow
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
with open("configs/config.yaml") as f:
    config = yaml.safe_load(f)

def test_model_loading():
    """Test the model loading logic"""
    try:
        # Set tracking URI
        tracking_uri = config["mlflow"]["tracking_uri"]
        logger.info(f"Setting MLflow tracking URI: {tracking_uri}")
        mlflow.set_tracking_uri(tracking_uri)
        
        # Get the model name
        model_name = config["model"]["name"]
        logger.info(f"Model name: {model_name}")
        
        # Try to load the model directly
        try:
            logger.info("Attempting to load model from Production stage...")
            model = mlflow.pyfunc.load_model(f"models:/{model_name}/Production")
            logger.info(f"Successfully loaded model from Production stage")
            logger.info(f"Model type: {type(model)}")
            logger.info(f"Model attributes: {dir(model)}")
            return True
        except Exception as e:
            logger.error(f"Failed to load from Production stage: {str(e)}")
            
            # Try to load the latest version
            try:
                logger.info("Attempting to load latest version...")
                model = mlflow.pyfunc.load_model(f"models:/{model_name}/latest")
                logger.info(f"Successfully loaded latest model version")
                logger.info(f"Model type: {type(model)}")
                logger.info(f"Model attributes: {dir(model)}")
                return True
            except Exception as e2:
                logger.error(f"Failed to load latest version: {str(e2)}")
                
                # Try to load by version number
                try:
                    logger.info("Attempting to load version 1...")
                    model = mlflow.pyfunc.load_model(f"models:/{model_name}/1")
                    logger.info(f"Successfully loaded model version 1")
                    logger.info(f"Model type: {type(model)}")
                    logger.info(f"Model attributes: {dir(model)}")
                    return True
                except Exception as e3:
                    logger.error(f"Failed to load version 1: {str(e3)}")
                    return False
            
    except Exception as e:
        logger.error(f"Error in model loading test: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_model_loading()
    if success:
        print("✅ Model loading test passed")
    else:
        print("❌ Model loading test failed") 