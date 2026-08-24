"""Configuration the CI tool reads, and the one decision involved in reading it.

`task ...` hands .env to a command via the Taskfile's ``dotenv:``; running the
CLI directly does not, and the two must not disagree about what is switched on.
:func:`merge_env` is pure — the composition root does the file read.
"""

from __future__ import annotations

from pathlib import Path

from ci.ports import FileSystem

# Providers the cluster can be configured without. Deploy already skips the dns
# stack on primary_dns_managed (ansible/playbooks/deploy/stacks.yml); the graph
# has to drop the edges into it too, or every routed stack becomes unresolvable.
CAPABILITY_GATES = {"dns": "PRIMARY_DNS_MANAGED"}

FALSEY = ("false", "no", "0", "")


def parse_dotenv(text: str) -> dict[str, str]:
    """The assignments in a .env file, unquoted, ignoring comments and junk."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip().removeprefix("export ").strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key, value = key.strip(), value.strip()
        if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def merge_env(dotenv_text: str, process_env: dict[str, str]) -> dict[str, str]:
    """``.env`` overlaid with the process environment, which wins."""
    return {**parse_dotenv(dotenv_text), **process_env}


def disabled_providers(env: dict[str, str], gates: dict[str, str] | None = None) -> set[str]:
    """Provider stacks this environment has switched off."""
    return {
        stack
        for stack, var in (CAPABILITY_GATES if gates is None else gates).items()
        if env.get(var, "true").strip().lower() in FALSEY
    }


def load_env(filesystem: FileSystem, repo_root: str | Path, process_env: dict[str, str]) -> dict[str, str]:
    """Read .env through the filesystem port and merge it. The only I/O here."""
    dotenv = Path(repo_root) / ".env"
    text = filesystem.read_text(dotenv) if filesystem.exists(dotenv) else ""
    return merge_env(text, process_env)
