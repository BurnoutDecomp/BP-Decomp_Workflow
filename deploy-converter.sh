#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
deploy_dir="$repo_dir/tools/assets/converter_ui/deploy"
cd "$repo_dir"
command -v docker >/dev/null || { echo "Install Docker Engine and the Compose plugin first. See deploy/README.md." >&2; exit 1; }
docker compose version >/dev/null
if [[ $# -gt 0 ]]; then
    case "$1" in
        *[!a-zA-Z0-9.-]*|""|-*|.*) echo "Pass a DNS hostname, for example convert.example.com" >&2; exit 2 ;;
    esac
    if [[ -f "$deploy_dir/.env" ]]; then
        echo "Existing deploy/.env kept. Edit PARADISE_DOMAIN there to change the hostname."
    else
        umask 077
        printf 'PARADISE_DOMAIN=%s\n' "$1" > "$deploy_dir/.env"
    fi
fi
if [[ ! -f "$deploy_dir/.env" ]]; then
    echo "Usage: bash deploy-converter.sh convert.example.com" >&2
    echo "Or copy tools/assets/converter_ui/deploy/.env.example to .env and edit it." >&2
    exit 2
fi
git submodule update --init --recursive -- tools/yap tools/volatility
docker compose --env-file "$deploy_dir/.env" -f "$deploy_dir/compose.yaml" up -d --build
docker compose --env-file "$deploy_dir/.env" -f "$deploy_dir/compose.yaml" ps
echo "Deployment started. Caddy obtains HTTPS once DNS points here and ports 80/443 are reachable."
