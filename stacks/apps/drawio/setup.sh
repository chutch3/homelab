#!/usr/bin/env bash
set -euo pipefail

echo "draw.io is stateless — no persistent storage or setup required."
echo "Deploy with: task ansible:deploy:stack -- -e \"stack_name=drawio\""
