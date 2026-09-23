"""报表 API: /api/v1/reports/..."""
from __future__ import annotations

from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.common import ApiResponse
from ..schemas.report import (
    AttendanceReport,
    LoadRateReport,
    TripAchievementReport,
)
from ..services import reports as reports_service

router = APIRouter(prefix="/api/v1/reports", tags=["报表"])


def _parse_date(s: str) -> date_cls:
    try:
        return date_cls.fromisoformat(s)
    except ValueError:
        raise HTTPException(status_code=400, detail="date 格式应为 YYYY-MM-DD")


@router.get("/attendance", response_model=ApiResponse[list[AttendanceReport]])
def attendance_report(date: str = Query(...), db: Session = Depends(get_db)):
    items = reports_service.build_attendance_report(db, _parse_date(date))
    return ApiResponse(data=items)


@router.get("/load-rate", response_model=ApiResponse[list[LoadRateReport]])
def load_rate_report(date: str = Query(...), db: Session = Depends(get_db)):
    items = reports_service.build_load_rate_report(db, _parse_date(date))
    return ApiResponse(data=items)


@router.get("/trip-achievement", response_model=ApiResponse[list[TripAchievementReport]])
def trip_achievement_report(date: str = Query(...), db: Session = Depends(get_db)):
    items = reports_service.build_trip_achievement_report(db, _parse_date(date))
    return ApiResponse(data=items)
