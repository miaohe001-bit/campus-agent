import hashlib
import json
import re
import urllib.request
from datetime import date, datetime, timedelta

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.enums import CrawlRunStatus, LeadStatus, MonitoringSourceStatus, MonitoringSourceType, RecruitmentEventType
from app.db.models import Campaign, CrawlRun, Lead, MonitoringSource, RecruitmentEvent
from app.planner.openai_planner import LLMPlanner
from app.schemas.monitoring import (
    LeadCreate,
    LeadRead,
    MonitoringSourceCreate,
    MonitoringSourceRead,
    XiaohongshuNoteCandidate,
)


COMPANY_ALIASES = {
    "腾讯": ["腾讯", "Tencent"],
    "字节跳动": ["字节", "字节跳动", "抖音", "飞书"],
    "阿里巴巴": ["阿里", "阿里巴巴", "淘天", "蚂蚁"],
    "美团": ["美团"],
    "京东": ["京东"],
    "快手": ["快手"],
    "小红书": ["小红书"],
    "百度": ["百度"],
    "网易": ["网易"],
    "拼多多": ["拼多多", "PDD"],
    "米哈游": ["米哈游"],
    "华为": ["华为"],
    "小米": ["小米"],
    "理想汽车": ["理想", "理想汽车"],
    "蔚来": ["蔚来"],
}

# Keep the monitoring vocabulary broad enough for the radar while campaigns
# themselves still come from verified recruitment sources in the database.
COMPANY_ALIASES.update({
    "滴滴": ["滴滴", "DiDi"],
    "哔哩哔哩": ["哔哩哔哩", "B站", "bilibili"],
    "携程": ["携程", "Trip.com"],
    "蚂蚁集团": ["蚂蚁集团", "蚂蚁金服"],
    "小鹏汽车": ["小鹏", "小鹏汽车"],
    "比亚迪": ["比亚迪", "BYD"],
    "DeepSeek": ["DeepSeek", "深度求索"],
    "MiniMax": ["MiniMax", "稀宇科技"],
    "月之暗面": ["月之暗面", "Kimi"],
    "智谱 AI": ["智谱", "智谱 AI", "ChatGLM"],
    "vivo": ["vivo", "维沃"],
    "科大讯飞": ["科大讯飞", "讯飞", "iFLYTEK"],
})

WXPUBLIC_FETCH_URL = "https://wxpub.aibana.art/fetch"
ARTICLE_MARKDOWN_URL = "https://anything-md.doocs.org/"


DEFAULT_XIAOHONGSHU_SOURCES = [
    {
        "display_name": "沐影（秋招版）",
        "value": "https://www.xiaohongshu.com/user/profile/6762739f0000000019009e68",
        "config": {
            "profile_id": "6762739f0000000019009e68",
            "verification_status": "verified_public_profile",
            "verified_at": "2026-08-10",
            "focus": ["2027届", "产品", "秋招", "测评"],
            "recent_company_signals": ["vivo", "拼多多", "科大讯飞"],
        },
    },
]


def list_sources(
    db: Session,
    *,
    user_id: str,
    source_type: MonitoringSourceType | None = None,
    include_paused: bool = False,
) -> list[MonitoringSourceRead]:
    statement: Select[tuple[MonitoringSource]] = select(MonitoringSource).where(MonitoringSource.user_id == user_id)
    if source_type is not None:
        statement = statement.where(MonitoringSource.source_type == source_type)
    if not include_paused:
        statement = statement.where(MonitoringSource.status == MonitoringSourceStatus.active)
    statement = statement.order_by(MonitoringSource.created_at.desc())
    return [MonitoringSourceRead.model_validate(source) for source in db.scalars(statement).all()]


