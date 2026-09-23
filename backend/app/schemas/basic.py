"""基础数据 schemas。"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .common import ORMModel


class StoreRouteMappingInline(BaseModel):
    route_id: str
    is_primary: bool = False


class StoreCreate(BaseModel):
    id: str = Field(..., description="门店编码")
    name: str
    address: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    terrain_type: str = "normal"
    time_window: str = "any"
    priority: int = 5
    enabled: bool = True
    route_mappings: list[StoreRouteMappingInline] = Field(default_factory=list)


class StoreUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    terrain_type: str | None = None
    time_window: str | None = None
    priority: int | None = None
    enabled: bool | None = None


class StoreRouteMappingOut(ORMModel):
    id: str
    store_id: str
    route_id: str
    is_primary: bool


class StoreOut(ORMModel):
    id: str
    name: str
    address: str | None
    longitude: float | None
    latitude: float | None
    terrain_type: str
    time_window: str
    priority: int
    enabled: bool


class RouteCreate(BaseModel):
    id: str
    name: str
    terrain_type: str = "normal"
    description: str | None = None
    enabled: bool = True


class RouteOut(ORMModel):
    id: str
    name: str
    terrain_type: str
    description: str | None
    enabled: bool


class DriverOut(ORMModel):
    id: str
    name: str
    phone: str | None
    status: str


class VehicleCreate(BaseModel):
    id: str
    plate: str
    vehicle_type: str = Field(..., description="4m2 | big | small")
    min_load: int
    max_load: int
    max_trips_per_day: int = 2
    driver_id: str | None = None
    warehouse_id: str | None = None
    status: str = "available"
    enabled: bool = True
    terrain_capabilities: dict[str, bool] = Field(
        default_factory=lambda: {"normal": True, "mid": True, "strict": True}
    )


class VehicleOut(ORMModel):
    id: str
    plate: str
    vehicle_type: str
    min_load: int
    max_load: int
    max_trips_per_day: int
    driver_id: str | None
    warehouse_id: str | None
    status: str
    enabled: bool


class WarehouseOut(ORMModel):
    id: str
    name: str
    address: str | None
