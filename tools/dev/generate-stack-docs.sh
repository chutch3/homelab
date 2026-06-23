#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STACKS_DIR="${REPO_ROOT}/stacks/apps"
OUTPUT_DIR="${REPO_ROOT}/docs/services"
INFRA_STACKS=("${REPO_ROOT}/stacks/reverse-proxy" "${REPO_ROOT}/stacks/monitoring" "${REPO_ROOT}/stacks/dns")

mkdir -p "${OUTPUT_DIR}"


count=0

for compose in "${STACKS_DIR}"/*/docker-compose.yml; do
    stack_name="$(basename "$(dirname "${compose}")")"
    output_file="${OUTPUT_DIR}/${stack_name}.md"
    dockumentor -c "${compose}" -t homelab.md -o "${output_file}" 2>/dev/null
    count=$((count + 1))
done

for infra_dir in "${INFRA_STACKS[@]}"; do
    compose="${infra_dir}/docker-compose.yml"
    if [[ -f "${compose}" ]]; then
        stack_name="$(basename "${infra_dir}")"
        output_file="${OUTPUT_DIR}/${stack_name}.md"
        dockumentor -c "${compose}" -t homelab.md -o "${output_file}" 2>/dev/null
        count=$((count + 1))
    fi
done

echo "✅ Generated docs for ${count} stacks in ${OUTPUT_DIR}"
