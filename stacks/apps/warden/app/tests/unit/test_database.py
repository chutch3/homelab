from sqlalchemy.engine import Engine

from warden.database import make_engine


def test_make_engine_returns_engine_with_tables():
    engine = make_engine("sqlite://")
    assert isinstance(engine, Engine)
