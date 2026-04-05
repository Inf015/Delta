'use client'

import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { getPilotSessionReport } from '../../../lib/api'

export default function TechSessionReportPage() {
  const { id } = useParams() as { id: string }
  const searchParams = useSearchParams()
  const pilotId = searchParams.get('pilot') || ''

  const [report, setReport] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!pilotId) { setError('Piloto no especificado'); setLoading(false); return }
    getPilotSessionReport(pilotId, id)
      .then(r => setReport(r))
      .catch(err => setError(err instanceof Error ? err.message : 'Error cargando reporte'))
      .finally(() => setLoading(false))
  }, [id, pilotId])

  if (loading) return <div className="text-gray-600 text-sm py-12 text-center">Cargando reporte...</div>
  if (error)   return (
    <div className="py-12 text-center">
      <p className="text-red-400 text-sm mb-4">{error}</p>
      <Link href="/technician" className="text-blue-400 text-sm hover:underline">← Volver</Link>
    </div>
  )
  if (!report) return null

  const sections = Object.entries(report).filter(([k]) => k.startsWith('section_'))

  return (
    <div>
      <div className="mb-8">
        <Link href="/technician" className="text-gray-500 text-xs hover:text-white inline-block mb-2">
          ← Equipo
        </Link>
        <h1 className="text-2xl font-bold text-white">Reporte de sesión</h1>
      </div>

      <div className="space-y-6">
        {sections.map(([key, content]) => (
          <div key={key} className="border border-gray-800 p-5">
            <h2 className="text-gray-500 text-xs uppercase tracking-widest mb-3">
              {key.replace('section_', 'Sección ').replace('_', ' ')}
            </h2>
            <pre className="text-white text-sm whitespace-pre-wrap font-mono leading-relaxed">
              {typeof content === 'string' ? content : JSON.stringify(content, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  )
}