def upsert_source(db: Session, *, user_id: str, payload: MonitoringSourceCreate) -> MonitoringSourceRead:
    statement = select(MonitoringSource).where(
        MonitoringSource.user_id == user_id,
        MonitoringSource.source_type == payload.source_type,
        MonitoringSource.value == payload.value,
    )
    source = db.scalars(statement).first()
    if source is None:
        source = MonitoringSource(user_id=user_id, **payload.model_dump())
        db.add(source)
    else:
        source.display_name = payload.display_name
        source.status = payload.status
        source.check_interval_minutes = payload.check_interval_minutes
        source.config = payload.config
    db.commit()
    db.refresh(source)
    return MonitoringSourceRead.model_validate(source)


def seed_default_xiaohongshu_sources(db: Session, *, user_id: str) -> list[MonitoringSourceRead]:
    seeded: list[MonitoringSourceRead] = []
    for item in DEFAULT_XIAOHONGSHU_SOURCES:
        seeded.append(
            upsert_source(
                db,
                user_id=user_id,
                payload=MonitoringSourceCreate(
                    source_type=MonitoringSourceType.xiaohongshu_profile,
                    display_name=item["display_name"],
                    value=item["value"],
                    check_interval_minutes=360,
                    config=item["config"],
                ),
            )
        )
    return seeded


def extract_mentioned_companies(text: str) -> list[str]:
    normalized_text = text.lower()
    companies: list[str] = []
    for company, aliases in COMPANY_ALIASES.items():
        if any(alias.lower() in normalized_text for alias in aliases):
            companies.append(company)
    return companies


def ingest_xiaohongshu_notes(
    db: Session,
    *,
    user_id: str,
    source_id: str,
    notes: list[XiaohongshuNoteCandidate],
) -> dict:
    source = db.get(MonitoringSource, source_id)
    if (
        source is None
        or source.user_id != user_id
        or source.source_type not in {
            MonitoringSourceType.xiaohongshu_profile,
            MonitoringSourceType.xiaohongshu_keyword,
        }
    ):
        raise ValueError("monitoring source not found")

    run = CrawlRun(
        user_id=user_id,
        source_id=source_id,
        status=CrawlRunStatus.completed,
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
        discovered_count=0,
        imported_count=0,
        metadata_={
            "adapter": "xiaohongshu_note_ingest",
            "note": "Real Xiaohongshu notes supplied by the discovery adapter; official verification is still required.",
        },
    )
    db.add(run)
    db.flush()

    imported: list[LeadRead] = []
    rejected: list[dict] = []
    for note in notes:
        title = note.title.strip()
        snippet = note.snippet.strip() if note.snippet else None
        if not _is_real_xiaohongshu_url(note.url):
            rejected.append({"url": note.url, "reason": "not a Xiaohongshu note URL"})
            continue
        text = f"{title}\n{snippet or ''}"
        companies = extract_mentioned_companies(text)
        if not companies or not _has_recruitment_signal(text):
            rejected.append({"url": note.url, "reason": "no company or campus recruitment signal"})
            continue
        canonical_url = _canonical_xiaohongshu_url(note.url)
        is_profile_evidence = "/user/profile/" in canonical_url
        identity = f"{canonical_url}:{title}" if is_profile_evidence else canonical_url
        source_item_key = hashlib.sha256(f"xiaohongshu:{identity}".encode("utf-8")).hexdigest()
        before = db.scalars(
            select(Lead).where(Lead.user_id == user_id, Lead.source_item_key == source_item_key)
        ).first()
        lead = upsert_lead(
            db,
            user_id=user_id,
            payload=LeadCreate(
                source_id=source.id,
                crawl_run_id=run.id,
                source_item_key=source_item_key,
                title=title,
                url=canonical_url,
                author_name=note.author_name or source.display_name,
                published_at=note.published_at,
                snippet=snippet,
                mentioned_companies=companies,
                payload={
                    "source_type": source.source_type,
                    "raw_source_url": note.url,
                    "content_kind": "recruitment_discovery_lead",
                    "adapter": "xiaohongshu_note_ingest",
                    "verification_status": "pending_official_wechat",
                    "evidence_scope": "profile_feed" if is_profile_evidence else "note",
                    "note_url_available": not is_profile_evidence,
                },
            ),
        )
        if before is None:
            imported.append(lead)

    run.discovered_count = len(notes)
    run.imported_count = len(imported)
    source.last_checked_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return {
        "run_id": run.id,
        "source_id": source.id,
        "status": run.status,
        "discovered_count": run.discovered_count,
        "imported_count": run.imported_count,
        "leads": [lead.model_dump(mode="json") for lead in imported],
        "rejected": rejected,
    }


