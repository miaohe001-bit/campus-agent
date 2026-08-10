from enum import StrEnum


class CompanyPriority(StrEnum):
    dream = "dream"
    target = "target"
    safe = "safe"


class ApplicationStage(StrEnum):
    submitted = "submitted"
    assessment = "assessment"
    written_test = "written_test"
    interview_1 = "interview_1"
    interview_2 = "interview_2"
    interview_3 = "interview_3"
    cross_interview = "cross_interview"
    hr_interview = "hr_interview"
    offer = "offer"
    failed = "failed"


class RecruitmentEventType(StrEnum):
    application_submitted = "application_submitted"
    assessment_received = "assessment_received"
    assessment_completed = "assessment_completed"
    written_test_scheduled = "written_test_scheduled"
    interview_scheduled = "interview_scheduled"
    interview_rescheduled = "interview_rescheduled"
    interview_canceled = "interview_canceled"
    offer_received = "offer_received"
    rejected = "rejected"
    deadline_updated = "deadline_updated"


class ScheduleType(StrEnum):
    application_deadline = "application_deadline"
    assessment_deadline = "assessment_deadline"
    written_test = "written_test"
    interview = "interview"
    offer_response_deadline = "offer_response_deadline"
    custom = "custom"


class ScheduleStatus(StrEnum):
    pending = "pending"
    completed = "completed"
    missed = "missed"
    canceled = "canceled"


class TodoStatus(StrEnum):
    pending = "pending"
    completed = "completed"
    expired = "expired"


class TodoSource(StrEnum):
    planner = "planner"
    user = "user"


class CompletionSource(StrEnum):
    user = "user"
    system = "system"


class MonitoringSourceType(StrEnum):
    xiaohongshu_profile = "xiaohongshu_profile"
    xiaohongshu_keyword = "xiaohongshu_keyword"
    wechat_official_account = "wechat_official_account"
    web_page = "web_page"


class MonitoringSourceStatus(StrEnum):
    active = "active"
    paused = "paused"


class CrawlRunStatus(StrEnum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class LeadStatus(StrEnum):
    new = "new"
    processed = "processed"
    ignored = "ignored"
