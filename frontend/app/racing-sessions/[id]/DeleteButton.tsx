'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { deleteRacingSession } from '../../lib/api'

export default function DeleteButton({ sessionId }: { sessionId: string }) {
  const router = useRouter()
  const [confirming, setConfirming] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleDelete() {
    setLoading(true)
    try {
      await deleteRacingSession(sessionId)
      router.push('/')
    } catch {
      setLoading(false)
      setConfirming(false)
    }
  }

  if (confirming) {
    return (
      <div className="flex gap-2">
        <button
          onClick={() => setConfirming(false)}
          className="border border-gray-700 text-gray-400 px-3 py-2 text-xs"
        >
          Cancelar
        </button>
        <button
          onClick={handleDelete}
          disabled={loading}
          className="bg-red-900 hover:bg-red-800 text-red-200 px-3 py-2 text-xs font-bold disabled:opacity-50"
        >
          {loading ? 'Borrando...' : '¿Confirmar borrado?'}
        </button>
      </div>
    )
  }

  return (
    <button
      onClick={() => setConfirming(true)}
      className="border border-gray-800 hover:border-red-900 text-gray-600 hover:text-red-500 px-3 py-2 text-xs transition-colors"
    >
      Borrar
    </button>
  )
}
