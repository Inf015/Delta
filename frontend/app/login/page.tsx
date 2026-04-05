'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { login } from '../lib/api'
import { setToken, setEmail, setIsAdmin, setRole } from '../lib/auth'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmailInput] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const result = await login(email, password)
      setToken(result.access_token)
      setEmail(result.email)
      setIsAdmin(result.is_admin)
      setRole(result.role ?? 'pilot')
      if (result.is_admin) router.replace('/admin')
      else if (result.role === 'technician') router.replace('/technician')
      else router.replace('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al iniciar sesión')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm border border-gray-800 p-8">
        <div className="mb-8">
          <span className="text-f1red font-bold text-xl tracking-wider">DELTA</span>
          <h1 className="text-white font-bold text-lg mt-4">Iniciar sesión</h1>
          <p className="text-gray-500 text-sm mt-1">Accede a tu cuenta</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1.5">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmailInput(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:outline-none focus:border-f1red transition-colors"
              placeholder="tu@email.com"
            />
          </div>

          <div>
            <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1.5">
              Contraseña
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:outline-none focus:border-f1red transition-colors"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="text-f1red text-sm">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-f1red hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white py-2 text-sm font-bold uppercase tracking-wide transition-colors"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>

        <p className="text-gray-500 text-sm mt-6 text-center">
          ¿Sin cuenta?{' '}
          <Link href="/register" className="text-f1red hover:underline">
            Regístrate
          </Link>
        </p>
      </div>
    </div>
  )
}
