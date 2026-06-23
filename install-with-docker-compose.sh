#!/usr/bin/env bash

set -euo pipefail

REPO_OWNER="SBTopZZZ-LG"
REPO_NAME="playquery"
RAW_BASE="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}"
API_BASE="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}"
TTY_DEVICE="/dev/tty"

# Provider-specific field declarations.
# Adding a new AI provider = adding entries to provider_is_known and
# provider_field_defs below.
# Each field: "KEY|prompt text|default value|is_secret (true/false)"
# Multiple fields for a single provider are emitted as separate lines.
provider_is_known() {
  case "$1" in
    copilot|openai) return 0 ;;
    *) return 1 ;;
  esac
}

provider_field_defs() {
  case "$1" in
    copilot)
      printf '%s\n' "GITHUB_TOKEN|GitHub token for Copilot||true"
      ;;
    openai)
      printf '%s\n' "API_KEY|API key for OpenAI-compatible endpoint||true"
      printf '%s\n' "BASE_URL|Base URL (OpenAI-compatible endpoint)|https://api.openai.com/v1|false"
      ;;
  esac
}

env_file_value() {
  local file="$1"
  local key="$2"

  [[ -f "$file" ]] || return 1
  sed -n "s/^${key}=//p" "$file" | tail -n 1
}

value_or_default() {
  local file="$1"
  local key="$2"
  local fallback="$3"
  local value=""

  value="$(env_file_value "$file" "$key" || true)"
  printf '%s' "${value:-$fallback}"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    exit 1
  fi
}

select_compose_command() {
  if command -v docker-compose >/dev/null 2>&1; then
    printf 'docker-compose'
    return
  fi

  if docker compose version >/dev/null 2>&1; then
    printf 'docker compose'
    return
  fi

  printf 'Neither docker-compose nor docker compose is available.\n' >&2
  exit 1
}

latest_release_ref() {
  curl -fsSL "${API_BASE}/releases/latest" \
    | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' \
    | head -n 1
}

ref_has_prod_compose() {
  local ref="$1"

  [[ -n "$ref" ]] || return 1
  curl -fsSI "${RAW_BASE}/${ref}/docker-compose.prod.yaml" >/dev/null
}

prompt_default() {
  local prompt="$1"
  local default_value="$2"
  local value

  if [[ ! -r "$TTY_DEVICE" ]]; then
    printf 'Interactive input requires a tty. Set the environment variables before running the installer.\n' >&2
    exit 1
  fi

  if [[ -n "$default_value" ]]; then
    read -r -p "$prompt [$default_value]: " value < "$TTY_DEVICE"
    printf '%s' "${value:-$default_value}"
    return
  fi

  read -r -p "$prompt: " value < "$TTY_DEVICE"
  printf '%s' "$value"
}

prompt_secret() {
  local prompt="$1"
  local default_value="${2:-}"
  local value=""

  if [[ ! -r "$TTY_DEVICE" ]]; then
    printf 'Interactive secret input requires a tty. Set PLAYQUERY_AI_GITHUB_TOKEN before running the installer.\n' >&2
    exit 1
  fi

  while [[ -z "$value" ]]; do
    read -r -s -p "$prompt: " value < "$TTY_DEVICE"
    printf '\n' > "$TTY_DEVICE"

    if [[ -z "$value" ]]; then
      value="$default_value"
    fi
  done

  printf '%s' "$value"
}

# Prompt for a single provider-specific field and assign the result to a
# variable named by the field's KEY (uppercase, e.g. GITHUB_TOKEN).
prompt_provider_field() {
  local field_def="$1"
  local key prompt default is_secret current_value env_var_name result

  local IFS_SAVE="$IFS"
  IFS='|' read -r key prompt default is_secret <<< "$field_def"
  IFS="$IFS_SAVE"

  env_var_name="PLAYQUERY_AI_${key}"
  current_value="${!env_var_name:-}"

  if [[ -n "$current_value" ]]; then
    printf -v "$key" '%s' "$current_value"
    return
  fi

  current_value="$(value_or_default "$ENV_FILE" "$env_var_name" "$default")"

  if [[ "$is_secret" == "true" ]]; then
    result="$(prompt_secret "$prompt" "$current_value")"
  else
    result="$(prompt_default "$prompt" "$current_value")"
  fi

  printf -v "$key" '%s' "$result"
}

