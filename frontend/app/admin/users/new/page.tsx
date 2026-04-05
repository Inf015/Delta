'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { adminCreateUser } from '../../../lib/api'

export default function NewUserPage() {
  const router = useRouter()
  const [form, setForm] = useState({
    email: '',
    password: '',
    name: '',
    plan: 'free',
    role: 'pilot',
    is_admin: false,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState('')

  function set(field: string, value: string | boolean) {
    setForm(f => ({ ...f, [field]: value }))
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await adminCreateUser(form)
      router.push('/admin')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear usuario')
      setSaving(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto">
      <div className="mb-8">
        <Link href="/admin" className="text-gray-500 text-xs hover:text-white inline-block mb-2">
          ← Admin
        </Link>
        <h1 className="text-2xl font-bold text-white">Nuevo usuario</h1>
        <p className="text-gray-500 text-sm mt-1">Crear cuenta desde el back office.</p>
      </div>

      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Email</label>
          <input
            type="email"
            required
            value={form.email}
            onChange={e => set('email', e.target.value)}
            placeholder="piloto@ejemplo.com"
            className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
          />
        </div>

        <div>
          <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Contraseña</label>
          <input
            type="password"
            required
            minLength={8}
            value={form.password}
            onChange={e => set('password', e.target.value)}
            placeholder="Mínimo 8 caracteres"
            className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
          />
        </div>

        <div>
          <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">
            Nombre <span className="text-gray-700">(opcional)</span>
          </label>
          <input
            value={form.name}
            onChange={e => set('name', e.target.value)}
            placeholder="Oliver Infante"
            className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
          />
        </div>

        <div>
          <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Plan</label>
          <select
            value={form.plan}
            onChange={e => set('plan', e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
          >
            <option value="free">Free — 3 análisis/mes</option>
            <option value="pro">Pro — 30 análisis/mes</option>
            <option value="team">Team — 100 análisis/mes</option>
          </select>
        </div>

        <div>
          <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Rol</label>
          <select
            value={form.role}
            onChange={e => set('role', e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
          >
            <option value="pilot">Piloto</option>
            <option value="technician">Técnico de equipo</option>
          </select>
        </div>

        <div className="flex items-center gap-3 border border-gray-800 px-4 py-3">
          <input
            type="checkbox"
            id="is_admin"
            checked={form.is_admin}
            onChange={e => set('is_admin', e.target.checked)}
            className="accent-f1red"
          />
          <label htmlFor="is_admin" className="text-gray-300 text-sm cursor-pointer">
            Permisos de administrador
          </label>
        </div>

        {error && (
          <p className="text-f1red text-sm border border-f1red/30 px-3 py-2">{error}</p>
        )}

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="flex-1 bg-f1red hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed text-white py-3 font-bold text-sm transition-colors"
          >
            {saving ? 'CREANDO...' : 'CREAR USUARIO'}
          </button>
          <Link
            href="/admin"
            className="border border-gray-700 hover:border-gray-500 text-gray-400 hover:text-white px-6 py-3 text-sm transition-colors flex items-center"
          >
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  )
}
