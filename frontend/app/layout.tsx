import "./globals.css";
import AppShell from "./AppShell";

export const metadata = { title: "Campus Agent", description: "你的秋招行动助理" };

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
