'use client'

import { useEffect, useState, useMemo } from 'react'
import Link from 'next/link'
import { getRacingSessions, RacingSession } from './lib/api'

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(d: string | null) {
  if (!d) return null
  try {
    return new Date(d).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return d
  }
}

function trackInitials(track: string | null) {
  if (!track) return '???'
  const words = track.trim().split(/\s+/)
  if (words.length === 1) return words[0].slice(0, 3).toUpperCase()
  return words.slice(0, 3).map((w) => w[0]).join('').toUpperCase()
}

// ── Config maps ───────────────────────────────────────────────────────────────

const SIM_COLORS: Record<string, string> = {
  'assetto corsa': '#3b82f6',
  'ac':            '#3b82f6',
  'acc':           '#06b6d4',
  'assetto corsa competizione': '#06b6d4',
  'iracing':       '#f97316',
  'rfactor2':      '#22c55e',
  'rfactor 2':     '#22c55e',
  'ams2':          '#a855f7',
  'automobilista 2': '#a855f7',
  'lmu':           '#eab308',
  'le mans ultimate': '#eab308',
}

function simColor(sim: string | null) {
  if (!sim) return '#4b5563'
  return SIM_COLORS[sim.toLowerCase()] ?? '#4b5563'
}

const SESSION_TYPE_STYLES: Record<string, { label: string; className: string }> = {
  practice:   { label: 'Práctica',      className: 'bg-gray-800 text-gray-400 border-gray-700' },
  qualifying: { label: 'Clasificación', className: 'bg-yellow-950 text-yellow-400 border-yellow-900' },
  race:       { label: 'Carrera',       className: 'bg-red-950 text-red-400 border-red-900' },
  hotlap:     { label: 'Hot Lap',       className: 'bg-purple-950 text-purple-400 border-purple-900' },
}

// ── SessionCard ───────────────────────────────────────────────────────────────

