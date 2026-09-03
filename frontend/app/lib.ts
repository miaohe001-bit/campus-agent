export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export const USER_ID = "local-user";

export type ApiResponse<T> = { code: number; message: string; data: T };
export type Priority = "dream" | "target" | "safe";
export type Goal = { graduation_year: string; target_positions: string[]; target_cities: string[]; target_industries: string[]; target_companies: { company_name: string; priority: Priority }[] };
export type Campaign = { id: string; company_name: string; name: string; status: string | null; target_graduation_year: string | null; position_categories: string[] | null; cities: string[] | null; deadline_at: string | null; source_name: string | null; source_url: string | null; application_url: string | null };
export type Application = { id: string; campaign_id: string | null; company_name: string; position_name: string; stage: string; source: string; last_changed_at: string };
export type RecruitmentEvent = { id: string; application_id: string | null; campaign_id: string | null; event_type: string; occurred_at: string; source: string; payload: Record<string, unknown> };
export type Todo = { id: string; date: string; title: string; status: "pending" | "completed" | "expired"; source: "planner" | "user"; completion_source: string | null; estimated_minutes: number | null; business_reason: string | null };
export type Schedule = { id: string; application_id: string | null; campaign_id: string | null; title: string; schedule_type: string; status: string; starts_at: string | null; deadline_at: string | null; source: string; reminder_minutes: number[]; change_log: Array<{changed_at?:string;changes?:Record<string,unknown>}> };
export type ReminderNotification = { id: string; schedule_id: string; title: string; schedule_type: string; event_at: string; remind_at: string; minutes_before: number; status: string };
export type EmailSyncResult = { ok: boolean; scanned_count: number; imported_count: number; skipped_count: number; reason: string | null };

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
  if (!response.ok) throw new Error(response.status === 404 ? "not-found" : `request-${response.status}`);
  return ((await response.json()) as ApiResponse<T>).data;
}

export const today = () => new Date().toISOString().slice(0, 10);
export const dateText = (value: string | null) => value ? new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "时间待确认";
export const stageLabels: Record<string, string> = { submitted: "已投递", assessment: "测评", written_test: "笔试", interview_1: "一面", interview_2: "二面", interview_3: "三面", cross_interview: "交叉面", hr_interview: "HR 面", offer: "Offer", failed: "已挂" };
export const scheduleLabels: Record<string, string> = { application_deadline: "网申截止", assessment_deadline: "测评截止", written_test: "笔试", interview: "面试", offer_response_deadline: "Offer 回复截止", custom: "自定义" };
export const scheduleStatusLabels: Record<string, string> = { pending: "待进行", completed: "已完成", missed: "已错过", canceled: "已取消" };
export const campaignStatusLabels: Record<string, string> = { open: "开放中", opened: "开放中", active: "开放中", upcoming: "即将开放", closed: "已截止", ended: "已截止" };
export const eventLabels: Record<string, string> = { application_submitted: "已提交投递", assessment_received: "收到测评", assessment_completed: "完成测评", written_test_scheduled: "笔试已安排", interview_scheduled: "面试已安排", interview_rescheduled: "面试时间变更", interview_canceled: "面试已取消", offer_received: "收到 Offer", rejected: "流程结束", deadline_updated: "截止时间更新" };

const companyLabels: Record<string, string> = {
  Tencent: "腾讯", ByteDance: "字节跳动", Alibaba: "阿里巴巴", Meituan: "美团",
  JD: "京东", Baidu: "百度", Huawei: "华为", Xiaomi: "小米",
};

export function normalizeCompanyName(value: string): string {
  return companyLabels[value.trim()] ?? value.trim();
}

export function localizeCategory(value: string): string {
  const labels: Record<string, string> = {
    product: "产品", engineering: "开发", development: "开发", algorithm: "算法",
    design: "设计", operation: "运营", data: "数据", testing: "测试",
  };
  return labels[value.trim().toLowerCase()] ?? value;
}

export function localizeTodoText(value: string | null): string | null {
  if (!value) return value;
  let text = value;
  for (const [english, chinese] of Object.entries(companyLabels)) text = text.replaceAll(english, chinese);
  text = text
    .replace(/Prepare for (.+?) Product Manager interview \(Stage 1\)/i, "准备 $1 产品经理一面")
    .replace(/Complete (.+?) interview experience survey/i, "完成 $1 面试体验调研")
    .replace(/Follow up (.+?) Product Manager progress/i, "跟进 $1 产品经理进度")
    .replace(/Urgent interview preparation for dream company/i, "Dream 公司面试临近，需要优先准备。")
    .replace(/Pending schedule item with time-sensitive feedback value/i, "待进行日程具有明确时效，需要及时处理。")
    .replace(/Product Manager/gi, "产品经理")
    .replace(/interview/gi, "面试")
    .replace(/survey/gi, "调研")
    .replace(/progress/gi, "进度");
  return text;
}
