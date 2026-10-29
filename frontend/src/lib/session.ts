import type { User } from "@/lib/types";
import { useSyncExternalStore } from "react";

let accessToken: string | null = null;
let currentUser: User | null = null;
const subscribers = new Set<() => void>();

function emitChange() { for (const listener of subscribers) listener(); }
function subscribe(listener: () => void) {
  subscribers.add(listener);
  return () => subscribers.delete(listener);
}

export function setSession(token: string, user: User) {
  accessToken = token;
  currentUser = user;
  emitChange();
}

export function clearSession() {
  accessToken = null;
  currentUser = null;
  emitChange();
}

export function getAccessToken() {
  return accessToken;
}

export function getSessionUser() {
  return currentUser;
}

export function useSessionUser() {
  return useSyncExternalStore(subscribe, getSessionUser, () => null);
}
