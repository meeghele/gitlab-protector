#!/usr/bin/env python3
"""
GitLab Protector - Manage branch and tag protection policies for GitLab projects.

This tool automates the application of branch and tag protection policies across
all projects in a GitLab namespace based on YAML configuration files. It provides
comprehensive access control, policy validation, exclusion patterns, and dry-run
functionality for enterprise GitLab management.

Copyright (c) 2025 Michele Tavella <meeghele@proton.me>
Licensed under the MIT License. See LICENSE file for details.

Author: Michele Tavella <meeghele@proton.me>
License: MIT
"""


import argparse
import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, NoReturn, Optional

import colorama
import gitlab
import yaml

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)

# Exit codes
EXIT_SUCCESS = 0
EXIT_EXECUTION_ERROR = 1
EXIT_MISSING_ARGUMENTS = 2
EXIT_CONFIG_NOT_FOUND = 10
EXIT_CONFIG_PARSE_ERROR = 11
EXIT_GITLAB_ERROR = 20
EXIT_GITLAB_CREATE_TAG_ERROR = 21
EXIT_GITLAB_CREATE_BRANCH_ERROR = 22
EXIT_AUTH_ERROR = 30


class AccessLevel(Enum):
    """Enumeration for GitLab access levels."""

    NO_ACCESS = "no_access"
    MINIMAL_ACCESS = "minimal_access"
    GUEST = "guest"
    REPORTER = "reporter"
    DEVELOPER = "developer"
    MAINTAINER = "maintainer"
    OWNER = "owner"
    ADMIN = "admin"


class ProtectionType(Enum):
    """Enumeration for protection types."""

    TAGS = "tags"
    BRANCHES = "branches"


# Access level mapping
ACCESS_LEVELS = {
    AccessLevel.NO_ACCESS.value: gitlab.const.AccessLevel.NO_ACCESS,
    AccessLevel.MINIMAL_ACCESS.value: gitlab.const.AccessLevel.MINIMAL_ACCESS,
    AccessLevel.GUEST.value: gitlab.const.AccessLevel.GUEST,
    AccessLevel.REPORTER.value: gitlab.const.AccessLevel.REPORTER,
    AccessLevel.DEVELOPER.value: gitlab.const.AccessLevel.DEVELOPER,
    AccessLevel.MAINTAINER.value: gitlab.const.AccessLevel.MAINTAINER,
    AccessLevel.OWNER.value: gitlab.const.AccessLevel.OWNER,
    AccessLevel.ADMIN.value: gitlab.const.AccessLevel.ADMIN,
}


@dataclass
class Config:
    """Configuration for GitLab protector."""

    url: str
    token: str
    namespace: str
    config_file: str
    dry_run: bool
    exclude: Optional[str]
    stop_on_error: bool


@dataclass
class ProtectionConfig:
    """Protection configuration from YAML."""

    tags: List[Dict[str, object]]
    branches: List[Dict[str, object]]


class ConfigValidator:
    """Handles YAML configuration validation."""

    @staticmethod
    def load_and_validate_config(config_file: str) -> ProtectionConfig:
        """Load and validate protection configuration from YAML."""
        if not os.path.isfile(config_file):
            Logger.error(f"error: YAML configuration file not found: {config_file}")
            sys.exit(EXIT_CONFIG_NOT_FOUND)
        Logger.debug(f"yaml config: {config_file}")

        try:
            with open(config_file, "r") as file:
                data = yaml.safe_load(file)

            # Validate structure
            if not isinstance(data, dict):
                raise ValueError("Configuration must be a dictionary")

            tags = data.get("tags", [])
            branches = data.get("branches", [])

            # Validate tag and branch configurations
            ConfigValidator._validate_protection_rules(tags, ProtectionType.TAGS.value)
            ConfigValidator._validate_protection_rules(
                branches, ProtectionType.BRANCHES.value
            )

            Logger.info(
                f"Loaded {len(tags)} tag rules and {len(branches)} branch rules"
            )
            return ProtectionConfig(tags=tags, branches=branches)

        except yaml.YAMLError as e:
            Logger.error(f"error parsing YAML configuration: {e}")
            sys.exit(EXIT_CONFIG_PARSE_ERROR)
        except Exception as e:
            Logger.error(f"error loading configuration file: {e}")
            sys.exit(EXIT_CONFIG_PARSE_ERROR)

    @staticmethod
    def _validate_protection_rules(rules: List[Dict], rule_type: str) -> None:
        """Validate protection rules structure."""
        for idx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise ValueError(f"{rule_type}[{idx}] must be a dictionary")

            # Check required fields
            if "name" not in rule:
                raise ValueError(f"{rule_type}[{idx}] missing required field 'name'")
            if "merge_access_level" not in rule:
                raise ValueError(
                    f"{rule_type}[{idx}] missing required field 'merge_access_level'"
                )
            if "push_access_level" not in rule:
                raise ValueError(
                    f"{rule_type}[{idx}] missing required field 'push_access_level'"
                )

            # Validate access levels
            mal = rule["merge_access_level"]
            pal = rule["push_access_level"]

            if mal not in ACCESS_LEVELS:
                raise ValueError(
                    f"{rule_type}[{idx}] invalid merge_access_level: {mal}"
                )
            if pal not in ACCESS_LEVELS:
                raise ValueError(f"{rule_type}[{idx}] invalid push_access_level: {pal}")


