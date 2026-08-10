from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.enums import MonitoringSourceType
from app.db.session import get_db
from app.schemas.monitoring import MonitoringSourceCreate, XiaohongshuNoteBatch
from app.schemas.responses import ApiResponse
from app.services.monitoring import (
    crawl_wechat_sources_wxpublic,
    create_followup_sources_from_new_leads,
    ingest_xiaohongshu_notes,
    import_official_wechat_candidates,
    list_leads,
    list_sources,
    seed_default_xiaohongshu_sources,
    upsert_source,
)
from app.services.monitoring_pipeline import run_monitoring_pipeline

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/sources", response_model=ApiResponse)
def read_sources(
    user_id: str = "local-user",
    source_type: MonitoringSourceType | None = None,
    include_paused: bool = False,
    db: Session = Depends(get_db),
) -> ApiResponse:
    sources = list_sources(
        db,
        user_id=user_id,
        source_type=source_type,
        include_paused=include_paused,
    )
    return ApiResponse(data={"items": [source.model_dump(mode="json") for source in sources]})


@router.post("/sources", response_model=ApiResponse)
def add_source(
    payload: MonitoringSourceCreate,
    user_id: str = "local-user",
    db: Session = Depends(get_db),
) -> ApiResponse:
    source = upsert_source(db, user_id=user_id, payload=payload)
    return ApiResponse(data=source.model_dump(mode="json"))


@router.post("/sources/xiaohongshu/defaults", response_model=ApiResponse)
def add_default_xiaohongshu_sources(user_id: str = "local-user", db: Session = Depends(get_db)) -> ApiResponse:
    sources = seed_default_xiaohongshu_sources(db, user_id=user_id)
    return ApiResponse(data={"items": [source.model_dump(mode="json") for source in sources]})


@router.post("/sources/{source_id}/xiaohongshu-notes", response_model=ApiResponse)
def add_xiaohongshu_notes(
    source_id: str,
    payload: XiaohongshuNoteBatch,
    user_id: str = "local-user",
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = ingest_xiaohongshu_notes(
        db,
        user_id=user_id,
        source_id=source_id,
        notes=payload.notes,
    )
    return ApiResponse(data=result)


@router.post("/crawl/wechat", response_model=ApiResponse)
def crawl_wechat_sources(
    user_id: str = "local-user",
    limit_per_source: int = Query(default=3, ge=1, le=10),
    days: int = Query(default=7, ge=1, le=60),
    company: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = crawl_wechat_sources_wxpublic(
        db,
        user_id=user_id,
        limit_per_source=limit_per_source,
        days=days,
        companies=company,
    )
    return ApiResponse(data=result)


@router.get("/leads", response_model=ApiResponse)
def read_leads(
    user_id: str = "local-user",
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse:
    leads = list_leads(db, user_id=user_id, limit=limit)
    return ApiResponse(data={"items": [lead.model_dump(mode="json") for lead in leads]})


@router.post("/leads/followup-sources", response_model=ApiResponse)
def create_followup_sources(
    user_id: str = "local-user",
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = create_followup_sources_from_new_leads(db, user_id=user_id)
    return ApiResponse(data=result)


@router.post("/leads/import-wechat-candidates", response_model=ApiResponse)
def import_wechat_candidate_leads(
    user_id: str = "local-user",
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = import_official_wechat_candidates(db, user_id=user_id)
    return ApiResponse(data=result)


@router.post("/pipeline/run", response_model=ApiResponse)
def run_pipeline(
    user_id: str = "local-user",
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = run_monitoring_pipeline(db, user_id=user_id, plan_date=date.today())
    return ApiResponse(data=result)
