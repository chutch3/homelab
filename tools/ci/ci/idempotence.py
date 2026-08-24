"""Second-run idempotence — the `ci idempotence` logic.

A converged playbook reports ``changed=0`` when run again. :func:`parse_recap`
and :func:`violations` are pure; :class:`IdempotenceCheck` takes the command
runner, so its tests drive both runs without invoking ansible.
"""

from __future__ import annotations

import logging
import re

from ci.ports import CommandRunner, Output

log = logging.getLogger(__name__)

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

    def __init__(self, commands: CommandRunner, output: Output) -> None:
        self._commands = commands
        self._output = output

    def verify(self, playbook: str, ansible_args: list[str] | None = None) -> int:
        cmd = ["ansible-playbook", playbook, *(ansible_args or [])]
        for run in (1, 2):
            log.info("=== idempotence: run %d/2 — %s", run, " ".join(cmd))
            result = self._commands.run(cmd, capture=True)
            self._output.raw(result.stdout)
            self._output.raw_err(result.stderr)

            if run == 1:
                if not result.ok:
                    log.error(
                        "✗ first run failed (rc=%d) — nothing to compare", result.returncode
                    )
                    return result.returncode
                continue

            try:
                recap = parse_recap(result.stdout)
            except ValueError as exc:
                log.error("✗ %s", exc)
                return 1
            if bad := violations(recap):
                log.error("✗ second run was not a no-op:")
                for host, why in sorted(bad.items()):
                    log.error("    %s: %s", host, why)
                return 1
            log.info("✓ second run reported no change on %d host(s)", len(recap))
        return 0
