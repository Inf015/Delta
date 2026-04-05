'use client'

import { useEffect, useRef, useState } from 'react'
import { getDeltaMap, getRacingSessions, DeltaMap, DeltaPoint, RacingSession } from '../../lib/api'

interface Props {
  racingSessionId: string
}

function deltaColor(delta_norm: number): string {
  const abs = Math.min(Math.abs(delta_norm), 1)
  // Minimum brightness 160 so even small deltas are visible
  const base = 160
  const bright = Math.round(base + (255 - base) * abs)
  if (delta_norm > 0.04)  return `rgb(0, ${bright}, 60)`        // green — A faster
  if (delta_norm < -0.04) return `rgb(${bright}, 30, 30)`       // red   — B faster
  return 'rgb(90, 90, 90)'                                        // neutral gray
}

function fmtDelta(seconds: number): string {
  const sign = seconds >= 0 ? '+' : ''
  return `${sign}${seconds.toFixed(3)}s`
}

function drawDeltaMap(canvas: HTMLCanvasElement, points: DeltaPoint[]) {
  const ctx = canvas.getContext('2d')
  if (!ctx || points.length < 2) return

  const W = canvas.width
  const H = canvas.height
  const PAD = 36

  ctx.clearRect(0, 0, W, H)
  ctx.fillStyle = '#111'
  ctx.fillRect(0, 0, W, H)

  // Bounds — flip Z so north is up
  const xs = points.map((p) => p.x)
  const zs = points.map((p) => -p.z)
  const xMin = Math.min(...xs), xMax = Math.max(...xs)
  const zMin = Math.min(...zs), zMax = Math.max(...zs)
  const xRange = xMax - xMin || 1
  const zRange = zMax - zMin || 1

  const scale = Math.min((W - PAD * 2) / xRange, (H - PAD * 2) / zRange)
  const offX = (W - xRange * scale) / 2 - xMin * scale
  const offZ = (H - zRange * scale) / 2 - zMin * scale

  function toCanvas(x: number, z: number): [number, number] {
    return [x * scale + offX, (-z) * scale + offZ]
  }

  const allPts = [...points, points[0]] // close loop

  // ── Pass 1: thick gray base (track outline) ───────────────────────────────
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.lineWidth = 14
  ctx.strokeStyle = '#2a2a2a'
  ctx.shadowBlur = 0
  ctx.beginPath()
  const [bx0, by0] = toCanvas(allPts[0].x, allPts[0].z)
  ctx.moveTo(bx0, by0)
  for (let i = 1; i < allPts.length; i++) {
    const [bx, by] = toCanvas(allPts[i].x, allPts[i].z)
    ctx.lineTo(bx, by)
  }
  ctx.stroke()

  // ── Pass 2: colored delta segments ───────────────────────────────────────
  ctx.lineWidth = 7
  ctx.shadowBlur = 8

  for (let i = 0; i < allPts.length - 1; i++) {
    const [x0, y0] = toCanvas(allPts[i].x, allPts[i].z)
    const [x1, y1] = toCanvas(allPts[i + 1].x, allPts[i + 1].z)
    const color = deltaColor(allPts[i].delta_norm)
    ctx.shadowColor = color
    ctx.beginPath()
    ctx.strokeStyle = color
    ctx.moveTo(x0, y0)
    ctx.lineTo(x1, y1)
    ctx.stroke()
  }

  ctx.shadowBlur = 0

}

export default function DeltaMapWidget({ racingSessionId }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [allSessions, setAllSessions] = useState<RacingSession[]>([])
  const [currentTrack, setCurrentTrack] = useState<string | null>(null)
  const [refId, setRefId] = useState<string>('')
  const [deltaData, setDeltaData] = useState<DeltaMap | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch all sessions to populate selector and get current track
  useEffect(() => {
    getRacingSessions().then((sessions) => {
      setAllSessions(sessions)
      const current = sessions.find((s) => s.id === racingSessionId)
      if (current) setCurrentTrack(current.track)
    })
  }, [racingSessionId])

  // Sessions eligible as reference: same track, not self
  const refOptions = allSessions.filter(
    (s) => s.id !== racingSessionId && s.track && s.track === currentTrack && s.lap_count > 0
  )

  // Fetch delta map when ref changes
  useEffect(() => {
    if (!refId) {
      setDeltaData(null)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    getDeltaMap(racingSessionId, refId)
      .then((data) => {
        setDeltaData(data)
        setLoading(false)
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Error desconocido')
        setLoading(false)
      })
  }, [racingSessionId, refId])

  // Draw canvas whenever data changes
  useEffect(() => {
    if (canvasRef.current && deltaData) {
      drawDeltaMap(canvasRef.current, deltaData.points)
    }
  }, [deltaData])

  return (
    <div className="border border-gray-800 p-4 mt-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-white font-bold text-sm uppercase tracking-wide">Mapa de Delta</h2>
        <div className="flex items-center gap-3">
          <span className="text-gray-500 text-xs">Referencia:</span>
          <select
            className="bg-gray-900 border border-gray-700 text-white text-xs px-3 py-1.5 focus:outline-none focus:border-f1red"
            value={refId}
            onChange={(e) => setRefId(e.target.value)}
          >
            <option value="">— Seleccionar sesión —</option>
            {refOptions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name || s.track || s.id.slice(0, 8)} · {s.best_lap_fmt}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!refId && (
        <div className="text-gray-600 text-xs text-center py-10">
          Selecciona una sesión de referencia del mismo circuito para ver el delta.
        </div>
      )}

      {refId && loading && (
        <div className="text-gray-400 text-xs text-center py-10">Calculando delta...</div>
      )}

      {refId && error && (
        <div className="text-red-400 text-xs text-center py-6">{error}</div>
      )}

      {deltaData && !loading && (
        <>
          {/* Lap time header */}
          <div className="grid grid-cols-3 gap-4 mb-4 text-center">
            <div className="border border-gray-800 p-3">
              <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Sesión A (esta)</p>
              <p className="text-green-400 font-bold text-lg">{deltaData.session_a.best_lap_fmt}</p>
            </div>
            <div className="border border-gray-800 p-3">
              <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Delta total</p>
              <p className={`font-bold text-lg ${deltaData.delta_total < 0 ? 'text-green-400' : deltaData.delta_total > 0 ? 'text-red-400' : 'text-gray-400'}`}>
                {fmtDelta(deltaData.delta_total)}
              </p>
            </div>
            <div className="border border-gray-800 p-3">
              <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Sesión B (ref)</p>
              <p className="text-gray-300 font-bold text-lg">{deltaData.session_b.best_lap_fmt}</p>
            </div>
          </div>

          {/* Canvas */}
          <canvas
            ref={canvasRef}
            width={900}
            height={520}
            className="w-full border border-gray-800 rounded"
            style={{ background: '#111' }}
          />

          {/* Legend */}
          <div className="flex items-center justify-center gap-6 mt-3 text-xs text-gray-500">
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-4 h-1.5 rounded" style={{ background: 'rgb(0,200,0)' }} />
              <span>A más rápido</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-4 h-1.5 rounded" style={{ background: 'rgb(80,80,80)' }} />
              <span>Igual</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-4 h-1.5 rounded" style={{ background: 'rgb(200,0,0)' }} />
              <span>B más rápido</span>
            </div>
          </div>
        </>
      )}

      {refOptions.length === 0 && currentTrack && (
        <p className="text-gray-600 text-xs text-center pt-2">
          No hay otras sesiones en {currentTrack} para comparar.
        </p>
      )}
    </div>
  )
}
