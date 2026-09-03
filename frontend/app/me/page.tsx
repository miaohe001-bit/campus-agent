"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api, EmailCredentialStatus, EmailSyncResult, Goal, Priority, userId } from "../lib";

const empty: Goal = { graduation_year: "2027", target_positions: [], target_cities: [], target_industries: [], target_companies: [] };

export default function Me() {
  const [goal, setGoal] = useState<Goal>(empty);
  const [editing, setEditing] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");
  const [emailStatus, setEmailStatus] = useState<EmailCredentialStatus | null>(null);
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [emailAddress, setEmailAddress] = useState("");
  const [authorizationCode, setAuthorizationCode] = useState("");

  useEffect(() => {
    api<Goal>(`/goals?user_id=${userId()}`).then(setGoal).catch(() => {});
    void loadEmailStatus();
  }, []);

  async function loadEmailStatus() {
    setEmailStatus(await api<EmailCredentialStatus>(`/email-credentials?user_id=${userId()}`));
  }

  async function save() {
    await api(`/goals?user_id=${userId()}`, { method: "PATCH", body: JSON.stringify(goal) });
    setEditing(false);
    setMessage("求职目标已更新。");
  }

  async function saveEmail(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      await api(`/email-credentials?user_id=${userId()}`, { method: "PUT", body: JSON.stringify({ email_address: emailAddress.trim(), authorization_code: authorizationCode.trim() }) });
      setAuthorizationCode("");
      setShowEmailForm(false);
      await loadEmailStatus();
      setMessage("邮箱授权已加密保存，可以开始同步。");
    } catch {
      setMessage("保存失败，请检查邮箱地址、授权码或系统加密配置。");
    }
  }

  async function removeEmail() {
    await api(`/email-credentials?user_id=${userId()}`, { method: "DELETE" });
    setEmailStatus({ configured: false, provider: "qq", masked_email_address: null, enabled: false, last_synced_at: null });
    setMessage("邮箱授权已移除。");
  }

  async function sync() {
    if (!emailStatus?.configured) { setShowEmailForm(true); return; }
    setSyncing(true);
    try {
      const result = await api<EmailSyncResult>(`/email-imports/qq/sync?user_id=${userId()}&replan=true`, { method: "POST" });
      if (!result.ok) throw new Error(result.reason ?? "sync-failed");
      localStorage.setItem("campus-agent:last-email-sync", new Date().toISOString());
      await loadEmailStatus();
      setMessage(result.imported_count ? `邮箱更新完成：识别 ${result.imported_count} 条新进展。` : `已检查 ${result.scanned_count} 封邮件，暂无新的招聘进展。`);
    } catch {
      setMessage("更新失败，请检查 QQ 邮箱是否已开启 IMAP，以及授权码是否有效。");
    } finally { setSyncing(false); }
  }

  return <div className="page">
    <header className="page-head"><p className="eyebrow">求职偏好与账户</p><h1>我的</h1><p>调整目标方向、提醒方式与数据授权。</p></header>
    {message && <p className="notice global">{message}</p>}
    <section className="settings-section">
      <div className="settings-title"><div><span>01</span><h2>求职目标设置</h2><p>用于雷达匹配、优先级判断和每日计划。</p></div><button className="secondary" onClick={() => editing ? void save() : setEditing(true)}>{editing ? "保存修改" : "编辑"}</button></div>
      <div className="goal-summary"><Summary label="求职届别" value={`${goal.graduation_year}${goal.graduation_year !== "社招" ? " 届" : ""}`} /><Summary label="目标岗位" value={goal.target_positions.join("、") || "未设置"} /><Summary label="目标城市" value={goal.target_cities.join("、") || "未设置"} /><Summary label="目标行业" value={goal.target_industries.join("、") || "未设置"} /></div>
      <div className="target-list"><h3>目标公司</h3>{goal.target_companies.map(company => <div key={company.company_name}><span className={`priority ${company.priority}`}>{company.priority}</span><strong>{company.company_name}</strong>{editing ? <select value={company.priority} onChange={event => setGoal({ ...goal, target_companies: goal.target_companies.map(item => item.company_name === company.company_name ? { ...item, priority: event.target.value as Priority } : item) })}><option value="dream">Dream · 冲刺</option><option value="target">Target · 重点</option><option value="safe">Safe · 保底</option></select> : <small>{company.priority === "dream" ? "冲刺" : company.priority === "target" ? "重点" : "保底"}</small>}</div>)}</div>
      <Link href="/onboarding" className="text-link">重新完整设置 →</Link>
    </section>
    <section className="settings-section"><div className="settings-title"><div><span>02</span><h2>提醒偏好</h2><p>系统按节点类型异步生成默认提醒。</p></div></div><div className="preference-list"><Preference title="截止事项" text="提前 3 天、1 天、当天提醒" /><Preference title="面试" text="提前 1 天、2 小时提醒" /><Preference title="笔试" text="提前 1 天、1 小时提醒" /></div></section>
    <section className="settings-section">
      <div className="settings-title"><div><span>03</span><h2>权限与隐私</h2><p>邮箱只用于识别招聘进展，不会代你回复邮件。</p></div></div>
      <div className="permission-card"><div className="permission-icon">✉</div><div><h3>QQ 招聘邮箱</h3><p>{emailStatus?.configured ? `已连接 ${emailStatus.masked_email_address}` : "尚未连接，每位使用者独立授权"}</p><span className="safe-text">授权码加密保存 · 只读取最近 20 封邮件</span></div><div className="permission-actions">{emailStatus?.configured && <button className="secondary" onClick={() => setShowEmailForm(true)}>更换邮箱</button>}<button className="primary" onClick={() => void sync()} disabled={syncing}>{syncing ? "同步中…" : emailStatus?.configured ? "立即同步" : "连接邮箱"}</button></div></div>
      {emailStatus?.configured && <button className="text-button danger-text" onClick={() => void removeEmail()}>移除邮箱授权</button>}
      {showEmailForm && <form className="credential-form" onSubmit={saveEmail}><label>QQ 邮箱<input type="email" required value={emailAddress} onChange={event => setEmailAddress(event.target.value)} placeholder="name@qq.com" /></label><label>IMAP 授权码<input type="password" required minLength={6} value={authorizationCode} onChange={event => setAuthorizationCode(event.target.value)} placeholder="不是 QQ 登录密码" /></label><p>在 QQ 邮箱设置中开启 IMAP 服务并生成授权码。授权码只会加密保存，不会再次显示。</p><div><button type="button" className="secondary" onClick={() => setShowEmailForm(false)}>取消</button><button className="primary" type="submit">保存并连接</button></div></form>}
      <div className="privacy-note"><strong>你的数据边界</strong><p>Campus Agent 不会自动投递、自动回复邮件或替你确认面试。你可以随时停止邮箱同步并移除授权。</p></div>
    </section>
  </div>;
}

function Summary({ label, value }: { label: string; value: string }) { return <div><span>{label}</span><strong>{value}</strong></div>; }
function Preference({ title, text }: { title: string; text: string }) { return <div><div><strong>{title}</strong><p>{text}</p></div><label className="switch"><input type="checkbox" defaultChecked /><span /></label></div>; }
