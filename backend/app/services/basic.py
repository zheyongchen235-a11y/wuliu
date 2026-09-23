"""基础数据服务：门店、线路、车辆、司机 CRUD。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models.basic import (
    Driver,
    Route,
    Store,
    StoreRouteMapping,
    Vehicle,
    VehicleTerrainCapability,
    Warehouse,
)


def list_stores(db: Session, *, enabled_only: bool = False) -> list[Store]:
    stmt = select(Store).options(selectinload(Store.route_mappings))
    if enabled_only:
        stmt = stmt.where(Store.enabled.is_(True))
    return list(db.scalars(stmt))


def get_store(db: Session, store_id: str) -> Store | None:
    return db.get(Store, store_id)


def upsert_store(db: Session, payload) -> Store:
    store = db.get(Store, payload.id)
    if store is None:
        store = Store(
            id=payload.id,
            name=payload.name,
            address=payload.address,
            longitude=payload.longitude,
            latitude=payload.latitude,
            terrain_type=payload.terrain_type,
            time_window=payload.time_window,
            priority=payload.priority,
            enabled=payload.enabled,
        )
        db.add(store)
    else:
        for f in ("name", "address", "longitude", "latitude", "terrain_type", "time_window", "priority", "enabled"):
            v = getattr(payload, f, None)
            if v is not None:
                setattr(store, f, v)
        db.query(StoreRouteMapping).filter(StoreRouteMapping.store_id == store.id).delete()
    db.flush()
    for mapping in payload.route_mappings:
        db.add(
            StoreRouteMapping(
                store_id=store.id,
                route_id=mapping.route_id,
                is_primary=mapping.is_primary,
            )
        )
    db.commit()
    db.refresh(store)
    return store


def list_routes(db: Session, *, enabled_only: bool = False) -> list[Route]:
    stmt = select(Route)
    if enabled_only:
        stmt = stmt.where(Route.enabled.is_(True))
    return list(db.scalars(stmt))


def upsert_route(db: Session, payload) -> Route:
    route = db.get(Route, payload.id)
    if route is None:
        route = Route(
            id=payload.id,
            name=payload.name,
            terrain_type=payload.terrain_type,
            description=payload.description,
            enabled=payload.enabled,
        )
        db.add(route)
    else:
        for f in ("name", "terrain_type", "description", "enabled"):
            v = getattr(payload, f, None)
            if v is not None:
                setattr(route, f, v)
    db.commit()
    db.refresh(route)
    return route


def list_drivers(db: Session) -> list[Driver]:
    return list(db.scalars(select(Driver)))


def list_vehicles(
    db: Session,
    *,
    vehicle_type: str | None = None,
    enabled_only: bool = False,
) -> list[Vehicle]:
    stmt = select(Vehicle).options(selectinload(Vehicle.terrain_capability))
    if vehicle_type:
        stmt = stmt.where(Vehicle.vehicle_type == vehicle_type)
    if enabled_only:
        stmt = stmt.where(Vehicle.enabled.is_(True))
    return list(db.scalars(stmt))


def get_vehicle(db: Session, vehicle_id: str) -> Vehicle | None:
    return db.get(Vehicle, vehicle_id)


def upsert_vehicle(db: Session, payload) -> Vehicle:
    vehicle = db.get(Vehicle, payload.id)
    capabilities = getattr(payload, "terrain_capabilities", None) or {}
    if vehicle is None:
        vehicle = Vehicle(
            id=payload.id,
            plate=payload.plate,
            vehicle_type=payload.vehicle_type,
            min_load=payload.min_load,
            max_load=payload.max_load,
            max_trips_per_day=payload.max_trips_per_day,
            driver_id=payload.driver_id,
            warehouse_id=payload.warehouse_id,
            status=payload.status,
            enabled=payload.enabled,
        )
        db.add(vehicle)
    else:
        for f in (
            "plate",
            "vehicle_type",
            "min_load",
            "max_load",
            "max_trips_per_day",
            "driver_id",
            "warehouse_id",
            "status",
            "enabled",
        ):
            v = getattr(payload, f, None)
            if v is not None:
                setattr(vehicle, f, v)
        db.query(VehicleTerrainCapability).filter(
            VehicleTerrainCapability.vehicle_id == vehicle.id
        ).delete()
    db.flush()
    for terrain, can_access in capabilities.items():
        db.add(
            VehicleTerrainCapability(
                vehicle_id=vehicle.id,
                terrain_type=terrain,
                can_access=bool(can_access),
            )
        )
    db.commit()
    db.refresh(vehicle)
    return vehicle


def list_warehouses(db: Session) -> list[Warehouse]:
    return list(db.scalars(select(Warehouse)))
