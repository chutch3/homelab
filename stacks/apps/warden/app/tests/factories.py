from __future__ import annotations

from datetime import datetime

from polyfactory.factories.dataclass_factory import DataclassFactory
from sqlmodel import SQLModel, create_engine

from warden.models import ArrType, Indexer, ProwlarrApp, WantedItem, WantKind
from warden.repositories.backoff import SearchBackoffRepository
from warden.repositories.efficacy import SearchAttemptRepository
from warden.repositories.progress import QueueProgressRepository


def _in_memory(repo_cls):
    """A repository backed by a fresh in-memory SQLite engine (orchestrator/repo tests)."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return repo_cls(engine)


def make_progress_repo() -> QueueProgressRepository:
    return _in_memory(QueueProgressRepository)


def make_efficacy_repo() -> SearchAttemptRepository:
    return _in_memory(SearchAttemptRepository)


def make_backoff_repo() -> SearchBackoffRepository:
    return _in_memory(SearchBackoffRepository)


class WantedItemFactory(DataclassFactory[WantedItem]):
    __model__ = WantedItem


def wanted_item(instance: str, rid: int, kind: WantKind = WantKind.MISSING,
                last_search_time: datetime | None = None) -> WantedItem:
    return WantedItemFactory.build(instance=instance, remote_id=rid, title=f"t{rid}", kind=kind,
                                   last_search_time=last_search_time)


def missing_item(instance: str, rid: int) -> WantedItem:
    return wanted_item(instance, rid, WantKind.MISSING)


class IndexerFactory(DataclassFactory[Indexer]):
    __model__ = Indexer
    id = 1
    name = "idx"
    enabled = True
    tags = (1,)
    categories = (2000,)
    query_limit = 20


class ProwlarrAppFactory(DataclassFactory[ProwlarrApp]):
    __model__ = ProwlarrApp
    implementation = "Radarr"
    tags = (2, 1)
    sync_categories = (2000, 2040)


def indexer(**overrides) -> Indexer:
    return IndexerFactory.build(**overrides)


def prowlarr_app(**overrides) -> ProwlarrApp:
    return ProwlarrAppFactory.build(**overrides)


class FakeArrClient:
    """In-memory ArrClient double for orchestrator tests (satisfies ArrClientProtocol
    structurally; a behaviour double, like fiber's FakeProbeProcess)."""

    def __init__(self, name: str, missing: list[WantedItem], cutoff: list[WantedItem] | None = None,
                 raises: bool = False, arr_type: ArrType = ArrType.RADARR, queue=None,
                 remove_raises: bool = False, grabs=None, grab_raises: bool = False,
                 root_folders=None, root_folders_raises: bool = False) -> None:
        self.name = name
        self.arr_type = arr_type
        self._missing = missing
        self._cutoff = cutoff or []
        self._raises = raises
        self._queue = queue or []
        self._remove_raises = remove_raises
        self._grabs = grabs or []
        self._grab_raises = grab_raises
        self._root_folders = root_folders or []
        self._root_folders_raises = root_folders_raises
        self.searched: list[list[int]] = []
        self.removed: list[int] = []
        self.grabbed_since: list = []
        self.root_folder_calls: int = 0

    async def list_missing(self) -> list[WantedItem]:
        if self._raises:
            raise RuntimeError("boom")
        return list(self._missing)

    async def list_cutoff_unmet(self) -> list[WantedItem]:
        return list(self._cutoff)

    async def trigger_search(self, ids: list[int]) -> None:
        self.searched.append(ids)

    async def list_queue(self):
        if self._raises:
            raise RuntimeError("boom")
        return list(self._queue)

    async def remove_queue_item(self, queue_id: int, *, remove_from_client: bool = True,
                                blocklist: bool = True) -> None:
        if self._remove_raises:
            raise RuntimeError("remove failed")
        self.removed.append(queue_id)

    async def list_grabbed_since(self, since):
        self.grabbed_since.append(since)
        if self._grab_raises:
            raise RuntimeError("history failed")
        return list(self._grabs)

    async def list_root_folders(self):
        self.root_folder_calls += 1
        if self._root_folders_raises:
            raise RuntimeError("rootfolder failed")
        return list(self._root_folders)
