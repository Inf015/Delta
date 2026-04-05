'use client'

import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { getRacingSession, RacingSessionDetail } from '../../lib/api'
import LapUploader from './LapUploader'
import SetupUploader from './SetupUploader'
import MapUploader from './MapUploader'
import DeleteButton from './DeleteButton'
import DeltaMap from './DeltaMap'
import TelemetryPanel from './TelemetryPanel'

function fmtTime(s: number) {
  const m = Math.floor(s / 60)
  const rem = s - m * 60
  return `${m}:${rem.toFixed(3).padStart(6, '0')}`
}

export default function RacingSessionPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const id = params.id as string
  const uploadError = searchParams.get('upload_error')
  const [session, setSession] = useState<RacingSessionDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>

    async function fetchAndSchedule() {
      const s = await getRacingSession(id)
      if (cancelled) return
      setSession(s)
      setLoading(false)

      // Auto-refresh mientras haya vueltas pendientes de procesar
      const hasPending = s && s.laps.some((l: { processed: boolean }) => !l.processed)
      if (hasPending) {
        timer = setTimeout(fetchAndSchedule, 5000)
      }
    }

    fetchAndSchedule()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [id])

  if (loading) {
    return <div className="text-gray-600 text-sm py-12 text-center">Cargando...</div>
  }

  if (!session) {
    return <div className="text-gray-500 text-sm py-12 text-center">Sesión no encontrada.</div>
  }

  const bestTime = session.laps.length > 0 ? Math.min(...session.laps.map((l) => l.lap_time)) : null

  return (
    <div>
      {uploadError && (
        <div className="mb-6 border border-yellow-700/50 bg-yellow-950/20 px-4 py-3 text-yellow-400 text-sm">
          <strong>Error al subir vueltas:</strong> {uploadError}. Usa el botón de abajo para reintentar.
        </div>
      )}
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <Link href="/" className="text-gray-500 text-xs hover:text-white mb-2 inline-block">
            ← Sesiones
          </Link>
          <h1 className="text-2xl font-bold text-white">{session.track || session.name || 'Sesión sin título'}</h1>
          <p className="text-gray-400 text-sm mt-1">
            {session.car || '—'} · {session.simulator || '—'} · {session.session_date || 'Sin fecha'}
          </p>
        </div>
        <div className="flex gap-2">
          {session.laps.length > 0 && (
            <Link
              href={`/racing-sessions/${session.id}/report`}
              className="bg-f1red hover:bg-red-700 text-white px-4 py-2 text-sm font-bold transition-colors"
            >
              Ver Reporte
            </Link>
          )}
          <Link
            href={`/compare?a=${session.id}`}
            className="border border-gray-700 hover:border-f1red text-gray-400 hover:text-f1red px-4 py-2 text-sm transition-colors"
          >
            Comparar
          </Link>
          <DeleteButton sessionId={session.id} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="border border-gray-800 p-4">
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Vueltas</p>
          <p className="text-2xl font-bold text-white">{session.laps.length}</p>
        </div>
        <div className="border border-gray-800 p-4">
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Mejor vuelta</p>
          <p className="text-2xl font-bold text-green-400">
            {bestTime ? fmtTime(bestTime) : '—'}
          </p>
        </div>
        <div className="border border-gray-800 p-4">
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Tipo</p>
          <p className="text-2xl font-bold text-white">{session.session_type}</p>
        </div>
      </div>

      {/* Upload de vueltas, setup y mapa */}
      <div className="grid grid-cols-3 gap-4 mb-2">
        <LapUploader racingSessionId={session.id} />
        <SetupUploader racingSessionId={session.id} hasSetup={!!session.setup_data} />
        <MapUploader racingSessionId={session.id} hasMap={false} />
      </div>

      {/* Laps table */}
      {session.laps.length === 0 ? (
        <div className="border border-gray-800 p-12 text-center mt-6">
          <p className="text-gray-500">Sin vueltas todavía. Sube tu primer CSV arriba.</p>
        </div>
      ) : (
        <div className="border border-gray-800 mt-6">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
                <th className="text-left px-4 py-3">Vuelta</th>
                <th className="text-right px-4 py-3">Tiempo</th>
                <th className="text-right px-4 py-3">S1</th>
                <th className="text-right px-4 py-3">S2</th>
                <th className="text-right px-4 py-3">S3</th>
                <th className="text-left px-4 py-3">Compuesto</th>
                <th className="text-center px-4 py-3">Estado</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {session.laps.map((lap, i) => {
                const isBest = bestTime !== null && Math.abs(lap.lap_time - bestTime) < 0.001
                return (
                  <tr
                    key={lap.session_id}
                    className={`border-b border-gray-900 hover:bg-gray-900 transition-colors ${
                      isBest ? 'bg-green-950/20' : i % 2 === 0 ? '' : 'bg-gray-950'
                    }`}
                  >
                    <td className="px-4 py-3 text-gray-400">
                      #{lap.lap_number}
                      {isBest && <span className="ml-2 text-xs text-green-400 font-bold">MEJOR</span>}
                    </td>
                    <td className={`px-4 py-3 text-right font-bold ${isBest ? 'text-green-400' : 'text-white'}`}>
                      {lap.lap_time_fmt}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-400">{lap.s1.toFixed(3)}</td>
                    <td className="px-4 py-3 text-right text-gray-400">{lap.s2.toFixed(3)}</td>
                    <td className="px-4 py-3 text-right text-gray-400">{lap.s3.toFixed(3)}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{lap.tyre_compound || '—'}</td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex flex-col items-center gap-1">
                        {!lap.valid ? (
                          <span className="text-xs px-2 py-0.5 bg-red-950 text-red-400 border border-red-900">
                            INVÁLIDA
                          </span>
                        ) : (
                          <span className={`text-xs px-2 py-0.5 ${lap.processed ? 'bg-green-900 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
                            {lap.processed ? 'Listo' : 'Procesando'}
                          </span>
                        )}
                        {lap.incidents && lap.incidents.length > 0 && (
                          <span
                            className="text-xs px-2 py-0.5 bg-orange-950 text-orange-400 border border-orange-900 cursor-help"
                            title={lap.incidents.map((inc) => inc.detail).join(' | ')}
                          >
                            ⚠ {lap.incidents.length} incidente{lap.incidents.length !== 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/sessions/${lap.session_id}`} className="text-f1red hover:underline text-xs">
                        Análisis →
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Delta Map */}
      {session.laps.length > 0 && (
        <DeltaMap racingSessionId={session.id} />
      )}

      {/* Telemetry Panel */}
      {session.laps.length > 0 && (
        <TelemetryPanel racingSessionId={session.id} />
      )}
    </div>
  )
}