def _is_real_xiaohongshu_url(value: str) -> bool:
    return bool(
        re.match(
            r"^https://(?:www\.)?xiaohongshu\.com/(?:explore/[A-Za-z0-9]+|user/profile/[A-Za-z0-9]+)",
            value,
        )
    ) or bool(re.match(r"^https://xhslink\.cn/[A-Za-z0-9/_-]+", value))


def _canonical_xiaohongshu_url(value: str) -> str:
    return value.split("?", 1)[0].split("#", 1)[0]


def _has_recruitment_signal(text: str) -> bool:
    return any(keyword in text for keyword in ["校招", "秋招", "校园招聘", "提前批", "应届", "投递"])


def _company_from_source(source: MonitoringSource) -> str:
    company_name = source.config.get("company_name")
    if isinstance(company_name, str) and company_name:
        return company_name
    return source.display_name.replace("招聘公众号搜索", "").strip()


def _mock_wechat_articles_for_source(source: MonitoringSource) -> list[dict]:
    company = _company_from_source(source)
    source_hash = hashlib.sha1(source.value.encode("utf-8")).hexdigest()[:10]
    return [
        {
            "title": f"{company} 2027 校园招聘正式启动",
            "url": f"https://mp.weixin.qq.com/s/mock-{source_hash}",
            "author_name": f"{company}招聘",
            "snippet": f"{company}校招公众号发布 2027 届校园招聘信息，包含岗位投递、测评和面试安排，等待进一步抽取为招聘项目。",
            "mentioned_companies": [company],
        }
    ]


def crawl_wechat_sources_mock(db: Session, *, user_id: str) -> dict:
    sources = db.scalars(
        select(MonitoringSource).where(
            MonitoringSource.user_id == user_id,
            MonitoringSource.status == MonitoringSourceStatus.active,
            MonitoringSource.source_type == MonitoringSourceType.wechat_official_account,
        )
    ).all()

    runs: list[dict] = []
    for source in sources:
        run = CrawlRun(
            user_id=user_id,
            source_id=source.id,
            status=CrawlRunStatus.completed,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            discovered_count=0,
            imported_count=0,
            metadata_={
                "adapter": "mock_wechat_article_search",
                "note": "MVP mock adapter: replace with wechat-reader or another selected WeChat article tool.",
            },
        )
        db.add(run)
        db.flush()

        imported: list[LeadRead] = []
        articles = _mock_wechat_articles_for_source(source)
        for article in articles:
            source_item_key = hashlib.sha256(f"wechat:{article['url']}".encode("utf-8")).hexdigest()
            before = db.scalars(
                select(Lead).where(Lead.user_id == user_id, Lead.source_item_key == source_item_key)
            ).first()
            lead = upsert_lead(
                db,
                user_id=user_id,
                payload=LeadCreate(
                    source_id=source.id,
                    crawl_run_id=run.id,
                    source_item_key=source_item_key,
                    title=article["title"],
                    url=article["url"],
                    author_name=article["author_name"],
                    snippet=article["snippet"],
                    mentioned_companies=article["mentioned_companies"],
                    payload={
                        "source_type": source.source_type,
                        "raw_source_query": source.value,
                        "content_kind": "official_wechat_article_candidate",
                        "confidence": "mock",
                    },
                ),
            )
            if before is None:
                imported.append(lead)

        run.discovered_count = len(articles)
        run.imported_count = len(imported)
        source.last_checked_at = datetime.utcnow()
        db.commit()
        db.refresh(run)
        runs.append(
            {
                "run_id": run.id,
                "source_id": source.id,
                "status": run.status,
                "discovered_count": run.discovered_count,
                "imported_count": run.imported_count,
                "leads": [lead.model_dump(mode="json") for lead in imported],
            }
        )

    return {
        "source_count": len(sources),
        "discovered_count": sum(run["discovered_count"] for run in runs),
        "imported_count": sum(run["imported_count"] for run in runs),
        "runs": runs,
    }


