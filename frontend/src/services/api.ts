/**
 * Client for the FastAPI backend (versioned REST under /api/v1).
 *
 * - Sends the in-memory access token as a Bearer header.
 * - On a 401, refreshes once via the httpOnly cookie and retries the request.
 * - The browser is never authoritative for scores, XP, mastery or timing — it only sends
 *   inputs and renders what the server returns.
 */
import { useAuthStore } from "@/stores/auth";
import type { ApiErrorBody, TokenResponse } from "@/types/api";

/** Empty = same origin (Next.js proxies /api/v1 to the backend; see next.config.ts). */
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const PREFIX = "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public fields: Record<string, string> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Options = Omit<RequestInit, "body"> & {
  body?: unknown;
  /** Send for answer / test submissions so retries are safe. */
  idempotencyKey?: string;
  /** Skip the automatic refresh-and-retry (used by the auth endpoints themselves). */
  noRetry?: boolean;
};

async function raw<T>(path: string, options: Options = {}): Promise<T> {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { body, idempotencyKey, headers, noRetry, ...init } = options;
  const token = useAuthStore.getState().accessToken;
  const isForm = typeof FormData !== "undefined" && body instanceof FormData; // file uploads
  let res: Response;
  try {
    res = await fetch(`${API_URL}${PREFIX}${path}`, {
      ...init,
      credentials: path.startsWith("/auth") ? "include" : "omit",
      headers: {
        ...(body !== undefined && !isForm && { "Content-Type": "application/json" }),
        ...(token && { Authorization: `Bearer ${token}` }),
        ...(idempotencyKey && { "Idempotency-Key": idempotencyKey }),
        ...headers,
      },
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.");
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const err = (data as ApiErrorBody | null)?.error;
    throw new ApiError(res.status, err?.code ?? "http_error", err?.message ?? res.statusText, err?.fields ?? {});
  }
  return data as T;
}

let refreshing: Promise<TokenResponse | null> | null = null;

/** Exchange the refresh cookie for a new access token. Concurrent callers share one request. */
export function refreshSession(): Promise<TokenResponse | null> {
  refreshing ??= raw<TokenResponse>("/auth/refresh", { method: "POST", noRetry: true })
    .then((t) => {
      useAuthStore.getState().setSession(t.access_token, t.user);
      return t;
    })
    .catch(() => {
      useAuthStore.getState().clear();
      return null;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  try {
    return await raw<T>(path, options);
  } catch (e) {
    const expired = e instanceof ApiError && e.status === 401 && e.code === "token_invalid";
    if (!expired || options.noRetry) throw e;
    const refreshed = await refreshSession();
    if (!refreshed) throw e;
    return raw<T>(path, options);
  }
}
