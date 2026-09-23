"""基础数据 API: /api/v1/stores, /vehicles, /routes, /drivers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.basic import (
    DriverOut,
    RouteCreate,
    RouteOut,
    StoreCreate,
    StoreOut,
    StoreUpdate,
    VehicleCreate,
    VehicleOut,
)
from ..schemas.common import ApiResponse, Page
from ..services import basic as basic_service

router = APIRouter(prefix="/api/v1", tags=["基础数据"])


@router.get("/stores", response_model=ApiResponse[list[StoreOut]])
def list_stores(
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    items = basic_service.list_stores(db, enabled_only=enabled_only)
    return ApiResponse(data=[StoreOut.model_validate(s) for s in items])


@router.post("/stores", response_model=ApiResponse[StoreOut])
def create_or_update_store(payload: StoreCreate, db: Session = Depends(get_db)):
    store = basic_service.upsert_store(db, payload)
    return ApiResponse(data=StoreOut.model_validate(store))


@router.put("/stores/{store_id}", response_model=ApiResponse[StoreOut])
def update_store(store_id: str, payload: StoreUpdate, db: Session = Depends(get_db)):
    store = basic_service.get_store(db, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    for f in ("name", "address", "terrain_type", "time_window", "priority", "enabled"):
        v = getattr(payload, f, None)
        if v is not None:
            setattr(store, f, v)
    db.commit()
    db.refresh(store)
    return ApiResponse(data=StoreOut.model_validate(store))


@router.get("/routes", response_model=ApiResponse[list[RouteOut]])
def list_routes(enabled_only: bool = Query(False), db: Session = Depends(get_db)):
    items = basic_service.list_routes(db, enabled_only=enabled_only)
    return ApiResponse(data=[RouteOut.model_validate(r) for r in items])


@router.post("/routes", response_model=ApiResponse[RouteOut])
def upsert_route(payload: RouteCreate, db: Session = Depends(get_db)):
    route = basic_service.upsert_route(db, payload)
    return ApiResponse(data=RouteOut.model_validate(route))


@router.get("/vehicles", response_model=ApiResponse[list[VehicleOut]])
def list_vehicles(
    vehicle_type: str | None = Query(None),
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    items = basic_service.list_vehicles(db, vehicle_type=vehicle_type, enabled_only=enabled_only)
    return ApiResponse(data=[VehicleOut.model_validate(v) for v in items])


@router.post("/vehicles", response_model=ApiResponse[VehicleOut])
def upsert_vehicle(payload: VehicleCreate, db: Session = Depends(get_db)):
    vehicle = basic_service.upsert_vehicle(db, payload)
    return ApiResponse(data=VehicleOut.model_validate(vehicle))


@router.get("/drivers", response_model=ApiResponse[list[DriverOut]])
def list_drivers(db: Session = Depends(get_db)):
    items = basic_service.list_drivers(db)
    return ApiResponse(data=[DriverOut.model_validate(d) for d in items])