class ProtectionManager:
    """Handles applying protection policies."""

    @staticmethod
    def apply_tag_protection(
        project: object, rule: Dict[str, object], stop_on_error: bool
    ) -> None:
        """Apply tag protection rule to project."""
        try:
            name = rule.get("name", "")
            push_level = rule.get("push_access_level", "")
            merge_level = rule.get("merge_access_level", "")

            if not isinstance(name, str) or not isinstance(push_level, str):
                Logger.error("invalid rule format for tag protection")
                return

            create_level = ACCESS_LEVELS.get(push_level)

            if create_level is None:
                Logger.error(f"invalid tag push_access_level value: {push_level}")
                return

            if merge_level and merge_level not in ACCESS_LEVELS:
                Logger.warn(
                    "merge_access_level specified for tag protection but ignored"
                )

            Logger.debug(f"protecting tag: {name} (create={push_level})")

            protection = {
                "name": name,
                "create_access_level": create_level,
                "allowed_to_create": [],
            }

            getattr(project, "protectedtags").create(protection)

        except gitlab.exceptions.GitlabAuthenticationError as e:
            Logger.error(f"authentication error: {e}")
            sys.exit(EXIT_AUTH_ERROR)
        except gitlab.exceptions.GitlabCreateError as e:
            # 422 means tag protection already exists
            if e.response_code != 422:
                Logger.error(f"tag protection error for '{name}': {e}")
                if stop_on_error:
                    sys.exit(EXIT_GITLAB_CREATE_TAG_ERROR)
        except Exception as e:
            Logger.error(f"unexpected error protecting tag '{name}': {e}")
            if stop_on_error:
                sys.exit(EXIT_GITLAB_CREATE_TAG_ERROR)

    @staticmethod
    def apply_branch_protection(
        project: object, rule: Dict[str, object], stop_on_error: bool
    ) -> None:
        """Apply branch protection rule to project."""
        try:
            name = rule.get("name", "")
            merge_level = rule.get("merge_access_level", "")
            push_level = rule.get("push_access_level", "")

            if (
                not isinstance(name, str)
                or not isinstance(merge_level, str)
                or not isinstance(push_level, str)
            ):
                Logger.error("invalid rule format for branch protection")
                return

            mal = ACCESS_LEVELS.get(merge_level)
            pal = ACCESS_LEVELS.get(push_level)

            if mal is None or pal is None:
                Logger.error(
                    f"invalid access levels: merge={merge_level}, push={push_level}"
                )
                return

            Logger.debug(
                f"protecting branch: {name} (merge={merge_level}, push={push_level})"
            )

            protection = {
                "name": name,
                "merge_access_level": mal,
                "push_access_level": pal,
                "allow_force_push": False,
                "code_owner_approval_required": False,
            }

            getattr(project, "protectedbranches").create(protection)

        except gitlab.exceptions.GitlabAuthenticationError as e:
            Logger.error(f"authentication error: {e}")
            sys.exit(EXIT_AUTH_ERROR)
        except gitlab.exceptions.GitlabCreateError as e:
            # 409 means branch protection already exists
            if e.response_code != 409:
                Logger.error(f"branch protection error for '{name}': {e}")
                if stop_on_error:
                    sys.exit(EXIT_GITLAB_CREATE_BRANCH_ERROR)
        except Exception as e:
            Logger.error(f"unexpected error protecting branch '{name}': {e}")
            if stop_on_error:
                sys.exit(EXIT_GITLAB_CREATE_BRANCH_ERROR)


