"""Second-run idempotence — the `ci idempotence` logic.

An Ansible run that converges reports ``changed=0`` the second time. That number
is the cheapest evidence we have that a playbook is declarative rather than
imperative, and it is what "re-running is the resume" rests on: if a re-run
against converged infrastructure genuinely does nothing, a killed run needs no
recovery mode, only the same command again.

:func:`parse_recap` and :func:`violations` are pure and unit-tested;
:func:`verify` is the subprocess wrapper that runs the playbook twice.
"""

from __future__ import annotations

import re
import subprocess
import sys

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_RECAP_HEADER = re.compile(r"^PLAY RECAP\b")
_HOST_LINE = re.compile(r"^(?P<host>\S+)\s*:\s+(?P<counters>(?:\w+=\d+\s*)+)$")

# A second run may not change anything, and must have actually run: a playbook
# that died before touching the host also reports changed=0.
_FATAL = ("failed", "unreachable")


def parse_recap(output: str) -> dict[str, dict[str, int]]:
    """Host -> counter map, read from the PLAY RECAP block of an Ansible run.

    Raises ValueError when there is no recap — a run that never got that far
    proves nothing, and must not be mistaken for a clean one.
    """
    lines = _ANSI.sub("", output).splitlines()
    for i, line in enumerate(lines):
        if _RECAP_HEADER.match(line):
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


def verify(playbook: str, ansible_args: list[str] | None = None) -> int:
    """Run the playbook twice; fail if the second run reports any change."""
    cmd = ["ansible-playbook", playbook, *(ansible_args or [])]
    for run in (1, 2):
        print(f"\n=== idempotence: run {run}/2 — {' '.join(cmd)}\n", flush=True)
        result = subprocess.run(cmd, capture_output=True, text=True)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        if run == 1:
            # The first run is allowed to change everything; it only has to work.
            if result.returncode != 0:
                print(f"\n✗ first run failed (rc={result.returncode}) — nothing to compare")
                return result.returncode
            continue

        try:
            recap = parse_recap(result.stdout)
        except ValueError as exc:
            print(f"\n✗ {exc}")
            return 1
        bad = violations(recap)
        if bad:
            print("\n✗ second run was not a no-op:")
            for host, why in sorted(bad.items()):
                print(f"    {host}: {why}")
            print("\n  A task reported a change against already-converged state. Give it a")
            print("  real changed_when, or make it stop rewriting identical content.")
            return 1
        print(f"\n✓ second run reported no change on {len(recap)} host(s)")
    return 0
