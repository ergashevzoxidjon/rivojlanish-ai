/** Backend API bilan ishlash. Token localStorage'da (bo'lmasa xotirada) saqlanadi. */

const TOKEN_KEY = "rivojlanish_token";
let memoryToken: string | null = null;

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY) ?? memoryToken;
  } catch {
    return memoryToken;
  }
}

export function setToken(token: string | null) {
  memoryToken = token;
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* maxfiy rejim — xotirada qoladi */
  }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export async function api<T = unknown>(path: string, method: Method = "GET", body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`/api${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ApiError(0, "Internet aloqasini tekshiring");
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data as { detail?: unknown }).detail;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? "Ma'lumotlar noto'g'ri to'ldirilgan"
          : "Xatolik yuz berdi";
    throw new ApiError(res.status, msg);
  }
  return data as T;
}

export const get = <T>(p: string) => api<T>(p);
export const post = <T>(p: string, b: unknown = {}) => api<T>(p, "POST", b);
export const put = <T>(p: string, b: unknown) => api<T>(p, "PUT", b);
export const patch = <T>(p: string, b: unknown) => api<T>(p, "PATCH", b);
export const del = <T>(p: string) => api<T>(p, "DELETE");

export function qs(params: Record<string, string | number | undefined | null>) {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") s.set(k, String(v));
  const str = s.toString();
  return str ? `?${str}` : "";
}
