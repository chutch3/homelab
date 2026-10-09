"""The collector's own failures, so nothing outside the adapters depends on the HTTP library."""


class SourceUnavailable(Exception):
    """A store could not be read: unreachable, an error status, or a reply that is not data."""


class OutOfTime(Exception):
    """Reading a store took longer than it was given."""


class DisktrackerUnavailable(Exception):
    """disktracker could not be read: unreachable, an error status, or a reply that is not data."""
