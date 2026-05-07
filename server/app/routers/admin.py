"""Админские служебные эндпоинты — журнал аудита."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..core.db import acquire_for_user
from ..core.security import CurrentUser, get_current_user, require_role

router = APIRouter(prefix="/admin", tags=["admin"])


class AuditEntry(BaseModel):
    log_id: int
    table_name: str
    row_pk: str
    action: str
    actor_id: int | None = None
    actor_name: str | None = None
    happened_at: datetime
    new_data: Any | None = None
    old_data: Any | None = None


@router.get(
    "/audit",
    response_model=list[AuditEntry],
    dependencies=[Depends(require_role("admin"))],
)
async def audit(
    table_name: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
) -> list[AuditEntry]:
    async with acquire_for_user(user.user_id) as conn:
        if table_name:
            rows = await conn.fetch(
                "SELECT log_id, table_name, row_pk, action::text, actor_id, actor_name, "
                "       happened_at, new_data, old_data "
                "  FROM audit_log WHERE table_name = $1 "
                "  ORDER BY happened_at DESC LIMIT $2",
                table_name,
                limit,
            )
        else:
            rows = await conn.fetch(
                "SELECT log_id, table_name, row_pk, action::text, actor_id, actor_name, "
                "       happened_at, new_data, old_data "
                "  FROM audit_log ORDER BY happened_at DESC LIMIT $1",
                limit,
            )
    return [AuditEntry(**dict(r)) for r in rows]
