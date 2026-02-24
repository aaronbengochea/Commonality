from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.auth.models import LoginRequest, SignupRequest, TokenResponse, UserResponse
from app.auth.service import (
    UsernameExistsError,
    create_access_token,
    create_user,
    get_user_by_username,
    verify_password,
)

router = APIRouter()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest):
    existing = get_user_by_username(body.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    try:
        user = create_user(
            username=body.username,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
            native_language=body.native_language,
        )
    except UsernameExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    token = create_access_token(user["userId"])
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user = get_user_by_username(body.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    if not verify_password(body.password, user["passwordHash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = create_access_token(user["userId"])
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        user_id=current_user["userId"],
        username=current_user["username"],
        first_name=current_user["firstName"],
        last_name=current_user["lastName"],
        native_language=current_user["nativeLanguage"],
    )