function SessionCard({ s }: { s: RacingSession }) {
  const color = simColor(s.simulator)
  const typeStyle = s.session_type
    ? (SESSION_TYPE_STYLES[s.session_type] ?? { label: s.session_type, className: 'bg-gray-800 text-gray-400 border-gray-700' })
    : null
  const initials = trackInitials(s.track)

  return (
    <Link
      href={`/racing-sessions/${s.id}`}
      className="group border border-gray-800 hover:border-gray-600 bg-gray-950 hover:bg-gray-900 transition-all flex flex-col border-l-4"
      style={{ borderLeftColor: color }}
    >
      {/* Track header con iniciales de fondo */}
      <div className="relative px-5 pt-5 pb-3 border-b border-gray-800 overflow-hidden">
        {/* Iniciales decorativas */}
        <span
          className="absolute right-3 top-1/2 -translate-y-1/2 text-6xl font-black tracking-tighter pointer-events-none select-none"
          style={{ color: 'rgba(255,255,255,0.04)' }}
          aria-hidden
        >
          {initials}
        </span>

        <p className="text-xs text-gray-500 uppercase tracking-widest mb-1 relative">Circuito</p>
        <h2 className="text-lg font-bold text-white leading-tight group-hover:text-f1red transition-colors relative">
          {s.track || <span className="text-gray-600 italic">Sin pista</span>}
        </h2>
        {s.name && (
          <p className="text-xs text-gray-500 mt-1 truncate relative">{s.name}</p>
        )}
      </div>

      {/* Auto + badges */}
      <div className="px-5 py-4 flex-1 flex flex-col gap-3">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-widest mb-1">Auto</p>
          <p className="text-sm font-semibold text-gray-200">
            {s.car || <span className="text-gray-600 italic">—</span>}
          </p>
        </div>

        <div className="flex flex-wrap gap-2 mt-auto">
          {s.simulator && (
            <span
              className="text-xs px-2 py-0.5 border font-medium"
              style={{
                color: color,
                borderColor: color,
                backgroundColor: `${color}15`,
              }}
            >
              {s.simulator}
            </span>
          )}
          {typeStyle && (
            <span className={`text-xs px-2 py-0.5 border ${typeStyle.className}`}>
              {typeStyle.label}
            </span>
          )}
          {s.session_date && (
            <span className="text-xs text-gray-600 py-0.5">
              {fmtDate(s.session_date)}
            </span>
          )}
        </div>
      </div>

      {/* Stats footer */}
      <div className="px-5 py-3 border-t border-gray-800 flex items-center justify-between">
        <div className="flex gap-5">
          <div>
            <p className="text-xs text-gray-600 uppercase tracking-wide">Vueltas</p>
            <p className="text-base font-bold text-white">{s.lap_count}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600 uppercase tracking-wide">Mejor vuelta</p>
            <p
              className="text-base font-bold text-green-400"
              style={s.best_lap ? { textShadow: '0 0 12px rgba(74,222,128,0.5)' } : undefined}
            >
              {s.best_lap_fmt || '—'}
            </p>
          </div>
        </div>
        <span className="text-f1red text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity">
          ABRIR →
        </span>
      </div>
    </Link>
  )
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

type SortKey = 'date-desc' | 'date-asc' | 'track' | 'best-time'

export default function Dashboard() {
  const [sessions, setSessions] = useState<RacingSession[]>([])
  const [loading, setLoading] = useState(true)
  const [filterTrack, setFilterTrack] = useState('')
  const [filterCar, setFilterCar] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('date-desc')

  useEffect(() => {
    getRacingSessions().then(setSessions).finally(() => setLoading(false))
  }, [])

  // Conteo de sesiones por pista
  const trackCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    sessions.forEach((s) => { if (s.track) counts[s.track] = (counts[s.track] ?? 0) + 1 })
    return counts
  }, [sessions])

  const tracks = useMemo(() => {
    return Object.keys(trackCounts).sort()
  }, [trackCounts])

  // Autos disponibles (filtrados por pista seleccionada) con conteo
  const carCounts = useMemo(() => {
    const base = filterTrack ? sessions.filter((s) => s.track === filterTrack) : sessions
    const counts: Record<string, number> = {}
    base.forEach((s) => { if (s.car) counts[s.car] = (counts[s.car] ?? 0) + 1 })
    return counts
  }, [sessions, filterTrack])

  const cars = useMemo(() => Object.keys(carCounts).sort(), [carCounts])

  const filtered = useMemo(() => {
    let list = sessions.filter((s) => {
      if (filterTrack && s.track !== filterTrack) return false
      if (filterCar && s.car !== filterCar) return false
      return true
    })

    list = [...list].sort((a, b) => {
      if (sortKey === 'date-desc') return (b.session_date ?? '').localeCompare(a.session_date ?? '')
      if (sortKey === 'date-asc')  return (a.session_date ?? '').localeCompare(b.session_date ?? '')
      if (sortKey === 'track')     return (a.track ?? '').localeCompare(b.track ?? '')
      if (sortKey === 'best-time') {
        if (a.best_lap === null) return 1
        if (b.best_lap === null) return -1
        return a.best_lap - b.best_lap
      }
      return 0
    })

    return list
  }, [sessions, filterTrack, filterCar, sortKey])

  const hasFilters = filterTrack || filterCar

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Sesiones</h1>
          <p className="text-gray-500 text-sm mt-1">
            {loading
              ? '...'
              : hasFilters
              ? `${filtered.length} de ${sessions.length} sesión${sessions.length !== 1 ? 'es' : ''}`
              : `${sessions.length} sesión${sessions.length !== 1 ? 'es' : ''} registrada${sessions.length !== 1 ? 's' : ''}`}
          </p>
        </div>
        <Link
          href="/racing-sessions/new"
          className="bg-f1red hover:bg-red-700 text-white px-4 py-2 text-sm font-bold transition-colors"
        >
          + NUEVA SESIÓN
        </Link>
      </div>

      {/* Filtros + orden */}
      {!loading && sessions.length > 1 && (
        <div className="flex flex-wrap gap-3 mb-6 items-center">
          <select
            value={filterTrack}
            onChange={(e) => { setFilterTrack(e.target.value); setFilterCar('') }}
            className="bg-gray-900 border border-gray-700 text-sm text-gray-300 px-3 py-2 focus:border-gray-500 focus:outline-none min-w-[190px]"
          >
            <option value="">Todos los circuitos</option>
            {tracks.map((t) => (
              <option key={t} value={t}>{t} ({trackCounts[t]})</option>
            ))}
          </select>

          <select
            value={filterCar}
            onChange={(e) => setFilterCar(e.target.value)}
            className="bg-gray-900 border border-gray-700 text-sm text-gray-300 px-3 py-2 focus:border-gray-500 focus:outline-none min-w-[190px] disabled:opacity-40"
            disabled={cars.length === 0}
          >
            <option value="">Todos los autos</option>
            {cars.map((c) => (
              <option key={c} value={c}>{c} ({carCounts[c]})</option>
            ))}
          </select>

          {/* Separador visual */}
          <div className="h-6 w-px bg-gray-700 hidden sm:block" />

          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            className="bg-gray-900 border border-gray-700 text-sm text-gray-300 px-3 py-2 focus:border-gray-500 focus:outline-none"
          >
            <option value="date-desc">Más reciente primero</option>
            <option value="date-asc">Más antigua primero</option>
            <option value="track">Por circuito (A–Z)</option>
            <option value="best-time">Por mejor tiempo</option>
          </select>

          {hasFilters && (
            <button
              onClick={() => { setFilterTrack(''); setFilterCar('') }}
              className="text-xs text-gray-500 hover:text-white border border-gray-700 hover:border-gray-500 px-3 py-2 transition-colors"
            >
              Limpiar filtros ×
            </button>
          )}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="border border-gray-800 p-12 text-center">
          <p className="text-gray-600 text-sm">Cargando sesiones...</p>
        </div>
      ) : sessions.length === 0 ? (
        <div className="border border-gray-800 p-12 text-center">
          <p className="text-gray-500 mb-4">Sin sesiones todavía.</p>
          <Link href="/racing-sessions/new" className="text-f1red hover:underline text-sm">
            Subir tu primer CSV →
          </Link>
        </div>
      ) : filtered.length === 0 ? (
        <div className="border border-gray-800 p-12 text-center">
          <p className="text-gray-500 mb-3">Sin sesiones para estos filtros.</p>
          <button
            onClick={() => { setFilterTrack(''); setFilterCar('') }}
            className="text-f1red hover:underline text-sm"
          >
            Ver todas las sesiones
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((s) => (
            <SessionCard key={s.id} s={s} />
          ))}
        </div>
      )}
    </div>
  )
}
