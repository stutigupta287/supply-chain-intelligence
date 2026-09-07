"""Tests for CLI functionality."""
import pytest
from unittest.mock import patch, Mock
from io import StringIO


def test_welcome_message():
    """Test that CLI displays welcome message with examples."""
    from src.assistant.cli import run_repl
    
    with patch('builtins.input', side_effect=['exit']), \
         patch('sys.stdout', new=StringIO()) as fake_out:
        
        try:
            run_repl()
        except SystemExit:
            pass
        
        output = fake_out.getvalue()
        assert "Supply Chain GenAI Assistant" in output
        assert "on-time rate" in output.lower()
        assert "exit" in output.lower() or "quit" in output.lower()
        assert "help" in output.lower()


def test_repl_exit_command():
    """Test that 'exit' command terminates the loop."""
    from src.assistant.cli import run_repl
    
    with patch('builtins.input', return_value='exit'), \
         patch('sys.stdout', new=StringIO()):
        
        # Should complete without exception
        run_repl()


def test_repl_help_command():
    """Test that 'help' command displays help text."""
    from src.assistant.cli import run_repl
    
    with patch('builtins.input', side_effect=['help', 'exit']), \
         patch('sys.stdout', new=StringIO()) as fake_out:
        
        run_repl()
        
        output = fake_out.getvalue()
        assert "supply chain" in output.lower() or "routes" in output.lower()
