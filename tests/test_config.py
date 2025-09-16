#!/usr/bin/env python3
"""
GitLab Protector Configuration Tests

Copyright (c) 2025 Michele Tavella <meeghele@proton.me>
Licensed under the MIT License.

Author: Michele Tavella <meeghele@proton.me>
"""

import os
import sys
import tempfile
from unittest.mock import patch, Mock
import pytest
import yaml

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module under test
import importlib.util
spec = importlib.util.spec_from_file_location("gitlab_protector", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gitlab-protector.py"))
gp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gp)


class TestConfig:
    """Test configuration management."""
    
    def test_config_creation(self):
        """Test Config dataclass creation."""
        config = gp.Config(
            url='https://gitlab.example.com',
            token='test-token',
            namespace='test-namespace',
            config_file='protection.yml',
            dry_run=False,
            exclude='proj1',
            stop_on_error=True
        )
        
        assert config.url == 'https://gitlab.example.com'
        assert config.token == 'test-token'
        assert config.namespace == 'test-namespace'
        assert config.config_file == 'protection.yml'
        assert config.dry_run is False
        assert config.exclude == 'proj1'
        assert config.stop_on_error is True
    
    def test_config_defaults(self):
        """Test Config with default values."""
        config = gp.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-namespace',
            config_file='protection.yml',
            dry_run=False,
            exclude=None,
            stop_on_error=False
        )
        
        assert config.exclude is None
        assert config.stop_on_error is False
        assert config.dry_run is False


class TestProtectionConfig:
    """Test ProtectionConfig dataclass."""
    
    def test_protection_config_creation(self):
        """Test ProtectionConfig dataclass creation."""
        tags = [{'name': 'v*', 'create_access_level': 'maintainer'}]
        branches = [{'name': 'main', 'push_access_level': 'maintainer'}]
        
        config = gp.ProtectionConfig(
            tags=tags,
            branches=branches
        )
        
        assert config.tags == tags
        assert config.branches == branches


class TestArgumentParsing:
    """Test command-line argument parsing."""
    
    def test_parse_args_minimal(self):
        """Test parsing minimal required arguments."""
        args = [
            '--token', 'test-token',
            '--namespace', 'test-ns',
            '--config', 'protection.yml'
        ]
        
        with patch('sys.argv', ['gitlab-protector.py'] + args):
            config = gp.parse_arguments()
            
        assert config.token == 'test-token'
        assert config.namespace == 'test-ns'
        assert config.config_file == 'protection.yml'
        assert config.url == 'https://gitlab.com'
        assert config.exclude is None
        assert config.dry_run is False
        assert config.stop_on_error is False
    
    def test_parse_args_all_options(self):
        """Test parsing all available arguments."""
        args = [
            '--url', 'https://gitlab.example.com',
            '--token', 'test-token',
            '--namespace', 'test-ns',
            '--config', 'protection.yml',
            '--exclude', 'proj1',
            '--dry-run',
            '--stop-on-error'
        ]
        
        with patch('sys.argv', ['gitlab-protector.py'] + args):
            config = gp.parse_arguments()
            
        assert config.url == 'https://gitlab.example.com'
        assert config.token == 'test-token'
        assert config.namespace == 'test-ns'
        assert config.config_file == 'protection.yml'
        assert config.exclude == 'proj1'
        assert config.dry_run is True
        assert config.stop_on_error is True
    
    @patch.dict(os.environ, {'GITLAB_TOKEN': 'env-token'})
    def test_token_from_environment(self):
        """Test token reading from environment variable."""
        args = [
            '--namespace', 'test-ns',
            '--config', 'protection.yml'
        ]
        
        with patch('sys.argv', ['gitlab-protector.py'] + args):
            config = gp.parse_arguments()
            
        assert config.token == 'env-token'
    
    def test_parse_args_missing_token_no_env(self):
        """Test parsing fails when token is missing and no env var."""
        args = [
            '--namespace', 'test-ns',
            '--config', 'protection.yml'
        ]
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('sys.argv', ['gitlab-protector.py'] + args):
                with pytest.raises(SystemExit) as exc_info:
                    gp.parse_arguments()
                
                assert exc_info.value.code == gp.EXIT_AUTH_ERROR


class TestConfigValidator:
    """Test ConfigValidator functionality."""
    
    def test_load_and_validate_config_minimal(self, tmp_path):
        """Test config file loading with minimal valid data."""
        config_data = {
            'tags': [],
            'branches': []
        }
        
        config_file = tmp_path / "test_config.yml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        result = gp.ConfigValidator.load_and_validate_config(str(config_file))
        
        assert isinstance(result, gp.ProtectionConfig)
        assert len(result.tags) == 0
        assert len(result.branches) == 0
    
    def test_load_and_validate_config_file_not_found(self):
        """Test config file not found error."""
        with pytest.raises(SystemExit) as exc_info:
            gp.ConfigValidator.load_and_validate_config('/nonexistent/file.yml')
        
        assert exc_info.value.code == gp.EXIT_CONFIG_NOT_FOUND
    
    def test_load_and_validate_config_parse_error(self, tmp_path):
        """Test config file parse error."""
        invalid_config = tmp_path / "invalid.yml"
        with open(invalid_config, 'w') as f:
            f.write("invalid: yaml: content: [\n")
        
        with pytest.raises(SystemExit) as exc_info:
            gp.ConfigValidator.load_and_validate_config(str(invalid_config))
        
        assert exc_info.value.code == gp.EXIT_CONFIG_PARSE_ERROR
    
    def test_config_validator_has_methods(self):
        """Test that ConfigValidator has expected methods."""
        assert hasattr(gp.ConfigValidator, 'load_and_validate_config')
        assert callable(gp.ConfigValidator.load_and_validate_config)


class TestLogger:
    """Test Logger class functionality."""
    
    def test_logger_debug(self, capsys):
        """Test Logger.debug method."""
        gp.Logger.debug("debug message")
        
        captured = capsys.readouterr()
        assert "debug message" in captured.out
    
    def test_logger_info(self, capsys):
        """Test Logger.info method."""
        gp.Logger.info("info message")
        
        captured = capsys.readouterr()
        assert "info message" in captured.out
    
    def test_logger_warn(self, capsys):
        """Test Logger.warn method."""
        gp.Logger.warn("warning message")
        
        captured = capsys.readouterr()
        assert "warning message" in captured.out
    
    def test_logger_error(self, capsys):
        """Test Logger.error method."""
        gp.Logger.error("error message")
        
        captured = capsys.readouterr()
        assert "error message" in captured.err


class TestAccessLevels:
    """Test access level mappings."""
    
    def test_access_levels_exist(self):
        """Test that all expected access levels exist."""
        expected_levels = [
            'no_access', 'minimal_access', 'guest', 'reporter', 
            'developer', 'maintainer', 'owner', 'admin'
        ]
        
        for level in expected_levels:
            assert level in gp.ACCESS_LEVELS
            assert isinstance(gp.ACCESS_LEVELS[level], int)
    
    def test_access_level_values(self):
        """Test access level constant values."""
        # Basic sanity check on some key levels
        assert gp.ACCESS_LEVELS['maintainer'] == 40
        assert gp.ACCESS_LEVELS['developer'] == 30
        assert gp.ACCESS_LEVELS['reporter'] == 20