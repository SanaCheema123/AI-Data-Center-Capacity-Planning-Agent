from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import Cluster, DataCenter, DataSource, InfrastructureMetric
from app.schemas.planning import CSVImportError, CSVImportResult

REQUIRED_COLUMNS = {
    "timestamp", "data_center", "cluster", "gpu_utilization", "installed_gpus",
    "power_usage_mw", "power_capacity_mw", "storage_used_tb", "storage_capacity_tb",
    "network_throughput_gbps", "network_capacity_gbps", "cooling_power_mw",
}
OPTIONAL_COLUMNS: set[str] = set()
METRICS = {
    "gpu_utilization": ("gpu", "%"),
    "installed_gpus": ("gpu", "GPUs"),
    "power_usage_mw": ("power", "MW"),
    "power_capacity_mw": ("power", "MW"),
    "cooling_power_mw": ("power", "MW"),
    "storage_used_tb": ("storage", "TB"),
    "storage_capacity_tb": ("storage", "TB"),
    "network_throughput_gbps": ("network", "Gbps"),
    "network_capacity_gbps": ("network", "Gbps"),
}


def _parse_timestamp(raw: str) -> datetime:
    value = raw.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class CSVImportService:
    @staticmethod
    def import_bytes(db: Session, filename: str, content: bytes) -> CSVImportResult:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            return CSVImportResult(filename=filename, rows_received=0, rows_imported=0, metrics_inserted=0, duplicates_skipped=0,
                                   errors=[CSVImportError(row=0, message="CSV must be UTF-8 encoded")])
        reader = csv.DictReader(io.StringIO(text))
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            return CSVImportResult(filename=filename, rows_received=0, rows_imported=0, metrics_inserted=0, duplicates_skipped=0,
                                   errors=[CSVImportError(row=1, message=f"Missing required columns: {', '.join(missing)}")])

        data_centers = list(db.scalars(select(DataCenter).where(DataCenter.deleted_at.is_(None))))
        dc_lookup = {dc.code.lower(): dc for dc in data_centers}
        dc_lookup.update({dc.name.lower(): dc for dc in data_centers})
        # Keep provenance per uploaded file. Re-importing the same filename reuses
        # the same source, while a different CSV is visible as its own real source.
        source = next((
            item for item in db.scalars(select(DataSource).where(DataSource.source_type == "csv").order_by(DataSource.id))
            if (item.configuration or {}).get("filename") == filename
        ), None)
        if source is None:
            safe_name = f"CSV · {filename}"[:120]
            # Avoid collisions if two historical records already used the same label.
            base = safe_name
            suffix = 2
            while db.scalar(select(DataSource).where(DataSource.name == safe_name)) is not None:
                tail = f" ({suffix})"
                safe_name = f"{base[:120-len(tail)]}{tail}"
                suffix += 1
            source = DataSource(
                name=safe_name,
                source_type="csv",
                status="connected",
                configuration={"filename": filename, "data_origin": "real"},
            )
            db.add(source); db.flush()

        cluster_lookup = {(c.data_center_id, c.name.lower()): c for c in db.scalars(select(Cluster))}
        parsed: list[tuple[int, DataCenter, Cluster | None, datetime, dict[str, float]]] = []
        errors: list[CSVImportError] = []
        rows_received = 0
        for row_number, row in enumerate(reader, start=2):
            rows_received += 1
            dc_raw = (row.get("data_center") or "").strip()
            dc = dc_lookup.get(dc_raw.lower())
            if dc is None:
                if not dc_raw:
                    errors.append(CSVImportError(row=row_number, field="data_center", message="Data center is required")); continue
                base_code = "".join(ch if ch.isalnum() else "-" for ch in dc_raw.upper()).strip("-")[:64] or "DATACENTER"
                code = base_code
                suffix = 2
                while db.scalar(select(DataCenter).where(DataCenter.code == code)) is not None:
                    code = f"{base_code[:58]}-{suffix}"
                    suffix += 1
                dc = DataCenter(
                    name=dc_raw, code=code, region="unspecified", country="unspecified",
                    timezone="UTC", status="active",
                    meta={"registered_via": "csv", "source_filename": filename, "data_origin": "real"},
                )
                db.add(dc); db.flush()
                dc_lookup[dc_raw.lower()] = dc
                dc_lookup[dc.code.lower()] = dc
            try:
                ts = _parse_timestamp(row.get("timestamp") or "")
            except Exception:
                errors.append(CSVImportError(row=row_number, field="timestamp", message="Invalid ISO-8601 timestamp")); continue
            cluster_name = (row.get("cluster") or "").strip()
            cluster = None
            if cluster_name:
                key = (dc.id, cluster_name.lower())
                cluster = cluster_lookup.get(key)
                if cluster is None:
                    try:
                        installed = int(float(row.get("installed_gpus") or 0))
                    except ValueError:
                        installed = 0
                    cluster = Cluster(data_center_id=dc.id, name=cluster_name, cluster_type="gpu", installed_gpu_count=max(installed, 0), status="active")
                    db.add(cluster); db.flush(); cluster_lookup[key] = cluster
            values: dict[str, float] = {}
            bad = False
            for name in METRICS:
                raw = row.get(name)
                if raw is None or raw.strip() == "":
                    if name in OPTIONAL_COLUMNS:
                        continue
                    errors.append(CSVImportError(row=row_number, field=name, message="Value is required")); bad = True; break
                try:
                    value = float(raw)
                except ValueError:
                    errors.append(CSVImportError(row=row_number, field=name, message="Value must be numeric")); bad = True; break
                if value < 0:
                    errors.append(CSVImportError(row=row_number, field=name, message="Value cannot be negative")); bad = True; break
                if name == "gpu_utilization" and value > 100:
                    errors.append(CSVImportError(row=row_number, field=name, message="GPU utilization cannot exceed 100%")); bad = True; break
                values[name] = value
            if not bad:
                # Cross-field physical validation prevents nonsensical capacity
                # data from entering the forecasting pipeline.
                installed = values.get("installed_gpus", 0.0)
                if installed <= 0 or abs(installed - round(installed)) > 1e-9:
                    errors.append(CSVImportError(row=row_number, field="installed_gpus", message="Installed GPUs must be a positive whole number")); bad = True
                elif values["power_capacity_mw"] <= 0 or values["power_usage_mw"] > values["power_capacity_mw"]:
                    errors.append(CSVImportError(row=row_number, field="power_capacity_mw", message="Power capacity must be positive and >= power usage")); bad = True
                elif values["storage_capacity_tb"] <= 0 or values["storage_used_tb"] > values["storage_capacity_tb"]:
                    errors.append(CSVImportError(row=row_number, field="storage_capacity_tb", message="Storage capacity must be positive and >= storage used")); bad = True
                elif values["network_capacity_gbps"] <= 0 or values["network_throughput_gbps"] > values["network_capacity_gbps"]:
                    errors.append(CSVImportError(row=row_number, field="network_capacity_gbps", message="Network capacity must be positive and >= network throughput")); bad = True
                elif values["cooling_power_mw"] > values["power_usage_mw"]:
                    errors.append(CSVImportError(row=row_number, field="cooling_power_mw", message="Cooling power cannot exceed total power usage")); bad = True
                if not bad:
                    if cluster is not None:
                        cluster.installed_gpu_count = int(round(installed))
                        cluster.meta = {**(cluster.meta or {}), "data_origin": "real", "source_filename": filename}
                    parsed.append((row_number, dc, cluster, ts, values))

        if not parsed:
            db.rollback()
            return CSVImportResult(filename=filename, rows_received=rows_received, rows_imported=0, metrics_inserted=0, duplicates_skipped=0, errors=errors[:100])

        timestamps = [x[3] for x in parsed]
        dc_ids = {x[1].id for x in parsed}
        existing_rows = db.scalars(select(InfrastructureMetric).where(
            InfrastructureMetric.source_id == source.id,
            InfrastructureMetric.data_center_id.in_(dc_ids),
            InfrastructureMetric.timestamp >= min(timestamps),
            InfrastructureMetric.timestamp <= max(timestamps),
            InfrastructureMetric.metric_name.in_(list(METRICS)),
        )).all()
        def norm_ts(ts):
            return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
        existing = {(m.data_center_id, m.cluster_id, norm_ts(m.timestamp), m.metric_name) for m in existing_rows}
        inserted = 0; duplicates = 0; imported_rows = 0
        for _, dc, cluster, ts, values in parsed:
            row_inserted = False
            for name, value in values.items():
                metric_type, unit = METRICS[name]
                cluster_id = cluster.id if cluster is not None and metric_type == "gpu" else None
                key = (dc.id, cluster_id, norm_ts(ts), name)
                if key in existing:
                    duplicates += 1; continue
                db.add(InfrastructureMetric(data_center_id=dc.id, cluster_id=cluster_id, source_id=source.id, timestamp=ts,
                                            metric_type=metric_type, metric_name=name, value=value, unit=unit,
                                            tags={"dataset": "csv", "data_origin": "real", "filename": filename}))
                existing.add(key); inserted += 1; row_inserted = True
            if row_inserted:
                imported_rows += 1
        source.status = "connected"; source.last_sync_at = datetime.now(timezone.utc); source.last_sync_status = "success"
        db.commit()
        imported_dcs = sorted({dc.id: dc.name for _, dc, _, _, _ in parsed}.items())
        return CSVImportResult(
            filename=filename,
            rows_received=rows_received,
            rows_imported=imported_rows,
            metrics_inserted=inserted,
            duplicates_skipped=duplicates,
            source_id=source.id,
            data_center_ids=[dc_id for dc_id, _ in imported_dcs],
            data_center_names=[name for _, name in imported_dcs],
            errors=errors[:100],
        )
