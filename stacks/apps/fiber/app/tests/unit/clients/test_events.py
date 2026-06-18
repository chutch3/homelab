import asyncio

from fiber.clients.events import EventBroker


async def test_subscriber_receives_publish() -> None:
    broker = EventBroker()
    q = broker.subscribe()
    await broker.publish("immich")
    assert await asyncio.wait_for(q.get(), 1) == "immich"
    broker.unsubscribe(q)
    assert q not in broker.subscribers
