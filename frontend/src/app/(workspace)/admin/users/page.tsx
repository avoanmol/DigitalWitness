"use client";

import { useEffect, useState } from "react";
import { ApiError, getManagedUsers, updateManagedUser } from "@/lib/api";
import { useSessionUser } from "@/lib/session";
import type { Role, User } from "@/lib/types";

const roles: Role[] = ["reporter", "investigator", "legal", "admin"];

function UserRow({ user, onSaved }: { user: User; onSaved: (user: User) => void }) {
  const [role, setRole] = useState<Role>(user.role);
  const [active, setActive] = useState(user.is_active);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function save() {
    setBusy(true);
    setError("");
    try { onSaved(await updateManagedUser(user.id, { role, is_active: active })); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : "Could not update this account."); }
    finally { setBusy(false); }
  }

  return <tr>
    <td><strong>{user.full_name}</strong><small>{user.email}</small></td>
    <td><select aria-label={`Role for ${user.email}`} value={role} onChange={(event) => setRole(event.target.value as Role)}>{roles.map((item) => <option key={item} value={item}>{item}</option>)}</select></td>
    <td><label className="admin-active-toggle"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} />{active ? "Active" : "Disabled"}</label></td>
    <td><button className="button button-subtle" onClick={save} disabled={busy || (role === user.role && active === user.is_active)}>{busy ? "Saving…" : "Save"}</button>{error && <small className="admin-row-error" role="alert">{error}</small>}</td>
  </tr>;
}

export default function AdminUsersPage() {
  const currentUser = useSessionUser();
  const authorized = currentUser?.role === "admin";
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!authorized) return;
    let active = true;
    getManagedUsers().then((result) => { if (active) { setUsers(result); setError(""); } })
      .catch((reason: unknown) => { if (active) setError(reason instanceof ApiError ? reason.message : "Could not load accounts."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [authorized]);

  if (!authorized) return <div className="inline-error" role="alert"><strong>Administrator access required</strong><span>Only an active admin can manage user accounts.</span></div>;
  return <>
    <div className="page-heading"><div><div className="eyebrow">ADMINISTRATION</div><h1>User accounts</h1><p>Assign workspace roles or disable an account. Every change is added to the audit trail.</p></div></div>
    {error && <div className="form-error" role="alert">{error}</div>}
    <section className="panel"><div className="panel-title-row"><div><h2>Registered users</h2><p>New registrations are reporters. Elevate roles only through an authorized administrator.</p></div><span className="count-pill">{users.length} accounts</span></div>
      {loading ? <div className="table-state"><div className="spinner" /><span>Loading accounts…</span></div> : users.length === 0 ? <div className="empty-state"><h3>No accounts found</h3></div> : <div className="table-wrap"><table className="data-table"><thead><tr><th>ACCOUNT</th><th>ROLE</th><th>STATUS</th><th>ACTION</th></tr></thead><tbody>{users.map((user) => <UserRow key={user.id} user={user} onSaved={(saved) => setUsers((current) => current.map((item) => item.id === saved.id ? saved : item))} />)}</tbody></table></div>}
    </section>
    <div className="split-note"><div className="notice-icon">i</div><p><strong>Protect administrator access.</strong><br />The API prevents disabling or demoting the last active administrator and does not allow an admin to remove their own access.</p></div>
  </>;
}
