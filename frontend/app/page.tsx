"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, dateText, Goal, localizeTodoText, ReminderNotification, Schedule, Todo, today, USER_ID } from "./lib";

export default function Home() {
  const router = useRouter();
  const [todos, setTodos] = useState<Todo[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [notifications, setNotifications] = useState<ReminderNotification[]>([]);
  const [minutes, setMinutes] = useState(60);
  const [customMinutes, setCustomMinutes] = useState("");
  const [planning, setPlanning] = useState(false);
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    try {
      await api<Goal>(`/goals?user_id=${USER_ID}`);
    } catch (error) {
      if ((error as Error).message === "not-found") router.replace("/onboarding");
    }
    const [todoData, scheduleData, notificationData] = await Promise.all([
      api<{ items: Todo[] }>(`/todos?user_id=${USER_ID}&date=${today()}`).catch(() => ({ items: [] })),
      api<{ items: Schedule[] }>(`/schedules?user_id=${USER_ID}&status=pending`).catch(() => ({ items: [] })),
      api<{ items: ReminderNotification[] }>(`/notifications?user_id=${USER_ID}`).catch(() => ({ items: [] })),
    ]);
    setTodos(todoData.items); setSchedules(scheduleData.items); setNotifications(notificationData.items);
  }
  useEffect(() => { void load(); }, []);

  async function plan() {
    setPlanning(true); setNotice("");
    try {
      await api(`/agent/runs/today?user_id=${USER_ID}&date=${today()}&available_minutes=${minutes}`, { method: "POST" });
      await load(); setNotice("今天的计划已根据最新进展排好。");
    } catch { setNotice("生成失败，请确认服务已启动后重试。"); }
    setPlanning(false);
  }
  async function complete(todo: Todo) {
    await api(`/todos/${todo.id}/completion?user_id=${USER_ID}`, { method: "PATCH", body: JSON.stringify({ completed: todo.status !== "completed", completion_source: "user" }) });
    await load();
  }
  async function postpone(todo: Todo) {
    const next = new Date(); next.setDate(next.getDate() + 1);
    await api(`/todos/${todo.id}?user_id=${USER_ID}`, { method: "PATCH", body: JSON.stringify({ date: next.toISOString().slice(0, 10) }) });
    await load(); setNotice("已延期到明天。");
  }
  async function ignore(todo: Todo) {
    await api(`/todos/${todo.id}?user_id=${USER_ID}`, { method: "PATCH", body: JSON.stringify({ status: "expired" }) });
    await load(); setNotice("已从今天忽略，可在历史记录中查看。");
  }
  async function addTodo(e: React.FormEvent) {
    e.preventDefault(); if (!title.trim()) return;
    await api(`/todos?user_id=${USER_ID}`, { method: "POST", body: JSON.stringify({ date: today(), title: title.trim(), source: "user", estimated_minutes: 20 }) });
    setTitle(""); setAdding(false); await load();
  }
  async function readNotification(id: string) {
    await api(`/notifications/${id}/read?user_id=${USER_ID}`, { method: "PATCH" });
    setNotifications(current => current.filter(item => item.id !== id));
  }
  const pending = todos.filter(t => t.status === "pending");
  const completed = todos.filter(t => t.status === "completed");
  const nextSchedule = [...schedules].sort((a,b) => (a.starts_at ?? a.deadline_at ?? "").localeCompare(b.starts_at ?? b.deadline_at ?? ""))[0];

  return <div className="page home-page">
    <section className="welcome"><div><p className="eyebrow">今日概览 · {new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", weekday: "long" }).format(new Date())}</p><h1>聚焦今天，推进下一步。</h1><p>基于最新投递进展、关键日程与目标优先级，整理今天值得投入的事项。</p></div>
      <div className="day-score"><strong>{pending.length}</strong><span>项待完成</span><small>{completed.length ? `已完成 ${completed.length} 项` : "从第一项开始吧"}</small></div>
    </section>

    {notifications.length > 0 && <section className="reminder-center"><div className="reminder-center-head"><div><p className="eyebrow">日程提醒</p><h2>{notifications.length} 项日程已进入提醒时间</h2></div><Link href="/schedule">查看全部日程 →</Link></div><div className="reminder-notifications">{notifications.map(item => <article key={item.id}><span className="reminder-bell">◷</span><div><strong>{item.title}</strong><p>{notificationLead(item.minutes_before)} · {dateText(item.event_at)}</p></div><Link href={`/schedule/${item.schedule_id}`}>查看</Link><button onClick={() => readNotification(item.id)}>已读</button></article>)}</div></section>}

    <section className="plan-card">
      <div className="section-title"><div><span className="ai-dot">✦</span><p className="eyebrow">AI 今日规划</p><h2>为今天留出多少时间？</h2></div><span className="quiet">聚焦至多 3 项关键行动</span></div>
      <div className="time-row">{[30,60,120,240].map(value => <button key={value} className={minutes === value && !customMinutes ? "selected" : ""} onClick={() => { setMinutes(value); setCustomMinutes(""); }}>{value < 60 ? `${value} 分钟` : value === 240 ? "4 小时+" : `${value/60} 小时`}</button>)}<label className="custom-time"><input type="number" min="15" max="720" step="5" value={customMinutes} onChange={event => { const value = event.target.value; setCustomMinutes(value); if (value) setMinutes(Math.min(720, Math.max(15, Number(value)))); }} placeholder="自定义"/><span>分钟</span></label><button className="primary" onClick={plan} disabled={planning}>{planning ? "正在规划…" : pending.length ? "重新规划" : "生成今日计划"}</button></div>
      {notice && <p className="notice">{notice}</p>}
    </section>

    <div className="content-grid">
      <section className="panel todo-panel"><div className="section-title"><div><p className="eyebrow">今日待办</p><h2>今日行动清单</h2></div><button className="text-button" onClick={() => setAdding(!adding)}>＋ 添加任务</button></div>
        {adding && <form className="inline-form" onSubmit={addTodo}><input autoFocus value={title} onChange={e => setTitle(e.target.value)} placeholder="输入一件今天要完成的事"/><button className="primary">添加</button></form>}
        <div className="todo-list">{pending.length === 0 ? <div className="empty"><span>✓</span><h3>今天的清单尚未生成</h3><p>设置可投入时间，获得一份结合当前求职进展的行动建议。</p></div> : pending.map((todo, index) => <article className="todo-item" key={todo.id}><button className="check" onClick={() => complete(todo)} aria-label="标记完成"/><span className="order">{String(index+1).padStart(2,"0")}</span><div><h3>{localizeTodoText(todo.title)}</h3><p>{localizeTodoText(todo.business_reason) ?? (todo.source === "planner" ? "基于当前求职进展生成" : "你添加的任务")}</p><small>{todo.source === "planner" ? "AI 规划" : "手动添加"} · 预计 {todo.estimated_minutes ?? 20} 分钟</small></div><div className="item-actions"><button onClick={() => postpone(todo)}>延期</button><button onClick={() => ignore(todo)}>忽略</button></div></article>)}</div>
        {completed.length > 0 && <details className="completed"><summary>已完成 {completed.length} 项</summary>{completed.map(todo => <button key={todo.id} onClick={() => complete(todo)}>✓ {todo.title}</button>)}</details>}
      </section>
      <aside className="side-stack">
        <section className="panel next-card"><p className="eyebrow">下一项关键日程</p>{nextSchedule ? <><h3>{nextSchedule.title}</h3><strong>{dateText(nextSchedule.starts_at ?? nextSchedule.deadline_at)}</strong><p>提醒将按你的偏好发送。</p></> : <><h3>近期日程已清空</h3><p>新的测评、笔试与面试安排会自动汇总至此。</p></>}<Link href="/schedule">查看全部日程 →</Link></section>
        <section className="quick-links"><Link href="/radar"><span>⌁</span><div><strong>秋招雷达</strong><small>发现匹配机会</small></div><b>→</b></Link><Link href="/applications"><span>▤</span><div><strong>我的投递</strong><small>跟进招聘流程</small></div><b>→</b></Link></section>
      </aside>
    </div>
  </div>;
}

function notificationLead(minutes: number) {
  if (minutes === 0) return "今天到期";
  if (minutes % 1440 === 0) return `还有 ${minutes / 1440} 天`;
  return `还有 ${minutes / 60} 小时`;
}
