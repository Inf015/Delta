'use client'

import { useRef, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { uploadTrackMap, trackMapUrl } from '../../lib/api'

interface Props {
  racingSessionId: string
  hasMap: boolean
}

export default function MapUploader({ racingSessionId, hasMap }: Props) {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(hasMap)

  useEffect(() => {
    // Probar si ya existe un mapa usando GET con auth
    const token = typeof window !== 'undefined' ? localStorage.getItem('delta_token') : null
    fetch(trackMapUrl(racingSessionId), {
      method: 'GET',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
      .then((r) => { if (r.ok) setDone(true) })
      .catch(() => {})
  }, [racingSessionId])

  async function handleFile(file: File) {
    setUploading(true)
    setError('')
    try {
      await uploadTrackMap(racingSessionId, file)
      setDone(true)
      router.refresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept=".png,.jpg,.jpeg,.svg,.webp"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
      />
      <button
        type="button"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
        className={`w-full border border-dashed py-3 text-xs transition-colors disabled:opacity-40 ${
          done
            ? 'border-blue-700 text-blue-400'
            : 'border-gray-800 text-gray-600 hover:border-gray-600 hover:text-gray-400'
        }`}
      >
        {uploading
          ? 'Subiendo mapa...'
          : done
          ? '✓ Mapa del circuito cargado'
          : '+ Mapa del circuito (PNG/JPG/SVG — opcional)'}
      </button>
      {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
      {done && (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="text-gray-700 hover:text-gray-500 text-xs mt-1"
        >
          ↺ cambiar mapa
        </button>
      )}
    </div>
  )
}
