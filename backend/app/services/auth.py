from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.models import User


class AuthenticationError(Exception):
    """Raised when user authentication fails."""


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email.lower())
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, email: str, password: str) -> User:
    existing = await get_user_by_email(session, email)
    if existing:
        raise ValueError("User with this email already exists")

    user = User(
        email=email.lower(),
        password_hash=get_password_hash(password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(session, email)
    if not user or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid credentials")
    return user


async def create_token_for_user(user: User) -> str:
    settings = get_settings()
    expires = timedelta(minutes=settings.access_token_expire_minutes)
    return create_access_token(subject=user.id, expires_delta=expires)
