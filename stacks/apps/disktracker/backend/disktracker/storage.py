"""PostgreSQL boundary, exercised with real-database integration tests."""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, cast
from uuid import UUID

from croniter import croniter
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    Uuid,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection, Engine, RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import Select

from disktracker.capacity import capacity_label
from disktracker.kinds import current_settings
from disktracker.prices import comparable_price
from disktracker.rules import (
    CapacityConflict,
    CapacityRequired,
    PriceRequired,
    fill_unknown,
    merge_plan,
    missing_detail,
    new_aliases,
    queue_reason,
    source_key,
    unchanged,
    with_carried_price,
)
from disktracker.schemas import (
    Activity,
    CollectorRun,
    ConditionRule,
    DriveSpecifications,
    ObservationInput,
    OfferEdit,
    PriceInput,
    Resolution,
    ScrapedInput,
    SourceInput,
)
from disktracker.specifications import Specifications

metadata = MetaData()
drives = Table(
    "drives",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("mpn", String(100), nullable=False, unique=True),
    Column("capacity_gb", Integer, nullable=False),
    Column("specifications", JSONB, nullable=False, server_default="{}"),
    Column("brand", String(60)),
)
sources = Table(
    "sources",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("key", String(40), nullable=False, unique=True),
    Column("name", String(80), nullable=False, unique=True),
    Column("kind", String(20), nullable=False),
    Column("settings", JSONB, nullable=False, server_default="{}"),
    Column("base_url", Text, nullable=False),
    Column("schedule", String(100), nullable=False),
    Column("enabled", Boolean, nullable=False),
    Column("transport", String(20), nullable=False, server_default="direct"),
    Column("basis", String(20), nullable=False),
    Column("notes", Text, nullable=False),
    Column("run_requested_at", DateTime(timezone=True)),
    Column("stop_requested_at", DateTime(timezone=True)),
)
listings = Table(
    "listings",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("title", String(160), nullable=False),
    Column("mpn", String(100), nullable=False),
    Column("store", String(20), nullable=False),
    Column("seller", String(120), nullable=False),
    Column("url", Text),
    Column("condition", String(40), nullable=False),
    Column("drive_id", Uuid, ForeignKey("drives.id"), nullable=False),
    Column("last_checked_at", DateTime(timezone=True)),
    Index("uq_listings_offer", "mpn", "store", "seller", "condition", unique=True),
)
observations = Table(
    "observations",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("listing_id", Uuid, ForeignKey("listings.id"), nullable=False),
    Column("item_price_cents", Integer, nullable=False),
    Column("shipping_cents", Integer),
    Column("in_stock", Boolean, nullable=False, server_default="true"),
    Column("acquisition_method", String(40), nullable=False, server_default="manual"),
    Column("observed_at", DateTime(timezone=True), nullable=False),
    Column("entered_at", DateTime(timezone=True), nullable=False),
    Column("notes", Text, nullable=False),
)
mpn_aliases = Table(
    "mpn_aliases",
    metadata,
    Column("alias", String(100), primary_key=True),
    Column("drive_id", Uuid, ForeignKey("drives.id"), nullable=False),
)
unmatched = Table(
    "unmatched",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("source", String(40), nullable=False),
    Column("url", Text, nullable=False),
    Column("title", String(160), nullable=False),
    Column("seller", String(120), nullable=False),
    Column("mpn", String(100)),
    Column("condition", String(40)),
    Column("capacity_gb", Integer),
    Column("item_price_cents", Integer),
    Column("shipping_cents", Integer),
    Column("in_stock", Boolean, nullable=False),
    Column("reason", String(40), nullable=False),
    Column("first_seen_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
    Index("uq_unmatched_source_url", "source", "url", unique=True),
)
scraped_matches = Table(
    "scraped_matches",
    metadata,
    Column("source", String(40), primary_key=True),
    Column("url", Text, primary_key=True),
    Column("mpn", String(100)),
    Column("condition", String(40)),
    Column("ignored", Boolean, nullable=False, server_default="false"),
)
RUN_COUNTS = ("seen", "recorded", "queued", "ignored", "failed", "rechecked", "recheck_failed")
collector_runs = Table(
    "collector_runs",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("source", String(40), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=False),
    Column("completed", Boolean, nullable=False),
    *(Column(count, Integer, nullable=False) for count in RUN_COUNTS),
    Column("stopped", Boolean, nullable=False, server_default="false"),
)
# The run each source has in progress, as the collector last said while running it.
ACTIVITY_COUNTS = ("seen", "recorded", "queued", "ignored", "failed")
collector_activity = Table(
    "collector_activity",
    metadata,
    Column("source", String(40), primary_key=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    *(Column(count, Integer, nullable=False) for count in ACTIVITY_COUNTS),
)
# When a collector was last heard from: one row, kept at this id.
CONTACT = 1
collector_contact = Table(
    "collector_contact",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("seen_at", DateTime(timezone=True), nullable=False),
)
condition_rules = Table(
    "condition_rules",
    metadata,
    Column("position", Integer, primary_key=True),
    Column("pattern", Text, nullable=False),
    Column("condition", String(40), nullable=False),
)
receipts = Table(
    "save_receipts",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("fingerprint", String(64), nullable=False),
    Column("result", JSONB),
)


class IdempotencyConflict(Exception):
    pass


class ListingNotFound(Exception):
    pass


class DriveNotFound(Exception):
    pass


class UnknownStore(Exception):
    pass


class SourceExists(Exception):
    pass


class SourceNotFound(Exception):
    pass


class SourceKept(Exception):
    """The source cannot be deleted; the message says why."""


class AliasConflict(Exception):
    pass


class UnmatchedNotFound(Exception):
    pass


def timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def run_view(row: dict[str, Any]) -> dict[str, Any]:
    run = {key: value for key, value in row.items() if key != "id"}
    return {
        **run,
        "started_at": timestamp(run["started_at"]),
        "finished_at": timestamp(run["finished_at"]),
    }


def drive_view(row: dict[str, Any], aliases: list[str]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "mpn": row["mpn"],
        "aliases": aliases,
        "brand": row["brand"],
        "capacity_gb": row["capacity_gb"],
        "specifications": Specifications.model_validate(row["specifications"]).model_dump(
            mode="json"
        ),
    }


def part_of(
    connection: Connection, rows: Select[Any], limit: int | None, offset: int
) -> tuple[list[RowMapping], int]:
    """limit of a query's rows from offset (all of them without a limit), and how many rows it
    has in all: what any list served a part at a time is read with."""
    total = connection.execute(
        select(func.count()).select_from(rows.order_by(None).subquery())
    ).scalar_one()
    return list(connection.execute(rows.limit(limit).offset(offset)).mappings()), total


class PostgresListings:
    def __init__(
        self, engine: Engine, now: Callable[[], datetime], next_id: Callable[[], UUID]
    ) -> None:
        self.engine, self.now, self.next_id = engine, now, next_id

    def _observation(self, row: dict[str, Any], capacity_gb: int) -> dict[str, Any]:
        total, unit = comparable_price(row["item_price_cents"], row["shipping_cents"], capacity_gb)
        return {
            "id": str(row["id"]),
            "item_price_cents": row["item_price_cents"],
            "shipping_cents": row["shipping_cents"],
            "shipping_known": row["shipping_cents"] is not None,
            "in_stock": row["in_stock"],
            "observed_at": timestamp(row["observed_at"]),
            "entered_at": timestamp(row["entered_at"]),
            "notes": row["notes"],
            "acquisition_method": row["acquisition_method"],
            "total_cents": total,
            "price_per_tb": unit,
        }

    def _drive(self, connection: Connection, row: dict[str, Any]) -> dict[str, Any]:
        aliases = connection.execute(
            select(mpn_aliases.c.alias)
            .where(mpn_aliases.c.drive_id == row["id"])
            .order_by(mpn_aliases.c.alias)
        ).scalars()
        return drive_view(row, list(aliases))

    def _summaries(self, connection: Connection, chosen: Select[Any]) -> list[dict[str, Any]]:
        """The chosen offers with their latest price, in a fixed number of queries."""
        offers = chosen.subquery()
        rows = [dict(row) for row in connection.execute(chosen).mappings()]
        latest = {
            price["listing_id"]: dict(price)
            for price in connection.execute(
                select(observations)
                .where(observations.c.listing_id.in_(select(offers.c.id)))
                .distinct(observations.c.listing_id)
                .order_by(
                    observations.c.listing_id,
                    observations.c.observed_at.desc(),
                    observations.c.entered_at.desc(),
                    observations.c.id.desc(),
                )
            ).mappings()
        }
        found = {
            drive["id"]: dict(drive)
            for drive in connection.execute(
                select(drives).where(drives.c.id.in_(select(offers.c.drive_id)))
            ).mappings()
        }
        names = dict(connection.execute(select(sources.c.key, sources.c.name)).tuples().all())
        aliases: dict[UUID, list[str]] = {}
        for alias in connection.execute(
            select(mpn_aliases)
            .where(mpn_aliases.c.drive_id.in_(select(offers.c.drive_id)))
            .order_by(mpn_aliases.c.alias)
        ).mappings():
            aliases.setdefault(alias["drive_id"], []).append(alias["alias"])
        return [
            {
                **self._summary(
                    row, found[row["drive_id"]], aliases.get(row["drive_id"], []), latest[row["id"]]
                ),
                "store_name": names[row["store"]],
            }
            for row in rows
        ]

    def _summary(
        self,
        row: dict[str, Any],
        drive: dict[str, Any],
        aliases: list[str],
        latest: dict[str, Any],
    ) -> dict[str, Any]:
        listing = {key: value for key, value in row.items() if key != "drive_id"}
        observed = latest["observed_at"]
        checked = max(observed, row["last_checked_at"] or observed)
        return {
            **listing,
            "last_checked_at": timestamp(checked),
            "drive": drive_view(drive, aliases),
            "id": str(row["id"]),
            "capacity_gb": drive["capacity_gb"],
            "latest": self._observation(latest, drive["capacity_gb"]),
        }

    def _histories(self, connection: Connection, chosen: Select[Any]) -> list[dict[str, Any]]:
        """The chosen offers with every price they have had, oldest first."""
        offers = self._summaries(connection, chosen)
        prices: dict[str, list[dict[str, Any]]] = {offer["id"]: [] for offer in offers}
        for price in connection.execute(
            select(observations)
            .where(observations.c.listing_id.in_(select(chosen.subquery().c.id)))
            .order_by(observations.c.observed_at, observations.c.entered_at, observations.c.id)
        ).mappings():
            prices[str(price["listing_id"])].append(dict(price))
        return [
            {
                **offer,
                "observations": [
                    self._observation(price, offer["capacity_gb"]) for price in prices[offer["id"]]
                ],
            }
            for offer in offers
        ]

    def _listing(self, connection: Connection, row: dict[str, Any]) -> dict[str, Any]:
        [listing] = self._histories(connection, select(listings).where(listings.c.id == row["id"]))
        return listing

    def _locked(self, connection: Connection, listing_id: UUID) -> dict[str, Any]:
        row = (
            connection.execute(
                select(listings).where(listings.c.id == listing_id).with_for_update()
            )
            .mappings()
            .first()
        )
        if row is None:
            raise ListingNotFound()
        return dict(row)

    def _resolve_drive(self, connection: Connection, mpn: str, capacity: int | None) -> UUID:
        """Link to the Drive for this MPN, creating it (Unknown specifications) on first sight."""
        find = select(drives).where(drives.c.mpn == mpn).with_for_update()
        drive = connection.execute(find).mappings().first()
        if drive is None:
            if capacity is None:
                raise CapacityRequired()
            connection.execute(
                pg_insert(drives)
                .values(id=self.next_id(), mpn=mpn, capacity_gb=capacity)
                .on_conflict_do_nothing(index_elements=[drives.c.mpn])
            )
            drive = connection.execute(find).mappings().one()
        if capacity is not None and capacity != drive["capacity_gb"]:
            raise CapacityConflict(
                f"MPN {mpn} is recorded as {capacity_label(drive['capacity_gb'])}."
                " Edit the drive's specifications to change its capacity."
            )
        return drive["id"]

    def _once(
        self, request_id: UUID, fingerprint: str, write: Callable[[Connection], dict[str, Any]]
    ) -> dict[str, Any]:
        with self.engine.begin() as connection:
            claimed = connection.execute(
                pg_insert(receipts)
                .values(id=request_id, fingerprint=fingerprint)
                .on_conflict_do_nothing(index_elements=[receipts.c.id])
                .returning(receipts.c.id)
            ).scalar_one_or_none()
            if claimed is None:
                saved = (
                    connection.execute(select(receipts).where(receipts.c.id == request_id))
                    .mappings()
                    .one()
                )
                if saved["fingerprint"] != fingerprint:
                    raise IdempotencyConflict(
                        "This save key was already used for a different request."
                    )
                return saved["result"]
            result = write(connection)
            connection.execute(
                update(receipts).where(receipts.c.id == request_id).values(result=result)
            )
            return result

    def record_price(
        self, entry: PriceInput, request_id: UUID, source: str = "manual"
    ) -> dict[str, Any]:
        def write(connection: Connection) -> dict[str, Any]:
            known = select(sources.c.key).where(sources.c.key == entry.store)
            if connection.execute(known).first() is None:
                raise UnknownStore()
            mpn = self._canonical_mpn(connection, entry.mpn)
            identity = {
                "mpn": mpn,
                "store": entry.store,
                "seller": entry.seller,
                "condition": entry.condition,
            }
            connection.execute(
                pg_insert(listings)
                .values(
                    id=self.next_id(),
                    drive_id=self._resolve_drive(connection, mpn, entry.capacity_gb),
                    **identity,
                    title=entry.title or mpn,
                    url=str(entry.url) if entry.url else None,
                )
                .on_conflict_do_nothing(
                    index_elements=[
                        listings.c.mpn,
                        listings.c.store,
                        listings.c.seller,
                        listings.c.condition,
                    ]
                )
            )
            listing_id = connection.execute(
                select(listings.c.id)
                .where(*(listings.c[key] == value for key, value in identity.items()))
                .with_for_update()
            ).scalar_one()
            observation = ObservationInput.model_validate(
                entry.model_dump(include=set(ObservationInput.model_fields))
            )
            entered_at = self.now()
            observed_at = observation.observed_at or entered_at
            values = observation.model_dump(exclude={"observed_at"})
            latest = (
                connection.execute(
                    select(observations)
                    .where(observations.c.listing_id == listing_id)
                    .order_by(observations.c.observed_at.desc(), observations.c.entered_at.desc())
                    .limit(1)
                )
                .mappings()
                .first()
            )
            values = with_carried_price(values, latest)
            if unchanged(values, observed_at, latest):
                connection.execute(
                    update(listings)
                    .where(listings.c.id == listing_id)
                    .values(last_checked_at=func.greatest(listings.c.last_checked_at, observed_at))
                )
            else:
                connection.execute(
                    insert(observations).values(
                        **values,
                        observed_at=observed_at,
                        id=self.next_id(),
                        listing_id=listing_id,
                        entered_at=entered_at,
                        acquisition_method=source,
                    )
                )
            return self._listing(connection, self._locked(connection, listing_id))

        fingerprint = sha256(f"price:{source}:{entry.model_dump_json()}".encode()).hexdigest()
        return self._once(request_id, fingerprint, write)

    def drive_capacity(self, mpn: str) -> int | None:
        """The capacity of the drive an MPN (or an alias of it) names; None for an unknown one."""
        with self.engine.connect() as connection:
            capacity: int | None = connection.execute(
                select(drives.c.capacity_gb).where(
                    drives.c.mpn == self._canonical_mpn(connection, mpn)
                )
            ).scalar_one_or_none()
            return capacity

    def _canonical_mpn(self, connection: Connection, mpn: str) -> str:
        canonical = connection.execute(
            select(drives.c.mpn)
            .join(mpn_aliases, mpn_aliases.c.drive_id == drives.c.id)
            .where(mpn_aliases.c.alias == mpn)
        ).scalar_one_or_none()
        return canonical or mpn

    def add_alias(self, drive_id: UUID, alias: str) -> dict[str, Any]:
        """Declare another MPN for a drive, merging any drive already recorded under it."""
        with self.engine.begin() as connection:
            drive = (
                connection.execute(select(drives).where(drives.c.id == drive_id).with_for_update())
                .mappings()
                .first()
            )
            if drive is None:
                raise DriveNotFound()
            taken = connection.execute(
                select(mpn_aliases.c.drive_id).where(mpn_aliases.c.alias == alias)
            ).scalar_one_or_none()
            if alias == drive["mpn"] or taken is not None:
                raise AliasConflict(f"{alias} already identifies a drive.")
            variant = (
                connection.execute(select(drives).where(drives.c.mpn == alias).with_for_update())
                .mappings()
                .first()
            )
            if variant is not None:
                self._merge_drive(connection, variant, drive)
            connection.execute(insert(mpn_aliases).values(alias=alias, drive_id=drive_id))
            return self._drive(connection, dict(drive))

    def _merge_drive(self, connection: Connection, variant: RowMapping, drive: RowMapping) -> None:
        def offers_of(drive_id: UUID) -> Sequence[RowMapping]:
            return (
                connection.execute(select(listings).where(listings.c.drive_id == drive_id))
                .mappings()
                .all()
            )

        for offer_id, twin in merge_plan(offers_of(variant["id"]), offers_of(drive["id"])):
            if twin is None:
                connection.execute(
                    update(listings)
                    .where(listings.c.id == offer_id)
                    .values(mpn=drive["mpn"], drive_id=drive["id"])
                )
            else:
                connection.execute(
                    update(observations)
                    .where(observations.c.listing_id == offer_id)
                    .values(listing_id=twin)
                )
                connection.execute(delete(listings).where(listings.c.id == offer_id))
        connection.execute(
            update(mpn_aliases)
            .where(mpn_aliases.c.drive_id == variant["id"])
            .values(drive_id=drive["id"])
        )
        connection.execute(delete(drives).where(drives.c.id == variant["id"]))

    def record_scraped(self, entry: ScrapedInput, request_id: UUID) -> dict[str, Any]:
        """Record a scraped offer as a price, or queue it for review when it cannot be matched."""
        with self.engine.connect() as connection:
            match = (
                connection.execute(
                    select(scraped_matches).where(
                        scraped_matches.c.source == entry.source,
                        scraped_matches.c.url == str(entry.url),
                    )
                )
                .mappings()
                .first()
            )
        if match is not None and match["ignored"]:
            return {"status": "ignored"}
        if match is not None:
            entry = entry.model_copy(
                update={
                    "mpn": entry.mpn or match["mpn"],
                    "condition": entry.condition or match["condition"],
                }
            )
        if not entry.in_stock:
            # Sold out is only a stock state: whatever price the store shows then (a placeholder,
            # say) is not recorded, so the offer keeps the price it last had in stock.
            entry = entry.model_copy(update={"item_price_cents": None, "shipping_cents": None})
        missing = missing_detail(entry.mpn, entry.condition)
        if missing is not None:
            return self._queue(entry, missing)
        try:
            offer = self.record_price(entry.as_price(), request_id, source=entry.source)
        except PriceRequired:
            # Only a sold-out offer lacks a price, and one never seen in stock has no real price
            # to track yet.
            return {"status": "ignored"}
        except (CapacityConflict, CapacityRequired) as error:
            return self._queue(entry, queue_reason(error))
        if entry.specifications is not None:
            self._fill_specifications(UUID(offer["drive"]["id"]), entry.specifications)
        if entry.brand is not None and offer["drive"]["brand"] is None:
            self._name_brand(UUID(offer["drive"]["id"]), entry.brand)
        for alias in new_aliases(entry.aliases, offer["drive"]["mpn"], offer["drive"]["aliases"]):
            try:
                self.add_alias(UUID(offer["drive"]["id"]), alias)
            except AliasConflict:
                # Already another drive's alias; leave that for a person to sort out.
                continue
        self._leave_queue(entry)
        return {"status": "recorded", "listing_id": offer["id"]}

    def _leave_queue(self, entry: ScrapedInput) -> None:
        """An offer that is recorded now is no longer waiting for review."""
        with self.engine.begin() as connection:
            connection.execute(
                delete(unmatched).where(
                    unmatched.c.source == entry.source, unmatched.c.url == str(entry.url)
                )
            )

    def _name_brand(self, drive_id: UUID, brand: str) -> None:
        """A source's brand only names a drive nobody has named yet."""
        with self.engine.begin() as connection:
            connection.execute(
                update(drives)
                .where(drives.c.id == drive_id, drives.c.brand.is_(None))
                .values(brand=brand)
            )

    def _fill_specifications(self, drive_id: UUID, found: Specifications) -> None:
        with self.engine.begin() as connection:
            current = connection.execute(
                select(drives.c.specifications).where(drives.c.id == drive_id).with_for_update()
            ).scalar_one()
            filled = fill_unknown(
                Specifications.model_validate(current).model_dump(mode="json"),
                found.model_dump(mode="json"),
            )
            connection.execute(
                update(drives).where(drives.c.id == drive_id).values(specifications=filled)
            )

    def _queue(self, entry: ScrapedInput, reason: str) -> dict[str, Any]:
        seen_at = entry.observed_at or self.now()
        fields = {
            **entry.model_dump(
                include={
                    "source",
                    "title",
                    "seller",
                    "mpn",
                    "condition",
                    "capacity_gb",
                    "item_price_cents",
                    "shipping_cents",
                    "in_stock",
                }
            ),
            "url": str(entry.url),
            "reason": reason,
            "last_seen_at": seen_at,
        }
        with self.engine.begin() as connection:
            item_id = connection.execute(
                pg_insert(unmatched)
                .values(id=self.next_id(), first_seen_at=seen_at, **fields)
                .on_conflict_do_update(
                    index_elements=[unmatched.c.source, unmatched.c.url], set_=fields
                )
                .returning(unmatched.c.id)
            ).scalar_one()
        return {"status": "queued", "unmatched_id": str(item_id)}

    def _unmatched(self, connection: Connection, item_id: UUID) -> dict[str, Any]:
        row = (
            connection.execute(select(unmatched).where(unmatched.c.id == item_id))
            .mappings()
            .first()
        )
        if row is None:
            raise UnmatchedNotFound()
        return dict(row)

    def _remember(self, connection: Connection, row: dict[str, Any], **decision: Any) -> None:
        connection.execute(
            pg_insert(scraped_matches)
            .values(source=row["source"], url=row["url"], **decision)
            .on_conflict_do_update(
                index_elements=[scraped_matches.c.source, scraped_matches.c.url], set_=decision
            )
        )

    def resolve_unmatched(self, item_id: UUID, resolution: Resolution) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = self._unmatched(connection, item_id)
        entry = ScrapedInput.model_validate(
            {
                **{key: row[key] for key in ("source", "url", "title", "seller")},
                **{key: row[key] for key in ("item_price_cents", "shipping_cents", "in_stock")},
                "mpn": resolution.mpn,
                "condition": resolution.condition,
                "capacity_gb": resolution.capacity_gb or row["capacity_gb"],
                "observed_at": row["last_seen_at"],
            }
        )
        offer = self.record_price(entry.as_price(), self.next_id(), source=entry.source)
        with self.engine.begin() as connection:
            connection.execute(delete(unmatched).where(unmatched.c.id == item_id))
            self._remember(
                connection, row, mpn=resolution.mpn, condition=resolution.condition, ignored=False
            )
        return offer

    def ignore_unmatched(self, item_id: UUID) -> None:
        with self.engine.begin() as connection:
            row = self._unmatched(connection, item_id)
            connection.execute(delete(unmatched).where(unmatched.c.id == item_id))
            self._remember(connection, row, mpn=None, condition=None, ignored=True)

    def list_unmatched(
        self,
        source: str | None = None,
        reason: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """The Review queue, newest first: the offers of this source and waiting for this
        reason when given, limit of them from offset; and how many there are in all, whatever
        the limit."""
        wanted = [
            column == value
            for column, value in ((unmatched.c.source, source), (unmatched.c.reason, reason))
            if value is not None
        ]
        with self.engine.connect() as connection:
            rows, total = part_of(
                connection,
                select(unmatched)
                .where(*wanted)
                .order_by(unmatched.c.last_seen_at.desc(), unmatched.c.id),
                limit,
                offset,
            )
            return [
                {
                    **row,
                    "id": str(row["id"]),
                    "first_seen_at": timestamp(row["first_seen_at"]),
                    "last_seen_at": timestamp(row["last_seen_at"]),
                }
                for row in rows
            ], total

    def replace_specifications(self, drive_id: UUID, entry: DriveSpecifications) -> dict[str, Any]:
        with self.engine.begin() as connection:
            updated = (
                connection.execute(
                    update(drives)
                    .where(drives.c.id == drive_id)
                    .values(
                        capacity_gb=entry.capacity_gb,
                        specifications=entry.specifications.model_dump(mode="json"),
                        **({"brand": entry.brand} if "brand" in entry.model_fields_set else {}),
                    )
                    .returning(*drives.c)
                )
                .mappings()
                .first()
            )
            if updated is None:
                raise DriveNotFound()
            return self._drive(connection, dict(updated))

    def edit_offer(self, listing_id: UUID, entry: OfferEdit) -> dict[str, Any]:
        fields = entry.model_dump(exclude_unset=True)
        if "url" in fields:
            fields["url"] = str(fields["url"]) if fields["url"] else None
        with self.engine.begin() as connection:
            self._locked(connection, listing_id)
            if fields:
                connection.execute(
                    update(listings).where(listings.c.id == listing_id).values(**fields)
                )
            return self._listing(connection, self._locked(connection, listing_id))

    def _delete_offer(self, connection: Connection, listing_id: UUID) -> None:
        connection.execute(delete(observations).where(observations.c.listing_id == listing_id))
        connection.execute(delete(listings).where(listings.c.id == listing_id))

    def delete_offer(self, listing_id: UUID) -> None:
        with self.engine.begin() as connection:
            self._locked(connection, listing_id)
            self._delete_offer(connection, listing_id)

    def delete_price(self, listing_id: UUID, observation_id: UUID) -> dict[str, Any] | None:
        """Remove a mistaken price; returns the offer, or None once its last price is gone."""
        with self.engine.begin() as connection:
            self._locked(connection, listing_id)
            removed = connection.execute(
                delete(observations).where(
                    observations.c.id == observation_id, observations.c.listing_id == listing_id
                )
            ).rowcount
            if not removed:
                raise ListingNotFound()
            remaining = connection.execute(
                select(observations.c.id).where(observations.c.listing_id == listing_id).limit(1)
            ).first()
            if remaining is None:
                self._delete_offer(connection, listing_id)
                return None
            return self._listing(connection, self._locked(connection, listing_id))

    def get(self, listing_id: UUID) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(select(listings).where(listings.c.id == listing_id))
                .mappings()
                .first()
            )
            return self._listing(connection, dict(row)) if row is not None else None

    def record_run(self, run: CollectorRun) -> dict[str, Any]:
        """Keep a run's outcome; the run is no longer in progress."""
        with self.engine.begin() as connection:
            connection.execute(insert(collector_runs).values(id=self.next_id(), **run.model_dump()))
            connection.execute(
                delete(collector_activity).where(collector_activity.c.source == run.source)
            )
        return run_view(run.model_dump())

    def _heard(self, connection: Connection) -> None:
        """A collector has just been heard from."""
        now = self.now()
        connection.execute(
            pg_insert(collector_contact)
            .values(id=CONTACT, seen_at=now)
            .on_conflict_do_update(index_elements=[collector_contact.c.id], set_={"seen_at": now})
        )

    def report_activity(self, progress: Activity) -> dict[str, bool]:
        """Keep how far a run in progress has got, and say whether it was asked to stop: a
        request made since the run started is for it."""
        values = {**progress.model_dump(), "updated_at": self.now()}
        with self.engine.begin() as connection:
            connection.execute(
                pg_insert(collector_activity)
                .values(**values)
                .on_conflict_do_update(index_elements=[collector_activity.c.source], set_=values)
            )
            self._heard(connection)
            asked = connection.execute(
                select(sources.c.stop_requested_at).where(sources.c.key == progress.source)
            ).scalar_one_or_none()
        return {"stop": asked is not None and asked >= progress.started_at}

    def collector_idle(self) -> None:
        """A collector is between runs, so no run is in progress: one it was restarted partway
        through is never reported, and would otherwise look as if it were still running."""
        with self.engine.begin() as connection:
            connection.execute(delete(collector_activity))
            self._heard(connection)

    def collector_status(self) -> dict[str, Any]:
        """When a collector was last heard from, the runs in progress, and the sources waiting
        to run, in the order they will."""
        with self.engine.connect() as connection:
            seen = connection.execute(select(collector_contact.c.seen_at)).scalar_one_or_none()
            running = [
                dict(row)
                for row in connection.execute(
                    select(collector_activity).order_by(collector_activity.c.started_at)
                ).mappings()
            ]
        busy = {run["source"] for run in running}
        waiting = [source["key"] for source in self.due_sources() if source["key"] not in busy]
        return {"seen_at": seen, "running": running, "waiting": waiting}

    def latest_runs(self) -> list[dict[str, Any]]:
        """The most recent run of each source, by source."""
        query = (
            select(collector_runs)
            .distinct(collector_runs.c.source)
            .order_by(collector_runs.c.source, collector_runs.c.finished_at.desc())
        )
        with self.engine.connect() as connection:
            return [run_view(dict(row)) for row in connection.execute(query).mappings()]

    def list_condition_rules(self) -> list[dict[str, Any]]:
        query = select(condition_rules.c.pattern, condition_rules.c.condition).order_by(
            condition_rules.c.position
        )
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(query).mappings()]

    def replace_condition_rules(self, rules: Sequence[ConditionRule]) -> list[dict[str, Any]]:
        """The rules, in the order given, in place of the ones kept before."""
        with self.engine.begin() as connection:
            connection.execute(delete(condition_rules))
            if rules:
                connection.execute(
                    insert(condition_rules),
                    [{"position": index, **rule.model_dump()} for index, rule in enumerate(rules)],
                )
        return [rule.model_dump() for rule in rules]

    @staticmethod
    def _due_at(
        source: dict[str, Any], last_started: datetime | None, now: datetime
    ) -> datetime | None:
        """When a source is next due: never, for a store entered by hand; when it was asked to
        run, if no run has started since; otherwise, while it is switched on, the first time its
        schedule fires after its last run started, or now if it has never run."""
        if source["kind"] == "manual":
            return None
        requested = source["run_requested_at"]
        if requested is not None and (last_started is None or requested > last_started):
            return cast(datetime, requested)
        if not source["enabled"]:
            return None
        if last_started is None:
            return now
        return cast(datetime, croniter(source["schedule"], last_started).get_next(datetime))

    def _source_views(
        self, connection: Connection, query: Select[Any], now: datetime | None = None
    ) -> list[dict[str, Any]]:
        """The sources the query selects, each with when it is next due, as of now."""
        return [view for view, _ in self._sources_asked(connection, query, now)]

    def _sources_asked(
        self, connection: Connection, query: Select[Any], now: datetime | None = None
    ) -> list[tuple[dict[str, Any], bool]]:
        """The sources the query selects, each with when it is next due, as of now, and whether
        that is because it was asked to run."""
        now = now or self.now()
        last_runs = (
            select(collector_runs.c.source, func.max(collector_runs.c.started_at).label("last"))
            .group_by(collector_runs.c.source)
            .subquery()
        )
        rows = connection.execute(
            query.add_columns(last_runs.c.last).outerjoin(
                last_runs, last_runs.c.source == sources.c.key
            )
        ).mappings()
        views = []
        for row in rows:
            source = {column.name: row[column.name] for column in sources.columns}
            due = self._due_at(source, row["last"], now)
            asked = due is not None and due == source["run_requested_at"]
            del source["run_requested_at"], source["stop_requested_at"]
            source["settings"] = current_settings(source["kind"], source["settings"])
            views.append(({**source, "id": str(source["id"]), "next_run_at": due}, asked))
        return views

    def _source_view(self, connection: Connection, source_id: UUID) -> dict[str, Any]:
        [view] = self._source_views(connection, select(sources).where(sources.c.id == source_id))
        return view

    def list_sources(self) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return self._source_views(connection, select(sources).order_by(sources.c.name))

    def due_sources(self) -> list[dict[str, Any]]:
        """The sources due to run now, in the order to run them: those asked to run, in the
        order they were asked, ahead of those whose schedule has fired, most overdue first."""
        now = self.now()
        with self.engine.connect() as connection:
            views = self._sources_asked(connection, select(sources), now)
        due = [
            (not asked, source["next_run_at"], source)
            for source, asked in views
            if source["next_run_at"] is not None and source["next_run_at"] <= now
        ]
        return [source for *_, source in sorted(due, key=lambda entry: entry[:2])]

    def request_run(self, source_id: UUID) -> dict[str, Any]:
        with self.engine.begin() as connection:
            asked = connection.execute(
                update(sources).where(sources.c.id == source_id).values(run_requested_at=self.now())
            ).rowcount
            if not asked:
                raise SourceNotFound()
            return self._source_view(connection, source_id)

    def request_stop(self, source_id: UUID) -> dict[str, Any]:
        """Ask the source's run in progress to stop; it is told the next time it says how far
        it has got. A run that starts later is not stopped by it."""
        with self.engine.begin() as connection:
            asked = connection.execute(
                update(sources)
                .where(sources.c.id == source_id)
                .values(stop_requested_at=self.now())
            ).rowcount
            if not asked:
                raise SourceNotFound()
            return self._source_view(connection, source_id)

    def delete_source(self, source_id: UUID) -> None:
        """Delete a source nothing is recorded under, with its runs and what it was told about
        scraped offers. One with offers, or queued offers, is kept, and so is Other."""
        with self.engine.begin() as connection:
            key = connection.execute(
                select(sources.c.key).where(sources.c.id == source_id).with_for_update()
            ).scalar_one_or_none()
            if key is None:
                raise SourceNotFound()
            if key == "other":
                raise SourceKept("Other is always kept, for one-off stores.")
            recorded = connection.execute(
                select(listings.c.id).where(listings.c.store == key).limit(1)
            ).first()
            queued = connection.execute(
                select(unmatched.c.id).where(unmatched.c.source == key).limit(1)
            ).first()
            if recorded or queued:
                raise SourceKept("Offers are recorded under this source. Switch it off instead.")
            connection.execute(delete(collector_runs).where(collector_runs.c.source == key))
            connection.execute(delete(scraped_matches).where(scraped_matches.c.source == key))
            connection.execute(delete(sources).where(sources.c.id == source_id))

    def add_source(self, entry: SourceInput) -> dict[str, Any]:
        source_id = self.next_id()
        try:
            with self.engine.begin() as connection:
                key = source_key(entry.name)
                connection.execute(
                    insert(sources).values(id=source_id, key=key, **entry.model_dump())
                )
                return self._source_view(connection, source_id)
        except IntegrityError as error:
            raise SourceExists(entry.name) from error

    def update_source(self, source_id: UUID, entry: SourceInput) -> dict[str, Any]:
        try:
            with self.engine.begin() as connection:
                changed = connection.execute(
                    update(sources).where(sources.c.id == source_id).values(**entry.model_dump())
                ).rowcount
                if not changed:
                    raise SourceNotFound()
                return self._source_view(connection, source_id)
        except IntegrityError as error:
            raise SourceExists(entry.name) from error

    def histories(self, listing_ids: Sequence[UUID]) -> list[dict[str, Any]]:
        query = (
            select(listings)
            .where(listings.c.id.in_(listing_ids))
            .order_by(listings.c.title, listings.c.id)
        )
        with self.engine.connect() as connection:
            return self._histories(connection, query)

    def list(self, store: str | None = None) -> list[dict[str, Any]]:
        query = select(listings).order_by(listings.c.title, listings.c.id)
        if store is not None:
            query = query.where(listings.c.store == store)
        with self.engine.connect() as connection:
            return self._summaries(connection, query)
