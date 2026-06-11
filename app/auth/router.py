from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.auth.models import User
from app.auth.schemas import AccessTokenResponse, RefreshTokenRequest, TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.auth.security import create_access_token, create_refresh_token, decode_token
from app.auth.service import authenticate_user, create_user, get_user_by_email, get_user_by_id
from app.common.dependencies import get_current_user
from app.common.exceptions import BadRequestException, UnauthorizedException
from app.common.responses import success_response
from app.database import get_db


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register/", status_code=status.HTTP_201_CREATED)
def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, request.email):
        raise BadRequestException("Email already registered")
    user = create_user(db, request.full_name, request.email, request.password)
    return success_response("User registered successfully", UserResponse.model_validate(user).model_dump(mode="json"))


@router.post("/login/")
def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise UnauthorizedException("Invalid email or password")
    token_data = TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )
    return success_response("Login successful", token_data.model_dump(mode="json"))


@router.post("/refresh/")
def refresh_access_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid or expired refresh token")
    user_id = payload.get("sub")
    user = get_user_by_id(db, int(user_id)) if user_id else None
    if not user or not user.is_active:
        raise UnauthorizedException("User not found or inactive")
    token_data = AccessTokenResponse(access_token=create_access_token(user.id))
    return success_response("Access token refreshed successfully", token_data.model_dump(mode="json"))


@router.get("/me/")
def get_me(current_user: User = Depends(get_current_user)):
    return success_response("Current user fetched successfully", UserResponse.model_validate(current_user).model_dump(mode="json"))
