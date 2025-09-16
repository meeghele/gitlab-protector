#!/usr/bin/env python3
"""
GitLab Protector Test Configuration and Fixtures

Copyright (c) 2025 Michele Tavella <meeghele@proton.me>
Licensed under the MIT License.

Author: Michele Tavella <meeghele@proton.me>
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock
from typing import Dict, List, Any

import pytest
import gitlab
import yaml


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_protection_config():
    """Provide sample protection configuration."""
    return {
        'branch_protection': {
            'main': {
                'push_access_level': 'maintainer',
                'merge_access_level': 'maintainer',
                'unprotect_access_level': 'maintainer',
                'allow_force_push': False
            },
            'develop': {
                'push_access_level': 'developer',
                'merge_access_level': 'maintainer',
                'unprotect_access_level': 'maintainer',
                'allow_force_push': False
            }
        },
        'tag_protection': {
            'v*': {
                'create_access_level': 'maintainer'
            },
            'release/*': {
                'create_access_level': 'developer'
            }
        }
    }


@pytest.fixture
def config_file(temp_dir, sample_protection_config):
    """Create a temporary config file."""
    config_path = os.path.join(temp_dir, 'protection.yml')
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(sample_protection_config, f)
    return config_path


@pytest.fixture
def mock_config():
    """Provide a mock configuration for testing."""
    return {
        'url': 'https://gitlab.example.com',
        'token': 'test-token-123',
        'namespace': 'test-namespace',
        'config_file': 'test-config.yml',
        'exclude': ['excluded-project'],
        'dry_run': False,
        'verbose': False
    }


@pytest.fixture
def mock_gitlab_client():
    """Provide a mock GitLab client."""
    client = Mock(spec=gitlab.Gitlab)
    client.auth.return_value = None
    return client


@pytest.fixture
def mock_project():
    """Provide a mock GitLab project."""
    project = Mock()
    project.id = 1
    project.name = 'test-project'
    project.path = 'test-project'
    project.namespace = {'full_path': 'test-namespace'}
    project.protectedbranches = Mock()
    project.protectedtags = Mock()
    project.branches = Mock()
    return project


@pytest.fixture
def mock_group():
    """Provide a mock GitLab group."""
    group = Mock()
    group.id = 1
    group.name = 'test-group'
    group.full_path = 'test-namespace'
    group.projects = Mock()
    group.subgroups = Mock()
    return group


@pytest.fixture
def mock_protected_branch():
    """Provide a mock protected branch."""
    branch = Mock()
    branch.name = 'main'
    branch.push_access_levels = [{'access_level': 40}]
    branch.merge_access_levels = [{'access_level': 40}]
    branch.unprotect_access_levels = [{'access_level': 40}]
    branch.allow_force_push = False
    return branch


@pytest.fixture
def mock_protected_tag():
    """Provide a mock protected tag."""
    tag = Mock()
    tag.name = 'v*'
    tag.create_access_levels = [{'access_level': 40}]
    return tag


@pytest.fixture
def sample_projects():
    """Provide sample project data for testing."""
    return [
        {
            'id': 1,
            'name': 'project1',
            'path': 'project1',
            'namespace': {'full_path': 'test'}
        },
        {
            'id': 2,
            'name': 'project2',
            'path': 'project2',
            'namespace': {'full_path': 'test'}
        }
    ]