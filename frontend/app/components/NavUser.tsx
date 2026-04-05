'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getEmail, removeToken } from '../lib/auth'

export default function NavUser() {
  const router = useRouter()
  const [email, setEmail] = useState<string | null>(null)

  useEffect(() => {
    setEmail(getEmail())
  }, [])

  function handleLogout() {
    removeToken()
    router.push('/login')
  }

  if (!email) return null

  return (
    <div className="ml-auto flex items-center gap-4">
      <span className="text-gray-500 text-xs">{email}</span>
      <button
        onClick={handleLogout}
        className="text-gray-400 hover:text-white text-xs uppercase tracking-wide transition-colors"
      >
        Salir
      </button>
    </div>
  )
}
