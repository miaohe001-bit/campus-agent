# Backend

Backend service for Campus Agent.

This folder keeps the MVP layers separated:

- `app/api`: HTTP routes.
- `app/runtime`: single loop runtime orchestration.
- `app/planner`: planner interface and implementations.
- `app/tools`: business-state tools used by the planner.
- `app/services`: deterministic business services.
- `app/db`: database configuration and models.

## OpenAI Planner configuration

For local Docker Compose runs, create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4o-mini
```

After editing `.env`, restart the backend:

```bash
docker compose up -d backend
```

If `OPENAI_API_KEY` is empty, the Agent uses the local fallback planner so the MVP flow can still be tested.

The planner uses an OpenAI-compatible client. For third-party compatible providers, set `OPENAI_BASE_URL`.

Examples:

```env
# OpenAI official
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4o-mini

# DeepSeek official compatible API
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat

# OpenRouter compatible API
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=deepseek/deepseek-v4-flash-0731
```

## MVP scheduler configuration

The backend starts one APScheduler job for the MVP single Loop Agent.

```env
SCHEDULER_ENABLED=true
SCHEDULER_USER_ID=local-user
SCHEDULER_TIMEZONE=Asia/Shanghai
SCHEDULER_DAILY_HOUR=9
SCHEDULER_DAILY_MINUTE=0
```

The scheduler status is available at:

```bash
curl http://localhost:8000/agent/scheduler
```

## Mock email import

Phase 7 uses a mock email import endpoint. It accepts copied email content and converts supported recruitment emails into append-only `RecruitmentEvent` records.

```bash
curl -X POST "http://localhost:8000/email-imports/mock?user_id=local-user" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "mock",
    "message_id": "example-message-id",
    "from_address": "recruiting@example.com",
    "subject": "Tencent Product Manager interview",
    "body": "Your interview is scheduled at 2026-08-06 10:00.",
    "application_id": "existing-application-id",
    "campaign_id": "existing-campaign-id"
  }'
```

Supported MVP event detection is rule-based for now:

- rejected
- offer received
- interview scheduled / rescheduled / canceled
- written test scheduled
- assessment received / completed
- deadline updated
- application submitted

## QQ email sync

QQ email sync uses IMAP over SSL.

In the project root `.env`, configure:

```env
QQ_EMAIL_ADDRESS=your_qq_number@qq.com
QQ_EMAIL_AUTHORIZATION_CODE=your_qq_mail_authorization_code
QQ_IMAP_HOST=imap.qq.com
QQ_IMAP_PORT=993
QQ_IMAP_MAILBOX=INBOX
QQ_IMAP_FETCH_LIMIT=20
```

Then restart backend:

```bash
docker compose up -d backend
```

Trigger sync:

```bash
curl -X POST "http://localhost:8000/email-imports/qq/sync?user_id=local-user"
```

Automatic QQ email sync is enabled by default:

```env
QQ_EMAIL_SYNC_ENABLED=true
QQ_EMAIL_SYNC_INTERVAL_HOURS=6
```

When a sync imports new recruitment events, the backend triggers today's Agent run automatically so the Todo list can be refreshed from the latest email state.

Notes:

- Use QQ 邮箱的“授权码”，不要使用 QQ 登录密码。
- The sync reads recent messages from `INBOX` in read-only mode.
- Message-ID is used as the idempotency key, so repeated syncs should not create duplicate events.
