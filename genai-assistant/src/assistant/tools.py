"""Tool definitions for LangChain with Pydantic schemas."""
import logging
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from . import api_client
from .api_client import (
    call_route_stats_api,
    call_shipments_api,
    aggregate_by_route,
    QueryShipmentsInput,
    PredictDelayInput,
    call_predict_delay_api
)

logger = logging.getLogger(__name__)


class RouteStatsInput(BaseModel):
    """Input schema for get_route_stats tool."""
    origin: str = Field(
        description="Origin port code in UN/LOCODE format (e.g., CNSHA for Shanghai)"
    )
    destination: str = Field(
        description="Destination port code in UN/LOCODE format (e.g., NLRTM for Rotterdam)"
    )


@tool(args_schema=RouteStatsInput)
def get_route_stats(origin: str, destination: str) -> dict:
    """Get on-time rate and average delay for a specific route.
    
    Returns shipment count, on-time percentage, and average delay hours
    for shipments between the specified origin and destination ports.
    
    Args:
        origin: Origin port code (e.g., CNSHA for Shanghai)
        destination: Destination port code (e.g., NLRTM for Rotterdam)
    
    Returns:
        Dictionary with on_time_rate (percentage), avg_delay_hours, and shipment_count,
        or error information if the API call fails
    """
    logger.info(f"🔧 Tool Called: get_route_stats(origin='{origin}', destination='{destination}')")
    return call_route_stats_api(origin, destination)


@tool(args_schema=QueryShipmentsInput)
def query_shipments(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    limit: int = 100,
    aggregate_by_route: bool = False
) -> dict:
    """Query shipments from the API with filtering and optional aggregation.
    
    This tool queries shipments with flexible filters and can aggregate results by route.
    Use aggregate_by_route=True for questions about "highest delay routes" or 
    "worst performing routes" - it will group shipments by route and calculate average delays.
    
    Args:
        origin: Origin port name (e.g., 'Shanghai')
        destination: Destination port name (e.g., 'Rotterdam')
        status: Shipment status filter ('DELIVERED', 'DELAYED', 'IN_TRANSIT', 'CANCELLED')
        from_date: Start date for filtering (ISO format YYYY-MM-DD)
        limit: Maximum number of shipments to return (1-500)
        aggregate_by_route: If True, groups by route and calculates average delay
    
    Returns:
        Dictionary with either individual shipments or aggregated route statistics,
        or error information if the API call fails
    """
    logger.info(
        f"🔧 Tool Called: query_shipments(origin={origin}, destination={destination}, "
        f"status={status}, from_date={from_date}, limit={limit}, aggregate_by_route={aggregate_by_route})"
    )
    
    # Call API
    result = api_client.call_shipments_api(origin, destination, status, from_date, limit)
    
    # Check for errors
    if "error" in result:
        return result
    
    # Return raw shipments if no aggregation requested
    if not aggregate_by_route:
        return result
    
    # Aggregate by route
    shipments = result["shipments"]
    routes = api_client.aggregate_by_route(shipments)
    
    return {
        "routes": routes,
        "count": len(routes),
        "aggregation": "by_route"
    }


@tool(args_schema=PredictDelayInput)
def predict_delay(shipment_id: str) -> dict:
    """Predict delay risk (>24 hours late) for a shipment using the real machine learning model.
    
    This tool uses a trained ML model to predict whether a shipment will be delayed (>24 hours late)
    based on booking-time features. Use this when asked about FUTURE delay risk or prediction for
    a specific shipment.
    
    Returns prediction (ON_TIME or DELAYED), probability (confidence in prediction 0.0-1.0),
    risk_score (probability of delay 0.0-1.0), confidence level (LOW/MEDIUM/HIGH based on 
    thresholds <0.55, 0.55-0.70, >0.70), and model_version (training timestamp).
    
    The shipment must exist in the database.
    
    Args:
        shipment_id: Shipment ID to predict delay risk for (e.g., 'SHP-00421')
    
    Returns:
        Dictionary with prediction fields (prediction, risk_score, confidence, probability, 
        model_version) or error information if the API call fails
    """
    logger.info(f"🔧 Tool Called: predict_delay(shipment_id={shipment_id})")
    return api_client.call_predict_delay_api(shipment_id)
