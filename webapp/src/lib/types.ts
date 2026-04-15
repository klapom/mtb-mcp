/* TrailPilot API TypeScript interfaces — derived from API_SPEC.md */

// ── Response Envelope ──────────────────────────────────────────────

export interface ApiResponse<T> {
  status: "ok";
  data: T;
  meta: { request_id: string; duration_ms: number; timestamp: string };
}

export interface ApiErrorResponse {
  status: "error";
  error: { code: string; message: string; details?: unknown };
  meta: { request_id: string; timestamp: string };
}

// ── Dashboard ──────────────────────────────────────────────────────

export interface DashboardData {
  ride_score: RideScore;
  weather_current: WeatherCurrent;
  trail_condition: TrailCondition;
  weekend_preview: WeekendPreview;
  next_service: NextService | null;
  active_timer: ActiveTimer | null;
}

export interface RideScore {
  score: number;
  verdict: string;
  weather_score: number;
  trail_score: number;
  wind_score: number;
  daylight_score: number;
  factors: string[];
}

export interface WeatherCurrent {
  temp_c: number;
  wind_speed_kmh: number;
  condition: string;
  humidity_pct: number;
  precipitation_mm: number;
}

export interface TrailCondition {
  surface: string;
  condition: string;
  confidence: string;
  rain_48h_mm: number;
}

export interface WeekendPreview {
  saturday: DayPreview;
  sunday: DayPreview;
}

export interface DayPreview {
  date?: string;
  score: number;
  verdict?: string;
  condition?: string;
  temp_range?: string;
}

export interface NextService {
  component_type: string;
  bike: string;
  brand?: string;
  model?: string;
  wear_pct: number;
  km_remaining?: number;
  status: string;
}

export interface ActiveTimer {
  active: boolean;
  remaining_minutes: number;
  ride_description: string;
}

// ── Weather ────────────────────────────────────────────────────────

export interface WeatherForecast {
  location_name: string;
  lat: number;
  lon: number;
  generated_at: string;
  hours: HourForecast[];
}

export interface HourForecast {
  time: string;
  temp_c: number;
  wind_speed_kmh: number;
  wind_gust_kmh: number;
  precipitation_mm: number;
  precipitation_probability: number;
  humidity_pct: number;
  condition: string;
}

export interface RainRadar {
  lat: number;
  lon: number;
  status: string;
  approaching: boolean;
  minutes_until_rain: number | null;
  intensity: string | null;
  summary: string;
}

export interface WeatherAlert {
  severity: string;
  headline: string;
  description: string;
  start: string;
  end: string;
  region: string;
}

export interface RainHistory {
  lat: number;
  lon: number;
  total_mm?: number;
  total_mm_48h?: number;
  hours?: { time: string; precipitation_mm: number }[];
  hourly_mm?: number[];
}

// ── Trails ─────────────────────────────────────────────────────────

export interface Trail {
  osm_id: number;
  name: string;
  mtb_scale: string;
  difficulty?: string;
  surface: string;
  length_m: number;
  lat?: number;
  lon?: number;
  geometry?: { lat: number; lon: number; ele: number | null }[];
  condition?: TrailCondition;
}

export interface TrailDetail extends Trail {
  description: string;
  elevation_gain_m: number;
  tags: Record<string, string>;
  condition: TrailCondition;
}

// ── Tours ──────────────────────────────────────────────────────────

export interface TourSummary {
  id: string;
  source: string;
  name: string;
  distance_km: number | null;
  elevation_m: number | null;
  elevation_up_m?: number | null;
  elevation_down_m?: number | null;
  duration_minutes?: number | null;
  difficulty: string | null;
  region?: string | null;
  sport?: string;
  url?: string;
  image_url?: string;
}

export interface TourDetail extends TourSummary {
  description: string;
  start_lat: number;
  start_lon: number;
  gpx_available: boolean;
  segments: { name: string; distance_km: number; difficulty: string }[];
}

// ── Bikes ──────────────────────────────────────────────────────────

export interface Bike {
  id: string;
  name: string;
  type: string;
  total_km: number;
  component_count: number;
  worst_wear_pct: number;
  worst_component: string;
}

export interface BikeComponent {
  id: string;
  component_type: string;
  brand: string;
  model: string;
  installed_at_km: number;
  current_km: number;
  max_km: number;
  wear_pct: number;
  status: string;
}

// ── Training ───────────────────────────────────────────────────────

export interface TrainingStatus {
  ctl: number;
  atl: number;
  tsb: number;
  fitness_level: string;
  trend: string;
}

export interface TrainingGoal {
  id: string;
  name: string;
  type?: string;
  target_date?: string;
  goal_type?: string;
  status?: string;
  progress_pct?: number;
  target_distance_km?: number | null;
  target_elevation_m?: number | null;
  target_ctl?: number | null;
  description?: string | null;
}

export interface TrainingPlan {
  goal_id: string;
  weeks: TrainingWeek[];
}

export interface TrainingWeek {
  week_number: number;
  phase: string;
  target_hours: number;
  target_tss: number;
  sessions: { day: string; type: string; duration_min: number; intensity: string }[];
}

export interface RaceReadiness {
  goal_id: string;
  ready: boolean;
  score: number;
  checklist: { item: string; status: string; detail: string }[];
}

// ── eBike ──────────────────────────────────────────────────────────

export interface RangeCheckResult {
  feasible: boolean;
  verdict: string;
  estimated_range_km: number;
  route_distance_km: number;
  elevation_gain_m: number;
  battery_at_finish_pct: number;
  modes: { mode: string; range_km: number; battery_pct: number }[];
}

// ── Safety ─────────────────────────────────────────────────────────

export interface SafetyTimer {
  timer_id: string;
  status: string;
  remaining_minutes: number;
  ride_description: string;
  started_at: string;
  expires_at: string;
  emergency_contact: string;
}

// ── Auth ──────────────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  email: string | null;
  display_name: string;
  avatar_url: string | null;
  home_lat: number | null;
  home_lon: number | null;
  strava_athlete_id: number | null;
  onboarding_done: boolean;
  strava_connected?: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface InviteLink {
  invite_id: string;
  token: string;
  expires_in_days: number;
}
