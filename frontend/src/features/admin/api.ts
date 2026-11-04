import { api } from "@/services/api";
import type {
  AdminUserDetail,
  AdminUserRow,
  AuditLogEntry,
  DeadLetter,
  HealthStatus,
  LoginEvent,
  Page,
  PlatformStats,
  RoleInfo,
} from "@/types/api";

function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") s.set(k, String(v));
  const str = s.toString();
  return str ? `?${str}` : "";
}

export const adminApi = {
  stats: () => api<PlatformStats>("/admin/stats"),
  health: () => api<HealthStatus>("/health").catch(() => null),
  users: (p: {
    q?: string;
    status?: string;
    role?: string;
    deletion_requested?: boolean;
    page: number;
    page_size?: number;
  }) => api<Page<AdminUserRow>>(`/admin/users${qs(p)}`),
  user: (id: string) => api<AdminUserDetail>(`/admin/users/${id}`),
  suspend: (id: string, reason: string) =>
    api<AdminUserDetail>(`/admin/users/${id}/suspend`, { method: "POST", body: { reason } }),
  activate: (id: string, reason?: string) =>
    api<AdminUserDetail>(`/admin/users/${id}/activate`, { method: "POST", body: { reason } }),
  roles: () => api<RoleInfo[]>("/admin/roles"),
  auditLogs: (p: { action?: string; target_id?: string; page: number }) =>
    api<Page<AuditLogEntry>>(`/admin/audit-logs${qs(p)}`),
  loginEvents: (p: { success?: boolean; email?: string; page: number }) =>
    api<Page<LoginEvent>>(`/admin/login-events${qs(p)}`),
  deadLetters: (page: number) => api<Page<DeadLetter>>(`/admin/dead-letters${qs({ page })}`),
};
