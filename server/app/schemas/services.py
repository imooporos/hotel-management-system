from pydantic import BaseModel, Field


class ServiceResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    price: float
    is_active: bool


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    price: float = Field(..., gt=0)


class ServiceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    price: float | None = Field(None, gt=0)
    is_active: bool | None = None
