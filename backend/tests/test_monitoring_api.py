from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import create_app
from app.db.models import Lead
from app.services import monitoring
from app.services.monitoring import _should_auto_import_wechat_candidate


def test_seed_default_xiaohongshu_sources() -> None:
    client = TestClient(create_app())

    response = client.post("/monitoring/sources/xiaohongshu/defaults?user_id=test-user")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["source_type"] == "xiaohongshu_profile"
    assert body["data"]["items"][0]["display_name"] == "沐影（秋招版）"
    assert body["data"]["items"][0]["config"]["verification_status"] == "verified_public_profile"


def _seed_and_get_xiaohongshu_source(client: TestClient, user_id: str) -> str:
    client.post(f"/monitoring/sources/xiaohongshu/defaults?user_id={user_id}")
    sources = client.get(
        f"/monitoring/sources?user_id={user_id}&source_type=xiaohongshu_profile"
    ).json()["data"]["items"]
    return sources[0]["id"]


def _real_note_payload() -> dict:
    return {
        "notes": [
            {
                "title": "腾讯、字节跳动 2027 届秋招启动",
                "url": "https://www.xiaohongshu.com/explore/66abc123",
                "author_name": "求职观察员",
                "snippet": "腾讯和字节跳动校招已经开放，等待官方公众号核验。",
            }
        ]
    }


