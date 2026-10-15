export type ResourceType = 'gpu'|'power'|'storage'|'network'
export type ForecastModelType = 'prophet'|'xgboost'
export type ForecastFrequency = 'daily'|'weekly'|'monthly'

export interface TokenResponse { access_token:string; refresh_token:string; token_type:string; expires_in?:number; user?:User }
export interface CapacitySummary { current_usage:number; current_capacity:number; utilization_percent:number; headroom:number; peak_demand:number; peak_demand_at:string; shortage_date:string|null; required_expansion:number }
export interface AccuracyMetrics { mae:number; rmse:number; mape:number; r2:number }
export interface ForecastPoint { timestamp:string; predicted:number; lower:number|null; upper:number|null; capacity:number|null }
export interface ForecastResponse { run_id:number; resource_type:ResourceType; model:string; model_engine:string; unit:string; data_center_id:number|null; frequency:ForecastFrequency; confidence:number; capacity:CapacitySummary; accuracy:AccuracyMetrics; points:ForecastPoint[] }
export interface ForecastRunPayload { model:ForecastModelType; data_center_id?:number|null; horizon:number; frequency:ForecastFrequency; confidence:number }
export interface Alert { id:number; data_center_id:number; resource_type:string; severity:string; title:string; description:string; current_value:number|null; threshold_value:number|null; forecast_value:number|null; predicted_shortage_at:string|null; status:string; triggered_at:string }
export interface ProcurementItem { id:number; data_center_id:number|null; resource_type:string; current_capacity:number|null; required_capacity:number|null; quantity:number|null; required_by:string|null; priority:string; status:string; estimated_cost:number|null; reason:string|null }
export interface ReportItem { id:number; data_center_id:number|null; report_type:string; title:string; status:string; generated_at:string|null; created_at:string }
export interface ReportCatalogItem { report_type:string; title:string; description:string; supports_pdf:boolean; supports_csv:boolean }
export interface Scenario { id:number; name:string; description:string|null; scenario_type:string; planning_horizon_months:number; assumptions:Record<string,unknown>; created_at:string }
export interface ScenarioComparison { id:number; name:string; scenario_type:string; description:string|null; planning_horizon_months:number; risk_level:string; risk_score:number; gpu_demand:number; power_demand_mw:number; storage_demand_tb:number; network_demand_gbps:number; estimated_capex:number|null; assumptions:Record<string,unknown> }
export interface Recommendation { resource_type:string; recommendation:string; reason:string; supporting_metrics:Record<string,unknown>; expected_impact:string; risk:string; dependencies:string[]; time_horizon:string; confidence:number; assumptions:string[] }
export interface DataCenter { id:number; name:string; code:string; region:string; country:string; timezone:string; status:string }
export interface DataSource { id:number; name:string; source_type:string; status:string; last_sync_at:string|null; last_sync_status:string|null; metric_count:number; data_center_names:string[] }
export interface PipelineStatus { scope:string; forecasts_completed:string[]; scenarios_refreshed:boolean; procurement_refreshed:boolean; alerts_refreshed:boolean; warnings:string[] }
export interface DataSourceSyncResult { source_id:number; status:string; metrics_received:number; metrics_inserted:number; duplicates_skipped:number; clusters_registered:number; data_center_registered:string|null; started_at:string; finished_at:string; pipeline:PipelineStatus[]; errors:{row:number;field:string|null;message:string}[] }
export interface Setting { id:number; key:string; value:Record<string,unknown> }
export interface DashboardSummary { data_centers:number; clusters:number; active_alerts:number; completed_forecasts:number; pending_procurement:number; latest_metric_at:string|null }
export interface User { id:number; email:string; full_name:string; is_active:boolean; roles:{id:number;name:string;description?:string|null}[]; created_at:string }
export interface NotificationSettings { email_alerts:boolean; webhook_alerts:boolean; capacity_alerts:boolean; forecast_completion:boolean; weekly_summary:boolean; webhook_url:string|null }
export interface CSVImportError { row:number; field:string|null; message:string }
export interface CSVImportResult { filename:string; rows_received:number; rows_imported:number; metrics_inserted:number; duplicates_skipped:number; source_id:number|null; data_center_ids:number[]; data_center_names:string[]; pipeline:PipelineStatus[]; errors:CSVImportError[] }
