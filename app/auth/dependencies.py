"""FastAPI dependencies for authentication and credit checks.

When AUTH_ENABLED=false (default), all dependencies are no-ops
so existing unauthenticated access continues to work.
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db_session
from app.models_auth import User

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> User | None:
    """Extract and validate the Bearer token, returning the User.

    When AUTH_ENABLED=false, returns None (open access).

    Raises:
        HTTPException 401: If auth is enabled and token is missing/invalid.
    """
    settings = get_settings()
    if not settings.AUTH_ENABLED:
        return None

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[len("Bearer "):]

    from app.auth.jwt_handler import decode_access_token

    try:
        user_id = decode_access_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    return user


async def require_admin_key(request: Request) -> None:
    """Verify the X-Admin-Key header matches ADMIN_API_KEY.

    Returns 403 if the key is empty (disabled) or doesn't match.
    """
    settings = get_settings()
    if not settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin endpoints are disabled (ADMIN_API_KEY not set)",
        )

    provided = request.headers.get("X-Admin-Key", "")
    if provided != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )


def require_credits(cost: int) -> Callable:
    """Factory that returns a dependency checking the user has enough credits.

    When AUTH_ENABLED=false, the returned dependency is a no-op.

    Usage::

        @router.post("/generate")
        async def generate(
            user: User | None = Depends(get_current_user),
            _credits=Depends(require_credits(5)),
        ):
            ...
    """

    async def _check_credits(
        request: Request,
        user: User | None = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> None:
        settings = get_settings()
        if not settings.AUTH_ENABLED or user is None:
            return

        from app.auth.credits import check_balance

        has_enough = await check_balance(session, user.id, cost)
        if not has_enough:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. This operation costs {cost} credits.",
            )

    return _check_credits
