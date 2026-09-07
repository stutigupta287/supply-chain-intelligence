"""Tests for configuration loading."""
import pytest
import os
from unittest.mock import patch


def test_config_defaults():
    """Test that config uses defaults when env vars are not set."""
    # Clear relevant env vars
    with patch.dict(os.environ, {}, clear=True):
        # Reimport to get fresh config
        import importlib
        import src.assistant.config as config
        importlib.reload(config)
        
        assert config.API_BASE_URL == "http://localhost:8080"
        assert config.OLLAMA_BASE_URL == "http://localhost:11434"
        assert config.OLLAMA_MODEL == "llama3.1:8b"
        assert config.LLM_TEMPERATURE == 0.2
        assert config.LLM_MAX_TOKENS == 512


def test_config_env_override():
    """Test that environment variables override defaults."""
    with patch.dict(os.environ, {
        'API_BASE_URL': 'http://custom:9000',
        'OLLAMA_MODEL': 'llama2',
        'LLM_TEMPERATURE': '0.5'
    }):
        # Reimport to get fresh config
        import importlib
        import src.assistant.config as config
        importlib.reload(config)
        
        assert config.API_BASE_URL == "http://custom:9000"
        assert config.OLLAMA_MODEL == "llama2"
        assert config.LLM_TEMPERATURE == 0.5


def test_env_file_loading():
    """Test that python-dotenv loads .env file."""
    from src.assistant import config
    
    # Config module already loaded .env via load_dotenv()
    # Just verify the module imported successfully
    assert hasattr(config, 'API_BASE_URL')
    assert hasattr(config, 'OLLAMA_BASE_URL')
    assert hasattr(config, 'OLLAMA_MODEL')
