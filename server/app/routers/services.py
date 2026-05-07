from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_connection
from app.core.security import require_role
from app.schemas.services import ServiceResponse, ServiceCreate, ServiceUpdate

router = APIRouter(prefix="/api/services", tags=["Услуги"])


@router.get("/", response_model=list[ServiceResponse])
async def list_services():
    """Список дополнительных услуг."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            "SELECT id, name, description, price, is_active FROM services WHERE is_active = TRUE ORDER BY name"
        )
    return [ServiceResponse(**dict(r)) for r in rows]


@router.get("/all", response_model=list[ServiceResponse])
async def list_all_services(
    _: dict = Depends(require_role("admin")),
):
    """Список всех услуг, включая неактивные (только админ)."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            "SELECT id, name, description, price, is_active FROM services ORDER BY name"
        )
    return [ServiceResponse(**dict(r)) for r in rows]


@router.post("/", response_model=ServiceResponse, status_code=201)
async def create_service(
    data: ServiceCreate,
    _: dict = Depends(require_role("admin")),
):
    """Создание услуги (только админ)."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO services (name, description, price)
            VALUES ($1, $2, $3)
            RETURNING id, name, description, price, is_active
            """,
            data.name, data.description, data.price,
        )
    return ServiceResponse(**dict(row))


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    data: ServiceUpdate,
    _: dict = Depends(require_role("admin")),
):
    """Обновление услуги (только админ)."""
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    set_parts = []
    values = []
    for i, (key, val) in enumerate(updates.items(), 1):
        set_parts.append(f"{key} = ${i}")
        values.append(val)

    values.append(service_id)
    query = f"""
        UPDATE services SET {', '.join(set_parts)}
        WHERE id = ${len(values)}
        RETURNING id, name, description, price, is_active
    """

    async with get_connection() as conn:
        row = await conn.fetchrow(query, *values)
        if row is None:
            raise HTTPException(status_code=404, detail="Услуга не найдена")

    return ServiceResponse(**dict(row))


@router.delete("/{service_id}")
async def delete_service(
    service_id: int,
    _: dict = Depends(require_role("admin")),
):
    """Деактивация услуги (мягкое удаление, только админ)."""
    async with get_connection() as conn:
        result = await conn.execute(
            "UPDATE services SET is_active = FALSE WHERE id = $1", service_id,
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Услуга не найдена")

    return {"detail": "Услуга деактивирована"}
