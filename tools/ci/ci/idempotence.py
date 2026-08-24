"""Second-run idempotence — the `ci idempotence` logic.

A converged playbook reports ``changed=0`` when run again. :func:`parse_recap`
and :func:`violations` are pure; :class:`IdempotenceCheck` takes the command
runner, so its tests drive both runs without invoking ansible.
"""

from __future__ import annotations

import re

from ci.adapters import CommandRunner, Console

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_HOST_LINE = re.compile(r"^(?P<host>\S+)\s*:\s+(?P<counters>(?:\w+=\d+\s*)+)$")
_FATAL = ("failed", "unreachable")


def parse_recap(output: str) -> dict[str, dict[str, int]]:
    """Host -> counter map, read from the PLAY RECAP block of an Ansible run.

    Raises ValueError when there is no recap: a run that died before reaching
    one reports no changes either, and must not be mistaken for a clean run.
    """
    lines = _ANSI.sub("", output).splitlines()
    for i, line in enumerate(lines):
        if line.startswith("PLAY RECAP"):
            break
    else:
        raise ValueError("no PLAY RECAP in output — the run did not complete")

    recap: dict[str, dict[str, int]] = {}
    for line in lines[i + 1:]:
        match = _HOST_LINE.match(line.strip())
        if not match:
            if recap:  # the block ended
                break
            continue
        recap[match.group("host")] = {
            k: int(v) for k, v in (p.split("=") for p in match.group("counters").split())
        }
    if not recap:
        raise ValueError("PLAY RECAP names no hosts")
    return recap


def violations(recap: dict[str, dict[str, int]]) -> dict[str, str]:
    """Hosts whose second run was not a no-op, mapped to why."""
    out = {}
    for host, counters in recap.items():
        fatal = [k for k in _FATAL if counters.get(k)]
        if fatal:
            out[host] = ", ".join(f"{k}={counters[k]}" for k in fatal)
        elif counters.get("changed"):
            out[host] = f"changed={counters['changed']}"
    return out


class IdempotenceCheck:
    """Runs a playbook twice; the second run must report no change."""

    def __init__(self, commands: CommandRunner, console: Console) -> None:
        self._commands = commands
        self._console = console

    def verify(self, playbook: str, ansible_args: list[str] | None = None) -> int:
        cmd = ["ansible-playbook", playbook, *(ansible_args or [])]
        for run in (1, 2):
            self._console.out(f"\n=== idempotence: run {run}/2 — {' '.join(cmd)}\n")
            result = self._commands.run(cmd, capture=True)
            self._console.out(result.stdout)
            self._console.err(result.stderr)

            if run == 1:
                if not result.ok:
                    self._console.out(
                        f"\n✗ first run failed (rc={result.returncode}) — nothing to compare"
                    )
                    return result.returncode
                continue

            try:
                recap = parse_recap(result.stdout)
            except ValueError as exc:
                self._console.out(f"\n✗ {exc}")
                return 1
            if bad := violations(recap):
                self._console.out("\n✗ second run was not a no-op:")
                for host, why in sorted(bad.items()):
                    self._console.out(f"    {host}: {why}")
                return 1
            self._console.out(f"\n✓ second run reported no change on {len(recap)} host(s)")
        return 0
