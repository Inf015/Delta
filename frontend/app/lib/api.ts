// Server-side: URL interna de Docker. Client-side: origen del browser (funciona con cualquier URL).
const API = typeof window === 'undefined'
  ? (process.env.API_URL || 'http://localhost:8000')
  : window.location.origin

// ── Types ────────────────────────────────────────────────────────────────────

export interface Session {
  session_id: string
  simulator: string
  track: string
  car: string
  lap_time: number
  lap_time_fmt: string
  s1: number
  s2: number
  s3: number
  tyre_compound: string
  track_length: number
  session_type: string
  lap_number: number
  valid: boolean
  racing_session_id: string | null
}

export interface Analysis {
  id: string
  status: 'pending' | 'processing' | 'done' | 'failed'
  pre_analysis: Record<string, unknown> | null
  ai_result: {
    summary?: string
    lap_context?: {
      classification: 'personal_best' | 'top_20pct' | 'average' | 'below_average'
      interpretation: string
    }
    sector_analysis?: {
      s1: { assessment: 'good' | 'ok' | 'weak'; detail: string }
      s2: { assessment: 'good' | 'ok' | 'weak'; detail: string }
      s3: { assessment: 'good' | 'ok' | 'weak'; detail: string }
    }
    scores?: {
      frenadas: number
      traccion: number
      curvas_rapidas: number
      gestion_gomas: number
      consistencia: number
    }
    strengths?: string[]
    issues?: Array<{ area: string; detail: string; severity: string }>
    recommendations?: Array<{ text: string; zone: string | null; expected_gain_s: number }>
    setup_suggestions?: string[]
    improvement_plan?: Array<{ step: number; action: string; zone: string; expected_gain_s: number }>
    next_session_focus?: string
  } | null
  tokens_input: number
  tokens_output: number
  completed_at: string | null
}

export interface RacingSession {
  id: string
  name: string | null
  track: string | null
  car: string | null
  simulator: string | null
  session_date: string | null
  session_type: string | null
  lap_count: number
  best_lap: number | null
  best_lap_fmt: string
}

export interface Incident {
  type: 'off_track_or_crash' | 'spin_or_crash' | 'impact' | 'all_wheel_slip' | 'kerb_or_jump'
  dist_m: number | null
  detail: string
  severity: 'high' | 'medium' | 'low'
}

export interface LapOut {
  session_id: string
  lap_number: number
  lap_time: number
  lap_time_fmt: string
  s1: number
  s2: number
  s3: number
  tyre_compound: string
  valid: boolean
  processed: boolean
  incidents?: Incident[]
}

export interface RacingSessionDetail {
  id: string
  name: string | null
  track: string | null
  car: string | null
  simulator: string | null
  session_date: string | null
  session_type: string | null
  laps: LapOut[]
  setup_data: Record<string, unknown> | null
}

export interface ComparisonResult {
  track: string
  session_a: { id: string; car: string; simulator: string }
  session_b: { id: string; car: string; simulator: string }
  best_lap_a: { lap_time: number; lap_time_fmt: string; s1: number; s2: number; s3: number }
  best_lap_b: { lap_time: number; lap_time_fmt: string; s1: number; s2: number; s3: number }
  delta_s1: number
  delta_s2: number
  delta_s3: number
  delta_total: number
  metrics_a: { max_speed: number | null; avg_throttle_pct: number | null; g_lat_max: number | null; g_lon_brake: number | null }
  metrics_b: { max_speed: number | null; avg_throttle_pct: number | null; g_lat_max: number | null; g_lon_brake: number | null }
  ai_comparison: {
    summary?: string
    advantage_a?: string[]
    advantage_b?: string[]
    key_differences?: Array<{ area: string; detail: string; favors: 'A' | 'B' | 'tie' }>
    recommendations?: Array<{ text: string; applies_to: 'A' | 'B' | 'both' }>
    verdict?: string
  }
}