prompt_confirm() {
  local prompt="$1"
  local default_value="${2:-n}"
  local prompt_suffix="y/N"
  local value

  if [[ ! -r "$TTY_DEVICE" ]]; then
    printf 'Interactive input requires a tty. Set the environment variables before running the installer.\n' >&2
    exit 1
  fi

  if [[ "$default_value" == "y" ]]; then
    prompt_suffix="Y/n"
  fi

  read -r -p "$prompt [$prompt_suffix]: " value < "$TTY_DEVICE"
  value="${value:-$default_value}"
  value="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  [[ "$value" == "y" || "$value" == "yes" ]]
}

stack_is_running() {
  local install_dir="$1"
  local compose_file="$2"

  [[ -f "$compose_file" ]] || return 1

  (
    cd "$install_dir"
    $COMPOSE_CMD -f "$compose_file" ps -q playquery 2>/dev/null
  ) | grep -q '.'
}

print_existing_stack_status() {
  local install_dir="$1"
  local env_file="$2"
  local latest_release_tag="$3"
  local current_image_tag="latest"

  current_image_tag="$(value_or_default "$env_file" "PLAYQUERY_IMAGE_TAG" "latest")"

  printf '\nPlayQuery is already running in %s.\n' "$install_dir"

  if [[ -n "$latest_release_tag" ]]; then
    printf 'Current configured image tag: %s\n' "$current_image_tag"
    printf 'Latest release tag: %s\n' "$latest_release_tag"

    if [[ "$current_image_tag" == "$latest_release_tag" ]]; then
      printf 'It is already running the latest released version.\n'
    elif [[ "$current_image_tag" != "latest" ]]; then
      printf 'Note: the running stack is outdated.\n'
    fi
  fi
}

require_command curl
require_command docker

COMPOSE_CMD="$(select_compose_command)"
LATEST_RELEASE_TAG="$(latest_release_ref || true)"
DEFAULT_REF="${LATEST_RELEASE_TAG:-main}"

if ! ref_has_prod_compose "$DEFAULT_REF"; then
  DEFAULT_REF="main"
fi

DEFAULT_IMAGE_TAG="$DEFAULT_REF"
if [[ "$DEFAULT_IMAGE_TAG" == "main" ]]; then
  DEFAULT_IMAGE_TAG="latest"
fi

INSTALL_DIR="${PLAYQUERY_INSTALL_DIR:-}"
if [[ -z "$INSTALL_DIR" ]]; then
  INSTALL_DIR="$(prompt_default 'Install directory' "$HOME/.playquery")"
fi

mkdir -p "$INSTALL_DIR"

COMPOSE_FILE="$INSTALL_DIR/docker-compose.prod.yaml"
ENV_FILE="$INSTALL_DIR/.env"
STACK_RUNNING=false

if stack_is_running "$INSTALL_DIR" "$COMPOSE_FILE"; then
  STACK_RUNNING=true
  print_existing_stack_status "$INSTALL_DIR" "$ENV_FILE" "$LATEST_RELEASE_TAG"

  if ! prompt_confirm 'Re-configure the existing stack' 'n'; then
    exit 0
  fi
fi

RELEASE_REF="${PLAYQUERY_RELEASE_REF:-}"
if [[ -z "$RELEASE_REF" ]]; then
  RELEASE_REF="$(prompt_default 'Release ref to install' "$DEFAULT_REF")"
fi

IMAGE_TAG="${PLAYQUERY_IMAGE_TAG:-}"
if [[ -z "$IMAGE_TAG" ]]; then
  IMAGE_TAG="$(prompt_default 'Docker image tag' "$DEFAULT_IMAGE_TAG")"
fi

