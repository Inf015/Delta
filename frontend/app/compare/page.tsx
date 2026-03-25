'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { useEffect, useState, Suspense } from 'react'
import { getRacingSessions, compareRacingSessions, RacingSession, ComparisonResult } from '../lib/api'

function deltaColor(delta: number): string {
  if (delta < 0) return 'text-green-400'
  if (delta > 0) return 'text-red-400'
  return 'text-gray-400'
}

function fmtDelta(delta: number): string {
  return `${delta > 0 ? '+' : ''}${delta.toFixed(3)}s`
}

function SectorBadge({ delta }: { delta: number }) {
  return (
    <span className={`font-bold ${deltaColor(delta)}`}>
      {fmtDelta(delta)}
    </span>
  )
}

function CompareContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const aId = searchParams.get('a') ?? ''

  const [sessions, setSessions] = useState<RacingSession[]>([])
  const [selectedB, setSelectedB] = useState('')
  const [result, setResult] = useState<ComparisonResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getRacingSessions().then(setSessions)
  }, [])

  const sessionA = sessions.find((s) => s.id === aId)
  const candidatesB = sessions.filter(
    (s) => s.id !== aId && (!sessionA || s.track === sessionA.track)
  )

  async function runCompare() {
    if (!aId || !selectedB) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await compareRacingSessions(aId, selectedB)
      setResult(res)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error al comparar')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-1">Comparar sesiones</h1>
        <p className="text-gray-500 text-sm">Selecciona dos sesiones del mismo circuito para comparar.</p>
      </div>

      {/* Selector */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        <div>
          <label className="text-gray-500 text-xs uppercase tracking-wide block mb-2">Sesión A</label>
          {sessionA ? (
            <div className="border border-gray-700 px-4 py-3">
              <p className="text-white font-bold">{sessionA.track}</p>
              <p className="text-gray-400 text-xs">{sessionA.car} · {sessionA.simulator} · {sessionA.session_date}</p>
            </div>
          ) : (
            <select
              value={aId}
              onChange={(e) => router.push(`/compare?a=${e.target.value}`)}
              className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm outline-none focus:border-f1red"
            >
              <option value="">— Seleccionar sesión A —</option>
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.track} · {s.car} · {s.session_date}
                </option>
              ))}
            </select>
          )}
        </div>

        <div>
          <label className="text-gray-500 text-xs uppercase tracking-wide block mb-2">Sesión B</label>
          <select
            value={selectedB}
            onChange={(e) => setSelectedB(e.target.value)}
            disabled={!aId || candidatesB.length === 0}
            className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm outline-none focus:border-f1red disabled:opacity-40"
          >
            <option value="">— Seleccionar sesión B —</option>
            {candidatesB.map((s) => (
              <option key={s.id} value={s.id}>
                {s.car} · {s.simulator} · {s.best_lap_fmt}
              </option>
            ))}
          </select>
          {aId && candidatesB.length === 0 && (
            <p className="text-gray-600 text-xs mt-1">No hay otras sesiones en el mismo circuito.</p>
          )}
        </div>
      </div>

      <button
        onClick={runCompare}
        disabled={!aId || !selectedB || loading}
        className="bg-f1red hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed text-white px-6 py-2 font-bold text-sm transition-colors mb-8"
      >
        {loading ? 'COMPARANDO...' : 'COMPARAR'}
      </button>

      {error && (
        <p className="text-f1red text-sm border border-f1red/30 px-3 py-2 mb-6">{error}</p>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-6">
          {/* Sector deltas */}
          <div className="border border-gray-800 p-6">
            <h2 className="text-white font-bold mb-4 text-sm uppercase tracking-wide">Sectores</h2>
            <div className="grid grid-cols-4 gap-4 text-center">
              {[
                { label: 'S1', delta: result.delta_s1 },
                { label: 'S2', delta: result.delta_s2 },
                { label: 'S3', delta: result.delta_s3 },
                { label: 'Total', delta: result.delta_total },
              ].map(({ label, delta }) => (
                <div key={label} className="border border-gray-900 p-3">
                  <p className="text-gray-500 text-xs mb-1">{label}</p>
                  <SectorBadge delta={delta} />
                  <p className="text-gray-600 text-xs mt-1">
                    {delta < 0 ? result.session_a.car : delta > 0 ? result.session_b.car : 'Empate'}
                  </p>
                </div>
              ))}
            </div>

            {/* Lap times */}
            <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-gray-800">
              {[
                { label: result.session_a.car, lap: result.best_lap_a },
                { label: result.session_b.car, lap: result.best_lap_b },
              ].map(({ label, lap }) => (
                <div key={label} className="text-center">
                  <p className="text-gray-500 text-xs mb-1">{label}</p>
                  <p className="text-2xl font-bold text-green-400">{lap.lap_time_fmt}</p>
                  <p className="text-gray-600 text-xs mt-1">
                    S1: {lap.s1.toFixed(3)} · S2: {lap.s2.toFixed(3)} · S3: {lap.s3.toFixed(3)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Metrics */}
          <div className="border border-gray-800 p-6">
            <h2 className="text-white font-bold mb-4 text-sm uppercase tracking-wide">Métricas</h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-xs border-b border-gray-800">
                  <th className="text-left py-2">Métrica</th>
                  <th className="text-right py-2">{result.session_a.car}</th>
                  <th className="text-right py-2">{result.session_b.car}</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { label: 'Vel. máxima (km/h)', a: result.metrics_a.max_speed, b: result.metrics_b.max_speed },
                  { label: 'Acelerador promedio (%)', a: result.metrics_a.avg_throttle_pct, b: result.metrics_b.avg_throttle_pct },
                  { label: 'G lateral máx.', a: result.metrics_a.g_lat_max, b: result.metrics_b.g_lat_max },
                  { label: 'G frenada máx.', a: result.metrics_a.g_lon_brake, b: result.metrics_b.g_lon_brake },
                ].map(({ label, a, b }) => (
                  <tr key={label} className="border-b border-gray-900">
                    <td className="py-2 text-gray-400">{label}</td>
                    <td className="py-2 text-right text-white">{a != null ? a.toFixed(1) : '—'}</td>
                    <td className="py-2 text-right text-white">{b != null ? b.toFixed(1) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* AI Comparison */}
          {result.ai_comparison && (
            <div className="border border-gray-800 p-6 space-y-4">
              <h2 className="text-white font-bold text-sm uppercase tracking-wide">Análisis IA</h2>

              {result.ai_comparison.summary && (
                <p className="text-gray-300 text-sm">{result.ai_comparison.summary}</p>
              )}

              {result.ai_comparison.key_differences && result.ai_comparison.key_differences.length > 0 && (
                <div>
                  <h3 className="text-gray-500 text-xs uppercase tracking-wide mb-2">Diferencias clave</h3>
                  <div className="space-y-2">
                    {result.ai_comparison.key_differences.map((d, i) => (
                      <div key={i} className="border border-gray-900 px-3 py-2">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-white text-xs font-bold">{d.area}</span>
                          <span className={`text-xs ${d.favors === 'A' ? 'text-blue-400' : d.favors === 'B' ? 'text-orange-400' : 'text-gray-500'}`}>
                            {d.favors === 'A' ? `Favorece ${result.session_a.car}` : d.favors === 'B' ? `Favorece ${result.session_b.car}` : 'Empate'}
                          </span>
                        </div>
                        <p className="text-gray-400 text-xs">{d.detail}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.ai_comparison.recommendations && result.ai_comparison.recommendations.length > 0 && (
                <div>
                  <h3 className="text-gray-500 text-xs uppercase tracking-wide mb-2">Recomendaciones</h3>
                  <ul className="space-y-1">
                    {result.ai_comparison.recommendations.map((r, i) => (
                      <li key={i} className="flex gap-2 text-sm">
                        <span className={`text-xs shrink-0 mt-0.5 ${r.applies_to === 'A' ? 'text-blue-400' : r.applies_to === 'B' ? 'text-orange-400' : 'text-gray-500'}`}>
                          [{r.applies_to === 'both' ? 'Ambos' : r.applies_to}]
                        </span>
                        <span className="text-gray-300">{r.text}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.ai_comparison.verdict && (
                <div className="border-t border-gray-800 pt-4">
                  <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Veredicto</p>
                  <p className="text-white font-bold">{result.ai_comparison.verdict}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="text-gray-500">Cargando...</div>}>
      <CompareContent />
    </Suspense>
  )
}