export interface CSVPreview {
  track: string
  car: string
  simulator: string
  session_date: string
  session_type: string
  lap_time: number
  lap_time_fmt: string
  s1: number
  s2: number
  s3: number
  tyre_compound: string
  track_length: number
  lap_number: number
}

// ── Track Info types ──────────────────────────────────────────────────────────

export interface KeyCorner {
  name: string
  type: string
  tip: string
}

export interface LapRecord {
  time: string
  driver: string
  year: number
  series: string
}

export interface TrackInfo {
  track_id: string
  raw_track_id: string
  display_name: string
  country: string | null
  track_type: 'real' | 'fictional' | 'unknown'
  length_m: number | null
  turns: number | null
  characteristics: string[]
  sectors: string[]
  key_corners: KeyCorner[]
  lap_record: LapRecord | null
  notes: string | null
  map_path: string | null
  has_map: boolean
  source: 'static' | 'claude' | 'unknown'
}

// ── Session Report types ─────────────────────────────────────────────────────

export interface LapRow {
  lap_number: number
  lap_time: number
  lap_time_fmt: string
  s1: number; s1_fmt: string
  s2: number; s2_fmt: string
  s3: number; s3_fmt: string
  delta: number
  delta_fmt: string
  status: string
  valid: boolean
  is_best: boolean
  is_best_s1: boolean
  is_best_s2: boolean
  is_best_s3: boolean
  incidents?: Incident[]
}

export interface SessionReport {
  section_0_track?: TrackInfo
  meta: {
    racing_session_id: string
    name: string | null
    track: string | null
    car: string | null
    simulator: string | null
    session_date: string | null
    session_type: string | null
    pilot: string
    tyre_compound: string | null
    tokens_used: number
  }
  section_1_summary: {
    total_laps: number
    valid_laps: number
    best_lap: number; best_lap_fmt: string
    worst_lap: number; worst_lap_fmt: string
    avg_lap: number; avg_lap_fmt: string
    best_s1: number; best_s1_fmt: string
    best_s2: number; best_s2_fmt: string
    best_s3: number; best_s3_fmt: string
    theoretical_best: number; theoretical_best_fmt: string
    potential_gain: number
    f1_best_s1: number; f1_best_s2: number; f1_best_s3: number
    max_speed_kmh?: number
    throttle_avg_pct?: number
    throttle_full_pct?: number
    rpm_max?: number
    fuel_used_per_lap?: number
    brake_hard_pct?: number
    handling?: string
    weak_sector?: string
  }
  section_2_lap_table: LapRow[]
  section_3_consistency: {
    score: number
    label: string
    std_dev: number
    interpretation?: string
  }
  section_4_tyres: {
    temp?: Record<string, { avg: number; max: number; min: number }>
    press?: Record<string, { avg: number; max: number; min: number }>
    camber_table?: Array<{ corner: string; inner?: number; mid?: number; outer?: number; diagnosis: string }>
    slip?: Record<string, { avg: number; max: number }>
    wear?: Array<{ corner: string; avg_pct?: number; max_pct?: number; end_pct?: number }>
    wear_diagnosis?: string[]
    carcass?: Record<string, { avg: number; max: number }>
    overheating_risk?: string[]
  }
  section_5_brakes: {
    temp?: Record<string, { avg: number; max: number }>
    balance?: { front_avg: number; rear_avg: number; bias: string }
    warning?: string
    zones?: Array<{ dist_m: number; speed_kmh: number; intensity: number }>
  }
  section_6_dynamics: {
    g_forces?: Array<{ metric: string; value: string; interpretation: string }>
    suspension?: Array<{ corner: string; avg_mm: number; range_mm: number; min_mm: number; max_mm: number }>
    ride_height?: { front_mm?: number; rear_mm?: number; rake_mm?: number; diagnosis?: string }
    tyre_loads?: { front_pct?: number; rear_pct?: number; balance_diag?: string; FL?: Record<string, number>; FR?: Record<string, number>; RL?: Record<string, number>; RR?: Record<string, number> }
    damper_analysis?: { diagnosis?: string; corners?: Record<string, { avg_ms: number; max_ms: number; p95_ms: number }> }
    yaw_rate?: { avg_rads: number; max_rads: number; p95_rads: number }
    lsd_analysis?: { accel_diff_avg?: number; accel_diff_max?: number; lsd_diagnosis?: string }
    steering?: { avg_abs: number; max_abs: number; understeer_score: number; understeer_level: string }
  }
  section_7_setup: {
    has_setup_data: boolean
    source?: string
    note?: string
    tyre_pressures?: Array<{ corner: string; avg?: number; min?: number; max?: number; target?: number }>
    raw?: Record<string, unknown>
  }
  section_8_technical?: {
    strengths: string[]
    improvements: string[]
    setup_recommendations: string[]
  }
  section_9_opportunities?: Array<{
    rank: number
    title: string
    detail: string
    estimated_gain_s: number
    occurs_in: string
  }>
  section_10_action_plan?: {
    focuses: Array<{ title: string; exercise: string; objective: string }>
    target_lap_time: number
    target_lap_time_fmt: string
    target_consistency_score: number
    timeline: string
  }
  section_11_engineer_diagnosis?: {
    what_is_working: string[]
    problems_detected: string[]
    driving_style: string[]
    setup_recommendations: string[]
    next_session_target: string
  }
}

