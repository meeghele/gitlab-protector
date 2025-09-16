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

    def test_collect_projects_traverses_subgroups(self):
        """Ensure subgroup traversal includes nested projects."""
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

        mock_api = Mock()
        mock_groups = Mock()
        mock_api.groups = mock_groups
        protector.gitlab_api = mock_api

        root_project = Mock()
        root_project.path_with_namespace = 'test-ns/root'
        subgroup_project = Mock()
        subgroup_project.path_with_namespace = 'test-ns/sub/repo'

        subgroup_stub = Mock()
        subgroup_stub.id = 321
        subgroup_stub.full_path = 'test-ns/sub'

        root_group = Mock()
        root_group.projects.list.return_value = [root_project]
        root_group.subgroups = Mock()
        root_group.subgroups.list.return_value = [subgroup_stub]

        subgroup_group = Mock()
        subgroup_group.projects.list.return_value = [subgroup_project]
        subgroup_group.subgroups = Mock()
        subgroup_group.subgroups.list.return_value = []

        def get_side_effect(identifier, **_kwargs):
            if identifier == 'test-ns':
                return root_group
            if identifier == 321:
                return subgroup_group
            raise AssertionError('unexpected group lookup')

        mock_groups.get.side_effect = get_side_effect

        protector._collect_projects()

        assert root_project in protector.projects
        assert subgroup_project in protector.projects
        assert len(protector.projects) == 2


class TestProtectionManager:
    """Test ProtectionManager functionality."""

    def test_protection_manager_exists(self):
        """Test that ProtectionManager class exists."""
        assert hasattr(gp, 'ProtectionManager')
        assert hasattr(gp.ProtectionManager, 'apply_branch_protection')
        assert hasattr(gp.ProtectionManager, 'apply_tag_protection')

    def test_apply_tag_protection_uses_push_level(self):
        """apply_tag_protection should honour push_access_level for create access."""
        project = Mock()
        project.protectedtags.create = Mock()

        rule = {
            'name': 'v*',
            'merge_access_level': 'maintainer',
            'push_access_level': 'developer'
        }

        gp.ProtectionManager.apply_tag_protection(project, rule, stop_on_error=False)

        project.protectedtags.create.assert_called_once()
        args, _ = project.protectedtags.create.call_args
        assert args[0]['create_access_level'] == gp.ACCESS_LEVELS['developer']


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
