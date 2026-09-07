"""HTTP client for Spring Boot API with response validation."""
import logging
import httpx
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError
from .config import API_BASE_URL

logger = logging.getLogger(__name__)


class ShipmentModel(BaseModel):
    """Individual shipment schema."""
    shipmentId: str
    originPort: str
    destinationPort: str
    status: str
    actualDelayHours: Optional[float]
    onTimeFlag: bool
    routeKey: str
    plannedDeparture: str
    actualArrival: Optional[str]


class ShipmentsPageResponse(BaseModel):
    """Paginated API response schema for shipments."""
    content: List[ShipmentModel]
    totalElements: int
    totalPages: int
    size: int
    number: int


class DelayPredictionResponse(BaseModel):
    """Real ML prediction response schema from ML microservice."""
    prediction: str  # "ON_TIME" or "DELAYED"
    probability: float  # 0.0 to 1.0 - confidence in predicted class
    delay_risk_score: float  # 0.0 to 1.0 - probability of delay occurring
    confidence: str  # "LOW" (<0.55), "MEDIUM" (0.55-0.70), or "HIGH" (>0.70)
    model_version: str  # Training timestamp (e.g., "20260906151259")


class PredictDelayInput(BaseModel):
    """Tool input schema for delay prediction."""
    shipment_id: str = Field(
        description="Shipment ID to predict delay risk for (e.g., 'SHP-00421'). Must exist in the database."
    )


class QueryShipmentsInput(BaseModel):
    """Input schema for query_shipments tool."""
    origin: Optional[str] = Field(
        default=None,
        description="Origin port name (e.g., 'Shanghai'). Leave empty to query all origins."
    )
    destination: Optional[str] = Field(
        default=None,
        description="Destination port name (e.g., 'Rotterdam'). Leave empty to query all destinations."
    )
    status: Optional[str] = Field(
        default=None,
        description="Shipment status filter: 'DELIVERED', 'DELAYED', 'IN_TRANSIT', or 'CANCELLED'"
    )
    from_date: Optional[str] = Field(
        default=None,
        description="Start date for filtering shipments (ISO format YYYY-MM-DD). Useful for 'this quarter', 'this month' queries."
    )
    limit: int = Field(
        default=100,
        description="Maximum number of shipments to return (1-500)"
    )
    aggregate_by_route: bool = Field(
        default=False,
        description="If true, groups results by route and calculates average delay. Use for 'highest delay routes' questions."
    )


class RouteStatsResponse(BaseModel):
    """Expected response schema from Spring Boot API."""
    origin: str
    destination: str
    routeKey: str
    shipmentCount: int
    averageDelayHours: float
    onTimeRate: float
    averageTransitDaysPlanned: float
    averageTransitDaysActual: float


def call_route_stats_api(origin: str, destination: str) -> dict:
    """
    Call Spring Boot API to get route statistics.
    
    Args:
        origin: Origin port code (e.g., CNSHA for Shanghai)
        destination: Destination port code (e.g., NLRTM for Rotterdam)
    
    Returns:
        Dictionary with summarized fields or error information
    """
    url = f"{API_BASE_URL}/routes/{origin}/{destination}/stats"
    
    logger.info(f"🌐 API Request: GET {url}")
    
    try:
        # httpx has 5s default timeout
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()  # Raise on 4xx/5xx
        
        logger.info(f"✓ API Response: {response.status_code} - {response.json()}")
        
        # Validate response schema
        validated = RouteStatsResponse.model_validate(response.json())
        
        # Return summarized fields (per D-13)
        result = {
            "on_time_rate": validated.onTimeRate,
            "avg_delay_hours": round(validated.averageDelayHours, 1),
            "shipment_count": validated.shipmentCount
        }
        logger.info(f"📊 Summarized Data: {result}")
        return result
        
    except httpx.HTTPStatusError as e:
        # API returned 4xx or 5xx
        logger.error(f"✗ API Error: {e.response.status_code}")
        return {"error": f"API error: {e.response.status_code}"}
    except httpx.TimeoutException:
        logger.error("✗ API Timeout")
        return {"error": "API timeout - please try again"}
    except ValidationError as e:
        # API response doesn't match expected schema
        logger.error(f"✗ Validation Error: {e.errors()[0]['msg']}")
        return {"error": f"Invalid API response: {e.errors()[0]['msg']}"}
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"✗ Unexpected Error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}