// ── Auth types ────────────────────────────────────────────────────────────────

export interface AuthResult {
  access_token: string
  token_type: string
  user_id: string
  email: string
  name: string
  is_admin: boolean
  role: string
}

// ── Admin types ───────────────────────────────────────────────────────────────

export interface AdminUser {
  id: string
  email: string
  name: string
  plan: string
  role: string
  is_active: boolean
  is_admin: boolean
  analyses_used: number
  analyses_limit: number
  racing_sessions: number
  laps_total: number
  tokens_used: number
  created_at: string
}

// ── Team types ────────────────────────────────────────────────────────────────

export interface TeamPilot {
  id: string
  email: string
  name: string
  plan: string
  racing_sessions: number
}

export interface TeamInfo {
  id: string
  name: string
  owner_id: string
  pilots: TeamPilot[]
}

export interface TeamSession {
  id: string
  pilot_email: string
  pilot_name: string
  name: string | null
  track: string | null
  car: string | null
  simulator: string | null
  session_type: string | null
  session_date: string | null
  lap_count: number
  best_lap_fmt: string
  has_report: boolean
}

export interface AdminStats {
  total_users: number
  active_users: number
  total_racing_sessions: number
  total_laps: number
  total_tokens: number
  users_by_plan: Record<string, number>
}

export interface AdminSession {
  id: string
  name: string | null
  track: string | null
  car: string | null
  simulator: string | null
  session_type: string | null
  session_date: string | null
  lap_count: number
  best_lap_fmt: string
  created_at: string
}

// ── Auth header helper ────────────────────────────────────────────────────────

function authHeader(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('delta_token') : null
  return {
    'ngrok-skip-browser-warning': 'true',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

// ── Auth functions ────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<AuthResult> {
  const res = await fetch(`${API}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error al iniciar sesión')
  }
  return res.json()
}

export async function register(email: string, password: string, name: string): Promise<AuthResult> {
  const res = await fetch(`${API}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
    body: JSON.stringify({ email, password, name }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error al registrarse')
  }
  return res.json()
}

// ── API functions ─────────────────────────────────────────────────────────────

export async function previewCSV(file: File): Promise<CSVPreview> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API}/api/v1/upload/preview`, { method: 'POST', headers: { ...authHeader() }, body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error al leer el CSV')
  }
  return res.json()
}

export async function createRacingSession(data: Partial<{
  name: string
  track: string
  car: string
  simulator: string
  session_date: string
  session_type: string
}> = {}): Promise<RacingSession> {
  const res = await fetch(`${API}/api/v1/racing-sessions/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error al crear sesión')
  }
  return res.json()
}

