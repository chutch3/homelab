#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Local mode uses an already-provisioned disposable MariaDB database and Ruby.
# CI/default mode provisions the identical runtime through Docker Compose.
if [[ ${PROJECTMONITOR_TEST_LOCAL:-0} == 1 ]]; then
    cd app
    bundle check
    npm ci
    exec bash script/test-all.sh
fi

compose=(docker compose -p "projectmonitor-tests-$$" -f compose.test.yml)
trap '"${compose[@]}" down --volumes --remove-orphans' EXIT
"${compose[@]}" up --build --abort-on-container-exit --exit-code-from tests
