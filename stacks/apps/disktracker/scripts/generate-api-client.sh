#!/usr/bin/env bash
# Regenerate the collector's disktracker API client from the backend's OpenAPI spec.
# With --check, regenerate into a scratch directory and fail if the committed client differs.
set -euo pipefail

readonly GENERATOR="openapi-python-client==0.29.1"
app_dir="${DISKTRACKER_APP_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
readonly app_dir
readonly client_dir="${app_dir}/collector/disktracker_api"
work_dir="$(mktemp -d)"
readonly work_dir
trap 'rm -rf "${work_dir}"' EXIT

generate() {
    local output="$1"
    # create_app only builds the app; nothing connects to this placeholder database.
    (cd "${app_dir}/backend" && uv run --frozen python -c '
import json
from disktracker.web import create_app
print(json.dumps(create_app("postgresql+psycopg://unused@localhost/unused").openapi(), indent=2, sort_keys=True))
') > "${work_dir}/openapi.json"
    uvx --from "${GENERATOR}" openapi-python-client generate \
        --path "${work_dir}/openapi.json" --output-path "${output}" \
        --meta none --config "${app_dir}/collector/api-client.yml" >&2
}

main() {
    case "${1:-}" in
        "")
            generate "${work_dir}/client"
            rm -rf "${client_dir}"
            mv "${work_dir}/client" "${client_dir}"
            ;;
        --check)
            generate "${work_dir}/client"
            if ! diff -r -x __pycache__ "${client_dir}" "${work_dir}/client" >&2; then
                echo "The collector's API client is out of date; run scripts/generate-api-client.sh" >&2
                return 1
            fi
            ;;
        *)
            echo "usage: $(basename -- "$0") [--check]" >&2
            return 2
            ;;
    esac
}

main "$@"
