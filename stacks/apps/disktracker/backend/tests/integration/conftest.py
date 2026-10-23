from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from disktracker.main import create_app


@pytest.fixture
def subject(database_url: str) -> Iterator[TestClient]:
    """The application, served on its own database, as a client reaches it."""
    with TestClient(create_app()) as client:
        yield client
