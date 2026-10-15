from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import DataCenter, InfrastructureMetric


def _is_demo_meta(meta: dict | None) -> bool:
    meta = meta or {}
    return str(meta.get("dataset", "")).lower() == "demo" or bool(meta.get("demo") is True)


def real_data_center_ids(db: Session) -> list[int]:
    """Return active, non-demo data centers that actually contain real telemetry.

    A center is considered real when it is not soft-deleted / demo-tagged and at
    least one metric exists whose dataset tag is not ``demo``. Older project
    versions may still have synthetic rows in the database; keeping this filter
    in the runtime scope prevents those rows from leaking into the UI's
    "All Data Centers" aggregate.
    """
    centers = list(db.scalars(select(DataCenter).where(DataCenter.deleted_at.is_(None))))
    candidates = {dc.id: dc for dc in centers if not _is_demo_meta(dc.meta)}
    if not candidates:
        return []

    pairs = db.execute(
        select(InfrastructureMetric.data_center_id, InfrastructureMetric.tags)
        .where(InfrastructureMetric.data_center_id.in_(list(candidates)))
    ).all()
    real_ids: set[int] = set()
    for dc_id, tags in pairs:
        tags = tags or {}
        if str(tags.get("dataset", "")).lower() != "demo" and not bool(tags.get("demo") is True):
            real_ids.add(int(dc_id))
    return sorted(real_ids)


def real_data_centers(db: Session) -> list[DataCenter]:
    ids = real_data_center_ids(db)
    if not ids:
        return []
    return list(db.scalars(select(DataCenter).where(DataCenter.id.in_(ids)).order_by(DataCenter.name)))


def ensure_real_data_center(db: Session, data_center_id: int) -> DataCenter | None:
    ids = set(real_data_center_ids(db))
    if data_center_id not in ids:
        return None
    return db.get(DataCenter, data_center_id)
