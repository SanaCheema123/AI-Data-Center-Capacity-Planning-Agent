from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.models.domain import DataCenter, DataSource, InfrastructureMetric, User
from app.schemas.domain import DataSourceRead
from app.schemas.planning import CSVImportResult, DataSourceCreateRequest, DataSourceSyncResult, MetricPushRequest
from app.services.csv_import import CSVImportService
from app.services.ingestion import IngestionError, MetricIngestionService
from app.services.pipeline import RealDataPipelineService
from app.services.data_scope import real_data_center_ids
from app.integrations.base import MetricSource, NormalizedMetric
from app.integrations.metrics import CANONICAL_METRICS

router = APIRouter()
MAX_CSV_BYTES = 10 * 1024 * 1024

VALID_SOURCE_TYPES = {"prometheus", "opentelemetry", "internal_api"}


@router.get("", response_model=list[DataSourceRead])
def list_sources(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows: list[DataSourceRead] = []
    real_ids = real_data_center_ids(db)
    for source in db.scalars(select(DataSource).order_by(DataSource.name)):
        if real_ids:
            source_metrics = list(db.scalars(
                select(InfrastructureMetric).where(
                    InfrastructureMetric.source_id == source.id,
                    InfrastructureMetric.data_center_id.in_(real_ids),
                )
            ))
            source_metrics = [
                m for m in source_metrics
                if str((m.tags or {}).get("dataset", "")).lower() != "demo"
                and not bool((m.tags or {}).get("demo") is True)
            ]
            covered_ids = sorted({m.data_center_id for m in source_metrics})
            metric_count = len(source_metrics)
            names = list(db.scalars(
                select(DataCenter.name).where(DataCenter.id.in_(covered_ids)).order_by(DataCenter.name)
            )) if covered_ids else []
        else:
            metric_count, names = 0, []
        # Hide stale legacy/demo source rows that no longer back any real telemetry.
        config = source.configuration or {}
        is_legacy_demo = bool(config.get("demo") is True or source.name.startswith("Demo "))
        if (is_legacy_demo or source.source_type == "csv") and metric_count == 0:
            continue
        rows.append(DataSourceRead(
            id=source.id, name=source.name, source_type=source.source_type, status=source.status,
            last_sync_at=source.last_sync_at, last_sync_status=source.last_sync_status,
            metric_count=metric_count, data_center_names=names,
        ))
    return rows


@router.post("", response_model=DataSourceRead, status_code=201)
def create_source(
    payload: DataSourceCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Infrastructure Planner")),
):
    if payload.source_type not in VALID_SOURCE_TYPES:
        raise ValueError(f"Unsupported source type: {payload.source_type}")
    exists = db.scalar(select(DataSource).where(DataSource.name == payload.name))
    if exists:
        raise ConflictError("A data source with this name already exists")
    obj = DataSource(
        name=payload.name,
        source_type=payload.source_type,
        status="disconnected",
        configuration=payload.configuration or {},
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{source_id}/sync", response_model=DataSourceSyncResult)
def sync_source(
    source_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Admin", "Infrastructure Planner", "Analyst")),
):
    source = db.get(DataSource, source_id)
    if source is None:
        raise NotFoundError("Data source not found")
    try:
        result = MetricIngestionService.sync_data_source(db, source)
        if result.metrics_inserted > 0:
            dc_ids = list(db.scalars(
                select(InfrastructureMetric.data_center_id)
                .where(InfrastructureMetric.source_id == source.id)
                .distinct()
            ))
            result.pipeline = RealDataPipelineService.refresh_after_ingestion(db, dc_ids, user)
        return result
    except IngestionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/csv/import", response_model=CSVImportResult)
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Admin", "Infrastructure Planner", "Analyst")),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Only CSV files are supported")
    content = await file.read(MAX_CSV_BYTES + 1)
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="CSV file exceeds the 10 MB upload limit")
    result = CSVImportService.import_bytes(db, file.filename or "upload.csv", content)
    # The workflow continues automatically from real ingestion into forecasting,
    # scenario analysis, procurement and alerts. Validation/import errors remain
    # in the response; no synthetic fallback data is ever generated.
    if result.metrics_inserted > 0 and result.data_center_ids:
        result.pipeline = RealDataPipelineService.refresh_after_ingestion(db, result.data_center_ids, user)
    return result

@router.post("/{source_id}/metrics", response_model=DataSourceSyncResult)
def push_metrics(
    source_id: int,
    payload: MetricPushRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Admin", "Infrastructure Planner", "Analyst")),
):
    """Authenticated push ingestion for internal APIs / OpenTelemetry adapters.

    Payload metric names must use the canonical registry. A complete capacity
    snapshot/history is required; missing required metrics are rejected rather
    than fabricated.
    """
    source = db.get(DataSource, source_id)
    if source is None:
        raise NotFoundError("Data source not found")
    if source.source_type not in {"internal_api", "opentelemetry"}:
        raise HTTPException(status_code=409, detail="This data source is not push-based")

    class _PayloadSource(MetricSource):
        def test_connection(self) -> bool:
            return True
        def collect(self):
            for item in payload.metrics:
                definition = CANONICAL_METRICS.get(item.metric_name)
                if definition is None:
                    raise IngestionError(f"Unknown canonical metric: {item.metric_name}")
                yield NormalizedMetric(
                    timestamp=item.timestamp,
                    data_center=item.data_center,
                    metric_name=item.metric_name,
                    value=item.value,
                    unit=definition.unit,
                    cluster=item.cluster,
                    attributes={"push_api": True, **item.attributes},
                )

    try:
        result = MetricIngestionService.ingest(db, source, _PayloadSource())
        if result.metrics_inserted > 0:
            dc_ids = list(db.scalars(
                select(InfrastructureMetric.data_center_id)
                .where(InfrastructureMetric.source_id == source.id)
                .distinct()
            ))
            result.pipeline = RealDataPipelineService.refresh_after_ingestion(db, dc_ids, user)
        return result
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