MCP_PORT="${PLAYQUERY_MCP_PORT:-}"
if [[ -z "$MCP_PORT" ]]; then
  MCP_PORT="$(prompt_default 'MCP host port' "$(value_or_default "$ENV_FILE" "PLAYQUERY_MCP_PORT" '8000')")"
fi

AI_MODEL="${PLAYQUERY_AI_MODEL:-}"
if [[ -z "$AI_MODEL" ]]; then
  AI_MODEL="$(prompt_default 'AI model' "$(value_or_default "$ENV_FILE" "PLAYQUERY_AI_MODEL" 'claude-haiku-4.5')")"
fi

IS_OPENAI=false
if [[ "$AI_MODEL" == openai* || "$AI_MODEL" == *openai* || "$AI_MODEL" == *Groq* || "$AI_MODEL" == *DeepInfra* || "$AI_MODEL" == *Cerebras* || "$AI_MODEL" == *Ollama* ]]; then
  IS_OPENAI=true
fi

if [[ -n "${PLAYQUERY_AI_TYPE:-}" ]]; then
  AI_TYPE="$PLAYQUERY_AI_TYPE"
else
  if [[ "$IS_OPENAI" == true ]]; then
    heuristic_default='openai'
  else
    heuristic_default='copilot'
  fi
  ai_type_default="$(value_or_default "$ENV_FILE" "PLAYQUERY_AI_TYPE" "$heuristic_default")"
  AI_TYPE="$(prompt_default 'AI provider type' "$ai_type_default")"
fi

API_KEY=""
BASE_URL=""
GITHUB_TOKEN=""

if provider_is_known "$AI_TYPE"; then
  while IFS= read -r _field_def; do
    [[ -n "$_field_def" ]] || continue
    prompt_provider_field "$_field_def"
  done < <(provider_field_defs "$AI_TYPE")
fi

LOGGING_LEVEL="${PLAYQUERY_LOGGING_LEVEL:-}"
if [[ -z "$LOGGING_LEVEL" ]]; then
  LOGGING_LEVEL="$(prompt_default 'Logging level' "$(value_or_default "$ENV_FILE" "PLAYQUERY_LOGGING_LEVEL" 'DEBUG')")"
fi

CORS_ORIGINS="${PLAYQUERY_MCP_CORS_ORIGINS:-}"
if [[ -z "$CORS_ORIGINS" ]]; then
  CORS_ORIGINS="$(prompt_default 'Allowed CORS origins' "$(value_or_default "$ENV_FILE" "PLAYQUERY_MCP_CORS_ORIGINS" '*')")"
fi

curl -fsSL "${RAW_BASE}/${RELEASE_REF}/docker-compose.prod.yaml" -o "$COMPOSE_FILE"

cat > "$ENV_FILE" <<EOF
PLAYQUERY_IMAGE_TAG=${IMAGE_TAG}
PLAYQUERY_AI_TYPE=${AI_TYPE}
PLAYQUERY_AI_MODEL=${AI_MODEL}
PLAYQUERY_AI_API_KEY=${API_KEY}
PLAYQUERY_AI_BASE_URL=${BASE_URL}
PLAYQUERY_LOGGING_LEVEL=${LOGGING_LEVEL}
PLAYQUERY_MCP_PORT=${MCP_PORT}
PLAYQUERY_MCP_CORS_ORIGINS=${CORS_ORIGINS}
PLAYQUERY_AI_GITHUB_TOKEN=${GITHUB_TOKEN}
EOF

cd "$INSTALL_DIR"
if [[ "$STACK_RUNNING" == true ]]; then
  $COMPOSE_CMD -f "$COMPOSE_FILE" down
fi
$COMPOSE_CMD -f "$COMPOSE_FILE" pull || true
$COMPOSE_CMD -f "$COMPOSE_FILE" up -d

printf '\nPlayQuery is starting.\n'
printf 'Install directory: %s\n' "$INSTALL_DIR"
printf 'MCP endpoint: http://localhost:%s/mcp\n' "$MCP_PORT"
