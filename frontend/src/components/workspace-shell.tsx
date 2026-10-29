"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { clearSession, useSessionUser } from "@/lib/session";
import { isMockMode } from "@/lib/api";
import { LogoMark } from "@/components/logo-mark";

const navItems = [
  { href: "/cases", label: "My reports", investigatorLabel: "Investigation desk", legalLabel: "Case review", adminLabel: "Case workspace", icon: "▦", roles: ["reporter", "investigator", "legal", "admin"] },
  { href: "/report/new", label: "Document evidence", icon: "＋", roles: ["reporter"] },
  { href: "/ai-review", label: "Review insights", icon: "◷", roles: ["investigator", "legal", "admin"] },
  { href: "/audit", label: "Audit trail", icon: "≋", roles: ["legal", "admin"] },
  { href: "/admin/users", label: "User accounts", icon: "♙", roles: ["admin"] },
];

export function WorkspaceShell({ children }: { children: ReactNode }) {
  const user = useSessionUser();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => { if (!user) router.replace("/login"); }, [router, user]);

  function logout() {
    clearSession();
    router.replace("/login");
  }

  const activeItem = navItems.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
  const activeLabel = user?.role === "investigator" && activeItem && "investigatorLabel" in activeItem ? activeItem.investigatorLabel
    : user?.role === "legal" && activeItem && "legalLabel" in activeItem ? activeItem.legalLabel
      : user?.role === "admin" && activeItem && "adminLabel" in activeItem ? activeItem.adminLabel
        : activeItem?.label || "Workspace";

  if (!user) return <main className="loading-screen"><div className="spinner" aria-hidden="true" /><p>Opening your workspace…</p></main>;

  return <div className="app-frame">
    <aside className="sidebar">
      <Link href={user.role === "reporter" ? "/report/new" : "/cases"} className="brand" aria-label="Digital Witness home"><LogoMark size={28} reversed /><span>Digital <span className="brand-light">Witness</span></span></Link>
      <div className="sidebar-caption">WORKSPACE</div>
      <nav aria-label="Primary navigation" className="side-nav">
        {navItems.filter((item) => item.roles.includes(user.role)).map((item) => {
          const active = pathname === item.href || (item.href !== "/cases" && pathname.startsWith(item.href)) || (item.href === "/cases" && pathname.startsWith("/cases"));
          const label = user.role === "investigator" && "investigatorLabel" in item ? item.investigatorLabel : user.role === "legal" && "legalLabel" in item ? item.legalLabel : user.role === "admin" && "adminLabel" in item ? item.adminLabel : item.label;
          return <Link className={`nav-link ${active ? "active" : ""}`} href={item.href} key={item.href}><span aria-hidden="true" className="nav-icon">{item.icon}</span>{label}</Link>;
        })}
      </nav>
      <div className="sidebar-bottom">
        <div className="privacy-note"><span className="privacy-dot" />Evidence files stay private<br /><small>Only fingerprints are anchored.</small></div>
        <div className="user-chip"><div className="avatar">{user.full_name.slice(0, 1).toUpperCase()}</div><div className="user-meta"><strong>{user.full_name}</strong><span>{user.role}</span></div><button className="icon-button logout" onClick={logout} aria-label="Log out" title="Log out">↗</button></div>
      </div>
    </aside>
    <div className="main-column">
      <header className="topbar">
        <div className="breadcrumb"><span>DigitalWitness</span><span className="crumb-sep">/</span><strong>{activeLabel}</strong></div>
        <div className="topbar-right">{isMockMode() && <span className="demo-pill"><span /> Synthetic demo</span>}<span className="role-pill">{user.role}</span></div>
      </header>
      {isMockMode() && <div className="mock-banner"><strong>Demo mode</strong><span>Sample data only. Uploads and actions stay in this browser and are not sent to the API.</span></div>}
      <main className="page-content">{children}</main>
      <footer className="page-footer">Digital Witness <span>·</span> Document clearly. Move forward. <span>·</span> All times shown in IST unless marked UTC</footer>
    </div>
  </div>;
}
