/* Typed API client for TrailPilot FastAPI backend */

import type {
  AuthUser,
  Bike,
  BikeComponent,
  DashboardData,
  RaceReadiness,
  RainHistory,
  RainRadar,
  RangeCheckResult,
  SafetyTimer,
  TourDetail,
  TourSummary,
  TrailDetail,
  TrainingGoal,
  TrainingPlan,
  TrainingStatus,
  Trail,
  WeatherAlert,
  WeatherForecast,
} from "./types";

function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") {
    return `http://${window.location.hostname}:8001/api/v1`;
  }
  return "http://localhost:8001/api/v1";
}

const API_BASE = getApiBase();

class ApiError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "ApiError";
  }
}

async function api<T>(path: string, opts?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("trailpilot_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${API_BASE}${path}`, {
    ...opts,
    headers: { ...headers, ...((opts?.headers as Record<string, string>) || {}) },
  });

  // Try refresh on 401
  if (resp.status === 401 && typeof window !== "undefined") {
    const refreshToken = localStorage.getItem("trailpilot_refresh_token");
    if (refreshToken) {
      try {
        const refreshResp = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        const refreshJson = await refreshResp.json();
        if (refreshJson.status === "ok") {
          localStorage.setItem("trailpilot_token", refreshJson.data.access_token);
          headers["Authorization"] = `Bearer ${refreshJson.data.access_token}`;
          const retryResp = await fetch(`${API_BASE}${path}`, {
            ...opts,
            headers: { ...headers, ...((opts?.headers as Record<string, string>) || {}) },
          });
          const retryJson = await retryResp.json();
          if (retryJson.status === "error")
            throw new ApiError(retryJson.error.code, retryJson.error.message);
          return retryJson.data as T;
        }
      } catch {
        /* refresh failed, fall through */
      }
    }
  }

  const json = await resp.json();
  if (json.status === "error") {
    throw new ApiError(json.error.code, json.error.message);
  }
  return json.data as T;
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined);
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");
}

// ── Dashboard ──────────────────────────────────────────────────────

export const Dashboard = {
  get: () => api<DashboardData>("/dashboard"),
};

// ── Weather ────────────────────────────────────────────────────────

export const Weather = {
  forecast: (lat?: number, lon?: number, hours = 72) =>
    api<WeatherForecast>(`/weather/forecast${qs({ lat, lon, hours })}`),
  rainRadar: (lat?: number, lon?: number) =>
    api<RainRadar>(`/weather/rain-radar${qs({ lat, lon })}`),
  alerts: (lat?: number, lon?: number) =>
    api<{ alerts: WeatherAlert[] }>(`/weather/alerts${qs({ lat, lon })}`),
  history: (lat?: number, lon?: number) =>
    api<RainHistory>(`/weather/history${qs({ lat, lon })}`),
};

// ── Trails ─────────────────────────────────────────────────────────

export const Trails = {
  list: (params?: { radius_km?: number; min_difficulty?: string; surface?: string }) =>
    api<Trail[]>(`/trails${qs(params ?? {})}`),
  get: (osmId: number) => api<TrailDetail>(`/trails/${osmId}`),
  condition: (osmId: number) =>
    api<TrailDetail["condition"]>(`/trails/${osmId}/condition`),
};

// ── Tours ──────────────────────────────────────────────────────────

export const Tours = {
  search: (query?: string, radius_km?: number) =>
    api<TourSummary[]>(`/tours/search${qs({ query, radius_km })}`),
  get: (source: string, id: string) =>
    api<TourDetail>(`/tours/${source}/${id}`),
  gpxUrl: (source: string, id: string) =>
    `${API_BASE}/tours/${source}/${id}/gpx`,
};

// ── Bikes ──────────────────────────────────────────────────────────

export const Bikes = {
  list: () => api<Bike[]>("/bikes"),
  components: (bikeId: string) =>
    api<BikeComponent[]>(`/bikes/${bikeId}/components`),
  logRide: (bikeId: string, body: { distance_km: number; duration_min?: number }) =>
    api<{ message: string }>(`/bikes/${bikeId}/rides`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  logService: (bikeId: string, body: { component_type: string; action: string }) =>
    api<{ message: string }>(`/bikes/${bikeId}/service`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

// ── Training ───────────────────────────────────────────────────────

export const Training = {
  status: () => api<TrainingStatus>("/training/status"),
  goals: () => api<TrainingGoal[]>("/training/goals"),
  plan: (goalId: string) => api<TrainingPlan>(`/training/goals/${goalId}/plan`),
  readiness: () => api<RaceReadiness>("/training/race-readiness"),
};

// ── eBike ──────────────────────────────────────────────────────────

export const EBike = {
  rangeCheck: (body: {
    battery_wh: number;
    battery_pct: number;
    distance_km: number;
    elevation_gain_m: number;
    rider_weight_kg: number;
  }) =>
    api<RangeCheckResult>("/ebike/range-check", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

// ── Safety ─────────────────────────────────────────────────────────

export const Safety = {
  getTimer: () => api<SafetyTimer>("/safety/timer"),
  startTimer: (body: {
    duration_minutes: number;
    ride_description: string;
    emergency_contact?: string;
  }) =>
    api<SafetyTimer>("/safety/timer", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  cancelTimer: (timerId: string) =>
    api<{ message: string }>(`/safety/timer/${timerId}`, { method: "DELETE" }),
};

// ── Auth ──────────────────────────────────────────────────────────

export const Auth = {
  stravaAuthorize: () => api<{ authorize_url: string }>("/auth/strava/authorize"),
  me: () => api<AuthUser>("/auth/me"),
};

export { api, ApiError };