class Logger:
    """Handles formatted console output with colors."""

    PROCESS_NAME = "gitlab-protector"

    @classmethod
    def debug(cls, *messages: str) -> None:
        """Print debug message in gray."""
        cls._write_stdout(colorama.Fore.LIGHTBLACK_EX, *messages)

    @classmethod
    def info(cls, *messages: str) -> None:
        """Print info message in green."""
        cls._write_stdout(colorama.Fore.GREEN, *messages)

    @classmethod
    def warn(cls, *messages: str) -> None:
        """Print warning message in yellow."""
        cls._write_stdout(colorama.Fore.YELLOW, *messages)

    @classmethod
    def error(cls, *messages: str) -> None:
        """Print error message in red to stderr."""
        cls._write_stderr(colorama.Fore.RED, *messages)

    @classmethod
    def _write_stdout(cls, color: str, *messages: str) -> None:
        """Write formatted message to stdout."""
        sys.stdout.write(cls._format_line(color, *messages) + "\n")

    @classmethod
    def _write_stderr(cls, color: str, *messages: str) -> None:
        """Write formatted message to stderr."""
        sys.stderr.write(cls._format_line(color, *messages) + "\n")

    @classmethod
    def _get_header(cls) -> str:
        """Get process header with PID."""
        return f"[{cls.PROCESS_NAME}:{os.getpid()}]"

    @classmethod
    def _format_line(cls, color: str, *messages: str) -> str:
        """Format a colored line with header."""
        header = cls._get_header()
        message = " ".join(str(msg) for msg in messages)
        return f"{color}{header}{colorama.Style.RESET_ALL} {message}"


class GitLabProtector:
    """Main class for protecting GitLab repositories."""

    def __init__(self, config: Config):
        """Initialize GitLab protector with configuration."""
        self.config = config
        self.gitlab_api: Optional[gitlab.Gitlab] = None
        self.projects: List[object] = []
        self.protection_config: Optional[ProtectionConfig] = None

    def run(self) -> int:
        """Execute the protection process."""
        try:
            self._load_protection_config()
            self._initialize_gitlab_api()
            self._collect_projects()

            if self.config.dry_run:
                Logger.info("dry-run completed")
                self._display_protection_summary()
                return EXIT_SUCCESS

            self._apply_protections()
            Logger.info("mission accomplished")
            return EXIT_SUCCESS

        except SystemExit as e:
            return int(e.code) if isinstance(e.code, int) else EXIT_EXECUTION_ERROR
        except Exception as e:
            Logger.error(f"unexpected error: {e}")
            return EXIT_EXECUTION_ERROR

    def _load_protection_config(self) -> None:
        """Load and validate protection configuration from YAML."""
        self.protection_config = ConfigValidator.load_and_validate_config(
            self.config.config_file
        )

    def _initialize_gitlab_api(self) -> None:
        """Initialize GitLab API connection."""
        Logger.info(f"init gitlab API: {self.config.url}")
        try:
            self.gitlab_api = gitlab.Gitlab(
                url=self.config.url, private_token=self.config.token
            )
            # Test authentication
            self.gitlab_api.auth()
        except gitlab.exceptions.GitlabAuthenticationError as e:
            Logger.error(f"authentication error: {e}")
            sys.exit(EXIT_AUTH_ERROR)
        except Exception as e:
            Logger.error(f"failed to initialize gitlab API: {e}")
            sys.exit(EXIT_GITLAB_ERROR)

    def _collect_projects(self) -> None:
        """Collect all projects from namespace and subgroups."""
        Logger.info(f"getting root groups: {self.config.namespace}")

        if self.gitlab_api is None:
            Logger.error("gitlab API not initialized")
            sys.exit(EXIT_GITLAB_ERROR)

        try:
            # Get root group
            root_group = self.gitlab_api.groups.get(
                self.config.namespace, lazy=False, include_subgroups=True
            )

            # Get projects from root group
            Logger.info("getting root projects")
            self._add_projects_from_group(root_group)

            # Get subgroups and their projects
            Logger.info("getting sub-groups and their projects")
            self._process_subgroups(root_group)

            Logger.info(f"found {len(self.projects)} projects to process")

        except gitlab.exceptions.GitlabGetError as e:
            Logger.error(f"failed to get namespace '{self.config.namespace}': {e}")
            sys.exit(EXIT_GITLAB_ERROR)
        except Exception as e:
            Logger.error(f"unexpected error while collecting projects: {e}")
            sys.exit(EXIT_GITLAB_ERROR)

    def _add_projects_from_group(self, group: object) -> None:
        """Add all projects from a group."""
        try:
            for project in getattr(group, "projects").list(all=True):
                self.projects.append(project)
                Logger.debug(
                    f"found: {getattr(project, 'path_with_namespace', 'unknown')}"
                )
        except Exception as e:
            Logger.error(f"error getting projects from group: {e}")
            raise

    def _process_subgroups(self, root_group: object) -> None:
        """Recursively process all subgroups."""
        if self.gitlab_api is None:
            Logger.error("gitlab API not initialized")
            sys.exit(EXIT_GITLAB_ERROR)

        try:
            to_visit = []
            visited = set()

            subgroups_manager = getattr(root_group, "subgroups", None)
            if subgroups_manager is not None:
                to_visit.extend(subgroups_manager.list(all=True, recursive=True))

            while to_visit:
                subgroup = to_visit.pop(0)
                subgroup_id = getattr(subgroup, "id", None)
                if subgroup_id is None or subgroup_id in visited:
                    continue

                visited.add(subgroup_id)
                subgroup_path = getattr(subgroup, "full_path", "")
                if self._is_excluded(subgroup_path):
                    Logger.warn(f"excluding: {subgroup_path}")
                    continue

                full_group = self.gitlab_api.groups.get(subgroup_id, lazy=False)
                self._add_projects_from_group(full_group)

        except Exception as e:
            Logger.error(f"error processing subgroups: {e}")
            sys.exit(EXIT_GITLAB_ERROR)

    def _is_excluded(self, path: str) -> bool:
        """Check if path matches exclusion pattern."""
        if self.config.exclude:
            return self.config.exclude in path
        return False

    def _display_protection_summary(self) -> None:
        """Display summary of protections that would be applied."""
        if self.protection_config is None:
            Logger.error("protection config not loaded")
            return

        Logger.info("protection rules to be applied:")

        for tag_rule in self.protection_config.tags:
            mal = tag_rule.get("merge_access_level", "unknown")
            pal = tag_rule.get("push_access_level", "unknown")
            name = tag_rule.get("name", "unknown")
            Logger.info(f"  Tag '{name}': merge={mal}, push={pal}")

        for branch_rule in self.protection_config.branches:
            mal = branch_rule.get("merge_access_level", "unknown")
            pal = branch_rule.get("push_access_level", "unknown")
            name = branch_rule.get("name", "unknown")
            Logger.info(f"  Branch '{name}': merge={mal}, push={pal}")

    def _apply_protections(self) -> None:
        """Apply protection policies to all projects."""
        for project in self.projects:
            self._protect_project(project)

    def _protect_project(self, project: object) -> None:
        """Apply protection policies to a single project."""
        if self.gitlab_api is None or self.protection_config is None:
            Logger.error("gitlab API or protection config not initialized")
            return

        project_path = getattr(project, "path_with_namespace", "unknown")
        Logger.info(f"processing: {project_path}")

        # Get full project object for modification
        full_project = self.gitlab_api.projects.get(project_path)

        # Apply tag protections
        for tag_rule in self.protection_config.tags:
            ProtectionManager.apply_tag_protection(
                full_project, tag_rule, self.config.stop_on_error
            )

        # Apply branch protections
        for branch_rule in self.protection_config.branches:
            ProtectionManager.apply_branch_protection(
                full_project, branch_rule, self.config.stop_on_error
            )


