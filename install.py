#!/usr/bin/env python3
# /// script
# dependencies = ["InquirerPy"]
# ///
"""PlayQuery installer — interactive CLI wizard for deploying via Docker Compose.

Usage:
    uv run --script https://raw.githubusercontent.com/SBTopZZZ-LG/playquery/refs/heads/main/install.py

Requires: Python 3.11+, InquirerPy, Docker (docker-compose or docker compose).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from InquirerPy import inquirer

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_OWNER = "SBTopZZZ-LG"
REPO_NAME = "playquery"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}"
API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
GITHUB_ISSUES_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/issues/new"

HEADER = r"""
  __    ___ _               ____                            ____
 / /   / _ \ | __ _ _   _  /___ \_   _  ___ _ __ _   _     / /\ \
/ /   / /_)/ |/ _` | | | |//  / / | | |/ _ \ '__| | | |   / /  \ \
\ \  / ___/| | (_| | |_| / \_/ /| |_| |  __/ |  | |_| |  / /   / /
 \_\ \/    |_|\__,_|\__, \___,_\ \__,_|\___|_|   \__, | /_/   /_/
                    |___/                        |___/
"""

# ---------------------------------------------------------------------------
# Provider field definitions
# ---------------------------------------------------------------------------
# Format: (env_key, prompt_text, default, is_secret)
# The env_key is the suffix after PLAYQUERY_AI_ (e.g., API_KEY -> PLAYQUERY_AI_API_KEY)

PROVIDER_FIELDS: dict[str, list[tuple[str, str, str, bool]]] = {
    "copilot": [
        ("GITHUB_TOKEN", "GitHub token for Copilot", "", True),
    ],
    "openai": [
        ("BASE_URL", "Base URL (OpenAI-compatible endpoint)", "https://api.openai.com/v1", False),
        ("API_KEY", "API key for OpenAI-compatible endpoint", "", True),
    ],
}

# ---------------------------------------------------------------------------
# Env file helpers
# ---------------------------------------------------------------------------


def read_env_file(path: Path) -> dict[str, str]:
    """Read a .env file into a dict of key -> value."""
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def write_env_file(path: Path, values: dict[str, str]) -> None:
    """Write a .env file from a dict of key -> value."""
    lines = [f"{key}={value}" for key, value in sorted(values.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Docker helpers
# ---------------------------------------------------------------------------


def select_compose_command() -> str:
    """Detect docker-compose or docker compose."""
    if shutil.which("docker-compose"):
        return "docker-compose"
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            check=True,
        )
        return "docker compose"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    sys.stderr.write(
        "Neither docker-compose nor docker compose is available.\n"
        "Install Docker: https://docs.docker.com/get-docker/\n"
    )
    sys.exit(1)


def stack_is_running(compose_cmd: str, install_dir: Path, compose_file: Path) -> bool:
    """Check if the playquery service is running."""
    if not compose_file.is_file():
        return False
    try:
        result = subprocess.run(
            compose_cmd.split() + ["-f", str(compose_file), "ps", "-q", "playquery"],
            capture_output=True,
            text=True,
            cwd=str(install_dir),
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False


# ---------------------------------------------------------------------------
# Version fetching
# ---------------------------------------------------------------------------


def fetch_latest_version() -> str | None:
    """Fetch the latest release tag from GitHub API."""
    try:
        result = subprocess.run(
            [
                "curl",
                "-sL",
                f"{API_BASE}/releases/latest",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        return data.get("tag_name")
    except (json.JSONDecodeError, subprocess.CalledProcessError, KeyError):
        return None


# ---------------------------------------------------------------------------
# Config sections
# ---------------------------------------------------------------------------


def prompt_ai_config(env: dict[str, str]) -> dict[str, str]:
    """Prompt for AI provider configuration."""
    print()
    print("─" * 60)
    print("  AI Provider")
    print("─" * 60)

    # Provider type
    current_ai_type = env.get("PLAYQUERY_AI_TYPE", "copilot")
    provider_type = inquirer.select(
        message="AI provider type:",
        choices=[
            {"name": "OpenAI / OpenAI-compatible", "value": "openai"},
            {"name": "GitHub Copilot", "value": "copilot"},
        ],
        default=current_ai_type,
    ).execute()

    result: dict[str, str] = {"PLAYQUERY_AI_TYPE": provider_type}

    # Clear old provider-specific fields
    for ptype, fields in PROVIDER_FIELDS.items():
        if ptype != provider_type:
            for env_key, _, _, _ in fields:
                result[f"PLAYQUERY_AI_{env_key}"] = ""

    # Provider-specific fields
    fields = PROVIDER_FIELDS.get(provider_type, [])
    for env_key, prompt_text, default, is_secret in fields:
        env_var = f"PLAYQUERY_AI_{env_key}"
        current_value = env.get(env_var, default)

        if is_secret:
            if current_value:
                prompt_suffix = " (leave empty to use existing secret)"
            else:
                prompt_suffix = ""

            value = inquirer.secret(
                message=f"{prompt_text}{prompt_suffix}:",
                default="",
            ).execute()

            if not value:
                if current_value:
                    value = current_value
                    print("  → Using existing secret.")
                else:
                    print("  → Field is required, cannot be empty.")
                    value = inquirer.secret(
                        message=f"{prompt_text} (required):",
                        default="",
                    ).execute()
                    if not value:
                        sys.exit(1)
        else:
            value = inquirer.text(
                message=f"{prompt_text} [{current_value}]:",
                default=current_value,
                validate=lambda x: len(x.strip()) > 0,
                invalid_message="Field cannot be empty.",
            ).execute()

        result[env_var] = value

    # Model ID
    current_model = env.get("PLAYQUERY_AI_MODEL", "claude-haiku-4.5")
    model_id = inquirer.text(
        message=f"AI model [{current_model}]:",
        default=current_model,
        validate=lambda x: len(x.strip()) > 0,
        invalid_message="Model ID cannot be empty.",
    ).execute()
    result["PLAYQUERY_AI_MODEL"] = model_id

    # Timeout
    current_timeout = env.get("PLAYQUERY_AI_TIMEOUT", "300")
    timeout = inquirer.text(
        message=f"AI timeout in seconds [{current_timeout}]:",
        default=current_timeout,
        validate=lambda x: x.strip().isdigit() and int(x.strip()) > 0,
        invalid_message="Timeout must be a positive integer.",
    ).execute()
    result["PLAYQUERY_AI_TIMEOUT"] = timeout

    return result


def prompt_search_engine_config(env: dict[str, str]) -> dict[str, str]:
    """Prompt for search engine configuration."""
    print()
    print("─" * 60)
    print("  Search Engine")
    print("─" * 60)

    result: dict[str, str] = {}

    # Type
    current_type = env.get("PLAYQUERY_SEARCH_ENGINE_TYPE", "searxng")
    engine_type = inquirer.text(
        message=f"Search engine type [{current_type}]:",
        default=current_type,
        validate=lambda x: len(x.strip()) > 0,
        invalid_message="Engine type cannot be empty.",
    ).execute()
    result["PLAYQUERY_SEARCH_ENGINE_TYPE"] = engine_type

    # Base URL
    current_base_url = env.get("PLAYQUERY_SEARCH_ENGINE_BASE_URL", "http://searxng:8080")
    base_url = inquirer.text(
        message=f"Search engine base URL [{current_base_url}]:",
        default=current_base_url,
        validate=lambda x: len(x.strip()) > 0,
        invalid_message="Base URL cannot be empty.",
    ).execute()
    result["PLAYQUERY_SEARCH_ENGINE_BASE_URL"] = base_url

    # User agent
    current_ua = env.get("PLAYQUERY_SEARCH_ENGINE_USER_AGENT", "PlayQuery/1.0")
    ua = inquirer.text(
        message=f"Search engine user agent [{current_ua}]:",
        default=current_ua,
        validate=lambda x: len(x.strip()) > 0,
        invalid_message="User agent cannot be empty.",
    ).execute()
    result["PLAYQUERY_SEARCH_ENGINE_USER_AGENT"] = ua

    # Timeout
    current_timeout = env.get("PLAYQUERY_SEARCH_ENGINE_TIMEOUT", "30")
    timeout = inquirer.text(
        message=f"Search engine timeout in seconds [{current_timeout}]:",
        default=current_timeout,
        validate=lambda x: x.strip().replace(".", "", 1).isdigit() and float(x.strip()) > 0,
        invalid_message="Timeout must be a positive number.",
    ).execute()
    result["PLAYQUERY_SEARCH_ENGINE_TIMEOUT"] = timeout

    return result


def prompt_scraper_config(env: dict[str, str]) -> dict[str, str]:
    """Prompt for scraper configuration."""
    print()
    print("─" * 60)
    print("  Scraper")
    print("─" * 60)

    result: dict[str, str] = {}

    # Type
    current_type = env.get("PLAYQUERY_SCRAPER_TYPE", "patchright")
    scraper_type = inquirer.text(
        message=f"Scraper type [{current_type}]:",
        default=current_type,
        validate=lambda x: len(x.strip()) > 0,
        invalid_message="Scraper type cannot be empty.",
    ).execute()
    result["PLAYQUERY_SCRAPER_TYPE"] = scraper_type

    # Headless
    current_headless = env.get("PLAYQUERY_SCRAPER_HEADLESS", "true")
    headless_default = current_headless.lower() in ("true", "1", "yes")
    headless = inquirer.confirm(
        message=f"Run scraper headless? [{'Y/n' if headless_default else 'y/N'}]:",
        default=headless_default,
    ).execute()
    result["PLAYQUERY_SCRAPER_HEADLESS"] = str(headless).lower()

    # Locale
    current_locale = env.get("PLAYQUERY_SCRAPER_LOCALE", "en-US")
    locale = inquirer.text(
        message=f"Scraper locale [{current_locale}]:",
        default=current_locale,
        validate=lambda x: len(x.strip()) > 0,
        invalid_message="Locale cannot be empty.",
    ).execute()
    result["PLAYQUERY_SCRAPER_LOCALE"] = locale

    # Timeout
    current_timeout = env.get("PLAYQUERY_SCRAPER_TIMEOUT", "30")
    timeout = inquirer.text(
        message=f"Scraper timeout in seconds [{current_timeout}]:",
        default=current_timeout,
        validate=lambda x: x.strip().replace(".", "", 1).isdigit() and float(x.strip()) > 0,
        invalid_message="Timeout must be a positive number.",
    ).execute()
    result["PLAYQUERY_SCRAPER_TIMEOUT"] = timeout

    return result


def prompt_logging_config(env: dict[str, str]) -> dict[str, str]:
    """Prompt for logging configuration."""
    print()
    print("─" * 60)
    print("  Logging")
    print("─" * 60)

    result: dict[str, str] = {}

    current_level = env.get("PLAYQUERY_LOGGING_LEVEL", "DEBUG")
    level = inquirer.select(
        message=f"Logging level [{current_level}]:",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=current_level,
    ).execute()
    result["PLAYQUERY_LOGGING_LEVEL"] = level

    return result


# ---------------------------------------------------------------------------
# Main installer flow
# ---------------------------------------------------------------------------


def main() -> None:
    print(HEADER)
    print("Welcome to PlayQuery Installer.")

    # Fetch latest version
    latest_version = fetch_latest_version()
    if latest_version:
        print(f"Latest Version: {latest_version}")
    else:
        print("Latest Version: (unable to fetch)")

    print()

    # Check Docker availability
    compose_cmd = select_compose_command()

    # Install path
    default_install_dir = Path.home() / ".playquery"
    install_dir_str = inquirer.text(
        message=f"Installation directory [{default_install_dir}]:",
        default=str(default_install_dir),
    ).execute()
    install_dir = Path(install_dir_str).expanduser().resolve()

    compose_file = install_dir / "docker-compose.prod.yaml"
    env_file = install_dir / ".env"

    # Check if path exists and has existing deployment
    stack_running = False
    if install_dir.exists() and compose_file.is_file():
        print(f"\nPlayQuery is already installed in {install_dir}.")
        reconfigure = inquirer.confirm(
            message="Re-configure/update the existing installation?",
            default=False,
        ).execute()
        if not reconfigure:
            print("\nAborted.")
            sys.exit(0)

        # Check if stack is running
        stack_running = stack_is_running(compose_cmd, install_dir, compose_file)
        if stack_running:
            print("  → Taking down existing stack (preserving volumes)...")
            try:
                subprocess.run(
                    compose_cmd.split() + ["-f", str(compose_file), "down"],
                    check=True,
                    cwd=str(install_dir),
                )
            except subprocess.CalledProcessError as e:
                sys.stderr.write(f"  → Failed to stop stack: {e}\n")
                sys.exit(1)
            print("  → Stack stopped.")
    else:
        install_dir.mkdir(parents=True, exist_ok=True)

    # Read existing .env for defaults
    env = read_env_file(env_file)

    # Determine image tag for docker-compose.prod.yaml download
    if latest_version:
        image_tag = latest_version
    else:
        image_tag = "latest"

    # If stack was running and we're updating, pin to latest version
    if stack_running and latest_version:
        image_tag = latest_version

    # Configure image tag in env (not prompted, derived from version)
    env["PLAYQUERY_IMAGE_TAG"] = image_tag

    # Ask for MCP port
    current_port = env.get("PLAYQUERY_MCP_PORT", "8000")
    mcp_port = inquirer.text(
        message=f"MCP host port [{current_port}]:",
        default=current_port,
        validate=lambda x: x.strip().isdigit() and 1 <= int(x.strip()) <= 65535,
        invalid_message="Port must be a number between 1 and 65535.",
    ).execute()
    env["PLAYQUERY_MCP_PORT"] = mcp_port

    # Ask for CORS origins
    current_cors = env.get("PLAYQUERY_MCP_CORS_ORIGINS", "*")
    cors_origins = inquirer.text(
        message=f"Allowed CORS origins [{current_cors}]:",
        default=current_cors,
    ).execute()
    env["PLAYQUERY_MCP_CORS_ORIGINS"] = cors_origins

    # AI Provider configuration
    ai_config = prompt_ai_config(env)

    # Search Engine configuration
    search_config = prompt_search_engine_config(env)

    # Scraper configuration
    scraper_config = prompt_scraper_config(env)

    # Logging configuration
    logging_config = prompt_logging_config(env)

    # Merge all configs
    env.update(ai_config)
    env.update(search_config)
    env.update(scraper_config)
    env.update(logging_config)

    # Download docker-compose.prod.yaml
    print()
    print("Downloading docker-compose.prod.yaml...")
    try:
        subprocess.run(
            [
                "curl",
                "-fsSL",
                f"{RAW_BASE}/{image_tag}/docker-compose.prod.yaml",
                "-o",
                str(compose_file),
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Failed to download docker-compose.prod.yaml: {e}\n")
        sys.exit(1)

    # Write .env file
    print("Writing .env file...")
    write_env_file(env_file, env)

    # Pull images (ignore errors)
    print("Pulling images...")
    subprocess.run(
        compose_cmd.split() + ["-f", str(compose_file), "pull"],
        cwd=str(install_dir),
    )

    # Start the stack
    print("Starting PlayQuery stack...")
    try:
        result = subprocess.run(
            compose_cmd.split() + ["-f", str(compose_file), "up", "-d"],
            check=True,
            cwd=str(install_dir),
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"\nFailed to start stack: {e}\n")
        if e.stdout:
            sys.stderr.write(f"stdout: {e.stdout}\n")
        if e.stderr:
            sys.stderr.write(f"stderr: {e.stderr}\n")
        sys.stderr.write(
            f"\nIf the above error persists, you can open a new issue at: {GITHUB_ISSUES_URL}\n"
        )
        sys.exit(1)

    # Conclusion
    print()
    print("PlayQuery is starting.")
    print(f"Install directory: {install_dir}")
    print(f"MCP endpoint: http://localhost:{mcp_port}/mcp")


if __name__ == "__main__":
    main()
