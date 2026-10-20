import type { components } from "@medicare/shared-types";
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
let refreshPromise: Promise<void> | null = null;
export async function api<T>(
  path: string,
  init: RequestInit = {},
  allowRefresh = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (init.method && init.method !== "GET") {
    const token = document.cookie
      .split("; ")
      .find((c) => c.startsWith("medicare_csrf="))
      ?.split("=")[1];
    if (token) headers.set("X-CSRF-Token", decodeURIComponent(token));
  }
  const res = await fetch("/api/v1" + path, {
    ...init,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (res.status === 401 && allowRefresh && !path.startsWith("/auth/")) {
    try {
      if (!refreshPromise)
        refreshPromise = api<void>(
          "/auth/refresh",
          { method: "POST" },
          false,
        ).finally(() => {
          refreshPromise = null;
        });
      await refreshPromise;
      return api<T>(path, init, false);
    } catch {
      /* Preserve the original authentication error when renewal is unavailable. */
    }
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      typeof data.detail === "string"
        ? data.detail
        : "Please check your entries and try again.",
    );
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
export type User = {
  id: string;
  email: string;
  name: string;
  language: "en" | "hi" | "bn";
  role: string;
  third_party_ai: boolean;
  mode: string;
};
export type Report = components["schemas"]["ReportOut"];
export type Measurement = components["schemas"]["Measurement"];
export type Analysis = components["schemas"]["AnalysisOut"];
export type Pharmacy = {
  id: string;
  name: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
  phone: string | null;
  hours: string[];
  directions_url: string;
  stock_status: string;
};
