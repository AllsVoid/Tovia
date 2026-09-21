"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, Globe2, Inbox, Notebook, UserRound } from "lucide-react";
import { AuthStatus } from "@/components/auth-status";
import { webOidcEnabled } from "@/lib/auth-mode";

const links = [
  { href: "/", label: "我的世界", icon: Globe2 },
  { href: "/calendar", label: "旅行日历", icon: CalendarDays },
  { href: "/trips", label: "旅行档案", icon: Notebook },
  { href: "/inbox", label: "收件箱", icon: Inbox },
  { href: "/profile", label: "我的", icon: UserRound },
];
export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const current = links.find((link) =>
    link.href === "/" ? path === "/" : path.startsWith(link.href),
  );
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <Link href="/" className="brand">
          Tovia<span>所 至</span>
        </Link>
        <nav aria-label="主导航">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              aria-current={current?.href === href ? "page" : undefined}
            >
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-note">
          凡我所至，
          <br />
          皆有所记。<p>我的旅行空间</p>
        </div>
      </aside>
      <div className="app-body">
        <header className="app-topbar">
          <span>个人空间 / {current?.label ?? "旅行"}</span>
          {webOidcEnabled ? <AuthStatus /> : <span>所至 · 旅行簿</span>}
        </header>
        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}
