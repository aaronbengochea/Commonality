from fastapi import APIRouter

router = APIRouter()


@router.post("/signup")
async def signup():
    # TODO: Implement in Phase 2
    return {"message": "not implemented"}


@router.post("/login")
async def login():
    # TODO: Implement in Phase 2
    return {"message": "not implemented"}


@router.get("/me")
async def me():
    # TODO: Implement in Phase 2
    return {"message": "not implemented"}
