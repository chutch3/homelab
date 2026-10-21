"""The catalog's corrections not yet given to their owners: a drive or offer corrected, an offer
or price removed, the condition rules. Every operation opens its own session and commits once. Prices are recorded by catalog.price_service
and catalog.ingestion_service, and review decisions by catalog.review_service."""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from disktracker.catalog.models import (
    ConditionRule,
    Offer,
    Price,
)
from disktracker.catalog.queries import offer_with_history
from disktracker.database import SessionFactory
from disktracker.errors import (
    OfferNotFound,
)


class CatalogRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory

    # Drives and the MPNs they go by.

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


def _lock_offer(session: Session, offer_id: UUID) -> None:
    """Hold an offer against other changes until the transaction ends."""
    if session.scalar(select(Offer.id).where(Offer.id == offer_id).with_for_update()) is None:
        raise OfferNotFound()


def _delete_offer(session: Session, offer_id: UUID) -> None:
    session.execute(delete(Price).where(Price.offer_id == offer_id))
    session.execute(delete(Offer).where(Offer.id == offer_id))
