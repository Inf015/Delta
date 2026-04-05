'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { adminListUsers, adminUpdateUser, adminGetUserSessions, AdminUser, AdminSession } from '../../../lib/api'
import { getIsAdmin } from '../../../lib/auth'

const PLAN_COLORS: Record<string, string> = {
  free:  'text-gray-400',
  pro:   'text-blue-400',
  team:  'text-purple-400',
}

export default function UserDetailPage() {
  const { id } = useParams() as { id: string }
  const router  = useRouter()

  const [user, setUser]         = useState<AdminUser | null>(null)
  const [sessions, setSessions] = useState<AdminSession[]>([])
  const [loading, setLoading]   = useState(true)
  const [saving, setSaving]     = useState(false)
  const [error, setError]       = useState('')

  // Edit form state
  const [editName, setEditName]     = useState('')
  const [editPlan, setEditPlan]     = useState('free')
  const [editRole, setEditRole]     = useState('pilot')
  const [editAdmin, setEditAdmin]   = useState(false)
  const [editActive, setEditActive] = useState(true)
  const [newPass, setNewPass]       = useState('')

  useEffect(() => {
    if (!getIsAdmin()) { router.replace('/'); return }
    load()
  }, [id])

  async function load() {
    setLoading(true)
    const [allUsers, userSessions] = await Promise.all([
      adminListUsers(),
      adminGetUserSessions(id),
    ])
    const found = allUsers.find(u => u.id === id) || null
    setUser(found)
    setSessions(userSessions)
    if (found) {
      setEditName(found.name)
      setEditPlan(found.plan)
      setEditRole(found.role ?? 'pilot')
      setEditAdmin(found.is_admin)
      setEditActive(found.is_active)
    }
    setLoading(false)
  }

  async function saveChanges(e: React.FormEvent) {
    e.preventDefault()
    if (!user) return
    setSaving(true)
    setError('')
    try {
      const payload: Record<string, unknown> = {
        name:      editName,
        plan:      editPlan,
        role:      editRole,
        is_admin:  editAdmin,
        is_active: editActive,
      }
      if (newPass) payload.password = newPass
      const updated = await adminUpdateUser(user.id, payload)
      setUser(updated)
      setNewPass('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="text-gray-600 text-sm py-12 text-center">Cargando...</div>
  if (!user)   return <div className="text-gray-500 text-sm py-12 text-center">Usuario no encontrado.</div>

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <Link href="/admin" className="text-gray-500 text-xs hover:text-white inline-block mb-2">
          ← Admin
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">
              {user.name || user.email}
              {user.is_admin && <span className="ml-3 text-sm text-f1red font-bold">ADMIN</span>}
              {user.role === 'technician' && <span className="ml-3 text-sm text-blue-400 font-bold">TÉCNICO</span>}
            </h1>
            <p className="text-gray-400 text-sm mt-1">{user.email}</p>
          </div>
          <span className={`text-sm font-bold uppercase ${PLAN_COLORS[user.plan] || 'text-gray-400'}`}>
            {user.plan}
          </span>
        </div>
      </div>

      {/* Stats del piloto */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="border border-gray-800 p-4">
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Sesiones</p>
          <p className="text-2xl font-bold text-white">{user.racing_sessions}</p>
        </div>
        <div className="border border-gray-800 p-4">
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Vueltas</p>
          <p className="text-2xl font-bold text-white">{user.laps_total}</p>
        </div>
        <div className="border border-gray-800 p-4">
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Tokens IA</p>
          <p className="text-2xl font-bold text-blue-400">{user.tokens_used.toLocaleString()}</p>
        </div>
        <div className="border border-gray-800 p-4">
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Análisis mes</p>
          <p className="text-2xl font-bold text-white">{user.analyses_used}/{user.analyses_limit}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Edit form */}
        <div>
          <h2 className="text-white font-bold mb-4 border-b border-gray-800 pb-2">Editar usuario</h2>
          <form onSubmit={saveChanges} className="space-y-4">
            <div>
              <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Nombre</label>
              <input
                value={editName}
                onChange={e => setEditName(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
              />
            </div>

            <div>
              <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Plan</label>
              <select
                value={editPlan}
                onChange={e => setEditPlan(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
              >
                <option value="free">Free</option>
                <option value="pro">Pro</option>
                <option value="team">Team</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Rol</label>
              <select
                value={editRole}
                onChange={e => setEditRole(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
              >
                <option value="pilot">Piloto</option>
                <option value="technician">Técnico de equipo</option>
              </select>
            </div>

            <div className="flex items-center gap-3 border border-gray-800 px-4 py-3">
              <input
                type="checkbox"
                id="edit_admin"
                checked={editAdmin}
                onChange={e => setEditAdmin(e.target.checked)}
                className="accent-f1red"
              />
              <label htmlFor="edit_admin" className="text-gray-300 text-sm cursor-pointer">
                Permisos de administrador
              </label>
            </div>

            <div className="flex items-center gap-3 border border-gray-800 px-4 py-3">
              <input
                type="checkbox"
                id="edit_active"
                checked={editActive}
                onChange={e => setEditActive(e.target.checked)}
                className="accent-f1red"
              />
              <label htmlFor="edit_active" className="text-gray-300 text-sm cursor-pointer">
                Cuenta activa
              </label>
            </div>

            <div>
              <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">
                Nueva contraseña <span className="text-gray-700">(dejar vacío para no cambiar)</span>
              </label>
              <input
                type="password"
                minLength={8}
                value={newPass}
                onChange={e => setNewPass(e.target.value)}
                placeholder="Mínimo 8 caracteres"
                className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
              />
            </div>

            {error && (
              <p className="text-f1red text-sm border border-f1red/30 px-3 py-2">{error}</p>
            )}

            <button
              type="submit"
              disabled={saving}
              className="w-full bg-f1red hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed text-white py-2.5 font-bold text-sm transition-colors"
            >
              {saving ? 'GUARDANDO...' : 'GUARDAR CAMBIOS'}
            </button>
          </form>
        </div>

        {/* Sessions list */}
        <div>
          <h2 className="text-white font-bold mb-4 border-b border-gray-800 pb-2">
            Sesiones ({sessions.length})
          </h2>
          {sessions.length === 0 ? (
            <p className="text-gray-600 text-sm">Sin sesiones todavía.</p>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {sessions.map(s => (
                <div key={s.id} className="border border-gray-800 px-4 py-3 hover:border-gray-700 transition-colors">
                  <div className="flex items-center justify-between">
                    <p className="text-white text-sm font-medium">
                      {s.track || s.name || 'Sin título'}
                    </p>
                    <span className="text-green-400 text-xs font-bold">{s.best_lap_fmt}</span>
                  </div>
                  <div className="flex gap-3 mt-1 text-gray-500 text-xs">
                    <span>{s.car || '—'}</span>
                    <span>{s.lap_count} vueltas</span>
                    <span>{s.session_date || '—'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