def crawl_wechat_sources_wxpublic(
    db: Session,
    *,
    user_id: str,
    limit_per_source: int = 3,
    days: int = 7,
    companies: list[str] | None = None,
) -> dict:
    statement = select(MonitoringSource).where(
            MonitoringSource.user_id == user_id,
            MonitoringSource.status == MonitoringSourceStatus.active,
            MonitoringSource.source_type == MonitoringSourceType.wechat_official_account,
        )
    if companies:
        statement = statement.where(
            MonitoringSource.config["company_name"].as_string().in_(companies)
        )
    sources = db.scalars(statement).all()

    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    runs: list[dict] = []
    for source in sources:
        account_name = _wxpublic_account_name_from_source(source)
        run = CrawlRun(
            user_id=user_id,
            source_id=source.id,
            status=CrawlRunStatus.pending,
            started_at=datetime.utcnow(),
            finished_at=None,
            discovered_count=0,
            imported_count=0,
            metadata_={
                "adapter": "wxpublic_fetch",
                "account_name": account_name,
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "note": "Real official-account fetch through wxpublic-fetch compatible API.",
            },
        )
        db.add(run)
        db.flush()

        imported: list[LeadRead] = []
        try:
            if not settings.wxpublic_app_id or not settings.wxpublic_secure_key:
                raise RuntimeError("WXPUBLIC credentials are not configured.")

            candidates = _fetch_wxpublic_article_candidates(
                account_name,
                start_date=start_date,
                end_date=end_date,
                limit=limit_per_source,
            )
            for candidate in candidates:
                source_item_key = hashlib.sha256(f"wxpublic:{candidate['url']}".encode("utf-8")).hexdigest()
                before = db.scalars(
                    select(Lead).where(Lead.user_id == user_id, Lead.source_item_key == source_item_key)
                ).first()
                text = f"{candidate['title']}\n{candidate.get('snippet') or ''}\n{account_name}"
                published_at = _parse_published_date(candidate.get("published_date"))
                lead = upsert_lead(
                    db,
                    user_id=user_id,
                    payload=LeadCreate(
                        source_id=source.id,
                        crawl_run_id=run.id,
                        source_item_key=source_item_key,
                        title=candidate["title"],
                        url=candidate["url"],
                        author_name=candidate.get("author_name") or _company_from_source(source),
                        snippet=candidate.get("snippet"),
                        published_at=published_at,
                        mentioned_companies=extract_mentioned_companies(text) or [_company_from_source(source)],
                        payload={
                            "source_type": source.source_type,
                            "raw_source_query": source.value,
                            "official_account_name": account_name,
                            "published_date": candidate.get("published_date"),
                            "content_kind": "official_wechat_article_candidate",
                            "confidence": "wxpublic_account_article",
                            "adapter": "wxpublic_fetch",
                            "markdown_excerpt": candidate.get("markdown_excerpt"),
                            "markdown": candidate.get("markdown"),
                        },
                    ),
                )
                if before is None:
                    imported.append(lead)

            run.status = CrawlRunStatus.completed
            run.discovered_count = len(candidates)
            run.imported_count = len(imported)
        except Exception as exc:  # noqa: BLE001 - keep crawl run failure visible to the product.
            run.status = CrawlRunStatus.failed
            run.error_message = str(exc)[:1000]

        run.finished_at = datetime.utcnow()
        source.last_checked_at = run.finished_at
        db.commit()
        db.refresh(run)
        runs.append(
            {
                "run_id": run.id,
                "source_id": source.id,
                "status": run.status,
                "discovered_count": run.discovered_count,
                "imported_count": run.imported_count,
                "error_message": run.error_message,
                "leads": [lead.model_dump(mode="json") for lead in imported],
            }
        )

    return {
        "source_count": len(sources),
        "discovered_count": sum(run["discovered_count"] for run in runs),
        "imported_count": sum(run["imported_count"] for run in runs),
        "runs": runs,
    }


