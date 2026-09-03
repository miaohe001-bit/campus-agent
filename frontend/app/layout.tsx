import "./globals.css";
import AppShell from "./AppShell";

export const metadata = { title: "Campus Agent", description: "聚合机会、投递进展与每日行动的校园求职助手" };

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body><AppShell>{children}</AppShell></body>
    </html>
  );
}
