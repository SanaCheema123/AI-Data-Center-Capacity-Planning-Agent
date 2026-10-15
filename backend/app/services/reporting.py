from __future__ import annotations

import csv
import logging
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models.domain import Alert, ForecastRun, ProcurementRecommendation, Report, User
from app.services.forecasting import ForecastingService
from app.services.data_scope import real_data_center_ids

logger = logging.getLogger(__name__)


class PDFRenderingUnavailableError(RuntimeError):
    """Raised when the PDF engine's native libraries are missing or broken."""

CATALOG = [
    ("executive", "Executive Capacity Report", "Executive summary of capacity, demand, risks, and actions."),
    ("gpu", "GPU Forecast Report", "GPU demand, utilization, headroom, and forecast results."),
    ("power", "Power Capacity Report", "Power demand, capacity utilization, and shortage analysis."),
    ("storage_network", "Storage & Network Report", "Storage growth and network throughput planning."),
    ("scenario", "Scenario Comparison", "Comparison of saved expansion scenarios and assumptions."),
    ("procurement", "Procurement Plan", "Capacity-driven procurement requirements and costs."),
    ("shortage_risk", "Shortage Risk Report", "Capacity alerts, thresholds, and predicted shortages."),
]

_TEMPLATE = Environment(autoescape=select_autoescape(default_for_string=True)).from_string("""<!doctype html><html><head><meta charset='utf-8'><style>
@page { size: A4; margin: 18mm; } body{font-family:Arial,sans-serif;color:#10204f;font-size:11px}h1{font-size:24px;margin:0 0 4px}h2{font-size:15px;margin:20px 0 8px}.muted{color:#65769a}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.card{border:1px solid #dce9f8;border-radius:10px;padding:10px}table{width:100%;border-collapse:collapse}th,td{padding:6px;border-bottom:1px solid #e7edf7;text-align:left}th{background:#f4f9ff}.badge{display:inline-block;padding:2px 6px;border-radius:999px;background:#f4e8fa}.footer{margin-top:24px;color:#74819d;font-size:9px}
</style></head><body><h1>{{ title }}</h1><div class='muted'>Generated {{ generated_at }} · Scope: {{ scope }}</div>
{% if forecasts %}<h2>Capacity forecasts</h2><div class='grid'>{% for f in forecasts %}<div class='card'><b>{{ f.resource|upper }}</b><br>Current usage: {{ f.current_usage }} {{ f.unit }}<br>Capacity: {{ f.current_capacity }} {{ f.unit }}<br>Peak forecast: {{ f.peak }} {{ f.unit }}<br>Headroom: {{ f.headroom }} {{ f.unit }}<br>Shortage: {{ f.shortage or 'Not predicted in horizon' }}</div>{% endfor %}</div>{% endif %}
{% if alerts %}<h2>Capacity risks</h2><table><tr><th>Severity</th><th>Resource</th><th>Alert</th><th>Status</th></tr>{% for a in alerts %}<tr><td>{{ a.severity }}</td><td>{{ a.resource_type }}</td><td>{{ a.title }}</td><td>{{ a.status }}</td></tr>{% endfor %}</table>{% endif %}
{% if scenarios %}<h2>Scenario analysis</h2><table><tr><th>Scenario</th><th>Risk</th><th>GPU</th><th>Power MW</th><th>Storage TB</th><th>Network Gbps</th></tr>{% for s in scenarios %}<tr><td>{{ s.name }}</td><td>{{ s.risk_level }} ({{ s.risk_score }}%)</td><td>{{ s.gpu_demand }}</td><td>{{ s.power_demand_mw }}</td><td>{{ s.storage_demand_tb }}</td><td>{{ s.network_demand_gbps }}</td></tr>{% endfor %}</table>{% endif %}
{% if procurement %}<h2>Procurement requirements</h2><table><tr><th>Resource</th><th>Quantity</th><th>Priority</th><th>Required by</th><th>Est. cost</th></tr>{% for p in procurement %}<tr><td>{{ p.resource_type }}</td><td>{{ p.quantity }}</td><td>{{ p.priority }}</td><td>{{ p.required_by or '—' }}</td><td>{{ p.estimated_cost if p.estimated_cost is not none else 'Unavailable' }}</td></tr>{% endfor %}</table>{% endif %}
{% if recommendations %}<h2>Recommended actions</h2>{% for r in recommendations %}<div class='card'><b>{{ r.resource_type|upper }}:</b> {{ r.recommendation }}<br><span class='muted'>{{ r.reason }}</span></div><br>{% endfor %}{% endif %}
<div class='footer'>AI Data Center Capacity Planning Agent · Values are generated from persisted application data and forecast runs.</div></body></html>""")


