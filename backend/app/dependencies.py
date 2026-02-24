import boto3
import redis.asyncio as redis

from app.config import settings

_dynamo_client = None
_redis_client = None


def get_dynamo_client():
    global _dynamo_client
    if _dynamo_client is None:
        _dynamo_client = boto3.resource(
            "dynamodb",
            endpoint_url=settings.dynamodb_endpoint,
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
    return _dynamo_client


async def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
