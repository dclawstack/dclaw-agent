from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import TokenOut, UserLogin, UserOut, UserRegister

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )
    payload = decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    result = await session.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


async def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    if creds is None:
        return None
    payload = decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        return None
    result = await session.execute(select(User).where(User.id == payload["sub"]))
    return result.scalar_one_or_none()


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister, session: AsyncSession = Depends(get_session)
) -> TokenOut:
    existing = await session.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return TokenOut(
        access_token=create_access_token(str(user.id)),
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenOut)
async def login(
    payload: UserLogin, session: AsyncSession = Depends(get_session)
) -> TokenOut:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenOut(
        access_token=create_access_token(str(user.id)),
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def get_me(current: User = Depends(get_current_user)) -> User:
    return current
