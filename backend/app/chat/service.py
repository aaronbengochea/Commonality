import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key
from openai import OpenAI

from app.config import settings
from app.dependencies import get_dynamo_client

_openai_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


def find_existing_chat(user_id: str, other_user_id: str) -> dict | None:
    """Check if a chat already exists between two users via user_chats table."""
    dynamo = get_dynamo_client()
    table = dynamo.Table("user_chats")
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"USER#{user_id}"),
    )
    for item in resp.get("Items", []):
        if item.get("otherUserId") == other_user_id:
            return item
    return None


def create_chat(current_user: dict, other_user: dict) -> str:
    """Create a new 1:1 chat. Writes to chats + user_chats tables.
    Returns the chat_id."""
    chat_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    dynamo = get_dynamo_client()

    # Write chat metadata
    chats_table = dynamo.Table("chats")
    chats_table.put_item(Item={
        "PK": f"CHAT#{chat_id}",
        "SK": "META",
        "chatId": chat_id,
        "memberUserIds": [current_user["userId"], other_user["userId"]],
        "createdAt": now,
    })

    # Write user_chats entry for both users
    user_chats_table = dynamo.Table("user_chats")
    user_chats_table.put_item(Item={
        "PK": f"USER#{current_user['userId']}",
        "SK": f"CHAT#{chat_id}",
        "chatId": chat_id,
        "otherUsername": other_user["username"],
        "otherUserId": other_user["userId"],
        "lastMessagePreview": None,
        "updatedAt": now,
    })
    user_chats_table.put_item(Item={
        "PK": f"USER#{other_user['userId']}",
        "SK": f"CHAT#{chat_id}",
        "chatId": chat_id,
        "otherUsername": current_user["username"],
        "otherUserId": current_user["userId"],
        "lastMessagePreview": None,
        "updatedAt": now,
    })

    return chat_id


def list_user_chats(user_id: str) -> list[dict]:
    """Return all chats for a user, sorted by most recently updated."""
    dynamo = get_dynamo_client()
    table = dynamo.Table("user_chats")
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"USER#{user_id}"),
    )
    items = resp.get("Items", [])
    items.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
    return items


def get_chat_meta(chat_id: str) -> dict | None:
    """Fetch chat metadata to verify membership."""
    dynamo = get_dynamo_client()
    table = dynamo.Table("chats")
    resp = table.get_item(Key={"PK": f"CHAT#{chat_id}", "SK": "META"})
    return resp.get("Item")


def send_message(chat_id: str, sender: dict, recipient: dict, text: str) -> tuple[dict, dict]:
    """Dual-write a message: original for sender, translated for recipient.
    Returns (sender_item, recipient_item)."""
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    sender_id = sender["userId"]
    recipient_id = recipient["userId"]
    sender_lang = sender["nativeLanguage"]
    recipient_lang = recipient["nativeLanguage"]

    dynamo = get_dynamo_client()
    messages_table = dynamo.Table("messages")

    # Store original message for sender
    sender_item = {
        "PK": f"USER#{sender_id}#CHAT#{chat_id}",
        "SK": f"MSG#{now}#{msg_id}",
        "messageId": msg_id,
        "text": text,
        "fromUserId": sender_id,
        "language": sender_lang,
        "timestamp": now,
    }
    messages_table.put_item(Item=sender_item)

    # Translate and store for recipient
    if sender_lang == recipient_lang:
        translated_text = text
    else:
        translated_text = translate_text(text, sender_lang, recipient_lang)

    recipient_item = {
        "PK": f"USER#{recipient_id}#CHAT#{chat_id}",
        "SK": f"MSG#{now}#{msg_id}",
        "messageId": msg_id,
        "text": translated_text,
        "fromUserId": sender_id,
        "language": recipient_lang,
        "timestamp": now,
    }
    messages_table.put_item(Item=recipient_item)

    # Update last message preview in user_chats for both users
    user_chats_table = dynamo.Table("user_chats")
    user_chats_table.update_item(
        Key={"PK": f"USER#{sender_id}", "SK": f"CHAT#{chat_id}"},
        UpdateExpression="SET lastMessagePreview = :preview, updatedAt = :now",
        ExpressionAttributeValues={":preview": text[:100], ":now": now},
    )
    user_chats_table.update_item(
        Key={"PK": f"USER#{recipient_id}", "SK": f"CHAT#{chat_id}"},
        UpdateExpression="SET lastMessagePreview = :preview, updatedAt = :now",
        ExpressionAttributeValues={":preview": translated_text[:100], ":now": now},
    )

    return sender_item, recipient_item


def get_messages(user_id: str, chat_id: str, cursor: str | None = None, limit: int = 50) -> tuple[list[dict], str | None]:
    """Fetch paginated messages for a user in a chat.
    Returns (messages, next_cursor)."""
    dynamo = get_dynamo_client()
    table = dynamo.Table("messages")

    query_kwargs: dict = {
        "KeyConditionExpression": Key("PK").eq(f"USER#{user_id}#CHAT#{chat_id}"),
        "ScanIndexForward": False,
        "Limit": limit,
    }

    if cursor:
        query_kwargs["ExclusiveStartKey"] = {
            "PK": f"USER#{user_id}#CHAT#{chat_id}",
            "SK": cursor,
        }

    resp = table.query(**query_kwargs)
    items = resp.get("Items", [])
    next_cursor = None
    if "LastEvaluatedKey" in resp:
        next_cursor = resp["LastEvaluatedKey"]["SK"]

    return items, next_cursor


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Translate text using OpenAI."""
    client = _get_openai_client()
    response = client.chat.completions.create(
        model=settings.openai_translation_model,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a translator. Translate the following text from {source_lang} to {target_lang}. "
                    "Return only the translated text, nothing else."
                ),
            },
            {"role": "user", "content": text},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
