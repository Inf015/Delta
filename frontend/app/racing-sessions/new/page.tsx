'use client'

import { useRouter } from 'next/navigation'
import { useState, useRef, DragEvent } from 'react'
import { previewCSV, createRacingSession, uploadCSVs, uploadSetup, CSVPreview } from '../../lib/api'

const SIMULATORS = ['AC', 'R3E']
const SESSION_TYPES = ['Practice', 'Qualify', 'Race']

export default function NewRacingSession() {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const setupRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [setupFile, setSetupFile] = useState<File | null>(null)
  const previewDone = useRef(false)

  const [form, setForm] = useState({
    name: '',
    track: '',
    car: '',
    simulator: 'AC',
    session_date: new Date().toISOString().slice(0, 10),
    session_type: 'Practice',
  })

  function set(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function addFiles(newFiles: File[]) {
    const csvs = newFiles.filter((f) => f.name.toLowerCase().endsWith('.csv'))
    if (!csvs.length) return

    if (!previewDone.current) {
      previewDone.current = true
      setPreviewing(true)
      try {
        const p: CSVPreview = await previewCSV(csvs[0])
        setForm((prev) => ({
          ...prev,
          track: p.track,
          car: p.car,
          simulator: p.simulator.toUpperCase(),
          session_date: p.session_date.slice(0, 10),
          session_type: p.session_type,
        }))
      } catch {
        previewDone.current = false
      } finally {
        setPreviewing(false)
      }
    }

    setFiles((prev) => [...prev, ...csvs])
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    if (e.dataTransfer.files.length) addFiles(Array.from(e.dataTransfer.files))
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')

    try {
      const rs = await createRacingSession({
        name: form.name || undefined,
        track: form.track || undefined,
        car: form.car || undefined,
        simulator: form.simulator,
        session_date: form.session_date,
        session_type: form.session_type,
      })

      if (files.length > 0) {
        await uploadCSVs(files, rs.id)
      }

      if (setupFile) {
        await uploadSetup(rs.id, setupFile)
      }

      router.push(`/racing-sessions/${rs.id}`)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error')
      setSaving(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto">
      <div className="mb-8">
        <a href="/" className="text-gray-500 text-xs hover:text-white inline-block mb-2">← Sesiones</a>
        <h1 className="text-2xl font-bold text-white">Nueva sesión</h1>
        <p className="text-gray-500 text-sm mt-1">
          Arrastra los CSVs para autocompletar. Todos los campos son opcionales.
        </p>
      </div>

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`border-2 border-dashed cursor-pointer p-8 text-center mb-6 transition-colors ${
          dragging ? 'border-f1red bg-red-950/20' : 'border-gray-800 hover:border-gray-600'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          multiple
          className="hidden"
          onChange={(e) => { if (e.target.files) addFiles(Array.from(e.target.files)) }}
        />
        {previewing ? (
          <p className="text-gray-400 text-sm">Leyendo CSV...</p>
        ) : files.length > 0 ? (
          <div>
            <p className="text-white font-bold text-sm">{files.length} vuelta{files.length !== 1 ? 's' : ''} en cola</p>
            <p className="text-gray-600 text-xs mt-1">Arrastra más para agregar</p>
          </div>
        ) : (
          <>
            <p className="text-gray-400 text-sm">Arrastra los CSVs de la sesión</p>
            <p className="text-gray-600 text-xs mt-1">Cada CSV = una vuelta · autocompleta el formulario</p>
          </>
        )}
      </div>

      {/* Files list */}
      {files.length > 0 && (
        <div className="mb-6 space-y-1">
          {files.map((f, i) => (
            <div key={i} className="flex items-center gap-2 text-xs border border-gray-900 px-3 py-1.5">
              <span className="w-2 h-2 rounded-full bg-gray-600 shrink-0" />
              <span className="text-gray-400 truncate flex-1">{f.name}</span>
              <button
                onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))}
                className="text-gray-700 hover:text-gray-400 shrink-0"
              >✕</button>
            </div>
          ))}
        </div>
      )}

      {/* Setup opcional */}
      <div className="mb-6">
        <input
          ref={setupRef}
          type="file"
          accept=".ini"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) setSetupFile(f)
          }}
        />
        <button
          type="button"
          onClick={() => setupRef.current?.click()}
          className={`w-full border border-dashed py-3 text-xs transition-colors ${
            setupFile
              ? 'border-green-700 text-green-400'
              : 'border-gray-800 text-gray-600 hover:border-gray-600 hover:text-gray-400'
          }`}
        >
          {setupFile ? `✓ Setup: ${setupFile.name}` : '+ Setup AC opcional (.ini) — mejora el análisis de Claude'}
        </button>
        {setupFile && (
          <button
            type="button"
            onClick={() => { setSetupFile(null); if (setupRef.current) setupRef.current.value = '' }}
            className="text-gray-700 hover:text-gray-500 text-xs mt-1"
          >
            ✕ quitar setup
          </button>
        )}
      </div>

      {/* Form */}
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Nombre de sesión <span className="text-gray-700">(opcional)</span></label>
          <input
            value={form.name}
            onChange={(e) => set('name', e.target.value)}
            placeholder="ej. Entreno tarde — Suzuka"
            className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Pista</label>
            <input
              value={form.track}
              onChange={(e) => set('track', e.target.value)}
              placeholder="ej. Monza"
              className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
            />
          </div>

          <div className="col-span-2">
            <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Auto</label>
            <input
              value={form.car}
              onChange={(e) => set('car', e.target.value)}
              placeholder="ej. Ferrari 488 GT3"
              className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
            />
          </div>

          <div>
            <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Simulador</label>
            <select
              value={form.simulator}
              onChange={(e) => set('simulator', e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
            >
              {SIMULATORS.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Tipo</label>
            <select
              value={form.session_type}
              onChange={(e) => set('session_type', e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
            >
              {SESSION_TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>

          <div className="col-span-2">
            <label className="block text-gray-500 text-xs uppercase tracking-wide mb-1">Fecha</label>
            <input
              value={form.session_date}
              onChange={(e) => set('session_date', e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-f1red outline-none"
            />
          </div>
        </div>

        {error && (
          <p className="text-f1red text-sm border border-f1red/30 px-3 py-2">{error}</p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="w-full bg-f1red hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed text-white py-3 font-bold text-sm transition-colors"
        >
          {saving
            ? 'CREANDO...'
            : files.length > 0
            ? `CREAR SESIÓN Y SUBIR ${files.length} VUELTA${files.length !== 1 ? 'S' : ''}${setupFile ? ' + SETUP' : ''}`
            : 'CREAR SESIÓN'}
        </button>
      </form>
    </div>
  )
}
