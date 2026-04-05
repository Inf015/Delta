'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { adminGetStats, adminListUsers, adminUpdateUser, AdminUser, AdminStats } from '../lib/api'
import { getIsAdmin } from '../lib/auth'

const PLAN_COLORS: Record<string, string> = {
  free:  'text-gray-400',
  pro:   'text-blue-400',
  team:  'text-purple-400',
}

const PLAN_LABELS: Record<string, string> = {
  free: 'Free',
  pro:  'Pro',
  team: 'Team',
}

const ROLE_COLORS: Record<string, string> = {
  pilot:      'text-gray-400',
  technician: 'text-blue-400',
}

export default function AdminPage() {
  const router = useRouter()
  const [stats, setStats]   = useState<AdminStats | null>(null)
  const [users, setUsers]   = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [updating, setUpdating] = useState<string | null>(null)

  useEffect(() => {
    if (!getIsAdmin()) { router.replace('/'); return }
    load()
  }, [])

  async function load() {
    setLoading(true)
    const [s, u] = await Promise.all([adminGetStats(), adminListUsers()])
    setStats(s)
    setUsers(u)
    setLoading(false)
  }

  async function toggleActive(user: AdminUser) {
    setUpdating(user.id)
    try {
      const updated = await adminUpdateUser(user.id, { is_active: !user.is_active })
      setUsers(prev => prev.map(u => u.id === user.id ? updated : u))
    } finally {
      setUpdating(null)
    }
  }

  async function changePlan(user: AdminUser, plan: string) {
    setUpdating(user.id)
    try {
      const updated = await adminUpdateUser(user.id, { plan })
      setUsers(prev => prev.map(u => u.id === user.id ? updated : u))
    } finally {
      setUpdating(null)
    }
  }

  async function changeRole(user: AdminUser, role: string) {
    setUpdating(user.id)
    try {
      const updated = await adminUpdateUser(user.id, { role })
      setUsers(prev => prev.map(u => u.id === user.id ? updated : u))
    } finally {
      setUpdating(null)
    }
  }

  const filtered = users.filter(u =>
    u.email.toLowerCase().includes(search.toLowerCase()) ||
    u.name.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) return <div className="text-gray-600 text-sm py-12 text-center">Cargando...</div>

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-widest mb-1">Back Office</p>
          <h1 className="text-2xl font-bold text-white">Administración</h1>
        </div>
        <Link
          href="/admin/users/new"
          className="bg-f1red hover:bg-red-700 text-white px-4 py-2 text-sm font-bold transition-colors"
        >
          + Nuevo usuario
        </Link>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard label="Usuarios" value={stats.total_users} sub={`${stats.active_users} activos`} />
          <StatCard label="Sesiones" value={stats.total_racing_sessions} />
          <StatCard label="Vueltas" value={stats.total_laps} />
          <StatCard label="Tokens IA" value={stats.total_tokens.toLocaleString()} color="text-blue-400" />
        </div>
      )}

      {/* Plan breakdown */}
      {stats && (
        <div className="flex gap-6 mb-8 border border-gray-800 px-5 py-3">
          {Object.entries(stats.users_by_plan).map(([plan, count]) => (
            <div key={plan} className="flex items-center gap-2">
              <span className={`text-xs font-bold uppercase ${PLAN_COLORS[plan] || 'text-gray-400'}`}>
                {PLAN_LABELS[plan] || plan}
              </span>
              <span className="text-white font-bold">{count}</span>
            </div>
          ))}
        </div>
      )}

      {/* Search */}
      <input
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Buscar por email o nombre..."
        className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none mb-4"
      />

      {/* Users table */}
      <div className="border border-gray-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
              <th className="text-left px-4 py-3">Piloto</th>
              <th className="text-center px-4 py-3">Plan</th>
              <th className="text-center px-4 py-3">Rol</th>
              <th className="text-right px-4 py-3">Sesiones</th>
              <th className="text-right px-4 py-3">Vueltas</th>
              <th className="text-right px-4 py-3">Tokens</th>
              <th className="text-right px-4 py-3">Análisis</th>
              <th className="text-center px-4 py-3">Estado</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((u, i) => (
              <tr
                key={u.id}
                className={`border-b border-gray-900 ${i % 2 === 0 ? '' : 'bg-gray-950'} hover:bg-gray-900 transition-colors`}
              >
                <td className="px-4 py-3">
                  <div>
                    <p className="text-white font-medium">
                      {u.name || '—'}
                      {u.is_admin && <span className="ml-2 text-xs text-f1red font-bold">ADMIN</span>}
                      {u.role === 'technician' && <span className="ml-2 text-xs text-blue-400 font-bold">TÉCNICO</span>}
                    </p>
                    <p className="text-gray-500 text-xs">{u.email}</p>
                  </div>
                </td>
                <td className="px-4 py-3 text-center">
                  <select
                    value={u.plan}
                    disabled={updating === u.id}
                    onChange={e => changePlan(u, e.target.value)}
                    className={`bg-transparent text-xs font-bold uppercase border-0 outline-none cursor-pointer ${PLAN_COLORS[u.plan] || 'text-gray-400'} disabled:opacity-40`}
                  >
                    <option value="free">Free</option>
                    <option value="pro">Pro</option>
                    <option value="team">Team</option>
                  </select>
                </td>
                <td className="px-4 py-3 text-center">
                  <select
                    value={u.role}
                    disabled={updating === u.id}
                    onChange={e => changeRole(u, e.target.value)}
                    className={`bg-transparent text-xs font-bold uppercase border-0 outline-none cursor-pointer ${ROLE_COLORS[u.role] || 'text-gray-400'} disabled:opacity-40`}
                  >
                    <option value="pilot">Piloto</option>
                    <option value="technician">Técnico</option>
                  </select>
                </td>
                <td className="px-4 py-3 text-right text-gray-300">{u.racing_sessions}</td>
                <td className="px-4 py-3 text-right text-gray-300">{u.laps_total}</td>
                <td className="px-4 py-3 text-right text-gray-500 text-xs">{u.tokens_used.toLocaleString()}</td>
                <td className="px-4 py-3 text-right text-gray-400 text-xs">
                  {u.analyses_used}/{u.analyses_limit}
                </td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => toggleActive(u)}
                    disabled={updating === u.id}
                    className={`text-xs px-2 py-0.5 border transition-colors disabled:opacity-40 ${
                      u.is_active
                        ? 'border-green-800 text-green-400 hover:border-red-800 hover:text-red-400'
                        : 'border-red-900 text-red-500 hover:border-green-800 hover:text-green-400'
                    }`}
                  >
                    {u.is_active ? 'Activo' : 'Inactivo'}
                  </button>
                </td>
                <td className="px-4 py-3 text-right">
                  <Link
                    href={`/admin/users/${u.id}`}
                    className="text-gray-500 hover:text-white text-xs transition-colors"
                  >
                    Ver →
                  </Link>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-600 text-sm">
                  No hay usuarios que coincidan.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatCard({ label, value, sub, color }: { label: string; value: number | string; sub?: string; color?: string }) {
  return (
    <div className="border border-gray-800 p-4">
      <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color || 'text-white'}`}>{value}</p>
      {sub && <p className="text-gray-600 text-xs mt-1">{sub}</p>}
    </div>
  )
}
