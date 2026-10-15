from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Table, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(TimestampMixin, Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255))
    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")


class User(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    roles: Mapped[list[Role]] = relationship(secondary=user_roles, back_populates="users", lazy="selectin")


class DataCenter(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "data_centers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    region: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    clusters: Mapped[list[Cluster]] = relationship(back_populates="data_center", cascade="all, delete-orphan")


class Cluster(TimestampMixin, Base):
    __tablename__ = "clusters"
    __table_args__ = (UniqueConstraint("data_center_id", "name", name="uq_cluster_dc_name"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_center_id: Mapped[int] = mapped_column(ForeignKey("data_centers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    cluster_type: Mapped[str] = mapped_column(String(64), default="gpu")
    gpu_model: Mapped[str | None] = mapped_column(String(120))
    installed_gpu_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="active")
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    data_center: Mapped[DataCenter] = relationship(back_populates="clusters")


class DataSource(TimestampMixin, Base):
    __tablename__ = "data_sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(32), default="disconnected", index=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_status: Mapped[str | None] = mapped_column(String(32))


class InfrastructureMetric(TimestampMixin, Base):
    __tablename__ = "infrastructure_metrics"
    __table_args__ = (
        Index("ix_metric_dc_ts", "data_center_id", "timestamp"),
        Index("ix_metric_cluster_ts", "cluster_id", "timestamp"),
        Index("ix_metric_type_ts", "metric_type", "timestamp"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_center_id: Mapped[int] = mapped_column(ForeignKey("data_centers.id", ondelete="CASCADE"), index=True)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("clusters.id", ondelete="SET NULL"), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id", ondelete="SET NULL"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metric_type: Mapped[str] = mapped_column(String(40), index=True)
    metric_name: Mapped[str] = mapped_column(String(100))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(40))
    tags: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ForecastModel(TimestampMixin, Base):
    __tablename__ = "forecast_models"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    model_type: Mapped[str] = mapped_column(String(40))
    version: Mapped[str] = mapped_column(String(40), default="1.0")
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ForecastRun(TimestampMixin, Base):
    __tablename__ = "forecast_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(40), index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("forecast_models.id"))
    data_center_id: Mapped[int | None] = mapped_column(ForeignKey("data_centers.id"), index=True)
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    horizon_months: Mapped[int] = mapped_column(Integer, default=12)
    frequency: Mapped[str] = mapped_column(String(20), default="monthly")
    confidence_interval: Mapped[float] = mapped_column(Float, default=0.9)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)


class ForecastResult(Base):
    __tablename__ = "forecast_results"
    __table_args__ = (Index("ix_forecast_result_run_ts", "forecast_run_id", "timestamp"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    forecast_run_id: Mapped[int] = mapped_column(ForeignKey("forecast_runs.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    predicted_value: Mapped[float] = mapped_column(Float)
    lower_bound: Mapped[float | None] = mapped_column(Float)
    upper_bound: Mapped[float | None] = mapped_column(Float)
    capacity_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(40))


class Scenario(TimestampMixin, Base):
    __tablename__ = "scenarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    scenario_type: Mapped[str] = mapped_column(String(32), default="custom")
    data_center_id: Mapped[int | None] = mapped_column(ForeignKey("data_centers.id"))
    planning_horizon_months: Mapped[int] = mapped_column(Integer, default=36)
    assumptions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class ScenarioResult(TimestampMixin, Base):
    __tablename__ = "scenario_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(40))
    gpu_demand: Mapped[float | None] = mapped_column(Float)
    power_demand_mw: Mapped[float | None] = mapped_column(Float)
    storage_demand_tb: Mapped[float | None] = mapped_column(Float)
    network_demand_gbps: Mapped[float | None] = mapped_column(Float)
    shortage_risk: Mapped[float | None] = mapped_column(Float)
    estimated_capex: Mapped[float | None] = mapped_column(Float)
    assumptions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ProcurementItem(TimestampMixin, Base):
    __tablename__ = "procurement_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(64), index=True)
    vendor: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    unit_capacity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(40))
    unit_cost: Mapped[float | None] = mapped_column(Float)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)


class ProcurementRecommendation(TimestampMixin, Base):
    __tablename__ = "procurement_recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_center_id: Mapped[int | None] = mapped_column(ForeignKey("data_centers.id"), index=True)
    forecast_run_id: Mapped[int | None] = mapped_column(ForeignKey("forecast_runs.id"))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("procurement_items.id"))
    resource_type: Mapped[str] = mapped_column(String(40), index=True)
    current_capacity: Mapped[float | None] = mapped_column(Float)
    required_capacity: Mapped[float | None] = mapped_column(Float)
    quantity: Mapped[float | None] = mapped_column(Float)
    required_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    priority: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text)


class Alert(TimestampMixin, Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_center_id: Mapped[int] = mapped_column(ForeignKey("data_centers.id"), index=True)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("clusters.id"))
    resource_type: Mapped[str] = mapped_column(String(40), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    current_value: Mapped[float | None] = mapped_column(Float)
    threshold_value: Mapped[float | None] = mapped_column(Float)
    forecast_value: Mapped[float | None] = mapped_column(Float)
    predicted_shortage_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    dedupe_key: Mapped[str] = mapped_column(String(255), index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AlertEvent(Base):
    __tablename__ = "alert_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Report(TimestampMixin, Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    data_center_id: Mapped[int | None] = mapped_column(ForeignKey("data_centers.id"))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    artifact_path: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class NotificationSetting(TimestampMixin, Base):
    __tablename__ = "notification_settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_notification_user"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    email_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    webhook_alerts: Mapped[bool] = mapped_column(Boolean, default=False)
    capacity_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    forecast_completion: Mapped[bool] = mapped_column(Boolean, default=True)
    weekly_summary: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_url: Mapped[str | None] = mapped_column(String(500))


class UserPreference(TimestampMixin, Base):
    __tablename__ = "user_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_preference_user"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    theme: Mapped[str] = mapped_column(String(20), default="system")
    accent: Mapped[str] = mapped_column(String(20), default="lavender")
    compact_mode: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str] = mapped_column(String(120), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(120))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
