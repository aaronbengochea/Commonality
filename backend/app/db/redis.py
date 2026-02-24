import logging

from app.dependencies import get_redis_client

logger = logging.getLogger(__name__)


async def publish(channel: str, message: str):
    """Publish a message to a Redis pub/sub channel."""
    client = await get_redis_client()
    await client.publish(channel, message)


async def subscribe(channel: str):
    """Subscribe to a Redis pub/sub channel. Returns a pubsub object."""
    client = await get_redis_client()
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)
    return pubsub


async def ping() -> bool:
    """Check Redis connectivity."""
    try:
        client = await get_redis_client()
        return await client.ping()
    except Exception:
        logger.exception("Redis ping failed")
        return False
