#!/usr/bin/env bash
# Regenerate the backend's description of the kinds of source from the collector's readers:
# each reader describes its own settings, and the backend checks stores against that and
# serves it to the Admin form. With --check, fail if the committed description differs.
set -euo pipefail

app_dir="${DISKTRACKER_APP_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
readonly app_dir
readonly kinds_file="${app_dir}/backend/disktracker/source_kinds.json"
work_dir="$(mktemp -d)"
readonly work_dir
trap 'rm -rf "${work_dir}"' EXIT

generate() {
    (cd "${app_dir}/collector" && uv run --frozen python -m collector.kinds) > "$1"
}

main() {
    case "${1:-}" in
        "" | --check) ;;
        *)
            echo "usage: generate-source-kinds.sh [--check]" >&2
            return 2
            ;;
    esac
    generate "${work_dir}/source_kinds.json"
    if [[ -z "${1:-}" ]]; then
        mv "${work_dir}/source_kinds.json" "${kinds_file}"
    elif ! diff "${kinds_file}" "${work_dir}/source_kinds.json" >&2; then
        echo "The backend's source kinds are out of date; run scripts/generate-source-kinds.sh" >&2
        return 1
    fi
}

main "$@"
