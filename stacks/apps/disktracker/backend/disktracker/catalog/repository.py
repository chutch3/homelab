"""The catalog's corrections not yet given to their owners: a drive's other MPNs (and merging drives
by them), a drive or offer corrected, an offer or price removed, the condition rules. Every
operation opens its own session and commits once. Prices are recorded by catalog.price_service
and catalog.ingestion_service, and review decisions by catalog.review_service."""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from disktracker.catalog.drive_repository import hold_mpn
from disktracker.catalog.models import (
    ConditionRule,
    Drive,
    MpnAlias,
    Offer,
    Price,
)
from disktracker.catalog.queries import aliases_of, offer_with_history
from disktracker.catalog.rules import (
    merge_plan,
)
from disktracker.catalog.schemas import Specifications
from disktracker.catalog.views import drive_view
from disktracker.database import SessionFactory, columns
from disktracker.errors import (
    AliasConflict,
    DriveNotFound,
    OfferNotFound,
)


class CatalogRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory

    # Drives and the MPNs they go by.

    def add_alias(self, drive_id: UUID, alias: str) -> dict[str, Any]:
        """Declare another MPN for a drive, merging in any drive already recorded under it."""
        with self.session_factory() as session:
            drive = _add_alias(session, drive_id, alias)
            session.commit()
            return drive_view(drive, aliases_of(session, drive_id))

    def edit_drive(
        self, drive_id: UUID, values: dict[str, Any], specifications: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Change what is given of a drive, its specifications one by one, and leave the rest."""
        with self.session_factory() as session:
            drive = _lock_drive(session, drive_id)
            if specifications is not None:
                values = values | {
                    "specifications": Specifications.model_validate(
                        drive.specifications | specifications
                    ).model_dump(mode="json")
                }
            if values:
                session.execute(update(Drive).where(Drive.id == drive_id).values(**values))
                session.refresh(drive)
            session.commit()
            return drive_view(drive, aliases_of(session, drive_id))

    # Offers and prices, corrected.

    def edit_offer(self, offer_id: UUID, fields: dict[str, Any]) -> dict[str, Any]:
        with self.session_factory() as session:
            _lock_offer(session, offer_id)
            if fields:
                session.execute(update(Offer).where(Offer.id == offer_id).values(**fields))
            offer = offer_with_history(session, offer_id)
            session.commit()
            return offer

    def delete_offer(self, offer_id: UUID) -> None:
        with self.session_factory() as session:
            _lock_offer(session, offer_id)
            _delete_offer(session, offer_id)
            session.commit()

    def delete_price(self, price_id: UUID) -> None:
        """Remove a price, and its offer with it when it was the offer's last. A price that is
        not there is already removed."""
        with self.session_factory() as session:
            offer_id = session.scalar(select(Price.offer_id).where(Price.id == price_id))
            if offer_id is None:
                return
            _lock_offer(session, offer_id)
            session.execute(delete(Price).where(Price.id == price_id))
            if session.scalar(select(Price.id).where(Price.offer_id == offer_id).limit(1)) is None:
                _delete_offer(session, offer_id)
            session.commit()

    # The rules that read a condition from listing text.

    def replace_condition_rules(self, rules: list[dict[str, Any]]) -> None:
        with self.session_factory() as session:
            session.execute(delete(ConditionRule))
            session.add_all(
                ConditionRule(position=index, **rule) for index, rule in enumerate(rules)
            )
            session.commit()


# What the operations above share, each on the session of the operation that calls it.


def _lock_drive(session: Session, drive_id: UUID) -> Drive:
    drive = session.scalars(select(Drive).where(Drive.id == drive_id).with_for_update()).first()
    if drive is None:
        raise DriveNotFound()
    return drive


def _lock_offer(session: Session, offer_id: UUID) -> None:
    """Hold an offer against other changes until the transaction ends."""
    if session.scalar(select(Offer.id).where(Offer.id == offer_id).with_for_update()) is None:
        raise OfferNotFound()


def _delete_offer(session: Session, offer_id: UUID) -> None:
    session.execute(delete(Price).where(Price.offer_id == offer_id))
    session.execute(delete(Offer).where(Offer.id == offer_id))


def _add_alias(session: Session, drive_id: UUID, alias: str) -> Drive:
    """Declare another MPN for a drive; a drive recorded under it is merged in, its offers
    moving across, or combining with the matching offer, and its own aliases following."""
    hold_mpn(session, alias)
    drive = _lock_drive(session, drive_id)
    taken = session.scalar(select(MpnAlias.drive_id).where(MpnAlias.alias == alias))
    if alias == drive.mpn or taken is not None:
        raise AliasConflict(f"{alias} already identifies a drive.")
    variant = session.scalars(select(Drive).where(Drive.mpn == alias).with_for_update()).first()
    if variant is not None:
        plan = merge_plan(
            [
                columns(offer)
                for offer in session.scalars(select(Offer).where(Offer.drive_id == variant.id))
            ],
            [
                columns(offer)
                for offer in session.scalars(select(Offer).where(Offer.drive_id == drive.id))
            ],
        )
        for offer_id, twin in plan:
            if twin is None:
                session.execute(
                    update(Offer)
                    .where(Offer.id == offer_id)
                    .values(mpn=drive.mpn, drive_id=drive.id)
                )
            else:
                # Its prices join the matching offer, and it goes.
                session.execute(
                    update(Price).where(Price.offer_id == offer_id).values(offer_id=twin)
                )
                session.execute(delete(Offer).where(Offer.id == offer_id))
        session.execute(
            update(MpnAlias).where(MpnAlias.drive_id == variant.id).values(drive_id=drive.id)
        )
        session.execute(delete(Drive).where(Drive.id == variant.id))
    session.add(MpnAlias(alias=alias, drive_id=drive_id))
    session.flush()
    return drive
