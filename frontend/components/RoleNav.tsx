"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearSession, useUser } from "@/lib/auth";
import type { Role } from "@/lib/types";

const links: { href: string; label: string; roles: Role[] }[] = [
  {
    href: "/report/new",
    label: "Report",
    roles: ["reporter", "investigator", "admin"],
  },
  {
    href: "/cases",
    label: "Cases",
    roles: ["investigator", "legal", "admin"],
  },
  {
    href: "/audit",
    label: "Audit Trail",
    roles: ["investigator", "legal", "admin"],
  },
];

const pill =
  "rounded-full border border-ink px-4 py-1.5 transition hover:bg-ink hover:text-paper";

export default function RoleNav() {
  const user = useUser();
  const router = useRouter();

  const visible = user
    ? links.filter((link) => link.roles.includes(user.role))
    : [];

  function logout() {
    clearSession();
    router.push("/login");
  }

  return (
    <nav className="flex flex-wrap items-center justify-end gap-x-4 gap-y-2 text-sm">
      {visible.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className="text-muted transition hover:text-ink"
        >
          {link.label}
        </Link>
      ))}

      {user ? (
        <button onClick={logout} className={pill}>
          Log out
        </button>
      ) : (
        <Link href="/login" className={pill}>
          Log in
        </Link>
      )}
    </nav>
  );
}