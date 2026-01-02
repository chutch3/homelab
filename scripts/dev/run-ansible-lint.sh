#!/bin/bash
set -e

# This script is a wrapper for ansible-lint that only runs it if there are
# ansible files to be linted. This is to prevent the pre-commit hook from
# running on every commit, even if there are no ansible changes.

ansible_files=()
for file in "$@"; do
    # Check if the file is within ansible/playbooks or ansible/roles and is a YAML file
    if [[ "$file" =~ ^ansible/(playbooks|roles)/.*\.(yml|yaml)$ ]]; then
        ansible_files+=("$file")
    fi
done

if [ ${#ansible_files[@]} -gt 0 ]; then
    ansible-lint "${ansible_files[@]}" --profile=basic
else
    # If no ansible files, exit successfully without running ansible-lint
    echo "No ansible files found to lint. Skipping ansible-lint."
    exit 0
fi
