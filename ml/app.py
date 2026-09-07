"""
ML Prediction Microservice
===========================

FastAPI service that loads the trained delay prediction model
and exposes a prediction endpoint.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import joblib
import json
import numpy as np
import pandas as pd
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Supply Chain ML Service",
    description="Delay prediction microservice",
    version="1.0.0"
)

# Global model and metadata
model = None
metadata = None
feature_columns = None


class PredictionRequest(BaseModel):
    """Request schema for delay prediction"""
    origin_port: str = Field(..., description="Origin port code")
    destination_port: str = Field(..., description="Destination port code")
    cargo_type: str = Field(..., description="Type of cargo")
    weight_tons: float = Field(..., description="Shipment weight in tons", gt=0)
    container_count: int = Field(..., description="Number of containers", gt=0)
    planned_transit_days: float = Field(..., description="Planned transit days", gt=0)
    booking_lead_days: float = Field(..., description="Days between booking and planned departure", ge=0)
    booking_month: int = Field(..., description="Month of booking (1-12)", ge=1, le=12)
    booking_day_of_week: int = Field(..., description="Day of week (0=Monday, 6=Sunday)", ge=0, le=6)
    origin_congestion_score: float = Field(..., description="Origin port congestion score", ge=0, le=10)
    destination_congestion_score: float = Field(..., description="Destination port congestion score", ge=0, le=10)


class PredictionResponse(BaseModel):
    """Response schema for delay prediction"""
    prediction: str = Field(..., description="Prediction: ON_TIME or DELAYED")
    probability: float = Field(..., description="Probability of predicted class")
    delay_risk_score: float = Field(..., description="Probability of delay (>24hrs late)")
    confidence: str = Field(..., description="Confidence level: LOW, MEDIUM, HIGH")
    model_version: str = Field(..., description="Model version used")


@app.on_event("startup")
async def load_model():
    """Load the trained model and metadata on startup"""
    global model, metadata, feature_columns
    
    try:
        model_path = Path("ml/delay_model.joblib")
        metadata_path = Path("ml/model_metadata.json")
        
        logger.info(f"Loading model from {model_path}")
        model = joblib.load(model_path)
        logger.info("✓ Model loaded successfully")
        
        logger.info(f"Loading metadata from {metadata_path}")
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        logger.info("✓ Metadata loaded successfully")
        
        # Extract feature columns in correct order
        feature_columns = (
            metadata['feature_columns']['categorical'] +
            metadata['feature_columns']['numeric']
        )
        logger.info(f"✓ Feature columns: {feature_columns}")
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Supply Chain ML Service",
        "status": "running",
        "model_loaded": model is not None,
        "model_version": metadata.get('model_version') if metadata else None
    }


@app.get("/health")
async def health():
    """Health check with model status"""
    if model is None or metadata is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return {
        "status": "healthy",
        "model_version": metadata.get('model_version'),
        "model_type": metadata.get('model_type'),
        "trained_at": metadata.get('trained_at_utc')
    }


@app.get("/model/info")
async def model_info():
    """Get model metadata and performance metrics"""
    if metadata is None:
        raise HTTPException(status_code=503, detail="Metadata not loaded")
    
    return {
        "model_version": metadata.get('model_version'),
        "model_type": metadata.get('model_type'),
        "trained_at": metadata.get('trained_at_utc'),
        "features": metadata.get('feature_columns'),
        "performance": metadata.get('test_set_evaluation'),
        "cross_validation": metadata.get('cross_validation')
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict_delay(request: PredictionRequest):
    """
    Predict if a shipment will be delayed (>24 hours late)
    
    Returns prediction, probability, and confidence level.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Convert request to DataFrame with column names (required for ColumnTransformer)
        data = {
            'origin_port': [request.origin_port],
            'destination_port': [request.destination_port],
            'cargo_type': [request.cargo_type],
            'weight_tons': [request.weight_tons],
            'container_count': [request.container_count],
            'planned_transit_days': [request.planned_transit_days],
            'booking_lead_days': [request.booking_lead_days],
            'booking_month': [request.booking_month],
            'booking_day_of_week': [request.booking_day_of_week],
            'origin_congestion_score': [request.origin_congestion_score],
            'destination_congestion_score': [request.destination_congestion_score]
        }
        
        X = pd.DataFrame(data)
        
        # Get prediction and probability
        prediction = model.predict(X)[0]
        probabilities = model.predict_proba(X)[0]
        
        # probability of delay (class 1)
        delay_prob = probabilities[1] if len(probabilities) > 1 else probabilities[0]
        
        # probability of predicted class
        predicted_prob = probabilities[prediction]
        
        # Determine prediction label
        prediction_label = "DELAYED" if prediction == 1 else "ON_TIME"
        
        # Determine confidence level based on probability
        if predicted_prob >= 0.7:
            confidence = "HIGH"
        elif predicted_prob >= 0.55:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        logger.info(
            f"Prediction: {prediction_label} "
            f"(prob={predicted_prob:.3f}, delay_risk={delay_prob:.3f})"
        )
        
        return PredictionResponse(
            prediction=prediction_label,
            probability=round(float(predicted_prob), 4),
            delay_risk_score=round(float(delay_prob), 4),
            confidence=confidence,
            model_version=metadata.get('model_version', 'unknown')
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