def call_predict_delay_api(shipment_id: str) -> dict:
    """
    Call Spring Boot API to get ML delay prediction for a shipment.
    
    Args:
        shipment_id: Shipment ID to predict delay risk for (e.g., 'SHP-00421')
    
    Returns:
        Dictionary with prediction fields or error information
    """
    url = f"{API_BASE_URL}/predict-delay/shipment/{shipment_id}"
    
    logger.info(f"🌐 API Request: POST {url}")
    
    try:
        # POST request with empty body, timeout 10 seconds
        response = httpx.post(url, timeout=10.0)
        response.raise_for_status()
        
        logger.info(f"✓ API Response: {response.status_code}")
        
        # Validate response schema
        validated = DelayPredictionResponse.model_validate(response.json())
        
        # Return prediction fields with proper mapping
        result = {
            "shipment_id": shipment_id,
            "prediction": validated.prediction,
            "risk_score": validated.delay_risk_score,  # Map from snake_case API
            "confidence": validated.confidence,
            "probability": validated.probability,
            "model_version": validated.model_version
        }
        logger.info(f"🔮 Prediction: {result}")
        return result
        
    except httpx.HTTPStatusError as e:
        # API returned 4xx or 5xx
        if e.response.status_code == 404:
            logger.error(f"✗ Shipment Not Found: {shipment_id}")
            return {"error": f"Shipment {shipment_id} not found in database"}
        else:
            logger.error(f"✗ API Error: {e.response.status_code}")
            return {"error": f"Prediction API error: {e.response.status_code}"}
    except httpx.TimeoutException:
        logger.error("✗ ML Service Timeout")
        return {"error": "ML service timeout - try again later"}
    except ValidationError as e:
        # API response doesn't match expected schema
        logger.error(f"✗ Validation Error: {e.errors()[0]['msg']}")
        return {"error": "Invalid prediction response from ML service"}
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"✗ Unexpected Error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}


def call_shipments_api(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    limit: int = 100
) -> dict:
    """
    Call Spring Boot API to query shipments.
    
    Args:
        origin: Origin port name (e.g., "Shanghai")
        destination: Destination port name (e.g., "Rotterdam")
        status: Shipment status filter
        from_date: Start date for filtering (ISO format YYYY-MM-DD)
        limit: Maximum number of shipments to return (1-500)
    
    Returns:
        Dictionary with shipments list, count, and total_available, or error information
    """
    params = {}
    
    # Uppercase port names and status for API
    if origin:
        params["origin"] = origin.upper()
    if destination:
        params["destination"] = destination.upper()
    if status:
        params["status"] = status.upper()
    
    # Convert from_date to ISO datetime format
    if from_date:
        params["fromDate"] = f"{from_date}T00:00:00"
    
    # Respect API pagination limits
    params["size"] = min(limit, 500)
    
    url = f"{API_BASE_URL}/shipments"
    
    logger.info(f"🌐 API Request: GET {url} with params {params}")
    
    try:
        # Longer timeout for aggregation queries
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        
        logger.info(f"✓ API Response: {response.status_code}")
        
        # Validate response schema
        page_response = ShipmentsPageResponse.model_validate(response.json())
        
        # Convert to dicts
        shipments = [
            {
                "shipment_id": s.shipmentId,
                "origin_port": s.originPort,
                "destination_port": s.destinationPort,
                "status": s.status,
                "actual_delay_hours": s.actualDelayHours,
                "on_time_flag": s.onTimeFlag,
                "route_key": s.routeKey,
                "planned_departure": s.plannedDeparture,
                "actual_arrival": s.actualArrival
            }
            for s in page_response.content
        ]
        
        return {
            "shipments": shipments,
            "count": len(shipments),
            "total_available": page_response.totalElements
        }
        
    except httpx.HTTPStatusError as e:
        logger.error(f"✗ API Error: {e.response.status_code}")
        return {"error": f"API error: {e.response.status_code}"}
    except httpx.TimeoutException:
        logger.error("✗ API Timeout")
        return {"error": "API timeout - please try again"}
    except ValidationError as e:
        logger.error(f"✗ Validation Error: {e.errors()[0]['msg']}")
        return {"error": f"Invalid API response: {e.errors()[0]['msg']}"}
    except Exception as e:
        logger.error(f"✗ Unexpected Error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}


def aggregate_by_route(shipments: List[dict]) -> List[dict]:
    """
    Aggregate shipments by route key and calculate statistics.
    
    Args:
        shipments: List of shipment dictionaries
    
    Returns:
        List of route statistics sorted by average delay descending
    """
    from collections import defaultdict
    
    routes = defaultdict(lambda: {
        "shipment_count": 0,
        "total_delay": 0.0,
        "on_time_count": 0,
        "origin": None,
        "destination": None
    })
    
    # Accumulate statistics per route
    for shipment in shipments:
        route_key = shipment["route_key"]
        routes[route_key]["shipment_count"] += 1
        routes[route_key]["total_delay"] += shipment.get("actual_delay_hours", 0.0) or 0.0
        if shipment.get("on_time_flag"):
            routes[route_key]["on_time_count"] += 1
        routes[route_key]["origin"] = shipment["origin_port"]
        routes[route_key]["destination"] = shipment["destination_port"]
    
    # Calculate averages
    result = []
    for route_key, stats in routes.items():
        avg_delay = stats["total_delay"] / stats["shipment_count"]
        on_time_rate = (stats["on_time_count"] / stats["shipment_count"]) * 100
        result.append({
            "route": route_key,
            "origin": stats["origin"],
            "destination": stats["destination"],
            "shipment_count": stats["shipment_count"],
            "avg_delay_hours": round(avg_delay, 1),
            "on_time_rate": round(on_time_rate, 1)
        })
    
    # Sort by average delay descending (highest delays first)
    result.sort(key=lambda x: x["avg_delay_hours"], reverse=True)
    
    return result
