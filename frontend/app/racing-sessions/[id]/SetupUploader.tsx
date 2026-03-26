'use client'

import { useRouter } from 'next/navigation'
import { useRef, useState } from 'react'
import { uploadSetup } from '../../lib/api'

export default function SetupUploader({
  racingSessionId,
  hasSetup,
}: {
  racingSessionId: string
  hasSetup: boolean
}) {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith('.ini')) {
      setError('Solo se aceptan archivos .ini')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await uploadSetup(racingSessionId, file)
      router.refresh()
      setDone(true)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error al subir setup')
    }
    setLoading(false)
  }

  return (
    <div className="border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-gray-500 text-xs uppercase tracking-wide">Setup (.ini)</p>
        {hasSetup && !done && (
          <span className="text-xs text-green-400">✓ Setup cargado</span>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".ini"
        className="hidden"
        onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]) }}
      />

      <button
        onClick={() => inputRef.current?.click()}
        disabled={loading}
        className="w-full border border-gray-700 hover:border-gray-500 text-gray-400 hover:text-white py-2 text-xs transition-colors disabled:opacity-40"
      >
        {loading ? 'Subiendo...' : hasSetup || done ? 'Reemplazar setup' : 'Subir setup AC (.ini)'}
      </button>

      {done && <p className="text-green-400 text-xs mt-2">✓ Setup actualizado — el reporte se regenerará</p>}
      {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
    </div>
  )
}
