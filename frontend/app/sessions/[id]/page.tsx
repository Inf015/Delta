import Link from 'next/link'
import { getAnalysis } from '../../lib/api'

const API = (typeof window === 'undefined'
  ? process.env.API_URL
  : process.env.NEXT_PUBLIC_API_URL) || 'http://localhost:8000'

function fmtTime(s: number) {
  if (!s || s <= 0) return '—'
  const m = Math.floor(s / 60)
  const rem = s - m * 60
  return `${m}:${rem.toFixed(3).padStart(6, '0')}`
}

function severityColor(s: string) {
  if (s === 'high') return 'text-red-400'
  if (s === 'medium') return 'text-yellow-400'
  return 'text-green-400'
}

function assessmentColor(a: string) {
  if (a === 'good') return 'text-green-400 border-green-900'
  if (a === 'weak') return 'text-red-400 border-red-900'
  return 'text-gray-400 border-gray-800'
}

function assessmentLabel(a: string) {
  if (a === 'good') return '▲ BUENO'
  if (a === 'weak') return '▼ DÉBIL'
  return '— OK'
}

function classificationLabel(c: string) {
  if (c === 'personal_best') return { label: 'MEJOR TIEMPO PERSONAL', color: 'text-green-400 border-green-800 bg-green-950/20' }
  if (c === 'top_20pct') return { label: 'TOP 20%', color: 'text-blue-400 border-blue-800 bg-blue-950/20' }
  if (c === 'below_average') return { label: 'BAJO PROMEDIO', color: 'text-red-400 border-red-800 bg-red-950/20' }
  return { label: 'PROMEDIO', color: 'text-gray-400 border-gray-800 bg-gray-900' }
}

function ScoreBar({ value, label }: { value: number; label: string }) {
  const pct = Math.min(100, (value / 10) * 100)
  const color = value >= 8 ? '#22c55e' : value >= 6 ? '#f97316' : value >= 4 ? '#eab308' : '#ef4444'
  return (
    <div className="flex items-center gap-3">
      <span className="text-gray-500 text-xs w-28 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-bold w-6 text-right" style={{ color }}>{value}</span>
    </div>
  )
}

async function getSession(id: string) {
  const res = await fetch(`${API}/api/v1/sessions/${id}`, { cache: 'no-store' })
  if (!res.ok) return null
  return res.json()
}

