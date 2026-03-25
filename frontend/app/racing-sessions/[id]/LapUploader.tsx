'use client'

import { useRouter } from 'next/navigation'
import { useState, useRef, DragEvent } from 'react'
import { uploadCSVs } from '../../lib/api'

type FileStatus = 'pending' | 'uploading' | 'done' | 'error'

interface FileItem {
  file: File
  status: FileStatus
  error?: string
}

export default function LapUploader({ racingSessionId }: { racingSessionId: string }) {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [items, setItems] = useState<FileItem[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ uploaded: number; skipped: number; duplicate: number } | null>(null)

  function addFiles(files: FileList | File[]) {
    const newItems: FileItem[] = Array.from(files)
      .filter((f) => f.name.toLowerCase().endsWith('.csv'))
      .map((f) => ({ file: f, status: 'pending' }))
    setItems((prev) => [...prev, ...newItems])
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files)
  }

  function update(index: number, patch: Partial<FileItem>) {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, ...patch } : it)))
  }

  async function submit() {
    const pending = items.map((it, i) => ({ it, i })).filter(({ it }) => it.status === 'pending' || it.status === 'error')
    if (!pending.length) return

    setLoading(true)
    setResult(null)
    pending.forEach(({ i }) => update(i, { status: 'uploading', error: undefined }))
    try {
      const res = await uploadCSVs(pending.map(({ it }) => it.file), racingSessionId)
      pending.forEach(({ i }) => update(i, { status: 'done' }))
      setResult({ uploaded: res.laps_uploaded, skipped: res.laps_skipped, duplicate: res.laps_duplicate })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Error'
      pending.forEach(({ i }) => update(i, { status: 'error', error: msg }))
    }
    setLoading(false)
    router.refresh()
  }

  const pendingCount = items.filter((it) => it.status === 'pending' || it.status === 'error').length
  const doneCount = items.filter((it) => it.status === 'done').length

  return (
    <div className="border border-gray-800 p-4">
      <p className="text-gray-500 text-xs uppercase tracking-wide mb-3">Agregar vueltas</p>

      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`border-2 border-dashed cursor-pointer py-6 text-center transition-colors ${
          dragging ? 'border-f1red bg-red-950/20' : 'border-gray-700 hover:border-gray-600'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          multiple
          className="hidden"
          onChange={(e) => { if (e.target.files) addFiles(e.target.files) }}
        />
        <p className="text-gray-500 text-sm">Arrastra CSVs aquí o haz click</p>
        <p className="text-gray-700 text-xs mt-1">Múltiples archivos permitidos</p>
      </div>

      {items.length > 0 && (
        <div className="mt-3 space-y-1">
          {items.map((item, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <span className={`shrink-0 w-2 h-2 rounded-full ${
                item.status === 'done' ? 'bg-green-400' :
                item.status === 'error' ? 'bg-red-400' :
                item.status === 'uploading' ? 'bg-blue-400 animate-pulse' :
                'bg-gray-600'
              }`} />
              <span className="text-gray-400 truncate flex-1">{item.file.name}</span>
              {item.error && <span className="text-red-400 shrink-0">{item.error}</span>}
              {item.status === 'done' && <span className="text-green-400 shrink-0">✓</span>}
              {item.status === 'pending' && (
                <button onClick={() => setItems((p) => p.filter((_, j) => j !== i))} className="text-gray-600 hover:text-gray-400 shrink-0">✕</button>
              )}
            </div>
          ))}
        </div>
      )}

      {result && (
        <div className="mt-3 text-xs border border-gray-800 px-3 py-2 space-y-0.5">
          {result.uploaded > 0 && <p className="text-green-400">✓ {result.uploaded} vuelta{result.uploaded !== 1 ? 's' : ''} subida{result.uploaded !== 1 ? 's' : ''}</p>}
          {result.duplicate > 0 && <p className="text-yellow-500">⚠ {result.duplicate} duplicada{result.duplicate !== 1 ? 's' : ''} (ya existía{result.duplicate !== 1 ? 'n' : ''})</p>}
          {result.skipped > 0 && <p className="text-gray-500">✕ {result.skipped} rechazada{result.skipped !== 1 ? 's' : ''} (inválida{result.skipped !== 1 ? 's' : ''} o pit lap)</p>}
        </div>
      )}

      {items.length > 0 && (
        <button
          onClick={submit}
          disabled={!pendingCount || loading}
          className="mt-3 w-full bg-f1red hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed text-white py-2 font-bold text-xs transition-colors"
        >
          {loading ? `SUBIENDO ${doneCount}/${items.length}...` : `SUBIR ${pendingCount} VUELTA${pendingCount !== 1 ? 'S' : ''}`}
        </button>
      )}
    </div>
  )
}
