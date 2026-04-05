'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  getMyTeam, createTeam, addPilotToTeam, removePilotFromTeam, getTeamSessions,
  TeamInfo, TeamSession,
} from '../lib/api'
import { getIsTechnician, getIsAdmin } from '../lib/auth'

export default function TechnicianPage() {
  const router = useRouter()
  const [team, setTeam]         = useState<TeamInfo | null>(null)
  const [sessions, setSessions] = useState<TeamSession[]>([])
  const [loading, setLoading]   = useState(true)
  const [noTeam, setNoTeam]     = useState(false)

  // crear equipo
  const [teamName, setTeamName] = useState('')
  const [creating, setCreating] = useState(false)

  // agregar piloto
  const [pilotEmail, setPilotEmail] = useState('')
  const [adding, setAdding]         = useState(false)
  const [addError, setAddError]     = useState('')

  const [activeTab, setActiveTab] = useState<'sessions' | 'pilots'>('sessions')

  useEffect(() => {
    if (!getIsTechnician() && !getIsAdmin()) { router.replace('/'); return }
    load()
  }, [])

  async function load() {
    setLoading(true)
    try {
      const [t, s] = await Promise.all([getMyTeam(), getTeamSessions()])
      setTeam(t)
      setSessions(s)
    } catch (err: unknown) {
      if (err instanceof Error && err.message.includes('No tienes un equipo')) {
        setNoTeam(true)
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateTeam(e: React.FormEvent) {
    e.preventDefault()
    if (!teamName.trim()) return
    setCreating(true)
    try {
      const t = await createTeam(teamName.trim())
      setTeam(t)
      setNoTeam(false)
      setSessions([])
    } finally {
      setCreating(false)
    }
  }

  async function handleAddPilot(e: React.FormEvent) {
    e.preventDefault()
    if (!pilotEmail.trim()) return
    setAdding(true)
    setAddError('')
    try {
      const pilot = await addPilotToTeam(pilotEmail.trim())
      setTeam(prev => prev ? { ...prev, pilots: [...prev.pilots, pilot] } : prev)
      setPilotEmail('')
      // recargar sesiones
      const s = await getTeamSessions()
      setSessions(s)
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Error al agregar piloto')
    } finally {
      setAdding(false)
    }
  }

  async function handleRemovePilot(pilotId: string) {
    if (!confirm('¿Quitar piloto del equipo?')) return
    await removePilotFromTeam(pilotId)
    setTeam(prev => prev ? { ...prev, pilots: prev.pilots.filter(p => p.id !== pilotId) } : prev)
    setSessions(prev => prev.filter(s => {
      const pilot = team?.pilots.find(p => p.id === pilotId)
      return pilot ? s.pilot_email !== pilot.email : true
    }))
  }

  if (loading) return <div className="text-gray-600 text-sm py-12 text-center">Cargando...</div>

  // Sin equipo → formulario de creación
  if (noTeam) {
    return (
      <div className="max-w-md mx-auto py-16">
        <p className="text-gray-500 text-xs uppercase tracking-widest mb-1">Técnico de equipo</p>
        <h1 className="text-2xl font-bold text-white mb-2">Crear tu equipo</h1>
        <p className="text-gray-500 text-sm mb-8">
          Crea un equipo para empezar a monitorear a tus pilotos.
        </p>
        <form onSubmit={handleCreateTeam} className="space-y-4">
          <div>
            <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Nombre del equipo</label>
            <input
              required
              value={teamName}
              onChange={e => setTeamName(e.target.value)}
              placeholder="Ej: Scuderia Delta"
              className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-blue-500 outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={creating}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white py-2.5 font-bold text-sm transition-colors"
          >
            {creating ? 'CREANDO...' : 'CREAR EQUIPO'}
          </button>
        </form>
      </div>
    )
  }

  if (!team) return null

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-widest mb-1">Técnico de equipo</p>
          <h1 className="text-2xl font-bold text-white">{team.name}</h1>
          <p className="text-gray-500 text-sm mt-1">{team.pilots.length} pilotos · {sessions.length} sesiones</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-gray-800">
        {(['sessions', 'pilots'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-bold uppercase tracking-wide transition-colors border-b-2 -mb-px ${
              activeTab === tab
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-500 hover:text-white'
            }`}
          >
            {tab === 'sessions' ? `Sesiones (${sessions.length})` : `Pilotos (${team.pilots.length})`}
          </button>
        ))}
      </div>

      {activeTab === 'sessions' && (
        <div>
          {sessions.length === 0 ? (
            <p className="text-gray-600 text-sm">Sin sesiones todavía. Agrega pilotos a tu equipo.</p>
          ) : (
            <div className="border border-gray-800">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
                    <th className="text-left px-4 py-3">Piloto</th>
                    <th className="text-left px-4 py-3">Circuito</th>
                    <th className="text-left px-4 py-3">Coche</th>
                    <th className="text-right px-4 py-3">Vueltas</th>
                    <th className="text-right px-4 py-3">Mejor vuelta</th>
                    <th className="text-right px-4 py-3">Fecha</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((s, i) => (
                    <tr
                      key={s.id}
                      className={`border-b border-gray-900 ${i % 2 === 0 ? '' : 'bg-gray-950'} hover:bg-gray-900 transition-colors`}
                    >
                      <td className="px-4 py-3">
                        <p className="text-white font-medium text-xs">{s.pilot_name}</p>
                        <p className="text-gray-500 text-xs">{s.pilot_email}</p>
                      </td>
                      <td className="px-4 py-3 text-gray-300">{s.track || '—'}</td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{s.car || '—'}</td>
                      <td className="px-4 py-3 text-right text-gray-300">{s.lap_count}</td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-green-400 font-bold text-xs font-mono">{s.best_lap_fmt}</span>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-500 text-xs">{s.session_date || '—'}</td>
                      <td className="px-4 py-3 text-right">
                        {s.has_report ? (
                          <Link
                            href={`/technician/sessions/${s.id}?pilot=${team.pilots.find(p => p.email === s.pilot_email)?.id}&name=${encodeURIComponent(s.pilot_name)}`}
                            className="text-blue-400 hover:text-blue-300 text-xs transition-colors"
                          >
                            Reporte →
                          </Link>
                        ) : (
                          <span className="text-gray-700 text-xs">Sin reporte</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'pilots' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Lista de pilotos */}
          <div>
            <h2 className="text-white font-bold mb-4 border-b border-gray-800 pb-2">Pilotos del equipo</h2>
            {team.pilots.length === 0 ? (
              <p className="text-gray-600 text-sm">Sin pilotos todavía.</p>
            ) : (
              <div className="space-y-2">
                {team.pilots.map(p => (
                  <div key={p.id} className="border border-gray-800 px-4 py-3 flex items-center justify-between hover:border-gray-700 transition-colors">
                    <div>
                      <p className="text-white font-medium text-sm">{p.name || p.email}</p>
                      <p className="text-gray-500 text-xs">{p.email} · {p.racing_sessions} sesiones · {p.plan}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <Link
                        href={`/technician/pilots/${p.id}`}
                        className="text-blue-400 hover:text-blue-300 text-xs transition-colors"
                      >
                        Ver →
                      </Link>
                      <button
                        onClick={() => handleRemovePilot(p.id)}
                        className="text-gray-600 hover:text-red-400 text-xs transition-colors"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Agregar piloto */}
          <div>
            <h2 className="text-white font-bold mb-4 border-b border-gray-800 pb-2">Agregar piloto</h2>
            <form onSubmit={handleAddPilot} className="space-y-3">
              <div>
                <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Email del piloto</label>
                <input
                  type="email"
                  required
                  value={pilotEmail}
                  onChange={e => setPilotEmail(e.target.value)}
                  placeholder="piloto@ejemplo.com"
                  className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-blue-500 outline-none"
                />
              </div>
              {addError && (
                <p className="text-red-400 text-sm border border-red-400/30 px-3 py-2">{addError}</p>
              )}
              <button
                type="submit"
                disabled={adding}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white py-2.5 font-bold text-sm transition-colors"
              >
                {adding ? 'AGREGANDO...' : 'AGREGAR PILOTO'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
