"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearSession, useUser } from "@/lib/auth";
import type { Role } from "@/lib/types";

const links: { href: string; label: string; roles: Role[] }[] = [
  { href: "/report/new", label: "Report", roles: ["reporter", "investigator", "admin"] },
  { href: "/cases", label: "Cases", roles: ["investigator", "legal", "admin"] },
  { href: "/audit", label: "Audit", roles: ["legal", "admin"] },
];

const pill =
  "rounded-full border border-ink px-4 py-1.5 transition hover:bg-ink hover:text-paper";

export default function RoleNav() {
  const user = useUser();
  const router = useRouter();
  const visible = user ? links.filter((l) => l.roles.includes(user.role)) : [];

  function logout() {
    clearSession();
    router.push("/login");
  }

  return (
    <nav className="flex items-center gap-4 text-sm">
      {visible.map((l) => (
        <Link key={l.href} href={l.href}
          className="hidden text-muted transition hover:text-ink sm:block">
          {l.label}
        </Link>
      ))}
      {user ? (
        <button onClick={logout} className={pill}>Log out</button>
      ) : (
        <Link href="/login" className={pill}>Log in</Link>
      )}
    </nav>
  );
}