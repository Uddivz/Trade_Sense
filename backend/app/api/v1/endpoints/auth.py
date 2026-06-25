"""
TradeSense — Auth Endpoints
Implements register, login, and /me routes.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, UserResponse, Token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Register a new user.
    Validates password strength, hashes password, and persists user.
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    if existing_user:
        logger.warning("Registration rejected — email already in use", extra={"email": user_in.email})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    new_user = User(
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        full_name=user_in.full_name,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    logger.info("New user registered", extra={"user_id": str(new_user.id), "email": new_user.email})
    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    OAuth2 compatible token login, retrieve a JWT access token.
    Accepts standard form-encoded username (email) and password.
    """
    # Retrieve user
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.password_hash):
        logger.warning("Login failed — invalid credentials", extra={"email": form_data.username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning("Login rejected — inactive account", extra={"user_id": str(user.id)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    # Generate access token
    access_token = create_access_token(subject=user.id)
    logger.info("User logged in", extra={"user_id": str(user.id), "email": user.email})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Return the profile of the currently authenticated user.
    Reads the Bearer token from the Authorization header, validates it,
    and returns the corresponding user record.
    """
    return current_user
