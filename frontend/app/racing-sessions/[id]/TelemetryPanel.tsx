'use client'

import { useEffect, useState } from 'react'
import { getLapTelemetry, LapTelemetry } from '../../lib/api'
import SpeedChart from './SpeedChart'
import TrackHeatmap from './TrackHeatmap'
import GearMap from './GearMap'
import LapReplay from './LapReplay'

type Tab = 'trazas' | 'velocidad' | 'marchas' | 'replay'

interface Props {
  racingSessionId: string
}

export default function TelemetryPanel({ racingSessionId }: Props) {
  const [data, setData] = useState<LapTelemetry | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('trazas')

  useEffect(() => {
    getLapTelemetry(racingSessionId).then((d) => {
      setData(d)
      setLoading(false)
    })
  }, [racingSessionId])

  const tabs: { key: Tab; label: string }[] = [
    { key: 'trazas',    label: 'Trazas' },
    { key: 'velocidad', label: 'Velocidad' },
    { key: 'marchas',   label: 'Marchas' },
    { key: 'replay',    label: 'Replay' },
  ]

  return (
    <div className="border border-gray-800 mt-6">
      <div className="flex border-b border-gray-800">
        <span className="text-gray-600 text-xs uppercase tracking-wide px-4 py-3 self-center">Telemetría</span>
        <div className="flex ml-2">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-3 text-xs uppercase tracking-wide transition-colors ${
                tab === t.key
                  ? 'text-white border-b-2 border-f1red -mb-px'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-4">
        {loading && (
          <div className="text-gray-600 text-xs text-center py-10">Cargando telemetría...</div>
        )}
        {!loading && !data && (
          <div className="text-gray-600 text-xs text-center py-10">
            Sin telemetría disponible. Sube un CSV con datos de posición.
          </div>
        )}
        {data && (
          <>
            {tab === 'trazas'    && <SpeedChart points={data.points} lapTimeFmt={data.lap_time_fmt} />}
            {tab === 'velocidad' && <TrackHeatmap points={data.points} />}
            {tab === 'marchas'   && <GearMap points={data.points} />}
            {tab === 'replay'    && <LapReplay points={data.points} lapTimeFmt={data.lap_time_fmt} lapTime={data.lap_time} />}
          </>
        )}
      </div>
    </div>
  )
}
