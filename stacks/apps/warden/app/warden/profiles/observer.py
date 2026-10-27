from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Literal, cast

from warden.arr_service import ArrService
from warden.clock import SystemClock
from warden.metrics import Metrics
from warden.profiles.compare import compare_profiles, select_profiles
from warden.profiles.sources import ProfileSource
from warden.profiles.settings import parse_selection


class Observer:
    def __init__(
        self, source: ProfileSource, arr: ArrService, selections: Mapping[str, str],
        metrics: Metrics, clock: SystemClock, emit: Callable[[str, dict[str, Any]], None],
        compare: Callable[..., dict[str, Any]] = compare_profiles,
    ) -> None:
        self.source = source
        self.arr = arr
        self.compare = compare
        self.selections = dict(selections)
        self.metrics = metrics
        self.clock = clock
        self.emit = emit

    async def tick(self) -> None:
        targets = []
        for name in self.arr.sources:
            try:
                selection = parse_selection(self.selections.get(name))
                if selection != []:
                    targets.append((name, selection))
            except ValueError:
                self.metrics.profile_failed(name)
                self.emit("profile_config_error", {"source": name, "reason": "invalid profile filter"})
        if not targets:
            return
        try:
            snapshot = await self.source.fetch()
        except Exception as exc:
            for name, _ in targets:
                self.metrics.profile_failed(name)
            self.emit("profile_repository_error", {"error_type": type(exc).__name__})
            return
        for name, selection in targets:
            try:
                source = cast(Literal["radarr", "sonarr"], name)
                selected = select_profiles(source, snapshot.documents, selection)
                profiles, formats = await self.arr.get_profiles(name)
                report = self.compare(source, snapshot.documents, profiles, formats, selected)
                counts = {kind: len({change["name"] for change in report["changes"] if change["kind"] == kind})
                          for kind in ("profile", "custom_format")}
                self.metrics.profile_checked(source, counts, len(report["conflicts"]), self.clock.now().timestamp())
                self.emit("profile_checked", {"source": source, "commit": snapshot.commit, "profiles": selected,
                                              "changes": report["changes"], "conflicts": report["conflicts"]})
            except Exception as exc:
                self.metrics.profile_failed(name)
                self.emit("profile_check_error", {"source": name, "commit": snapshot.commit,
                                                   "error_type": type(exc).__name__})
