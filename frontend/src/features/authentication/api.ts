import { api } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import type { AuthUser, Message, SessionInfo, TokenResponse } from "@/types/api";
import type { RegisterValues } from "./schemas";

export type Portal = "student" | "admin";

export async function login(portal: Portal, email: string, password: string) {
  const t = await api<TokenResponse>(portal === "admin" ? "/auth/admin/login" : "/auth/login", {
    method: "POST",
    body: { email, password },
    noRetry: true,
  });
  useAuthStore.getState().setSession(t.access_token, t.user);
  return t.user;
}

export function register(v: RegisterValues) {
  return api<{ user_id: string; status: string; message: string }>("/auth/register", {
    method: "POST",
    noRetry: true,
    body: {
      display_name: v.display_name,
      email: v.email,
      password: v.password,
      is_minor: v.is_minor,
      guardian_email: v.is_minor ? v.guardian_email : null,
      accept_terms: v.accept_terms,
    },
  });
}

export async function logout() {
  try {
    await api<Message>("/auth/logout", { method: "POST", noRetry: true });
  } finally {
    useAuthStore.getState().clear();
  }
}

export const verifyEmail = (token: string) =>
  api<Message>("/auth/verify-email", { method: "POST", body: { token }, noRetry: true });
export const grantGuardianConsent = (token: string) =>
  api<Message>("/auth/guardian-consent", { method: "POST", body: { token }, noRetry: true });
export const resendVerification = (email: string) =>
  api<Message>("/auth/resend-verification", { method: "POST", body: { email }, noRetry: true });
export const resendGuardianConsent = (email: string) =>
  api<Message>("/auth/resend-guardian-consent", { method: "POST", body: { email }, noRetry: true });
export const forgotPassword = (email: string) =>
  api<Message>("/auth/forgot-password", { method: "POST", body: { email }, noRetry: true });
export const resetPassword = (token: string, new_password: string) =>
  api<Message>("/auth/reset-password", { method: "POST", body: { token, new_password }, noRetry: true });
export const changePassword = (current_password: string, new_password: string) =>
  api<Message>("/auth/change-password", { method: "POST", body: { current_password, new_password } });

export const getMe = () => api<AuthUser>("/auth/me");
export const listSessions = () => api<SessionInfo[]>("/auth/sessions");
export const revokeSession = (id: string) => api<Message>(`/auth/sessions/${id}`, { method: "DELETE" });
export async function logoutAll() {
  await api<Message>("/auth/logout-all", { method: "POST" });
  useAuthStore.getState().clear();
}
