"""What the catalog and reporting mean alike by an offer's latest price, and by an offer that
counts: the definitions every read and write of them uses, so none can mean another."""

from disktracker.catalog.models import Offer, Price

# An offer's prices, latest first: the latest seen, then the latest entered, then the latest made,
# so that one of several seen and entered at one moment is the latest everywhere.
LATEST_FIRST = (Price.observed_at.desc(), Price.entered_at.desc(), Price.id.desc())

# What counts in a ranking, a distribution or a trend: every offer but those held while a person
# settles what their page is (catalog.models.Offer.held_reason). Administration, store freshness
# and an offer's own history include held offers too.
COUNTED = Offer.held_reason.is_(None)
