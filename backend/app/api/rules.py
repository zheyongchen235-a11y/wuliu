"""规则配置 API: /api/v1/rules."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.common import ApiResponse
from ..schemas.rules import (
    ConstraintConfigCreate,
    ConstraintConfigOut,
    LoadRuleOut,
    TerrainRuleOut,
    TripRuleOut,
)
from ..services import rules as rules_service

router = APIRouter(prefix="/api/v1/rules", tags=["规则配置"])


@router.get("/terrain", response_model=ApiResponse[list[TerrainRuleOut]])
def list_terrain_rules(db: Session = Depends(get_db)):
    items = rules_service.list_terrain_rules(db)
    return ApiResponse(data=[TerrainRuleOut.model_validate(t) for t in items])


@router.get("/trip", response_model=ApiResponse[list[TripRuleOut]])
def list_trip_rules(db: Session = Depends(get_db)):
    items = rules_service.list_trip_rules(db)
    return ApiResponse(data=[TripRuleOut.model_validate(t) for t in items])


@router.get("/load", response_model=ApiResponse[list[LoadRuleOut]])
def list_load_rules(db: Session = Depends(get_db)):
    items = rules_service.list_load_rules(db)
    return ApiResponse(data=[LoadRuleOut.model_validate(l) for l in items])


@router.get("/constraints", response_model=ApiResponse[list[ConstraintConfigOut]])
def list_constraints(active_only: bool = False, db: Session = Depends(get_db)):
    items = rules_service.list_constraint_configs(db, active_only=active_only)
    return ApiResponse(data=[ConstraintConfigOut.model_validate(c) for c in items])


@router.post("/constraints", response_model=ApiResponse[ConstraintConfigOut])
def upsert_constraint(payload: ConstraintConfigCreate, db: Session = Depends(get_db)):
    try:
        cfg = rules_service.upsert_constraint_config(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ApiResponse(data=ConstraintConfigOut.model_validate(cfg))
