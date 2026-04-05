'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { getPilotSessions, getMyTeam, TeamSession, TeamPilot } from '../../../lib/api'

export default function TechPilotPage() {
  const { id } = useParams() as { id: string }
  const [pilot, setPilot]       = useState<TeamPilot | null>(null)
  const [sessions, setSessions] = useState<TeamSession[]>([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  useEffect(() => {
    async function load() {
      try {
        const [team, sess] = await Promise.all([getMyTeam(), getPilotSessions(id)])
        const p = team.pilots.find(p => p.id === id) || null
        setPilot(p)
        setSessions(sess)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error cargando datos')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  if (loading) return <div className="text-gray-600 text-sm py-12 text-center">Cargando...</div>
  if (error)   return <div className="text-red-400 text-sm py-12 text-center">{error}</div>

  return (
    <div>
      <div className="mb-8">
        <Link href="/technician" className="text-gray-500 text-xs hover:text-white inline-block mb-2">
          ← Equipo
        </Link>
        <h1 className="text-2xl font-bold text-white">{pilot?.name || pilot?.email || 'Piloto'}</h1>
        {pilot && <p className="text-gray-400 text-sm mt-1">{pilot.email} · Plan {pilot.plan}</p>}
      </div>

      <h2 className="text-white font-bold mb-4 border-b border-gray-800 pb-2">
        Sesiones ({sessions.length})
      </h2>

      {sessions.length === 0 ? (
        <p className="text-gray-600 text-sm">Sin sesiones todavía.</p>
      ) : (
        <div className="space-y-2">
          {sessions.map(s => (
            <div key={s.id} className="border border-gray-800 px-4 py-3 hover:border-gray-700 transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white text-sm font-medium">{s.track || s.name || 'Sin título'}</p>
                  <div className="flex gap-3 mt-1 text-gray-500 text-xs">
                    <span>{s.car || '—'}</span>
                    <span>{s.lap_count} vueltas</span>
                    <span>{s.session_date || '—'}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-green-400 text-xs font-bold font-mono">{s.best_lap_fmt}</span>
                  {s.has_report ? (
                    <Link
                      href={`/technician/sessions/${s.id}?pilot=${id}`}
                      className="text-blue-400 hover:text-blue-300 text-xs transition-colors"
                    >
                      Reporte →
                    </Link>
                  ) : (
                    <span className="text-gray-700 text-xs">Sin reporte</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
