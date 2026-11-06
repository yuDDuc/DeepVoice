export const API = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/v1";
export const WS = process.env.NEXT_PUBLIC_WS_URL || "/ws/v1";
function csrf() {
  return typeof document === "undefined"
    ? ""
    : decodeURIComponent(
        document.cookie
          .split("; ")
          .find((x) => x.startsWith("avrt_csrf="))
          ?.split("=")[1] || "",
      );
}
export async function api<T = any>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  headers.set("X-CSRF-Token", csrf());
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (response.status === 401 && retry && !path.startsWith("/auth/")) {
    await api("/auth/refresh", { method: "POST" }, false);
    return api(path, init, false);
  }
  if (!response.ok) {
    let message = "Kết nối thất bại";
    try {
      const body = await response.json();
      message =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail);
    } catch {
      message = await response.text().catch(() => message);
    }
    throw new Error(message || `HTTP ${response.status}`);
  }
  return response.json();
}
export interface User {
  id: string;
  email: string;
  role: "user" | "admin";
  credits: number;
}
export interface Segment {
  direction: "en-vi" | "vi-en";
  id: string;
  source_text: string;
  target_text: string;
  state: string;
  mock: boolean;
  saved: boolean;
  verification: { warnings: string[]; semantic_verified: boolean };
  timings: { asr_ms?: number; mt_ms: number; total_ms: number };
  audio?: { mime: string; base64: string };
}
export interface Model {
  role: string;
  model_id: string;
  model_revision: string;
  source: string;
  device: string;
  status: string;
  preflight: { ok: boolean; note: string };
  input_shape: number[];
  execution: string;
}
export function download(
  name: string,
  body: string,
  type = "application/json",
) {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
