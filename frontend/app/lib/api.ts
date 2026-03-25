const API = (typeof window === 'undefined'
  ? process.env.API_URL
  : process.env.NEXT_PUBLIC_API_URL) || 'http://localhost:8000'

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
    strengths?: string[]
    issues?: Array<{ area: string; detail: string; severity: string }>
    recommendations?: Array<{ text: string; zone: string | null; expected_gain_s: number }>
    setup_suggestions?: string[]
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
  }
  section_5_brakes: {
    temp?: Record<string, { avg: number; max: number }>
    balance?: { front_avg: number; rear_avg: number; bias: string }
    warning?: string
  }
  section_6_dynamics: {
    g_forces?: Array<{ metric: string; value: string; interpretation: string }>
    suspension?: Array<{ corner: string; avg_mm: number; range_mm: number; min_mm: number; max_mm: number }>
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

// ── API functions ─────────────────────────────────────────────────────────────

export async function previewCSV(file: File): Promise<CSVPreview> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API}/api/v1/upload/preview`, { method: 'POST', body: form })
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
    headers: { 'Content-Type': 'application/json' },
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
    headers: { 'Content-Type': 'application/json' },
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
  const res = await fetch(`${API}/api/v1/upload/`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error al subir archivos')
  }
  return res.json()
}

export async function getSessions(): Promise<Session[]> {
  const res = await fetch(`${API}/api/v1/sessions/`, { cache: 'no-store' })
  if (!res.ok) return []
  return res.json()
}

export async function getAnalysis(sessionId: string): Promise<Analysis | null> {
  const res = await fetch(`${API}/api/v1/sessions/${sessionId}/analysis`, { cache: 'no-store' })
  if (!res.ok) return null
  return res.json()
}

export async function getRacingSessions(): Promise<RacingSession[]> {
  const res = await fetch(`${API}/api/v1/racing-sessions/`, { cache: 'no-store' })
  if (!res.ok) return []
  return res.json()
}

export async function getRacingSession(id: string): Promise<RacingSessionDetail | null> {
  const res = await fetch(`${API}/api/v1/racing-sessions/${id}`, { cache: 'no-store' })
  if (!res.ok) return null
  return res.json()
}

export async function getSessionReport(id: string): Promise<SessionReport | null> {
  const res = await fetch(`${API}/api/v1/racing-sessions/${id}/report`, { cache: 'no-store' })
  if (!res.ok) return null
  return res.json()
}

export function sessionPdfUrl(id: string): string {
  return `${API}/api/v1/racing-sessions/${id}/pdf`
}

export async function uploadSetup(racingSessionId: string, file: File): Promise<{ ok: boolean; sections: string[] }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API}/api/v1/racing-sessions/${racingSessionId}/setup`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Error al subir setup')
  }
  return res.json()
}

export async function compareRacingSessions(aId: string, bId: string): Promise<ComparisonResult> {
  const res = await fetch(`${API}/api/v1/racing-sessions/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_a_id: aId, session_b_id: bId }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Error al comparar sesiones')
  }
  return res.json()
}