def _wxpublic_account_name_from_source(source: MonitoringSource) -> str:
    configured_name = source.config.get("official_account_name")
    if isinstance(configured_name, str) and configured_name.strip():
        return configured_name.strip()
    company = _company_from_source(source)
    if company:
        return f"{company}招聘"
    return source.value


def _fetch_wxpublic_article_candidates(
    account_name: str,
    *,
    start_date: date,
    end_date: date,
    limit: int,
) -> list[dict]:
    payload = json.dumps(
        {
            "app_id": settings.wxpublic_app_id,
            "secure_key": settings.wxpublic_secure_key,
            "name": account_name,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        WXPUBLIC_FETCH_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="ignore")
    data = json.loads(body)
    if data.get("error"):
        raise RuntimeError(str(data["error"]))

    urls = data.get("urls") or []
    published_dates = data.get("date") or []
    candidates: list[dict] = []
    for index, url in enumerate(urls[:limit]):
        if not isinstance(url, str) or not url:
            continue
        metadata = _fetch_article_metadata(url)
        published_date = published_dates[index] if index < len(published_dates) else None
        fallback_title = f"{account_name} {published_date or ''} 公众号文章".strip()
        candidates.append(
            {
                "title": metadata.get("title") or fallback_title,
                "url": url,
                "author_name": account_name,
                "snippet": metadata.get("snippet") or fallback_title,
                "published_date": published_date,
                "markdown_excerpt": metadata.get("markdown_excerpt"),
                "markdown": metadata.get("markdown"),
            }
        )
    return candidates


def _fetch_article_metadata(url: str) -> dict:
    payload = json.dumps({"url": url}).encode("utf-8")
    request = urllib.request.Request(
        ARTICLE_MARKDOWN_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "curl/8.0.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="ignore")
        data = json.loads(body)
    except Exception:  # noqa: BLE001 - article conversion is best-effort; URL lead is still useful.
        return {}

    markdown = data.get("markdown") or ""
    title = data.get("name") or _first_markdown_heading(markdown)
    clean_text = _clean_markdown_text(markdown)
    return {
        "title": title,
        "snippet": clean_text[:300] if clean_text else None,
        "markdown_excerpt": clean_text[:2000] if clean_text else None,
        "markdown": markdown[:20000] if markdown else None,
    }


def _first_markdown_heading(markdown: str) -> str | None:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or None
    return None


def _clean_markdown_text(markdown: str) -> str:
    text = re.sub(r"!\[[^\]]*]\([^)]*\)", "", markdown)
    text = re.sub(r"\[[^\]]*]\([^)]*\)", "", text)
    text = re.sub(r"[#>*_`-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_published_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def create_followup_sources_from_new_leads(db: Session, *, user_id: str) -> dict:
    leads = db.scalars(
        select(Lead)
        .where(
            Lead.user_id == user_id,
            Lead.status == LeadStatus.new,
        )
        .order_by(Lead.created_at.asc())
    ).all()

    created_sources: dict[tuple[MonitoringSourceType, str], MonitoringSourceRead] = {}
    processed_lead_count = 0
    for lead in leads:
        if (
            lead.payload.get("adapter") != "xiaohongshu_note_ingest"
            or lead.payload.get("content_kind") != "recruitment_discovery_lead"
        ):
            continue
        processed_lead_count += 1
        for company in lead.mentioned_companies:
            wechat_value = f"{company} 招聘 校招 公众号"
            created_sources[(MonitoringSourceType.wechat_official_account, wechat_value)] = upsert_source(
                db,
                user_id=user_id,
                payload=MonitoringSourceCreate(
                    source_type=MonitoringSourceType.wechat_official_account,
                    display_name=f"{company}招聘公众号搜索",
                    value=wechat_value,
                    check_interval_minutes=360,
                    config={
                        "company_name": company,
                        "official_account_name": f"{company}招聘",
                        "trigger_lead_id": lead.id,
                        "purpose": "find official WeChat recruitment information",
                    },
                ),
            )
        lead.status = LeadStatus.processed

    db.commit()
    unique_sources = list(created_sources.values())
    return {
        "processed_lead_count": processed_lead_count,
        "created_source_count": len(unique_sources),
        "sources": [source.model_dump(mode="json") for source in unique_sources],
    }


def list_leads(db: Session, *, user_id: str, limit: int = 50) -> list[LeadRead]:
    statement = (
        select(Lead)
        .where(Lead.user_id == user_id)
        .order_by(Lead.published_at.desc().nullslast(), Lead.created_at.desc())
        .limit(limit)
    )
    return [LeadRead.model_validate(lead) for lead in db.scalars(statement).all()]


def import_official_wechat_candidates(db: Session, *, user_id: str) -> dict:
    leads = db.scalars(
        select(Lead)
        .where(
            Lead.user_id == user_id,
            Lead.status == LeadStatus.new,
        )
        .order_by(Lead.created_at.asc())
    ).all()

    imported_campaigns: list[dict] = []
    imported_events: list[dict] = []
    skipped_leads: list[dict] = []
    for lead in leads:
        if lead.payload.get("content_kind") != "official_wechat_article_candidate":
            continue
        if not _is_real_wxpublic_recruitment_lead(lead):
            skipped_leads.append({"lead_id": lead.id, "reason": "not an explicit campus recruitment campaign"})
            lead.status = LeadStatus.ignored
            continue

        companies = lead.mentioned_companies or extract_mentioned_companies(f"{lead.title}\n{lead.snippet or ''}")
        if not companies:
            skipped_leads.append({"lead_id": lead.id, "reason": "no company mentioned"})
            lead.status = LeadStatus.ignored
            continue

        expected_company = _expected_company_from_lead_source(db, lead)
        if expected_company and expected_company not in companies:
            skipped_leads.append(
                {
                    "lead_id": lead.id,
                    "reason": f"candidate does not match source company: {expected_company}",
                }
            )
            continue

        company = expected_company or companies[0]
        llm_decision, llm_trace = _classify_wxpublic_candidate_with_planner(lead=lead, company=company)
        if llm_decision is not None:
            lead.payload = {
                **lead.payload,
                "planner_recruitment_decision": llm_decision,
                "planner_recruitment_trace": llm_trace,
            }
        if llm_decision is not None and not llm_decision.get("is_official_recruitment"):
            skipped_leads.append({"lead_id": lead.id, "reason": "planner rejected official recruitment article"})
            lead.status = LeadStatus.ignored
            continue
        if llm_decision is None and not _should_auto_import_wechat_candidate(lead, company):
            skipped_leads.append({"lead_id": lead.id, "reason": "not confident official recruitment article"})
            continue

        campaign = _upsert_campaign_from_wechat_lead(db, lead=lead, company=company, extraction=llm_decision)
        event = _upsert_recruitment_event_from_wechat_lead(
            db,
            user_id=user_id,
            lead=lead,
            company=company,
            campaign_id=campaign.id,
            extraction=llm_decision,
        )
        lead.status = LeadStatus.processed
        imported_campaigns.append(
            {
                "id": campaign.id,
                "company_name": campaign.company_name,
                "name": campaign.name,
                "source_url": campaign.source_url,
            }
        )
        imported_events.append(
            {
                "id": event.id,
                "campaign_id": event.campaign_id,
                "event_type": event.event_type,
                "idempotency_key": event.idempotency_key,
            }
        )

    db.commit()
    return {
        "processed_lead_count": len(imported_campaigns) + len(skipped_leads),
        "imported_campaign_count": len(imported_campaigns),
        "imported_event_count": len(imported_events),
        "campaigns": imported_campaigns,
        "events": imported_events,
        "skipped_leads": skipped_leads,
    }


def _classify_wxpublic_candidate_with_planner(*, lead: Lead, company: str) -> tuple[dict | None, dict | None]:
    if lead.payload.get("adapter") != "wxpublic_fetch":
        return None, None
    planner = LLMPlanner()
    decision, trace = planner.classify_recruitment_article(
        {
            "expected_company": company,
            "title": lead.title,
            "author_name": lead.author_name,
            "snippet": lead.snippet,
            "url": lead.url,
            "published_at": lead.published_at.isoformat() if lead.published_at else None,
            "markdown_excerpt": lead.payload.get("markdown_excerpt"),
            "markdown": lead.payload.get("markdown"),
        }
    )
    decision_data = decision.model_dump(mode="json")
    if trace["planner"].startswith("fallback_"):
        return None, trace
    return decision_data, trace


def _upsert_campaign_from_wechat_lead(
    db: Session,
    *,
    lead: Lead,
    company: str,
    extraction: dict | None = None,
) -> Campaign:
    canonical_url = _canonical_wechat_url(lead.url)
    statement = select(Campaign).where(Campaign.source_url == canonical_url)
    campaign = db.scalars(statement).first()
    extracted_company = _extracted_str(extraction, "company_name") or company
    graduation_year = _normalize_graduation_year(
        _extract_graduation_year(lead) or _extracted_str(extraction, "graduation_year")
    )
    campaign_name = _normalized_campaign_title(lead, extracted_company)
    position_categories = _extracted_str_list(extraction, "position_categories")
    cities = _extracted_str_list(extraction, "cities")
    published_at = _parse_date(_extracted_str(extraction, "published_at")) or (
        lead.published_at.date() if lead.published_at else None
    )
    deadline_at = _parse_datetime(_extracted_str(extraction, "deadline_at"))
    if campaign is None:
        campaign = Campaign(
            company_name=extracted_company,
            name=campaign_name,
            status="open",
            target_graduation_year=graduation_year,
            position_categories=position_categories,
            cities=cities,
            industries=None,
            published_at=published_at,
            deadline_at=deadline_at,
            source_name=lead.author_name or "微信公众号",
            source_url=canonical_url,
        )
        db.add(campaign)
        db.flush()
    else:
        campaign.company_name = extracted_company
        campaign.name = campaign_name
        campaign.status = "open"
        campaign.target_graduation_year = campaign.target_graduation_year or graduation_year
        campaign.position_categories = campaign.position_categories or position_categories
        campaign.cities = campaign.cities or cities
        campaign.published_at = campaign.published_at or published_at
        campaign.deadline_at = campaign.deadline_at or deadline_at
        campaign.source_name = campaign.source_name or lead.author_name or "微信公众号"
    return campaign


def _expected_company_from_lead_source(db: Session, lead: Lead) -> str | None:
    source = db.get(MonitoringSource, lead.source_id)
    if source is None:
        return None
    company_name = source.config.get("company_name")
    if isinstance(company_name, str) and company_name:
        return company_name
    return None


def _find_existing_campaign_by_company_year(
    db: Session,
    *,
    company: str,
    graduation_year: str | None,
) -> Campaign | None:
    statement = select(Campaign).where(Campaign.company_name == company)
    if graduation_year is not None:
        statement = statement.where(Campaign.target_graduation_year == graduation_year)
    return db.scalars(statement.order_by(Campaign.created_at.desc())).first()


def _upsert_recruitment_event_from_wechat_lead(
    db: Session,
    *,
    user_id: str,
    lead: Lead,
    company: str,
    campaign_id: str,
    extraction: dict | None = None,
) -> RecruitmentEvent:
    idempotency_key = f"wechat-candidate:{lead.source_item_key}:campaign-opened"
    event = db.scalars(select(RecruitmentEvent).where(RecruitmentEvent.idempotency_key == idempotency_key)).first()
    if event is None:
        event = RecruitmentEvent(
            user_id=user_id,
            application_id=None,
            campaign_id=campaign_id,
            event_type=RecruitmentEventType.deadline_updated,
            occurred_at=lead.published_at or datetime.utcnow(),
            source="wechat_candidate",
            payload={
                "title": lead.title,
                "company_name": company,
                "source_url": lead.url,
                "snippet": lead.snippet,
                "extraction": extraction,
                "application_url": _extracted_str(extraction, "application_url"),
                "note": "MVP import from official WeChat article candidate with Planner extraction.",
            },
            idempotency_key=idempotency_key,
        )
        db.add(event)
        db.flush()
    return event


def _campaign_name_from_lead(lead: Lead, company: str) -> str:
    graduation_year = _extract_graduation_year(lead)
    if graduation_year:
        return f"{company} {graduation_year} 校园招聘"
    return lead.title


def _extract_graduation_year(lead: Lead) -> str | None:
    text = f"{lead.title}\n{lead.snippet or ''}"
    for year in ["2027", "2026", "2025"]:
        if year in text:
            return year
    return None


def _normalize_graduation_year(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"20(?:2[5-9]|3\d)", value)
    if match:
        return match.group(0)
    short_match = re.search(r"(?:^|\D)(2[5-9])(?:\D|$)", value)
    if short_match:
        return f"20{short_match.group(1)}"
    return value


def _normalized_campaign_title(lead: Lead, company: str) -> str:
    title = re.sub(r"\.html?$", "", lead.title, flags=re.IGNORECASE)
    title = re.sub(r"[_]+", " ", title)
    return re.sub(r"\s+", " ", title).strip() or f"{company}校园招聘"


def _canonical_wechat_url(url: str | None) -> str:
    if not url:
        return ""
    values: list[str] = []
    for key in ["__biz", "mid", "idx", "sn"]:
        match = re.search(rf"(?:[?&]){key}=([^&#]+)", url)
        if match:
            values.append(f"{key}={match.group(1)}")
    return f"https://mp.weixin.qq.com/s?{'&'.join(values)}" if len(values) == 4 else url


def _is_real_wxpublic_recruitment_lead(lead: Lead) -> bool:
    if lead.payload.get("adapter") != "wxpublic_fetch":
        return False
    if not lead.url or "mp.weixin.qq.com/s" not in lead.url or "/mock-" in lead.url:
        return False
    title = re.sub(r"[_.]", "", lead.title)
    has_year = bool(re.search(r"(?:2027|27)\s*届|2027", title, flags=re.IGNORECASE))
    has_campaign = any(keyword in title for keyword in [
        "校园招聘", "校招", "秋招", "早鸟通道", "青云计划", "北斗计划", "顶尖技术人才计划",
    ])
    excluded = any(
        keyword in title
        for keyword in ["校园大使", "社招", "大赛", "论文", "FAQ", "Q&A", "QampA", "问答", "攻略"]
    )
    return has_year and has_campaign and not excluded


def _extracted_str(extraction: dict | None, key: str) -> str | None:
    if not extraction:
        return None
    value = extraction.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _extracted_str_list(extraction: dict | None, key: str) -> list[str] | None:
    if not extraction:
        return None
    value = extraction.get(key)
    if not isinstance(value, list):
        return None
    items = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return items or None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if len(normalized) == 10:
        normalized = f"{normalized}T23:59:59"
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None


def _should_auto_import_wechat_candidate(lead: Lead, company: str) -> bool:
    text = f"{lead.title}\n{lead.snippet or ''}\n{lead.author_name or ''}"
    if company not in text:
        return False
    if not any(keyword in text for keyword in ["校园招聘", "校招", "招聘"]):
        return False
    noisy_keywords = ["内推码", "汇总", "整理", "大厂", "港漂", "信息差", "求职日记", "名企"]
    if any(keyword in text for keyword in noisy_keywords):
        return False
    return True


def upsert_lead(db: Session, *, user_id: str, payload: LeadCreate) -> LeadRead:
    statement = select(Lead).where(Lead.user_id == user_id, Lead.source_item_key == payload.source_item_key)
    lead = db.scalars(statement).first()
    if lead is None:
        lead = Lead(user_id=user_id, **payload.model_dump())
        db.add(lead)
    else:
        for field, value in payload.model_dump().items():
            setattr(lead, field, value)
    db.commit()
    db.refresh(lead)
    return LeadRead.model_validate(lead)