export default async function SessionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const [session, analysis] = await Promise.all([
    getSession(id),
    getAnalysis(id),
  ])

  if (!session) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500">Sesión no encontrada.</p>
        <Link href="/" className="text-f1red text-sm mt-4 inline-block hover:underline">← Volver</Link>
      </div>
    )
  }

  const pre = analysis?.pre_analysis as Record<string, unknown> | null
  const ai = analysis?.ai_result

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link href="/" className="text-gray-600 text-xs hover:text-gray-400 mb-2 inline-block">← Sesiones</Link>
          <h1 className="text-xl font-bold text-white">{session.track}</h1>
          <p className="text-gray-500 text-sm">{session.car} · {session.simulator} · {session.session_type}</p>
        </div>
        {session.pdf_path && (
          <a
            href={`${API}/api/v1/sessions/${id}/pdf`}
            target="_blank"
            className="border border-f1red text-f1red hover:bg-f1red hover:text-white px-4 py-2 text-xs font-bold transition-colors"
          >
            PDF ↓
          </a>
        )}
      </div>

      {/* Tiempo y sectores */}
      <div className="grid grid-cols-4 gap-px bg-gray-800">
        {[
          { label: 'VUELTA', value: fmtTime(session.lap_time), big: true },
          { label: 'SECTOR 1', value: session.s1?.toFixed(3) ?? '—' },
          { label: 'SECTOR 2', value: session.s2?.toFixed(3) ?? '—' },
          { label: 'SECTOR 3', value: session.s3?.toFixed(3) ?? '—' },
        ].map(({ label, value, big }) => (
          <div key={label} className="bg-black p-4 text-center">
            <p className="text-gray-600 text-xs mb-1">{label}</p>
            <p className={`font-bold font-mono ${big ? 'text-2xl text-green-400' : 'text-lg text-white'}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Estado */}
      {(!analysis || analysis.status === 'pending' || analysis.status === 'processing') && (
        <div className="border border-yellow-800 bg-yellow-950/20 px-4 py-3 text-sm text-yellow-400">
          ⏳ Análisis en curso — recarga en unos segundos.
        </div>
      )}
      {analysis?.status === 'failed' && (
        <div className="border border-red-800 bg-red-950/20 px-4 py-3 text-sm text-red-400">
          ✗ El análisis falló. Intenta subir el CSV de nuevo.
        </div>
      )}

      {ai && (
        <>
          {/* Clasificación contextual */}
          {ai.lap_context && (() => {
            const { label, color } = classificationLabel(ai.lap_context.classification)
            return (
              <div className={`border px-4 py-3 flex items-center gap-4 ${color}`}>
                <span className="font-bold text-sm">{label}</span>
                <span className="text-sm opacity-80">{ai.lap_context.interpretation}</span>
              </div>
            )
          })()}

          {/* Resumen */}
          {ai.summary && (
            <section>
              <h2 className="text-xs uppercase text-gray-600 mb-3 tracking-widest">Resumen</h2>
              <p className="text-gray-300 text-sm leading-relaxed border-l-2 border-f1red pl-4">{ai.summary}</p>
            </section>
          )}

          {/* Desglose por sector */}
          {ai.sector_analysis && (
            <section>
              <h2 className="text-xs uppercase text-gray-600 mb-3 tracking-widest">Análisis por Sector</h2>
              <div className="grid grid-cols-3 gap-3">
                {(['s1', 's2', 's3'] as const).map((sector) => {
                  const s = ai.sector_analysis![sector]
                  const cls = assessmentColor(s.assessment)
                  return (
                    <div key={sector} className={`border p-4 ${cls}`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-bold text-sm uppercase">{sector.toUpperCase()}</span>
                        <span className={`text-xs font-bold ${cls.split(' ')[0]}`}>{assessmentLabel(s.assessment)}</span>
                      </div>
                      <p className="text-gray-400 text-xs leading-relaxed">{s.detail}</p>
                    </div>
                  )
                })}
              </div>
            </section>
          )}

          {/* Scores */}
          {ai.scores && (
            <section>
              <h2 className="text-xs uppercase text-gray-600 mb-3 tracking-widest">Puntuación técnica</h2>
              <div className="border border-gray-800 p-4 space-y-3">
                <ScoreBar value={ai.scores.frenadas} label="Frenadas" />
                <ScoreBar value={ai.scores.traccion} label="Tracción" />
                <ScoreBar value={ai.scores.curvas_rapidas} label="Curvas rápidas" />
                <ScoreBar value={ai.scores.gestion_gomas} label="Gestión gomas" />
                <ScoreBar value={ai.scores.consistencia} label="Consistencia" />
              </div>
            </section>
          )}

          {/* Fortalezas / Problemas */}
          <div className="grid grid-cols-2 gap-6">
            {ai.strengths && ai.strengths.length > 0 && (
              <section>
                <h2 className="text-xs uppercase text-gray-600 mb-3 tracking-widest">Fortalezas</h2>
                <ul className="space-y-2">
                  {ai.strengths.map((s, i) => (
                    <li key={i} className="text-sm text-gray-300 flex gap-2">
                      <span className="text-green-500 flex-shrink-0">✓</span>{s}
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {ai.issues && ai.issues.length > 0 && (
              <section>
                <h2 className="text-xs uppercase text-gray-600 mb-3 tracking-widest">Problemas</h2>
                <ul className="space-y-2">
                  {ai.issues.map((issue, i) => (
                    <li key={i} className="text-sm">
                      <span className={`font-bold ${severityColor(issue.severity)}`}>{issue.area}</span>
                      <span className="text-gray-400"> — {issue.detail}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>

          {/* Recomendaciones */}
          {ai.recommendations && ai.recommendations.length > 0 && (
            <section>
              <h2 className="text-xs uppercase text-gray-600 mb-3 tracking-widest">Recomendaciones</h2>
              <div className="space-y-3">
                {ai.recommendations.map((r, i) => (
                  <div key={i} className="border border-gray-800 p-4 flex gap-4 items-start">
                    <span className="text-f1red font-bold text-lg w-6 flex-shrink-0">{i + 1}</span>
                    <div className="flex-1">
                      <p className="text-sm text-white">{r.text}</p>
                      <div className="flex gap-4 mt-1">
                        {r.zone && <span className="text-xs text-gray-500">📍 {r.zone}</span>}
                        {r.expected_gain_s > 0 && (
                          <span className="text-xs text-green-500">−{r.expected_gain_s.toFixed(2)}s estimado</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Setup */}
          {ai.setup_suggestions && ai.setup_suggestions.length > 0 && (
            <section>
              <h2 className="text-xs uppercase text-gray-600 mb-3 tracking-widest">Setup</h2>
              <ul className="space-y-1">
                {ai.setup_suggestions.map((s, i) => (
                  <li key={i} className="text-sm text-gray-400 flex gap-2">
                    <span className="text-gray-600">→</span>{s}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Plan de mejora */}
          {ai.improvement_plan && ai.improvement_plan.length > 0 && (
            <section className="border border-f1red/30 bg-red-950/10 p-5">
              <h2 className="text-xs uppercase text-gray-600 mb-4 tracking-widest">Plan para la próxima vuelta</h2>
              <div className="space-y-4">
                {ai.improvement_plan.map((step) => (
                  <div key={step.step} className="flex gap-4 items-start">
                    <span className="text-f1red font-bold text-xl w-6 flex-shrink-0 leading-none">{step.step}</span>
                    <div className="flex-1">
                      <p className="text-white text-sm font-bold">{step.action}</p>
                      <div className="flex gap-4 mt-1">
                        {step.zone && <span className="text-xs text-gray-500">📍 {step.zone}</span>}
                        {step.expected_gain_s > 0 && (
                          <span className="text-xs text-green-500">−{step.expected_gain_s.toFixed(2)}s estimado</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Legacy: next_session_focus (compatibilidad con análisis viejos) */}
          {ai.next_session_focus && !ai.improvement_plan?.length && (
            <section className="border border-f1red/30 bg-red-950/10 p-4">
              <h2 className="text-xs uppercase text-gray-600 mb-2 tracking-widest">Próxima sesión</h2>
              <p className="text-white text-sm font-bold">{ai.next_session_focus}</p>
            </section>
          )}

          <p className="text-gray-700 text-xs text-right">
            {analysis.tokens_input + analysis.tokens_output} tokens
            {analysis.completed_at && ` · ${new Date(analysis.completed_at).toLocaleString('es')}`}
          </p>
        </>
      )}

      {/* Pre-análisis — datos brutos */}
      {pre && (
        <details className="border border-gray-800">
          <summary className="px-4 py-3 text-xs text-gray-600 cursor-pointer hover:text-gray-400 uppercase tracking-widest">
            Pre-análisis (datos brutos)
          </summary>
          <div className="px-4 pb-4 grid grid-cols-2 gap-4 text-xs mt-2">
            {!!pre.speed && (
              <div>
                <p className="text-gray-600 mb-1">Velocidad</p>
                <p>Max: <span className="text-white">{(pre.speed as Record<string,number>).max} km/h</span></p>
                <p>Avg: <span className="text-white">{(pre.speed as Record<string,number>).avg} km/h</span></p>
              </div>
            )}
            {!!pre.g_forces && (
              <div>
                <p className="text-gray-600 mb-1">G-Forces</p>
                <p>Lateral máx: <span className="text-white">{Math.max((pre.g_forces as Record<string,number>).lat_max_left ?? 0, (pre.g_forces as Record<string,number>).lat_max_right ?? 0).toFixed(2)}G</span></p>
                <p>Frenada: <span className="text-white">{(pre.g_forces as Record<string,number>).lon_max_brake?.toFixed(2)}G</span></p>
              </div>
            )}
            {!!pre.throttle && (
              <div>
                <p className="text-gray-600 mb-1">Throttle</p>
                <p>Avg: <span className="text-white">{(pre.throttle as Record<string,number>).avg}%</span></p>
                <p>A fondo: <span className="text-white">{(pre.throttle as Record<string,number>).full_pct}% del tiempo</span></p>
              </div>
            )}
            {!!pre.handling && (
              <div>
                <p className="text-gray-600 mb-1">Balance</p>
                <p className="text-white capitalize">{pre.handling as string}</p>
              </div>
            )}
          </div>
        </details>
      )}
    </div>
  )
}
