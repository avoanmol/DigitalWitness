import type { User } from "@/lib/types";
import { useSyncExternalStore } from "react";

let accessToken: string | null = null;
let currentUser: User | null = null;
let sessionRestored = false;
const subscribers = new Set<() => void>();
const SESSION_STORAGE_KEY = "digitalwitness.session.v1";

function emitChange() { for (const listener of subscribers) listener(); }
function subscribe(listener: () => void) {
  subscribers.add(listener);
  return () => subscribers.delete(listener);
}

function restoreSession() {
  if (sessionRestored || typeof window === "undefined") return;
  sessionRestored = true;
  try {
    const stored = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!stored) return;
    const value = JSON.parse(stored) as { token?: unknown; user?: unknown };
    if (typeof value.token !== "string" || !value.token || !value.user || typeof value.user !== "object") return;
    const user = value.user as Partial<User>;
    if (typeof user.id !== "string" || typeof user.email !== "string" || typeof user.full_name !== "string" || !["reporter", "investigator", "legal", "admin"].includes(user.role || "")) return;
    accessToken = value.token;
    currentUser = user as User;
  } catch {
    try { window.sessionStorage.removeItem(SESSION_STORAGE_KEY); } catch { /* Storage may be disabled. */ }
  }
}

export function setSession(token: string, user: User) {
  accessToken = token;
  currentUser = user;
  sessionRestored = true;
  try { window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ token, user })); } catch { /* Keep the in-memory session if storage is unavailable. */ }
  emitChange();
}

export function clearSession() {
  accessToken = null;
  currentUser = null;
  sessionRestored = true;
  try { window.sessionStorage.removeItem(SESSION_STORAGE_KEY); } catch { /* Storage may be disabled. */ }
  emitChange();
}

export function getAccessToken() {
  restoreSession();
  return accessToken;
}

export function getSessionUser() {
  restoreSession();
  return currentUser;
}

export function useSessionUser() {
  return useSyncExternalStore(subscribe, getSessionUser, () => null);
}

/** Distinguish the server's empty auth snapshot from a hydrated signed-out client. */
export function useSessionHydrated() {
  return useSyncExternalStore(subscribe, () => true, () => false);
}
