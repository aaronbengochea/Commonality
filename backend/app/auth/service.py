import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from app.config import settings
from app.dependencies import get_dynamo_client

ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except Exception:
        return False


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_user_by_username(username: str) -> dict | None:
    """Look up a user by username via GSI1."""
    dynamo = get_dynamo_client()
    table = dynamo.Table("users")
    resp = table.query(
        IndexName="GSI1",
        KeyConditionExpression=Key("GSI1PK").eq(f"USERNAME#{username}") & Key("GSI1SK").eq("PROFILE"),
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def get_user_by_id(user_id: str) -> dict | None:
    """Fetch a user record by user ID."""
    dynamo = get_dynamo_client()
    table = dynamo.Table("users")
    resp = table.get_item(Key={"PK": f"USER#{user_id}", "SK": "PROFILE"})
    return resp.get("Item")


class UsernameExistsError(Exception):
    """Raised when attempting to create a user with a taken username."""


def create_user(username: str, password: str, first_name: str, last_name: str, native_language: str) -> dict:
    """Create a new user in DynamoDB. Returns the user item (without passwordHash).
    Raises UsernameExistsError if the username is already taken."""
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    password_hash = hash_password(password)

    item = {
        "PK": f"USER#{user_id}",
        "SK": "PROFILE",
        "GSI1PK": f"USERNAME#{username}",
        "GSI1SK": "PROFILE",
        "userId": user_id,
        "username": username,
        "firstName": first_name,
        "lastName": last_name,
        "nativeLanguage": native_language,
        "passwordHash": password_hash,
        "createdAt": now,
    }

    dynamo = get_dynamo_client()
    table = dynamo.Table("users")
    try:
        table.put_item(Item=item, ConditionExpression=Attr("PK").not_exists())
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise UsernameExistsError()
        raise

    safe_item = {k: v for k, v in item.items() if k != "passwordHash"}
    return safe_item
