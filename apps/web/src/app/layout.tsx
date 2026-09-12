import type { Metadata } from "next";
import Link from "next/link";
import { Providers } from "./providers";
import "./globals.css";
export const metadata: Metadata = {
  title: "Tovia 所至",
  description: "凡我所至，皆有所记。个人旅行数据库。",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <header className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6 border-b border-border px-6 py-6">
            <Link href="/" className="text-xl font-semibold tracking-tight">
              Tovia <span className="ml-2 font-normal">所至</span>
            </Link>
            <nav aria-label="主导航" className="flex flex-wrap gap-6 text-sm">
              <Link href="/">我的世界</Link>
              <Link href="/calendar">日历</Link>
              <Link href="/trips">旅行</Link>
              <Link href="/inbox">收件箱</Link>
              <Link href="/profile">我的</Link>
            </nav>
          </header>
          <main className="mx-auto max-w-6xl px-6 py-14">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
