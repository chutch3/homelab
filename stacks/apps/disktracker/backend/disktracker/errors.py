"""What can go wrong in a workflow; disktracker.http_errors says how each is answered over HTTP."""


class CapacityRequired(Exception):
    """A drive not recorded yet needs its capacity."""


class CapacityConflict(Exception):
    """The capacity given is not the drive's; the message says what it is."""


class PriceRequired(Exception):
    """An offer with no price yet needs one."""


class IdempotencyConflict(Exception):
    pass


class DecisionConflict(Exception):
    pass


class OfferNotFound(Exception):
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


class MpnTaken(Exception):
    """An MPN already identifies a drive, as its own MPN or another of its MPNs."""


class MergeConflict(Exception):
    """Two drives cannot be merged as they are: the fields they differ on, or why else not."""

    def __init__(self, fields: list[str], why: str = "") -> None:
        self.fields = fields
        super().__init__(why or f"The drives differ on {', '.join(fields)}: correct one first.")


class SameDrive(Exception):
    """A drive cannot be merged into itself."""


class ReviewItemNotFound(Exception):
    pass


class RunNotFound(Exception):
    pass


class RunConflict(Exception):
    """A run cannot become what was asked; the message says why."""


class UnknownSource(Exception):
    pass
