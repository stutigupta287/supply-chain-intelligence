"""Pytest fixtures for GenAI assistant tests."""
import pytest
from unittest.mock import Mock
import httpx


@pytest.fixture
def mock_api_response():
    """Valid RouteStatsResponse JSON from API."""
    return {
        "origin": "CNSHA",
        "destination": "NLRTM",
        "routeKey": "CNSHA → NLRTM",
        "shipmentCount": 12,
        "averageDelayHours": 22.833333333333332,
        "onTimeRate": 75.0,
        "averageTransitDaysPlanned": 24.916666666666668,
        "averageTransitDaysActual": 25.555555555555557
    }


@pytest.fixture
def mock_api_error_response():
    """Mock HTTP 500 error response."""
    response = Mock(spec=httpx.Response)
    response.status_code = 500
    response.json.return_value = {"error": "Internal server error"}
    return response


@pytest.fixture
def mock_api_timeout():
    """Mock timeout exception."""
    return httpx.TimeoutException("Request timed out")


@pytest.fixture
def mock_llm_tool_call():
    """Mocked LangChain response with tool_calls."""
    response = Mock()
    response.tool_calls = [
        {
            "name": "get_route_stats",
            "args": {"origin": "CNSHA", "destination": "NLRTM"},
            "id": "call_123"
        }
    ]
    response.content = ""
    return response


def mock_prediction_response(
    prediction: str = "DELAYED",
    probability: float = 0.85,
    confidence: str = "HIGH",
    model_version: str = "20260906151259"
):
    """Mock ML prediction API response (helper function, not a fixture)."""
    response = Mock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {
        "prediction": prediction,
        "probability": probability,
        "delay_risk_score": probability,  # API uses snake_case
        "confidence": confidence,
        "model_version": model_version
    }
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def mock_shipments_response():
    """Valid ShipmentsPageResponse JSON from API with 3 sample shipments."""
    return {
        "content": [
            {
                "shipmentId": "SHP-00001",
                "originPort": "SHANGHAI",
                "destinationPort": "ROTTERDAM",
                "status": "DELIVERED",
                "actualDelayHours": 5.0,
                "onTimeFlag": True,
                "routeKey": "SHANGHAI → ROTTERDAM",
                "plannedDeparture": "2024-01-01T10:00:00",
                "actualArrival": "2024-01-20T15:00:00"
            },
            {
                "shipmentId": "SHP-00002",
                "originPort": "SHANGHAI",
                "destinationPort": "ROTTERDAM",
                "status": "DELAYED",
                "actualDelayHours": 12.0,
                "onTimeFlag": False,
                "routeKey": "SHANGHAI → ROTTERDAM",
                "plannedDeparture": "2024-01-02T10:00:00",
                "actualArrival": "2024-01-22T22:00:00"
            },
            {
                "shipmentId": "SHP-00003",
                "originPort": "SINGAPORE",
                "destinationPort": "HAMBURG",
                "status": "DELIVERED",
                "actualDelayHours": 3.0,
                "onTimeFlag": True,
                "routeKey": "SINGAPORE → HAMBURG",
                "plannedDeparture": "2024-01-03T10:00:00",
                "actualArrival": "2024-01-18T13:00:00"
            }
        ],
        "totalElements": 3,
        "totalPages": 1,
        "size": 20,
        "number": 0
    }


@pytest.fixture
def mock_empty_shipments_response():
    """Valid ShipmentsPageResponse with empty content."""
    return {
        "content": [],
        "totalElements": 0,
        "totalPages": 0,
        "size": 20,
        "number": 0
    }
