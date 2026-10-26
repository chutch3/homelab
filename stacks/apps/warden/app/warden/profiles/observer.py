from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal, cast

from warden.clients.arr import ArrClient
from warden.clock import SystemClock
from warden.metrics import Metrics
from warden.profiles.compare import compare_catalog, select_profiles
from warden.profiles.catalog import CatalogSource
from warden.profiles.settings import parse_selection


class Observer:
    def __init__(
        self, catalog: CatalogSource, clients: Sequence[ArrClient], selections: Mapping[str, str],
        metrics: Metrics, clock: SystemClock, emit: Callable[[str, dict[str, Any]], None],
    ) -> None:
        self.catalog = catalog
        self.clients = list(clients)
        self.selections = dict(selections)
        self.metrics = metrics
        self.clock = clock
        self.emit = emit

    async def tick(self) -> None:
        targets = []
        for client in self.clients:
            try:
                selection = parse_selection(self.selections.get(client.name))
                if selection != []:
                    targets.append((client, selection))
            except ValueError:
                self.metrics.profile_failed(client.name)
                self.emit("profile_config_error", {"source": client.name, "reason": "invalid profile filter"})
        if not targets:
            return
        try:
            snapshot = await self.catalog.fetch()
        except Exception as exc:
            for client, _ in targets:
                self.metrics.profile_failed(client.name)
            self.emit("profile_repository_error", {"error_type": type(exc).__name__})
            return
        for client, selection in targets:
            try:
                source = cast(Literal["radarr", "sonarr"], client.name)
                selected = select_profiles(source, snapshot.documents, selection)
                profiles = await client.list_quality_profiles()
                formats = await client.list_custom_formats()
                report = compare_catalog(source, snapshot.documents, profiles, formats, selected)
                counts = {kind: len({change["name"] for change in report["changes"] if change["kind"] == kind})
                          for kind in ("profile", "custom_format")}
                self.metrics.profile_checked(source, counts, len(report["conflicts"]), self.clock.now().timestamp())
                self.emit("profile_checked", {"source": source, "commit": snapshot.commit, "profiles": selected,
                                              "changes": report["changes"], "conflicts": report["conflicts"]})
            except Exception as exc:
                self.metrics.profile_failed(client.name)
                self.emit("profile_check_error", {"source": client.name, "commit": snapshot.commit,
                                                   "error_type": type(exc).__name__})
