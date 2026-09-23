"""规则服务：地形/趟次/装载规则、约束配置版本管理。"""
from __future__ import annotations

from sqlalchemy import select

from ..models.rules import (
    ConstraintConfig,
    ConstraintSnapshot,
    LoadRule,
    TerrainRule,
    TripRule,
)


def list_terrain_rules(db) -> list[TerrainRule]:
    return list(db.scalars(select(TerrainRule)))


def list_trip_rules(db) -> list[TripRule]:
    return list(db.scalars(select(TripRule)))


def list_load_rules(db) -> list[LoadRule]:
    return list(db.scalars(select(LoadRule)))


def list_constraint_configs(db, *, active_only: bool = False) -> list[ConstraintConfig]:
    stmt = select(ConstraintConfig).order_by(ConstraintConfig.version.desc())
    if active_only:
        stmt = stmt.where(ConstraintConfig.is_active.is_(True))
    return list(db.scalars(stmt))


def get_active_constraint_config(db) -> ConstraintConfig | None:
    stmt = select(ConstraintConfig).where(ConstraintConfig.is_active.is_(True)).limit(1)
    return db.scalars(stmt).first()


def get_constraint_config_by_version(db, version: str) -> ConstraintConfig | None:
    return db.scalars(
        select(ConstraintConfig).where(ConstraintConfig.version == version).limit(1)
    ).first()


def upsert_constraint_config(db, payload) -> ConstraintConfig:
    existing = get_constraint_config_by_version(db, payload.version)
    if existing is None:
        cfg = ConstraintConfig(
            version=payload.version,
            name=payload.name,
            description=payload.description,
            hard_constraints=payload.hard_constraints,
            soft_constraints=payload.soft_constraints,
            weights=payload.weights,
            is_active=payload.is_active,
        )
        db.add(cfg)
    else:
        for f in (
            "name",
            "description",
            "hard_constraints",
            "soft_constraints",
            "weights",
            "is_active",
        ):
            v = getattr(payload, f, None)
            if v is not None:
                setattr(existing, f, v)
        cfg = existing
    if payload.is_active:
        # 同版本互斥：取消其它激活
        for other in list_constraint_configs(db):
            if other.id != cfg.id and other.is_active:
                other.is_active = False
    db.commit()
    db.refresh(cfg)
    return cfg


def create_constraint_snapshot(db, *, task_id: str, config: ConstraintConfig) -> ConstraintSnapshot:
    snapshot = ConstraintSnapshot(
        task_id=task_id,
        rule_version=config.version,
        hard_constraints=config.hard_constraints,
        soft_constraints=config.soft_constraints,
        weights=config.weights,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
