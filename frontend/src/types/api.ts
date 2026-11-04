export type ApiErrorBody = { error: { code: string; message: string; fields?: Record<string, string> } };

export type HealthStatus = Record<"database" | "redis" | "r2", string>;

export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

export type AuthUser = {
  id: string;
  email: string;
  status: string;
  roles: string[];
  permissions: string[];
  display_name: string | null;
  onboarding_completed: boolean | null;
};

export type TokenResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
};

export type Message = { message: string };

export type SessionInfo = {
  id: string;
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
  user_agent: string | null;
  ip_address: string | null;
  current: boolean;
};

export type StudentProfile = {
  user_id: string;
  email: string;
  display_name: string;
  timezone: string;
  is_minor: boolean;
  guardian_email: string | null;
  onboarding_completed: boolean;
  study_mode: string | null;
  deletion_requested_at: string | null;
  created_at: string;
};

export type PlatformStats = {
  total_students: number;
  new_registrations_7d: number;
  active_students_7d: number;
  pending_verification: number;
  pending_guardian_consent: number;
  suspended: number;
  deletion_requests: number;
  failed_logins_24h: number;
  failed_jobs: number;
  outbox_backlog: number;
  generated_at: string;
};

export type UserStatus = "pending_verification" | "pending_consent" | "active" | "suspended" | "deleted";

export type AdminUserRow = {
  id: string;
  email: string;
  display_name: string | null;
  status: UserStatus;
  roles: string[];
  is_minor: boolean | null;
  created_at: string;
  last_login_at: string | null;
  deletion_requested_at: string | null;
};

export type LoginEvent = {
  id: string;
  email: string;
  portal: "student" | "admin";
  success: boolean;
  reason: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
};

export type AdminUserDetail = AdminUserRow & {
  email_verified_at: string | null;
  suspended_reason: string | null;
  guardian_email_masked: string | null;
  timezone: string | null;
  active_sessions: number;
  recent_logins: LoginEvent[];
};

export type AuditLogEntry = {
  id: string;
  actor_user_id: string | null;
  actor_email: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
};

export type RoleInfo = { name: string; description: string; permissions: string[] };

export type DeadLetter = {
  id: string;
  task_name: string;
  event_id: string | null;
  error: string;
  created_at: string;
  replayed_at: string | null;
};
