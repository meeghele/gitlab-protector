# GitLab Protector

<div align="center">
  <img src="images/gitlab-protector_512.jpg" alt="GitLab Protector Logo" width="200"/>
</div>

[![CI](https://github.com/meeghele/gitlab-protector/actions/workflows/ci.yml/badge.svg)](https://github.com/meeghele/gitlab-protector/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Python command-line tool that manages branch and tag protection policies for GitLab projects based on YAML configuration files.

## Features

- **Policy automation**: Apply branch and tag protection policies across all projects in a GitLab namespace
- **YAML configuration**: Define protection rules using simple, readable YAML files
- **Namespace coverage**: Automatically processes all projects in a namespace, including nested subgroups
- **Access level control**: Set merge and push access levels for branches and tags
- **Exclusion patterns**: Option to exclude specific subgroups or projects based on name patterns
- **Dry-run mode**: Preview what would be protected without making any changes
- **Error handling**: Configurable behavior on API errors with detailed logging
- **Robust validation**: Validates YAML configuration and access levels before execution
- **Colored output**: Terminal color output for better readability

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python gitlab-protector.py -n NAMESPACE -c CONFIG_FILE [options]
```

### Authentication

Set your GitLab token using one of these methods:

1. **Environment variable (recommended):**
   ```bash
   export GITLAB_TOKEN=your-api-token
   python gitlab-protector.py -n your-namespace -c protection.yaml
   ```

2. **Command line argument:**
   ```bash
   python gitlab-protector.py -n your-namespace -c protection.yaml -t your-api-token
   ```

### Command Line Options

| Option | Long Option | Description |
|--------|-------------|-------------|
| `-u` | `--url` | Base URL of the GitLab instance (default: `https://gitlab.com`) |
| `-t` | `--token` | GitLab API token (can also use `GITLAB_TOKEN` env var) |
| `-n` | `--namespace` | **Required.** Namespace (group) to protect |
| `-c` | `--config` | **Required.** YAML configuration file with protection rules |
| `-d` | `--dry-run` | Show what would be done without making changes |
| `-e` | `--exclude` | Pattern to exclude from subgroups and projects |
| `-s` | `--stop-on-error` | Stop execution on GitLab API errors (excluding auth/409/422) |
| `-h` | `--help` | Show help message and exit |

## Configuration

Create a YAML file defining your protection policies:

### Basic Configuration

```yaml
branches:
  - name: "main"
    merge_access_level: "maintainer"
    push_access_level: "maintainer"
  - name: "develop"
    merge_access_level: "developer"
    push_access_level: "developer"

tags:
  - name: "*"
    merge_access_level: "maintainer"
    push_access_level: "maintainer"
  - name: "v*"
    merge_access_level: "maintainer"
    push_access_level: "no_access"
```

### Access Levels

Available access levels (from most to least restrictive):

| Level | Description |
|-------|-------------|
| `no_access` | No access |
| `minimal_access` | Minimal access (GitLab Premium) |
| `guest` | Guest level |
| `reporter` | Reporter level |
| `developer` | Developer level |
| `maintainer` | Maintainer level |
| `owner` | Owner level (groups only) |
| `admin` | Admin level (instance) |

### Advanced Configuration

```yaml
branches:
  # Protect main branch - only maintainers can merge/push
  - name: "main"
    merge_access_level: "maintainer"
    push_access_level: "maintainer"
  
  # Protect release branches - developers can merge, maintainers can push
  - name: "release/*"
    merge_access_level: "developer"
    push_access_level: "maintainer"
  
  # Development branch - developers can do everything
  - name: "develop"
    merge_access_level: "developer"
    push_access_level: "developer"

tags:
  # Protect all tags - only maintainers can create
  - name: "*"
    merge_access_level: "maintainer"
    push_access_level: "maintainer"
  
  # Lock version tags - no one can push to them
  - name: "v*"
    merge_access_level: "maintainer"
    push_access_level: "no_access"
```

## Examples

**Basic usage:**
```bash
python gitlab-protector.py -n mygroup -c protection.yaml
```

**Dry run to preview changes:**
```bash
python gitlab-protector.py -n mygroup -c protection.yaml --dry-run
```

**Exclude archived projects:**
```bash
python gitlab-protector.py -n mygroup -c protection.yaml --exclude archived
```

**Use custom GitLab instance:**
```bash
python gitlab-protector.py -n mygroup -c protection.yaml -u https://gitlab.company.com
```

**Stop on first error:**
```bash
python gitlab-protector.py -n mygroup -c protection.yaml --stop-on-error
```

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Execution error |
| 2 | Missing required arguments |
| 10 | Configuration file not found |
| 11 | Configuration parsing error |
| 20 | GitLab API error |
| 21 | Tag protection error |
| 22 | Branch protection error |
| 30 | Authentication error |

## Token Permissions

Your GitLab token needs:
- **Scope**: API (Full API access)
- **Role**: Maintainer or Owner on the target namespace

Create a token at your GitLab instance under User Settings > Access Tokens.

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.