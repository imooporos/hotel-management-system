from pydantic import BaseModel
from datetime import date


class RevenueByCategory(BaseModel):
    category_id: int
    category_name: str
    total_bookings: int
    total_revenue: float
    avg_revenue_per_booking: float
    avg_nights: float


class OccupancyReport(BaseModel):
    start_date: date
    end_date: date
    occupancy_rate: float
    category_id: int | None = None
    category_name: str | None = None


class AuditLogEntry(BaseModel):
    id: int
    table_name: str
    record_id: int
    action: str
    old_data: dict | None = None
    new_data: dict | None = None
    changed_by: str | None = None
    changed_at: str
