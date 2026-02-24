from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def create_chat():
    # TODO: Implement in Phase 3
    return {"message": "not implemented"}


@router.get("")
async def list_chats():
    # TODO: Implement in Phase 3
    return {"chats": []}


@router.get("/{chat_id}/messages")
async def get_messages(chat_id: str, cursor: str | None = None, limit: int = 50):
    # TODO: Implement in Phase 3
    return {"messages": [], "next_cursor": None}
