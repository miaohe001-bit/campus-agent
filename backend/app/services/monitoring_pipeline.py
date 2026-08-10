from datetime import date

from sqlalchemy.orm import Session

from app.runtime import loop as agent_loop
from app.services import monitoring
from app.services.monitoring import (
    create_followup_sources_from_new_leads,
    import_official_wechat_candidates,
    seed_default_xiaohongshu_sources,
)


def run_monitoring_pipeline(db: Session, *, user_id: str, plan_date: date) -> dict:
    seed_result = seed_default_xiaohongshu_sources(db, user_id=user_id)
    followup_result = create_followup_sources_from_new_leads(db, user_id=user_id)
    wechat_result = monitoring.crawl_wechat_sources_wxpublic(db, user_id=user_id)
    import_result = import_official_wechat_candidates(db, user_id=user_id)

    agent_result = None
    if import_result["imported_event_count"] > 0:
        agent_run = agent_loop.run_today_agent(db, user_id=user_id, plan_date=plan_date)
        agent_result = agent_run.model_dump(mode="json")

    return {
        "seeded_source_count": len(seed_result),
        "xiaohongshu": {
            "source_count": len(seed_result),
            "adapter": "xiaohongshu_note_ingest",
            "note": "Waiting for real notes; no mock leads are generated.",
        },
        "followup_sources": followup_result,
        "wechat": wechat_result,
        "import": import_result,
        "agent_run": agent_result,
    }
