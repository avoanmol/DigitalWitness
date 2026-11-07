"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { clearSession, useSessionHydrated, useSessionUser } from "@/lib/session";
import { isMockMode } from "@/lib/api";
import { LogoMark } from "@/components/logo-mark";

const navItems = [
  { href: "/my-reports", label: "My reports", roles: ["reporter"] },
  { href: "/cases", label: "Cases", investigatorLabel: "Cases", legalLabel: "Case review", adminLabel: "Case workspace", roles: ["investigator", "legal", "admin"] },
  { href: "/report/new", label: "Document evidence", roles: ["reporter"] },
  { href: "/insights", label: "Review insights", roles: ["investigator", "legal", "admin"] },
  { href: "/ai-review", label: "AI feedback", roles: ["investigator", "legal", "admin"] },
  { href: "/audit", label: "Audit trail", roles: ["legal", "admin"] },
  { href: "/admin/users", label: "User accounts", roles: ["admin"] },
];

export function WorkspaceShell({ children }: { children: ReactNode }) {
  const user = useSessionUser();
  const sessionHydrated = useSessionHydrated();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => { if (sessionHydrated && !user) router.replace("/login"); }, [router, sessionHydrated, user]);

  function logout() {
    clearSession();
    router.replace("/login");
  }

  const activeItem = navItems.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
  const activeLabel = user?.role === "investigator" && activeItem && "investigatorLabel" in activeItem ? activeItem.investigatorLabel
    : user?.role === "legal" && activeItem && "legalLabel" in activeItem ? activeItem.legalLabel
      : user?.role === "admin" && activeItem && "adminLabel" in activeItem ? activeItem.adminLabel
        : activeItem?.label || "Workspace";

  if (!sessionHydrated || !user) return <main className="loading-screen"><div className="spinner" aria-hidden="true" /><p>Opening your workspace…</p></main>;

  return <div className="app-frame">
    <header className="dw-header">
      <Link href={user.role === "reporter" ? "/my-reports" : "/cases"} className="dw-brand" aria-label="DigitalWitness workspace">
        <LogoMark size={30} />
        <span>Digital<span>Witness</span></span>
      </Link>
      <nav aria-label="Workspace navigation" className="dw-nav">
        {navItems.filter((item) => item.roles.includes(user.role)).map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const label = user.role === "investigator" && "investigatorLabel" in item ? item.investigatorLabel
            : user.role === "legal" && "legalLabel" in item ? item.legalLabel
              : user.role === "admin" && "adminLabel" in item ? item.adminLabel : item.label;
          return <Link className={`dw-nav-link ${active ? "active" : ""}`} href={item.href} key={item.href} aria-current={active ? "page" : undefined}>{label}</Link>;
        })}
      </nav>
      <div className="dw-account">
        {isMockMode() && <span className="demo-pill"><span /> Synthetic demo</span>}
        <span className="dw-account-name"><span className="avatar">{user.full_name.slice(0, 1).toUpperCase()}</span><span><strong>{user.full_name}</strong><small>{user.role}</small></span></span>
        <button className="dw-logout" onClick={logout}>Log out</button>
      </div>
    </header>
    {isMockMode() && <div className="mock-banner"><strong>Demo mode</strong><span>Sample data only. Uploads and actions stay in this browser and are not sent to the API.</span></div>}
    <main className="page-content">{children}</main>
    <footer className="page-footer">DigitalWitness <span>·</span> Preserve the record. Keep control of what you share. <span>·</span> Times shown in IST unless marked UTC</footer>
  </div>;
}