export async function updateRacingSession(id: string, data: Partial<{
  name: string
  track: string
  car: string
  simulator: string
  session_date: string
  session_type: string
}>): Promise<RacingSession> {
  const res = await fetch(`${API}/api/v1/racing-sessions/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error al actualizar sesión')
  }
  return res.json()
}

export async function uploadCSVs(files: File[], racingSessionId: string): Promise<{
  laps_uploaded: number
  laps_skipped: number
  laps_duplicate: number
}> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  form.append('racing_session_id', racingSessionId)
  const url = `${API}/api/v1/upload/`
  console.log('[Delta] uploadCSVs fetch to', url, 'files:', files.map(f => f.name + '(' + f.size + 'b)'))
  let res: Response
  try {
    res = await fetch(url, { method: 'POST', headers: { ...authHeader() }, body: form })
  } catch (netErr) {
    console.error('[Delta] uploadCSVs network error:', netErr)
    throw new Error('Error de red al subir archivos. Revisa tu conexión.')
  }
  if (!res.ok) {
    if (res.status === 413) throw new Error('Archivos demasiado grandes. Súbelos de a pocos (máx ~400MB total).')
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error al subir archivos')
  }
  return res.json()
}

export async function getSessions(): Promise<Session[]> {
  const res = await fetch(`${API}/api/v1/sessions/`, { cache: 'no-store', headers: { ...authHeader() } })
  if (!res.ok) return []
  return res.json()
}

export async function getAnalysis(sessionId: string): Promise<Analysis | null> {
  const res = await fetch(`${API}/api/v1/sessions/${sessionId}/analysis`, { cache: 'no-store', headers: { ...authHeader() } })
  if (!res.ok) return null
  return res.json()
}

export async function getRacingSessions(): Promise<RacingSession[]> {
  const res = await fetch(`${API}/api/v1/racing-sessions/`, { cache: 'no-store', headers: { ...authHeader() } })
  if (!res.ok) return []
  return res.json()
}

export async function deleteRacingSession(id: string): Promise<void> {
  const res = await fetch(`${API}/api/v1/racing-sessions/${id}`, { method: 'DELETE', headers: { ...authHeader() } })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error al eliminar sesión')
  }
}

export async function getRacingSession(id: string): Promise<RacingSessionDetail | null> {
  const res = await fetch(`${API}/api/v1/racing-sessions/${id}`, { cache: 'no-store', headers: { ...authHeader() } })
  if (!res.ok) return null
  return res.json()
}

export async function getSessionReport(id: string): Promise<SessionReport | null> {
  const res = await fetch(`${API}/api/v1/racing-sessions/${id}/report`, { cache: 'no-store', headers: { ...authHeader() } })
  if (!res.ok) return null
  return res.json()
}

export function sessionPdfUrl(id: string): string {
  return `${API}/api/v1/racing-sessions/${id}/pdf`
}

export async function uploadSetup(racingSessionId: string, file: File): Promise<{ ok: boolean; sections: string[] }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API}/api/v1/racing-sessions/${racingSessionId}/setup`, { method: 'POST', headers: { ...authHeader() }, body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error al subir setup')
  }
  return res.json()
}

export async function uploadTrackMap(racingSessionId: string, file: File): Promise<{ ok: boolean; track_id: string }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API}/api/v1/racing-sessions/${racingSessionId}/track-map`, { method: 'POST', headers: { ...authHeader() }, body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error al subir mapa')
  }
  return res.json()
}

export function trackMapUrl(racingSessionId: string): string {
  return `${API}/api/v1/racing-sessions/${racingSessionId}/track-map`
}

export async function compareRacingSessions(aId: string, bId: string): Promise<ComparisonResult> {
  const res = await fetch(`${API}/api/v1/racing-sessions/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ session_a_id: aId, session_b_id: bId }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Error al comparar sesiones')
  }
  return res.json()
}

