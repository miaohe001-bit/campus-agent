"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const items = [
  ["/", "今日", "⌂"], ["/radar", "秋招雷达", "⌁"], ["/applications", "我的投递", "▤"],
  ["/schedule", "日程", "◷"], ["/me", "我的", "○"],
];

export default function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const onboarding = path === "/onboarding";
  return <div className="app-shell">
    {!onboarding && <header className="topbar">
      <Link href="/" className="brand"><span className="brand-mark">CA</span><span>Campus Agent</span></Link>
      <nav>{items.map(([href, label, icon]) => <Link key={href} href={href} className={path === href ? "active" : ""}><span>{icon}</span>{label}</Link>)}</nav>
      <Link href="/me" className="avatar" aria-label="进入我的">你</Link>
    </header>}
    <main className={onboarding ? "onboarding-main" : "main-content"}>{children}</main>
    {!onboarding && <nav className="bottom-nav">{items.map(([href, label, icon]) => <Link key={href} href={href} className={path === href ? "active" : ""}><span>{icon}</span>{label}</Link>)}</nav>}
  </div>;
}
