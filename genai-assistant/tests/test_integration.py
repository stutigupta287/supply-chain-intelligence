"""Integration tests for end-to-end flow."""
import pytest
from unittest.mock import patch, Mock


def test_route_on_time_rate_question(mock_api_response):
    """Test end-to-end flow: tool execution → API → response."""
    from src.assistant.tools import get_route_stats
    
    # Mock the API client
    with patch('src.assistant.api_client.httpx.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Execute tool directly (simulating what LLM would do)
        tool_result = get_route_stats.invoke({"origin": "CNSHA", "destination": "NLRTM"})
        
        # Verify tool result
        assert "on_time_rate" in tool_result
        assert "avg_delay_hours" in tool_result
        assert "shipment_count" in tool_result
        assert tool_result["on_time_rate"] == 75.0
        assert tool_result["shipment_count"] == 12
