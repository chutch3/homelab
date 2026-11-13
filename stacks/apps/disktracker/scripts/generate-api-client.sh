#!/usr/bin/env bash
# Regenerate, from the backend's OpenAPI spec, the collector's disktracker API client and the
# frontend's API types. With --check, regenerate into a scratch directory and fail if either
# committed copy differs.
set -euo pipefail

readonly GENERATOR="openapi-python-client==0.29.1"
app_dir="${DISKTRACKER_APP_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
readonly app_dir
readonly client_dir="${app_dir}/collector/disktracker_api"
readonly types_file="${app_dir}/frontend/src/api-schema.ts"
work_dir="$(mktemp -d)"
readonly work_dir
trap 'rm -rf "${work_dir}"' EXIT

generate() {
    local output="$1" types="$2"
    # create_app only builds the app; nothing connects to this placeholder database. A model
    # read and written differently has an -Input and an -Output schema under one title, and the
    # generator names classes by title, so each is titled by its own name.
    (cd "${app_dir}/backend" && uv run --frozen python -c '
import json, os
from disktracker.main import create_app
os.environ["DISKTRACKER_DATABASE_URL"] = "postgresql+psycopg://unused@localhost/unused"
spec = create_app().openapi()
for name, schema in spec["components"]["schemas"].items():
    if name.endswith(("-Input", "-Output")):
        schema["title"] = name.replace("-", "")
print(json.dumps(spec, indent=2, sort_keys=True))
') > "${work_dir}/openapi.json"
    uvx --from "${GENERATOR}" openapi-python-client generate \
        --path "${work_dir}/openapi.json" --output-path "${output}" \
        --meta none --config "${app_dir}/collector/api-client.yml" >&2
    # Match the repository's whitespace hooks before comparing generated output.
    # Standard-library cleanup keeps this deterministic without adding a formatter dependency.
    uv run --frozen --project "${app_dir}/backend" python - "${output}" <<'PY'
from pathlib import Path
import sys

for path in Path(sys.argv[1]).rglob("*.py"):
    text = "\n".join(line.rstrip() for line in path.read_text().splitlines()).rstrip()
    path.write_text(text + "\n" if text else "")
PY
    # The frontend's generator is the one its package.json pins.
    # A field is optional exactly when the spec says so: it already says which defaults the API
    # always gives back.
    (cd "${app_dir}/frontend" && npx --no-install openapi-typescript "${work_dir}/openapi.json" \
        --default-non-nullable false \
        --output "${types}" >&2)
}

main() {
    case "${1:-}" in
        "")
            generate "${work_dir}/client" "${types_file}"
            rm -rf "${client_dir}"
            mv "${work_dir}/client" "${client_dir}"
            ;;
        --check)
            generate "${work_dir}/client" "${work_dir}/api-schema.ts"
            if ! diff -r -x __pycache__ "${client_dir}" "${work_dir}/client" >&2; then
                echo "The collector's API client is out of date; run scripts/generate-api-client.sh" >&2
                return 1
            fi
            if ! diff "${types_file}" "${work_dir}/api-schema.ts" >&2; then
                echo "The frontend's API types are out of date; run scripts/generate-api-client.sh" >&2
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
