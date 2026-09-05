/**
 * Centralized API client.
 *
 * - Base URL from VITE_API_BASE_URL (defaults to "" = same origin, proxied by Vite)
 * - Attaches the JWT from localStorage
 * - JSON request/response handling (FormData passthrough for uploads)
 * - Normalized ApiError carrying an HTTP status (or 0 for network/timeout) and
 *   a friendly, non-technical message
 * - A 401 anywhere (except login/register) clears the token and dispatches
 *   `lcd:unauthorized` so the auth context can sign the session out cleanly
 */
const TOKEN_KEY = "lcd_token";

export const UNAUTHORIZED_EVENT = "lcd:unauthorized";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

/** Default per-request timeout; uploads and long AI calls override it. */
const DEFAULT_TIMEOUT_MS = 90_000;
const UPLOAD_TIMEOUT_MS = 240_000;

export type ApiErrorKind = "offline" | "timeout" | "http" | "unknown";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  kind: ApiErrorKind;
  constructor(message: string, status: number, kind: ApiErrorKind = "http") {
    super(message);
    this.status = status;
    this.kind = kind;
  }
}

/** Non-technical fallbacks used when the server returns no readable body. */
const FALLBACK_MESSAGES: Record<number, string> = {
  400: "The request could not be processed. Please check your input and try again.",
  401: "Your session has expired. Please sign in again.",
  403: "You don't have permission to do that.",
  404: "That wasn't found. It may have been moved or deleted.",
  405: "That action is not supported.",
  408: "The request timed out. Please try again.",
  409: "That already exists or conflicts with something else.",
  413: "The file is too large. Try a smaller file.",
  415: "That file type isn't supported.",
  422: "The request could not be validated.",
  429: "Too many attempts. Please wait a moment and try again.",
  500: "Something went wrong on our side. Please try again.",
  502: "The service is temporarily unavailable. Please try again.",
  503: "The service is temporarily unavailable. Please try again.",
  504: "The request timed out. Please try again.",
};

async function request<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/api${path}`, { ...options, headers, signal: controller.signal });
  } catch (e) {
    const aborted = e instanceof DOMException && e.name === "AbortError";
    throw new ApiError(
      aborted
        ? "The request took too long and was cancelled. Please try again."
        : "Cannot reach the server. Check your connection and try again.",
      0,
      aborted ? "timeout" : "offline",
    );
  } finally {
    window.clearTimeout(timer);
  }

  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }

  if (res.status === 401 && !path.startsWith("/auth/login") && !path.startsWith("/auth/register")) {
    setToken(null);
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }

  if (!res.ok) {
    const serverMessage =
      body && typeof body === "object" && "error" in body && typeof (body as { error: unknown }).error === "string"
        ? String((body as { error: string }).error).trim()
        : "";
    const message = serverMessage || FALLBACK_MESSAGES[res.status] || "The request failed. Please try again.";
    throw new ApiError(message, res.status);
  }
  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown, asForm?: FormData) =>
    request<T>(path, {
      method: "POST",
      body: asForm ?? (body !== undefined ? JSON.stringify(body) : undefined),
    }, asForm ? UPLOAD_TIMEOUT_MS : DEFAULT_TIMEOUT_MS),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