def parse_arguments() -> Config:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Apply branch and tag protection policies to GitLab projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -n mygroup -c protection.yaml
  %(prog)s -n mygroup -c protection.yaml --dry-run
  %(prog)s -n mygroup -c protection.yaml --exclude archived
  %(prog)s -n mygroup -c protection.yaml --stop-on-error
        """,
    )

    parser.add_argument(
        "-u",
        "--url",
        dest="url",
        default="https://gitlab.com",
        help="Base URL of the GitLab instance (default: https://gitlab.com)",
    )

    parser.add_argument(
        "-t",
        "--token",
        dest="token",
        help="GitLab API token (can also use GITLAB_TOKEN env var)",
    )

    parser.add_argument(
        "-n",
        "--namespace",
        dest="namespace",
        required=True,
        help="Namespace (group) to protect",
    )

    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        required=True,
        help="YAML configuration file with protection rules",
    )

    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "-e",
        "--exclude",
        dest="exclude",
        help="Pattern to exclude from subgroups and projects",
    )

    parser.add_argument(
        "-s",
        "--stop-on-error",
        action="store_true",
        dest="stop_on_error",
        help="Stop execution on GitLab API errors (excluding auth/409/422)",
    )

    args = parser.parse_args()

    # Handle token
    token = args.token or os.getenv("GITLAB_TOKEN")
    if not token:
        Logger.error(
            "error: gitlab token not provided. "
            "use -t or set GITLAB_TOKEN environment variable"
        )
        sys.exit(EXIT_AUTH_ERROR)

    if args.token:
        Logger.warn(
            "warning: token provided via command line argument "
            "(consider using environment variable)"
        )

    return Config(
        url=args.url,
        token=token,
        namespace=args.namespace,
        config_file=args.config,
        dry_run=args.dry_run,
        exclude=args.exclude,
        stop_on_error=args.stop_on_error,
    )


def main() -> NoReturn:
    """Main entry point."""
    if __name__ != "__main__":
        sys.exit(EXIT_EXECUTION_ERROR)

    config = parse_arguments()
    protector = GitLabProtector(config)
    sys.exit(protector.run())


if __name__ == "__main__":
    main()