def test_real_xiaohongshu_note_ingest_creates_discovery_lead() -> None:
    client = TestClient(create_app())
    user_id = f"test-user-crawl-{uuid4()}"

    source_id = _seed_and_get_xiaohongshu_source(client, user_id)
    response = client.post(
        f"/monitoring/sources/{source_id}/xiaohongshu-notes?user_id={user_id}",
        json=_real_note_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["imported_count"] == 1
    first_lead = body["data"]["leads"][0]
    assert "腾讯" in first_lead["mentioned_companies"]
    assert "字节跳动" in first_lead["mentioned_companies"]
    assert first_lead["payload"]["verification_status"] == "pending_official_wechat"


def test_real_xiaohongshu_note_ingest_is_idempotent() -> None:
    client = TestClient(create_app())
    user_id = f"test-user-idempotent-{uuid4()}"

    source_id = _seed_and_get_xiaohongshu_source(client, user_id)
    endpoint = f"/monitoring/sources/{source_id}/xiaohongshu-notes?user_id={user_id}"
    first_response = client.post(endpoint, json=_real_note_payload())
    second_response = client.post(endpoint, json=_real_note_payload())

    assert first_response.json()["data"]["imported_count"] == 1
    assert second_response.json()["data"]["imported_count"] == 0


def test_xiaohongshu_note_ingest_rejects_non_xiaohongshu_url() -> None:
    client = TestClient(create_app())
    user_id = f"test-user-invalid-url-{uuid4()}"
    source_id = _seed_and_get_xiaohongshu_source(client, user_id)
    payload = _real_note_payload()
    payload["notes"][0]["url"] = "https://example.com/fake-note"

    response = client.post(
        f"/monitoring/sources/{source_id}/xiaohongshu-notes?user_id={user_id}",
        json=payload,
    )

    assert response.json()["data"]["imported_count"] == 0
    assert response.json()["data"]["rejected"][0]["reason"] == "not a Xiaohongshu note URL"


def test_xiaohongshu_profile_feed_evidence_is_traceable() -> None:
    client = TestClient(create_app())
    user_id = f"test-user-profile-feed-{uuid4()}"
    source_id = _seed_and_get_xiaohongshu_source(client, user_id)
    payload = {
        "notes": [
            {
                "title": "vivo 27届产品测评分享",
                "url": "https://www.xiaohongshu.com/user/profile/6762739f0000000019009e68",
                "author_name": "沐影（秋招版）",
                "snippet": "vivo 27届产品秋招测评线索，等待官方公众号核验。",
            }
        ]
    }

    response = client.post(
        f"/monitoring/sources/{source_id}/xiaohongshu-notes?user_id={user_id}",
        json=payload,
    )

    lead = response.json()["data"]["leads"][0]
    assert lead["payload"]["evidence_scope"] == "profile_feed"
    assert lead["payload"]["note_url_available"] is False


def test_leads_create_followup_sources() -> None:
    client = TestClient(create_app())
    user_id = f"test-user-followup-{uuid4()}"

    source_id = _seed_and_get_xiaohongshu_source(client, user_id)
    client.post(
        f"/monitoring/sources/{source_id}/xiaohongshu-notes?user_id={user_id}",
        json=_real_note_payload(),
    )
    response = client.post(f"/monitoring/leads/followup-sources?user_id={user_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["processed_lead_count"] == 1
    assert body["data"]["created_source_count"] == 2
    source_types = {item["source_type"] for item in body["data"]["sources"]}
    assert source_types == {"wechat_official_account"}

    second_response = client.post(f"/monitoring/leads/followup-sources?user_id={user_id}")
    assert second_response.json()["data"]["processed_lead_count"] == 0


def test_wechat_candidate_auto_import_filter() -> None:
    clean_lead = Lead(
        user_id="test-user",
        source_id="source-id",
        source_item_key="clean",
        title="腾讯 2027 校园招聘正式启动",
        author_name="腾讯招聘",
        snippet="投递通道开放",
        mentioned_companies=["腾讯"],
        payload={},
    )
    noisy_lead = Lead(
        user_id="test-user",
        source_id="source-id",
        source_item_key="noisy",
        title="【含内推码】腾讯史上最大规模校招",
        author_name="第三方求职号",
        snippet="内推码汇总",
        mentioned_companies=["腾讯"],
        payload={},
    )

    assert _should_auto_import_wechat_candidate(clean_lead, "腾讯")
    assert not _should_auto_import_wechat_candidate(noisy_lead, "腾讯")


def test_supporting_wechat_content_is_not_a_campaign() -> None:
    from app.services.monitoring import _is_real_wxpublic_recruitment_lead

    for title in ["科大讯飞2027校招笔试攻略", "科大讯飞2027届秋季校园招聘QampA"]:
        lead = Lead(
            user_id="test-user",
            source_id="source-id",
            source_item_key=title,
            title=title,
            url="https://mp.weixin.qq.com/s?__biz=test&mid=1&idx=1&sn=test",
            author_name="科大讯飞招聘",
            mentioned_companies=["科大讯飞"],
            payload={"adapter": "wxpublic_fetch"},
        )
        assert not _is_real_wxpublic_recruitment_lead(lead)


def test_import_wechat_candidates_requires_source_company_match() -> None:
    client = TestClient(create_app())
    user_id = f"test-user-company-match-{uuid4()}"

    client.post(
        f"/monitoring/sources?user_id={user_id}",
        json={
            "source_type": "wechat_official_account",
            "display_name": "腾讯招聘公众号搜索",
            "value": "腾讯 招聘 校招 公众号",
            "config": {"company_name": "腾讯"},
        },
    )
    sources = client.get(f"/monitoring/sources?user_id={user_id}").json()["data"]["items"]
    source_id = sources[0]["id"]
    # Manually add a mismatched candidate under the Tencent source.
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        db.add(
            Lead(
                user_id=user_id,
                source_id=source_id,
                source_item_key=f"mismatch-{uuid4()}",
                title="小米 2027 校园招聘正式启动",
                url="https://mp.weixin.qq.com/s?__biz=xiaomi&mid=1&idx=1&sn=mismatch",
                author_name="小米招聘",
                snippet="小米校招启动",
                mentioned_companies=["小米"],
                payload={"content_kind": "official_wechat_article_candidate", "adapter": "wxpublic_fetch"},
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post(f"/monitoring/leads/import-wechat-candidates?user_id={user_id}")
    skipped_reasons = [item["reason"] for item in response.json()["data"]["skipped_leads"]]

    assert any("candidate does not match source company" in reason for reason in skipped_reasons)


def test_wechat_crawl_can_target_selected_companies(monkeypatch) -> None:
    client = TestClient(create_app())
    user_id = f"test-user-targeted-wechat-{uuid4()}"
    for company in ["vivo", "科大讯飞"]:
        client.post(
            f"/monitoring/sources?user_id={user_id}",
            json={
                "source_type": "wechat_official_account",
                "display_name": f"{company}招聘公众号搜索",
                "value": f"{company} 招聘 校招 公众号",
                "config": {"company_name": company, "official_account_name": f"{company}招聘"},
            },
        )

    monkeypatch.setattr(
        monitoring,
        "_fetch_wxpublic_article_candidates",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(monitoring.settings, "wxpublic_app_id", "test-app")
    monkeypatch.setattr(monitoring.settings, "wxpublic_secure_key", "test-key")

    response = client.post(
        f"/monitoring/crawl/wechat?user_id={user_id}&company=vivo&days=7&limit_per_source=1"
    )

    assert response.json()["data"]["source_count"] == 1