// ── Delta Map types and API ───────────────────────────────────────────────────

export interface DeltaPoint {
  x: number
  z: number
  delta: number
  delta_norm: number
  speed_a: number
  speed_b: number
}

export interface DeltaMap {
  points: DeltaPoint[]
  session_a: { id: string; track: string; best_lap_fmt: string; lap_time: number }
  session_b: { id: string; track: string; best_lap_fmt: string; lap_time: number }
  delta_total: number
}

export async function getDeltaMap(sessionId: string, refId: string): Promise<DeltaMap> {
  const res = await fetch(
    `${API}/api/v1/racing-sessions/${sessionId}/delta-map?ref=${refId}`,
    { headers: { ...authHeader() } }
  )
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || 'Error al calcular delta map')
  }
  return res.json()
}

// ── Lap Telemetry types and API ───────────────────────────────────────────────

export interface LapTelemetryPoint {
  d: number        // 0-1 lap distance
  x: number
  z: number
  speed: number    // km/h
  throttle: number // 0-100
  brake: number    // 0-100
  gear: number     // 0-8
}

export interface LapTelemetry {
  lap_time: number
  lap_time_fmt: string
  lap_number: number
  points: LapTelemetryPoint[]
}

export async function getLapTelemetry(sessionId: string): Promise<LapTelemetry | null> {
  const res = await fetch(
    `${API}/api/v1/racing-sessions/${sessionId}/lap-telemetry`,
    { headers: { ...authHeader() } }
  )
  if (!res.ok) return null
  return res.json()
}

// ── Admin API ─────────────────────────────────────────────────────────────────

async function adminFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${API}/api/v1/admin${path}`, {
    ...options,
    headers: { ...authHeader(), ...(options.headers as Record<string, string> || {}) },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error en el servidor')
  }
  return res
}

export async function adminGetStats(): Promise<AdminStats> {
  return (await adminFetch('/stats')).json()
}

export async function adminListUsers(): Promise<AdminUser[]> {
  return (await adminFetch('/users')).json()
}

export async function adminCreateUser(data: {
  email: string
  password: string
  name?: string
  plan?: string
  is_admin?: boolean
}): Promise<AdminUser> {
  return (await adminFetch('/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })).json()
}

export async function adminUpdateUser(
  userId: string,
  data: { name?: string; plan?: string; role?: string; is_active?: boolean; is_admin?: boolean; password?: string }
): Promise<AdminUser> {
  return (await adminFetch(`/users/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })).json()
}

export async function adminGetUserSessions(userId: string): Promise<AdminSession[]> {
  return (await adminFetch(`/users/${userId}/sessions`)).json()
}

// ── Team / Technician functions ───────────────────────────────────────────────

async function teamFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('delta_token') : null
  const res = await fetch(`${API}/api/v1/teams${path}`, {
    ...options,
    headers: {
      'ngrok-skip-browser-warning': 'true',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error en el servidor')
  }
  return res
}

export async function createTeam(name: string): Promise<TeamInfo> {
  return (await teamFetch('/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })).json()
}

export async function getMyTeam(): Promise<TeamInfo> {
  return (await teamFetch('/my')).json()
}

export async function addPilotToTeam(email: string): Promise<TeamPilot> {
  return (await teamFetch('/my/members', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })).json()
}

export async function removePilotFromTeam(pilotId: string): Promise<void> {
  await teamFetch(`/my/members/${pilotId}`, { method: 'DELETE' })
}

export async function getTeamSessions(): Promise<TeamSession[]> {
  return (await teamFetch('/my/sessions')).json()
}

export async function getPilotSessions(pilotId: string): Promise<TeamSession[]> {
  return (await teamFetch(`/my/pilots/${pilotId}/sessions`)).json()
}

export async function getPilotSessionReport(pilotId: string, sessionId: string): Promise<Record<string, unknown>> {
  return (await teamFetch(`/my/pilots/${pilotId}/sessions/${sessionId}/report`)).json()
}
