"""Tests for tool implementations."""
import pytest
from unittest.mock import patch, Mock
import httpx
from pydantic import ValidationError


def test_get_route_stats_success(mock_api_response):
    """Test get_route_stats with valid API response."""
    from src.assistant.tools import get_route_stats
    
    with patch('src.assistant.api_client.httpx.get') as mock_get:
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = get_route_stats.invoke({"origin": "CNSHA", "destination": "NLRTM"})
        
        assert "on_time_rate" in result
        assert "avg_delay_hours" in result
        assert "shipment_count" in result
        assert result["on_time_rate"] == 75.0
        assert result["avg_delay_hours"] == 22.8
        assert result["shipment_count"] == 12


def test_get_route_stats_http_error():
    """Test get_route_stats with HTTP 500 error."""
    from src.assistant.tools import get_route_stats
    
    with patch('src.assistant.api_client.httpx.get') as mock_get:
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )
        mock_get.return_value = mock_response
        
        result = get_route_stats.invoke({"origin": "CNSHA", "destination": "NLRTM"})
        
        assert "error" in result
        assert "API error" in result["error"]


def test_get_route_stats_timeout():
    """Test get_route_stats with timeout."""
    from src.assistant.tools import get_route_stats
    
    with patch('src.assistant.api_client.httpx.get') as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Request timed out")
        
        result = get_route_stats.invoke({"origin": "CNSHA", "destination": "NLRTM"})
        
        assert "error" in result
        assert "timeout" in result["error"].lower()


def test_get_route_stats_validation_error():
    """Test get_route_stats with invalid API response schema."""
    from src.assistant.tools import get_route_stats
    
    with patch('src.assistant.api_client.httpx.get') as mock_get:
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        # Missing required fields
        mock_response.json.return_value = {"invalid": "response"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = get_route_stats.invoke({"origin": "CNSHA", "destination": "NLRTM"})
        
        assert "error" in result
        assert "Invalid API response" in result["error"]


def test_predict_delay_success(mocker):
    """Test predict_delay with successful real ML prediction."""
    from src.assistant.tools import predict_delay
    from tests.conftest import mock_prediction_response
    
    with patch('src.assistant.api_client.httpx.post') as mock_post:
        mock_post.return_value = mock_prediction_response(
            prediction="DELAYED",
            probability=0.85,
            confidence="HIGH"
        )
        
        result = predict_delay.invoke({"shipment_id": "SHP-00421"})
        
        assert result["prediction"] == "DELAYED"
        assert result["risk_score"] == 0.85  # Mapped from delay_risk_score
        assert result["confidence"] == "HIGH"
        assert result["probability"] == 0.85
        assert result["model_version"] == "20260906151259"


def test_predict_delay_on_time(mocker):
    """Test predict_delay with ON_TIME prediction."""
    from src.assistant.tools import predict_delay
    from tests.conftest import mock_prediction_response
    
    with patch('src.assistant.api_client.httpx.post') as mock_post:
        mock_post.return_value = mock_prediction_response(
            prediction="ON_TIME",
            probability=0.65,
            confidence="MEDIUM"
        )
        
        result = predict_delay.invoke({"shipment_id": "SHP-12345"})
        
        assert result["prediction"] == "ON_TIME"
        assert result["confidence"] == "MEDIUM"


def test_predict_delay_shipment_not_found(mocker):
    """Test predict_delay with 404 error."""
    from src.assistant.tools import predict_delay
    
    with patch('src.assistant.api_client.httpx.post') as mock_post:
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )
        
        result = predict_delay.invoke({"shipment_id": "INVALID"})
        
        assert "error" in result
        assert "not found" in result["error"].lower()


def test_predict_delay_timeout(mocker):
    """Test predict_delay with timeout error."""
    from src.assistant.tools import predict_delay
    
    with patch('src.assistant.api_client.httpx.post') as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Request timed out")
        
        result = predict_delay.invoke({"shipment_id": "SHP-00421"})
        
        assert "error" in result
        assert "timeout" in result["error"].lower()


def test_query_shipments_success(mock_shipments_response):
    """Test query_shipments with valid API response."""
    from src.assistant.tools import query_shipments
    
    with patch('src.assistant.api_client.httpx.get') as mock_get:
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_shipments_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = query_shipments.invoke({"origin": "Shanghai", "limit": 50})
        
        assert result["count"] == 3
        assert "shipments" in result
        assert result["shipments"][0]["shipment_id"] == "SHP-00001"
        assert result["total_available"] == 3


def test_query_shipments_with_aggregation(mock_shipments_response):
    """Test query_shipments with route aggregation."""
    from src.assistant.tools import query_shipments
    
    with patch('src.assistant.api_client.httpx.get') as mock_get:
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_shipments_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = query_shipments.invoke({"aggregate_by_route": True})
        
        assert "routes" in result
        assert result["aggregation"] == "by_route"
        assert result["count"] == 2  # Two distinct routes
        # Highest delay route should be first (SHANGHAI → ROTTERDAM with avg 8.5)
        assert result["routes"][0]["route"] == "SHANGHAI → ROTTERDAM"
        assert result["routes"][0]["avg_delay_hours"] == 8.5  # (5.0 + 12.0) / 2


def test_query_shipments_empty_results(mock_empty_shipments_response):
    """Test query_shipments with empty results."""
    from src.assistant.tools import query_shipments
    
    with patch('src.assistant.api_client.httpx.get') as mock_get:
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_empty_shipments_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = query_shipments.invoke({"origin": "UNKNOWN"})
        
        assert result["count"] == 0
        assert result["shipments"] == []


def test_query_shipments_timeout():
    """Test query_shipments with timeout."""
    from src.assistant.tools import query_shipments
    
    with patch('src.assistant.api_client.httpx.get') as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Request timed out")
        
        result = query_shipments.invoke({"origin": "Shanghai"})
        
        assert "error" in result
        assert "timeout" in result["error"].lower()


def test_query_shipments_http_error():
    """Test query_shipments with HTTP error."""
    from src.assistant.tools import query_shipments
    
    with patch('src.assistant.api_client.httpx.get') as mock_get:
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )
        mock_get.return_value = mock_response
        
        result = query_shipments.invoke({"origin": "Shanghai"})
        
        assert "error" in result
        assert "500" in result["error"]


def test_query_shipments_validation_error():
    """Test query_shipments with invalid API response."""
    from src.assistant.tools import query_shipments
    
    with patch('src.assistant.api_client.httpx.get') as mock_get:
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        # Missing required fields
        mock_response.json.return_value = {"invalid": "response"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = query_shipments.invoke({"origin": "Shanghai"})
        
        assert "error" in result
        assert "invalid" in result["error"].lower()
