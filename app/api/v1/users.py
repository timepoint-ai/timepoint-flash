"""User API endpoints — user-scoped timepoints and data export.

Endpoints:
    GET /api/v1/users/me/timepoints — Paginated list of authenticated user's timepoints
    GET /api/v1/users/me/export     — Full JSON export of user data (GDPR SAR)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db_session
from app.models import Timepoint, TimepointStatus
from app.models_auth import CreditAccount, CreditTransaction, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


# ---------- Response schemas ----------


class UserTimepointSummary(BaseModel):
    """Lightweight timepoint summary for user listings."""

    id: str
    query: str
    slug: str
    status: str
    year: int | None = None
    location: str | None = None
    has_image: bool = False
    created_at: str | None = None


class UserTimepointListResponse(BaseModel):
    """Paginated user timepoints."""

    items: list[UserTimepointSummary]
    total: int
    page: int
    page_size: int


class UserExportResponse(BaseModel):
    """Full user data export for GDPR Subject Access Requests."""

    user: dict
    credit_history: list[dict]
    timepoints: list[dict]


# ---------- Endpoints ----------


@router.get("/me/timepoints", response_model=UserTimepointListResponse)
async def get_my_timepoints(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    user: User | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserTimepointListResponse:
    """Paginated list of the authenticated user's timepoints."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    query = (
        select(Timepoint)
        .where(Timepoint.user_id == user.id, Timepoint.is_deleted == False)  # noqa: E712
        .order_by(Timepoint.created_at.desc())
    )

    if status_filter:
        try:
            status_enum = TimepointStatus(status_filter)
            query = query.where(Timepoint.status == status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter

    # Total count
    count_subquery = query.subquery()
    count_result = await session.execute(
        select(func.count()).select_from(count_subquery)
    )
    total = count_result.scalar() or 0

    # Paginated results
    result = await session.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    timepoints = result.scalars().all()

    items = [
        UserTimepointSummary(
            id=tp.id,
            query=tp.query,
            slug=tp.slug,
            status=tp.status.value if tp.status else "unknown",
            year=tp.year,
            location=tp.location,
            has_image=tp.has_image,
            created_at=tp.created_at.isoformat() if tp.created_at else None,
        )
        for tp in timepoints
    ]

    return UserTimepointListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/me/export", response_model=UserExportResponse)
async def export_my_data(
    user: User | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserExportResponse:
    """Full JSON export of user data for GDPR Subject Access Request compliance.

    Returns profile, complete credit history, and full scene JSON for every
    user timepoint. Requires Bearer JWT.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # User profile
    user_data = {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "is_active": user.is_active,
    }

    # Credit history
    acct_result = await session.execute(
        select(CreditAccount).where(CreditAccount.user_id == user.id)
    )
    account = acct_result.scalar_one_or_none()

    credit_history: list[dict] = []
    if account is not None:
        txn_result = await session.execute(
            select(CreditTransaction)
            .where(CreditTransaction.credit_account_id == account.id)
            .order_by(CreditTransaction.created_at.desc())
        )
        credit_history = [
            {
                "amount": t.amount,
                "balance_after": t.balance_after,
                "type": t.transaction_type.value,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in txn_result.scalars()
        ]

    # All user timepoints with full scene data
    tp_result = await session.execute(
        select(Timepoint)
        .where(Timepoint.user_id == user.id)
        .order_by(Timepoint.created_at.desc())
    )
    timepoints = [tp.to_dict() for tp in tp_result.scalars()]

    return UserExportResponse(
        user=user_data,
        credit_history=credit_history,
        timepoints=timepoints,
    )
