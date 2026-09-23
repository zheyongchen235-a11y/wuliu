"""业务基础数据模型：门店、线路、车辆、司机、仓库。"""
from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, GUID, TimestampMixin


class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouse"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    address: Mapped[str | None] = mapped_column(String(256))
    organization_id: Mapped[str | None] = mapped_column(String(64))


class Route(Base, TimestampMixin):
    """配送线路。"""

    __tablename__ = "route"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    terrain_type: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")
    # normal / mid / strict（普通 / 中控 / 严控）
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Store(Base, TimestampMixin):
    """门店。"""

    __tablename__ = "store"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    address: Mapped[str | None] = mapped_column(String(256))
    longitude: Mapped[float | None] = mapped_column(Float)
    latitude: Mapped[float | None] = mapped_column(Float)
    terrain_type: Mapped[str] = mapped_column(String(32), default="normal")
    time_window: Mapped[str] = mapped_column(String(16), default="any")
    # AM / PM / any（上午门店 / 下午门店 / 不限）
    priority: Mapped[int] = mapped_column(Integer, default=5)
    # 1 高 - 9 低
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    route_mappings: Mapped[list["StoreRouteMapping"]] = relationship(
        "StoreRouteMapping", back_populates="store", cascade="all, delete-orphan"
    )


class StoreRouteMapping(Base, TimestampMixin):
    """门店-线路多对多映射。"""

    __tablename__ = "store_route_mapping"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    store_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("store.id", ondelete="CASCADE"), nullable=False
    )
    route_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("route.id", ondelete="CASCADE"), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    # 是否主线路（交界门店可有多条，但需指定一条主线路）

    store: Mapped[Store] = relationship("Store", back_populates="route_mappings")
    route: Mapped[Route] = relationship("Route")


class Driver(Base, TimestampMixin):
    __tablename__ = "driver"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    organization_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="available")
    # available / on_leave / disabled


class Vehicle(Base, TimestampMixin):
    """车辆档案。"""

    __tablename__ = "vehicle"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plate: Mapped[str] = mapped_column(String(32), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # 4m2 / big / small（四米二 / 大包 / 小包）
    min_load: Mapped[int] = mapped_column(Integer, nullable=False)
    max_load: Mapped[int] = mapped_column(Integer, nullable=False)
    max_trips_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    driver_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("driver.id"))
    warehouse_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("warehouse.id"))
    status: Mapped[str] = mapped_column(String(16), default="available")
    # available / maintenance / dispatched / disabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    terrain_capability: Mapped[list["VehicleTerrainCapability"]] = relationship(
        "VehicleTerrainCapability", back_populates="vehicle", cascade="all, delete-orphan"
    )


class VehicleTerrainCapability(Base, TimestampMixin):
    """车辆地形能力：4m2 全能去 / big 大小包能去 / small 小包能去。"""

    __tablename__ = "vehicle_terrain_capability"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    vehicle_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False
    )
    terrain_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # normal / mid / strict
    can_access: Mapped[bool] = mapped_column(Boolean, default=True)

    vehicle: Mapped[Vehicle] = relationship("Vehicle", back_populates="terrain_capability")
