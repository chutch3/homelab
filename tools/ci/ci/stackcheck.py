"""The invariants every stack in the tree must hold — the `ci check-stacks` verdict.

Two rules today: the ``x-homelab`` declarations resolve and are complete, and
every stack declares a healthcheck. They share a command because they share a
question — is this tree deployable — and a tree read once answers both.

Convergence is what makes the second rule matter: the deploy waits for each
stack to converge before starting the next, and Swarm calls a task ``running``
the moment its process starts unless a healthcheck says otherwise. See
docs/architecture/overview.md, "What converged means".
"""

from __future__ import annotations

import logging

from ci.stackgraph import DependencyGraph, UnresolvedGraph

log = logging.getLogger(__name__)

# The ratchet: stacks that predate the healthcheck rule. It only ever shrinks —
# a new stack must declare one, and a name here that has since gained one is a
# test failure, so the list cannot rot into a permanent exemption.
WITHOUT_HEALTHCHECK = frozenset({
    "actual_server", "archivebox", "beholder", "cert-sync-nas", "cicd",
    "claudecodeui", "code-server", "downloads", "drawio", "emby", "fiber",
    "flaresolverr", "freshrss", "gamarr", "github-runner", "homepage", "kiwix",
    "kolibri", "komga", "kopia", "librechat", "llama-cpp", "mealie", "mlflow",
    "node-red", "open-webui", "profilarr", "prowlarr", "radarr", "rstudio",
    "searxng", "sonarr", "takeout-manager", "uptime-kuma", "vaultwarden",
    "warden", "whisparr",
})


def check_stacks(graph: DependencyGraph) -> int:
    """Every invariant, over one read of the tree. Non-zero names what failed."""
    try:
        stacks = graph.stacks()
        graph.resolve()
    except UnresolvedGraph as exc:
        log.error("✗ %s", exc)
        return 1

    failed = _check_declarations(graph) | _check_healthchecks(graph)
    if failed:
        return 1
    log.info("✓ %d stacks resolve, declare what they need, and say when they are ready", len(stacks))
    return 0


def _check_declarations(graph: DependencyGraph) -> bool:
    if not (missing := graph.undeclared()):
        return False
    log.error("✗ dependencies visible in the compose file but not declared in x-homelab.requires:")
    for stack, requires in sorted(missing.items()):
        log.error("    %s: %s", stack, ", ".join(sorted(requires)))
    return True


def _check_healthchecks(graph: DependencyGraph) -> bool:
    bare = sorted(
        name
        for name, stack in graph.stacks().items()
        if not stack.healthchecked and name not in WITHOUT_HEALTHCHECK
    )
    if not bare:
        return False
    log.error("✗ stacks with no healthcheck — the deploy cannot tell when they are ready:")
    for name in bare:
        log.error("    %s", name)
    return True
