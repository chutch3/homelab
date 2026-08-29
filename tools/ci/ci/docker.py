"""The Swarm as the docker CLI describes it.

Everything that knows docker exists is here: the argv, the format templates, and
the JSON they come back as. Every read asks for JSON, so nothing parses
formatted text. Nothing here writes — a plan that mutated the thing it is
describing would be a lie, and nothing here decides what the answers *mean*.

Only services are read. `docker stack ls` is a grouping of the namespace label
every service already carries, so asking for it would be a second, weaker source
for something the first read already knows.
"""

from __future__ import annotations

import json

from ci.ports import CommandRunner
from ci.stackstate import Service

SERVICE_LS = ["docker", "service", "ls", "--format", "{{json .}}"]
STACK_LABEL = "com.docker.stack.namespace"
INSPECT_FORMAT = (
    '{"Name":{{json .Spec.Name}},'
    f'"Stack":{{{{json (index .Spec.Labels "{STACK_LABEL}")}}}},'
    '"Update":{{if .UpdateStatus}}{{json .UpdateStatus.State}}{{else}}"none"{{end}}}'
)
SERVICE_INSPECT = ["docker", "service", "inspect", "--format", INSPECT_FORMAT]


class ClusterUnreachable(Exception):
    """The cluster could not be read, so no state can be reported."""


class Docker:
    """Reads the Swarm through the docker CLI."""

    def __init__(self, commands: CommandRunner) -> None:
        self._commands = commands

    def inspect(self, names: list[str]) -> list[dict[str, str]]:
        """Inspects the given services, returning their details."""
        inspect_outcome = self._commands.run(SERVICE_INSPECT + names, capture=True)
        if not inspect_outcome.ok:
            return []
        return [json.loads(line) for line in inspect_outcome.stdout.splitlines() if line.strip()]

    def ls(self) -> list[dict[str, str]]:
        """Lists all services, returning their details."""
        ls_outcome = self._commands.run(SERVICE_LS, capture=True)
        if not ls_outcome.ok:
            return []
        return [json.loads(line) for line in ls_outcome.stdout.splitlines() if line.strip()]

    def services(self) -> list[Service]:
        """Every service the cluster holds, with the stack it belongs to."""
        listed = self.ls()
        inspect_data = self.inspect([service["Name"] for service in listed])
        return [
            Service.from_row(
                name=list["Name"],
                stack=inspect["Stack"],
                update=inspect["Update"],
                replicas=list["Replicas"],
            )
            for list, inspect in zip(listed, inspect_data)
            if list and inspect
        ]
