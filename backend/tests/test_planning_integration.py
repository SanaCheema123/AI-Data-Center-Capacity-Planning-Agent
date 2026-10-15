from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.models.domain import DataCenter, ForecastModel, InfrastructureMetric, ProcurementItem, Scenario
from app.models.system_setting import SystemSetting
from app.schemas.forecasting import ForecastRunRequest
from app.services.forecasting import ForecastingService
from app.services.planning import AlertService, ProcurementService, RecommendationService, ScenarioService


def make_db():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine); Session=sessionmaker(bind=engine,autoflush=False,autocommit=False); db=Session()
    dc=DataCenter(name='Plan Test',code='PLAN-1',region='test',country='PK',timezone='UTC',meta={});db.add(dc);db.flush()
    db.add(ForecastModel(name='XGBoost',model_type='xgboost',version='3',config={},is_enabled=True))
    db.add(SystemSetting(key='capacity_thresholds',value={'gpu':70,'power':70,'storage':70,'network':70}))
    for name,kind,m in [('Conservative','conservative',.9),('Base Case','base',1.0),('Aggressive','aggressive',1.2)]: db.add(Scenario(name=name,description=name,scenario_type=kind,planning_horizon_months=36,assumptions={'growth_multiplier':m}))
    for category,cap,cost in [('gpu',8,1000),('power',1,2000),('storage',100,3000),('network',100,4000)]: db.add(ProcurementItem(name=category,category=category,unit_capacity=cap,unit=category,unit_cost=cost,lead_time_days=30))
    start=datetime(2024,1,1,tzinfo=timezone.utc)
    for i in range(30):
        ts=start+timedelta(days=30*i)
        rows=[('gpu','gpu_utilization',60+i*.8,'%'),('gpu','installed_gpus',256,'gpus'),('power','power_usage_mw',25+i*.8,'MW'),('power','power_capacity_mw',50,'MW'),('storage','storage_used_tb',3500+i*160,'TB'),('storage','storage_capacity_tb',7000,'TB'),('network','network_throughput_gbps',300+i*14,'Gbps'),('network','network_capacity_gbps',600,'Gbps')]
        for t,n,v,u in rows: db.add(InfrastructureMetric(data_center_id=dc.id,timestamp=ts,metric_type=t,metric_name=n,value=v,unit=u,tags={}))
    db.commit()
    for r in ['gpu','power','storage','network']: ForecastingService.run(db,ForecastRunRequest(resource_type=r,model='xgboost',data_center_id=dc.id,horizon=6,frequency='monthly',confidence=.9))
    return db,dc.id


def test_scenario_procurement_alert_and_recommendation_services_are_forecast_grounded():
    db,dc_id=make_db()
    try:
        scenarios=ScenarioService.compare(db,dc_id,persist=True)
        assert len(scenarios)==3
        assert scenarios[2].gpu_demand>scenarios[0].gpu_demand
        procurement=ProcurementService.generate(db,dc_id)
        assert all(x.forecast_run_id is not None for x in procurement)
        alerts=AlertService.evaluate(db,dc_id)
        assert all(x.data_center_id==dc_id for x in alerts)
        recs=RecommendationService.list(db,dc_id)
        assert len(recs)==4
        assert all('forecast_peak' in x.supporting_metrics for x in recs)
    finally:
        db.close()
