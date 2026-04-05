'use client'

import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { getPilotSessionReport, SessionReport } from '../../../lib/api'
import ReportView from '../../../components/ReportView'

export default function TechSessionReportPage() {
  const { id } = useParams() as { id: string }
  const searchParams = useSearchParams()
  const pilotId   = searchParams.get('pilot') || ''
  const pilotName = searchParams.get('name')  || undefined

  const [report, setReport]   = useState<SessionReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  useEffect(() => {
    if (!pilotId) { setError('Piloto no especificado'); setLoading(false); return }
    getPilotSessionReport(pilotId, id)
      .then(r => setReport(r as unknown as SessionReport))
      .catch(err => setError(err instanceof Error ? err.message : 'Error cargando reporte'))
      .finally(() => setLoading(false))
  }, [id, pilotId])

  if (loading) return <div className="text-gray-600 text-sm py-12 text-center">Cargando reporte...</div>
  if (error) return (
    <div className="py-12 text-center">
      <p className="text-red-400 text-sm mb-4">{error}</p>
      <Link href="/technician" className="text-blue-400 text-sm hover:underline">← Volver</Link>
    </div>
  )
  if (!report) return null

  return (
    <ReportView
      report={report}
      sessionId={id}
      backHref="/technician"
      backLabel="← Equipo"
      pilotName={pilotName}
    />
  )
}
