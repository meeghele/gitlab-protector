#!/usr/bin/env python3
"""
GitLab Protector Main Class Tests

Copyright (c) 2025 Michele Tavella <meeghele@proton.me>
Licensed under the MIT License.

Author: Michele Tavella <meeghele@proton.me>
"""

import os
import sys
from unittest.mock import patch, Mock, MagicMock
import pytest

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module under test
import importlib.util
spec = importlib.util.spec_from_file_location("gitlab_protector", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gitlab-protector.py"))
gp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gp)


class TestGitLabProtector:
    """Test GitLabProtector main class."""
    
    def test_init(self):
        """Test GitLabProtector initialization."""
        config = gp.Config(
            url='https://gitlab.com',
            token='test-token', 
            namespace='test-ns',
            config_file='protection.yml',
            dry_run=False,
            exclude=None,
            stop_on_error=False
        )
        
        protector = gp.GitLabProtector(config)
        
        assert protector.config == config
        assert protector.protection_config is None
        assert protector.gitlab_api is None
        assert protector.projects == []
    
    @patch('gitlab.Gitlab')
    def test_initialize_gitlab_api_success(self, mock_gitlab_class):
        """Test successful GitLab API initialization."""
        mock_api = Mock()
        mock_gitlab_class.return_value = mock_api
        
        config = gp.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns',
            config_file='protection.yml',
            dry_run=False,
            exclude=None,
            stop_on_error=False
        )
        
        protector = gp.GitLabProtector(config)
        
        protector._initialize_gitlab_api()
        
        mock_gitlab_class.assert_called_once_with(url='https://gitlab.com', private_token='test-token')
        mock_api.auth.assert_called_once()
        assert protector.gitlab_api == mock_api
    
    @patch('gitlab.Gitlab')
    @patch('sys.exit')
    def test_initialize_gitlab_api_failure(self, mock_exit, mock_gitlab_class):
        """Test GitLab API initialization failure."""
        mock_api = Mock()
        mock_api.auth.side_effect = Exception("Authentication failed")
        mock_gitlab_class.return_value = mock_api
        
        config = gp.Config(
            url='https://gitlab.com',
            token='invalid-token',
            namespace='test-ns',
            config_file='protection.yml',
            dry_run=False,
            exclude=None,
            stop_on_error=False
        )
        
        protector = gp.GitLabProtector(config)
        
        protector._initialize_gitlab_api()
        
        mock_exit.assert_called_once_with(gp.EXIT_GITLAB_ERROR)
    
    @patch.object(gp.GitLabProtector, '_apply_protections')
    @patch.object(gp.GitLabProtector, '_collect_projects')
    @patch.object(gp.GitLabProtector, '_initialize_gitlab_api')
    @patch.object(gp.GitLabProtector, '_load_protection_config')
    def test_run_success(self, mock_load_config, mock_init_api, mock_collect, mock_apply):
        """Test successful run execution."""
        config = gp.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns',
            config_file='protection.yml',
            dry_run=False,
            exclude=None,
            stop_on_error=False
        )
        
        protector = gp.GitLabProtector(config)
        
        result = protector.run()
        
        assert result == gp.EXIT_SUCCESS
        mock_load_config.assert_called_once()
        mock_init_api.assert_called_once()
        mock_collect.assert_called_once()
        mock_apply.assert_called_once()
    
    @patch.object(gp.GitLabProtector, '_collect_projects')
    @patch.object(gp.GitLabProtector, '_initialize_gitlab_api')
    @patch.object(gp.GitLabProtector, '_load_protection_config')
    def test_run_dry_run_mode(self, mock_load_config, mock_init_api, mock_collect):
        """Test run execution in dry-run mode."""
        config = gp.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns',
            config_file='protection.yml',
            dry_run=True,  # Dry run mode
            exclude=None,
            stop_on_error=False
        )
        
        protector = gp.GitLabProtector(config)
        
        result = protector.run()
        
        assert result == gp.EXIT_SUCCESS
        mock_load_config.assert_called_once()
        mock_init_api.assert_called_once()
        mock_collect.assert_called_once()
        # _apply_protections should not be called in dry-run mode
    
    @patch.object(gp.GitLabProtector, '_load_protection_config')
    def test_run_exception_handling(self, mock_load_config):
        """Test run exception handling."""
        mock_load_config.side_effect = Exception("Test error")
        
        config = gp.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns',
            config_file='protection.yml',
            dry_run=False,
            exclude=None,
            stop_on_error=False
        )
        
        protector = gp.GitLabProtector(config)
        
        result = protector.run()
        
        assert result == gp.EXIT_EXECUTION_ERROR


class TestProtectionManager:
    """Test ProtectionManager functionality."""
    
    def test_protection_manager_exists(self):
        """Test that ProtectionManager class exists."""
        assert hasattr(gp, 'ProtectionManager')
        assert hasattr(gp.ProtectionManager, 'apply_branch_protection')
        assert hasattr(gp.ProtectionManager, 'apply_tag_protection')


class TestMainFunction:
    """Test main function."""
    
    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        assert hasattr(gp, 'main')
        assert callable(gp.main)
    
    def test_parse_arguments_function_exists(self):
        """Test that parse_arguments function exists and is callable."""
        assert hasattr(gp, 'parse_arguments')
        assert callable(gp.parse_arguments)