def _render_pdf(html: str, target: Path) -> None:
    """Render a PDF without making native WeasyPrint libraries mandatory.

    ReportLab is the portable baseline (works on Windows/macOS/Linux). When
    WeasyPrint is available with its GTK/Pango runtime, it is used for richer
    HTML/CSS fidelity. If not, ReportLab still produces a valid readable PDF.
    """
    try:
        from weasyprint import HTML
        HTML(string=html).write_pdf(str(target))
        return
    except Exception:
        logger.info("weasyprint_unavailable_using_reportlab", exc_info=True)

    try:
        from html.parser import HTMLParser
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

        class _TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts: list[str] = []
            def handle_data(self, data: str) -> None:
                text = " ".join(data.split())
                if text:
                    self.parts.append(text)

        parser = _TextExtractor()
        parser.feed(html)
        text = "\n".join(parser.parts)
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
        story = []
        for line in text.splitlines():
            if line.strip():
                story.append(Paragraph(line.strip(), styles["BodyText"]))
                story.append(Spacer(1, 2*mm))
        doc.build(story)
        return
    except Exception as exc:
        logger.warning("pdf_rendering_failed", exc_info=True)
        raise PDFRenderingUnavailableError(f"PDF rendering failed: {exc}") from exc


def _serialize(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


class ProductionReportService:
    CATALOG = CATALOG

    @staticmethod
    def _bundle(db: Session, data_center_id: int | None) -> dict[str, Any]:
        forecasts = []
        for resource in ("gpu", "power", "storage", "network"):
            try:
                f = ForecastingService.latest(db, resource, data_center_id)
                forecasts.append({
                    "resource": resource, "unit": f.unit,
                    "current_usage": round(f.capacity.current_usage, 2),
                    "current_capacity": round(f.capacity.current_capacity, 2),
                    "peak": round(f.capacity.peak_demand, 2), "headroom": round(f.capacity.headroom, 2),
                    "shortage": f.capacity.shortage_date.isoformat() if f.capacity.shortage_date else None,
                    "model": f.model_engine, "accuracy": _serialize(f.accuracy),
                })
            except Exception:
                continue
        alert_stmt = select(Alert)
        proc_stmt = select(ProcurementRecommendation)
        if data_center_id is not None:
            alert_stmt = alert_stmt.where(Alert.data_center_id == data_center_id)
            proc_stmt = proc_stmt.where(ProcurementRecommendation.data_center_id == data_center_id)
        else:
            real_ids = real_data_center_ids(db)
            alert_stmt = alert_stmt.where(Alert.data_center_id.in_(real_ids)) if real_ids else alert_stmt.where(Alert.id == -1)
            proc_stmt = proc_stmt.where(ProcurementRecommendation.data_center_id.is_(None))
        alerts = list(db.scalars(alert_stmt.order_by(Alert.triggered_at.desc()).limit(100)))
        procurement = list(db.scalars(proc_stmt.order_by(ProcurementRecommendation.created_at.desc()).limit(100)))
        expected_ids = {data_center_id} if data_center_id is not None else set(real_data_center_ids(db))
        procurement = [
            p for p in procurement
            if p.forecast_run_id is not None
            and (lambda run: run is not None and (run.metrics or {}).get("data_origin") == "real"
                 and set((run.metrics or {}).get("data_center_ids") or []) == expected_ids)(db.get(ForecastRun, p.forecast_run_id))
        ]
        from app.services.planning import RecommendationService, ScenarioService
        scenarios = ScenarioService.compare(db, data_center_id)
        recommendations = RecommendationService.list(db, data_center_id)
        return {
            "forecasts": forecasts,
            "alerts": [{"severity": a.severity, "resource_type": a.resource_type, "title": a.title, "status": a.status,
                        "predicted_shortage_at": a.predicted_shortage_at.isoformat() if a.predicted_shortage_at else None} for a in alerts],
            "procurement": [{"resource_type": p.resource_type, "quantity": p.quantity, "priority": p.priority,
                             "required_by": p.required_by.isoformat() if p.required_by else None,
                             "estimated_cost": p.estimated_cost, "status": p.status} for p in procurement],
            "scenarios": [_serialize(s) for s in scenarios],
            "recommendations": [_serialize(r) for r in recommendations],
        }

    @staticmethod
    def generate(db: Session, report_type: str, data_center_id: int | None, user: User) -> Report:
        item = next((x for x in CATALOG if x[0] == report_type), None)
        if item is None:
            raise NotFoundError("Unknown report type")
        real_ids = real_data_center_ids(db)
        expected_ids = [data_center_id] if data_center_id is not None else real_ids
        if data_center_id is not None and data_center_id not in real_ids:
            raise NotFoundError("Data center not found or has no real telemetry")
        if not expected_ids:
            raise NotFoundError("No real infrastructure data is available for this report")
        report = Report(
            report_type=report_type,
            title=item[1],
            status="generating",
            owner_id=user.id,
            data_center_id=data_center_id,
            metadata_json={
                "source": "database",
                "data_origin": "real",
                "data_center_ids": expected_ids,
                "description": item[2],
            },
        )
        db.add(report); db.flush()
        out_dir = Path(settings.report_output_dir).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            bundle = ProductionReportService._bundle(db, data_center_id)
            generated_at = datetime.now(timezone.utc)
            base = f"report-{report.id}-{report_type}"
            pdf_path = out_dir / f"{base}.pdf"
            csv_path = out_dir / f"{base}.csv"
            html = _TEMPLATE.render(title=item[1], generated_at=generated_at.isoformat(), scope=data_center_id or "All data centers", **bundle)
            try:
                _render_pdf(html, pdf_path)
                pdf_available = True
            except PDFRenderingUnavailableError as exc:
                # The report record and CSV artifact stay usable; the failure is
                # reported honestly instead of marking the report completed.
                logger.warning("report_pdf_unavailable report_id=%s: %s", report.id, exc)
                pdf_available = False
            ProductionReportService._write_csv(csv_path, bundle)
            report.status = "completed"
            report.generated_at = generated_at
            report.artifact_path = str(pdf_path) if pdf_available else None
            report.metadata_json = {**report.metadata_json, "csv_path": str(csv_path), "pdf_available": pdf_available, "bundle_counts": {k: len(v) for k, v in bundle.items()}}
            if not pdf_available:
                report.metadata_json["pdf_error"] = "PDF rendering is unavailable on this host (missing native libraries); CSV report generated."
            db.commit(); db.refresh(report)
            return report
        except Exception as exc:
            report.status = "failed"
            report.metadata_json = {**report.metadata_json, "error": str(exc)}
            db.commit()
            raise

    @staticmethod
    def _safe_csv_cell(value: Any) -> Any:
        # Prevent spreadsheet formula injection when exports are opened in Excel/Sheets.
        if isinstance(value, str) and value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + value
        return value

    @staticmethod
    def _write_csv(path: Path, bundle: dict[str, Any]) -> None:
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            row = lambda values: writer.writerow([ProductionReportService._safe_csv_cell(v) for v in values])
            row(["section", "resource_or_name", "metric", "value"])
            for f in bundle["forecasts"]:
                for key in ("current_usage", "current_capacity", "peak", "headroom", "shortage", "model"):
                    row(["forecast", f["resource"], key, f.get(key)])
            for a in bundle["alerts"]:
                row(["alert", a["resource_type"], a["title"], a["status"]])
            for scenario in bundle["scenarios"]:
                row(["scenario", scenario["name"], "risk_score", scenario["risk_score"]])
            for procurement in bundle["procurement"]:
                row(["procurement", procurement["resource_type"], "quantity", procurement["quantity"]])

    @staticmethod
    def artifact(report: Report, kind: str) -> Path:
        if report.status != "completed":
            raise NotFoundError("Report artifact is not available")
        raw = report.artifact_path if kind == "pdf" else (report.metadata_json or {}).get("csv_path")
        if not raw:
            raise NotFoundError(f"{kind.upper()} artifact is not available")
        path = Path(raw).resolve()
        root = Path(settings.report_output_dir).expanduser().resolve()
        if root not in path.parents or not path.is_file():
            raise NotFoundError("Report artifact is unavailable")
        return path
