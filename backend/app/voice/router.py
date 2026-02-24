from fastapi import APIRouter

router = APIRouter()


@router.post("/token")
async def create_voice_token():
    # TODO: Implement in Phase 4
    return {"message": "not implemented"}
