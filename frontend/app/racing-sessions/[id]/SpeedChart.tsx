'use client'

import { useEffect, useRef } from 'react'
import { LapTelemetryPoint } from '../../lib/api'

interface Props {
  points: LapTelemetryPoint[]
  lapTimeFmt: string
}

function draw(canvas: HTMLCanvasElement, points: LapTelemetryPoint[]) {
  const ctx = canvas.getContext('2d')
  if (!ctx || points.length < 2) return

  const W = canvas.width
  const H = canvas.height
  const PL = 48, PR = 10, PT = 24, PB = 24
  const SPLIT = Math.floor(H * 0.58)
  const GAP = 18

  ctx.clearRect(0, 0, W, H)
  ctx.fillStyle = '#111'
  ctx.fillRect(0, 0, W, H)

  const speeds    = points.map((p) => p.speed)
  const maxSpeed  = Math.max(...speeds)
  const minSpeed  = Math.min(...speeds)
  const sRange    = maxSpeed - minSpeed || 1

  // ── vertical grid (shared) ──────────────────────────────────────────
  ctx.strokeStyle = '#1e1e1e'
  ctx.lineWidth = 1
  for (let i = 0; i <= 4; i++) {
    const x = PL + (i / 4) * (W - PL - PR)
    ctx.beginPath()
    ctx.moveTo(x, PT)
    ctx.lineTo(x, H - PB)
    ctx.stroke()
    ctx.fillStyle = '#3a3a3a'
    ctx.font = '10px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(`${i * 25}%`, x, H - 6)
  }

  // ── Speed section ────────────────────────────────────────────────────
  const sH = SPLIT - PT
  const sY = PT

  // horizontal grid
  for (let i = 0; i <= 4; i++) {
    const y = sY + sH - (i / 4) * sH
    ctx.strokeStyle = '#1e1e1e'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(PL, y)
    ctx.lineTo(W - PR, y)
    ctx.stroke()
    ctx.fillStyle = '#3a3a3a'
    ctx.font = '10px monospace'
    ctx.textAlign = 'right'
    ctx.fillText(String(Math.round(minSpeed + (i / 4) * sRange)), PL - 4, y + 3)
  }

  // label
  ctx.fillStyle = '#555'
  ctx.font = '9px monospace'
  ctx.textAlign = 'left'
  ctx.fillText('VELOCIDAD km/h', PL + 6, sY + 14)

  // speed area fill
  ctx.fillStyle = 'rgba(200,200,200,0.06)'
  ctx.beginPath()
  ctx.moveTo(PL, sY + sH)
  points.forEach((p) => {
    const x = PL + p.d * (W - PL - PR)
    const y = sY + sH - ((p.speed - minSpeed) / sRange) * sH
    ctx.lineTo(x, y)
  })
  ctx.lineTo(W - PR, sY + sH)
  ctx.closePath()
  ctx.fill()

  // speed line
  ctx.strokeStyle = '#d4d4d4'
  ctx.lineWidth = 2
  ctx.lineJoin = 'round'
  ctx.beginPath()
  points.forEach((p, i) => {
    const x = PL + p.d * (W - PL - PR)
    const y = sY + sH - ((p.speed - minSpeed) / sRange) * sH
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
  })
  ctx.stroke()

  // ── Throttle / Brake section ─────────────────────────────────────────
  const bY = SPLIT + GAP
  const bH = H - bY - PB

  ctx.fillStyle = '#555'
  ctx.font = '9px monospace'
  ctx.textAlign = 'left'
  ctx.fillText('THROTTLE / BRAKE %', PL + 6, bY + 14)

  for (let i = 0; i <= 2; i++) {
    const y = bY + bH - (i / 2) * bH
    ctx.fillStyle = '#3a3a3a'
    ctx.font = '10px monospace'
    ctx.textAlign = 'right'
    ctx.fillText(String(i * 50), PL - 4, y + 3)
  }

  // throttle fill
  ctx.fillStyle = 'rgba(0,190,60,0.18)'
  ctx.beginPath()
  ctx.moveTo(PL, bY + bH)
  points.forEach((p) => {
    ctx.lineTo(PL + p.d * (W - PL - PR), bY + bH - (p.throttle / 100) * bH)
  })
  ctx.lineTo(W - PR, bY + bH)
  ctx.closePath()
  ctx.fill()

  ctx.strokeStyle = 'rgb(0,200,70)'
  ctx.lineWidth = 1.5
  ctx.lineJoin = 'round'
  ctx.beginPath()
  points.forEach((p, i) => {
    const x = PL + p.d * (W - PL - PR)
    const y = bY + bH - (p.throttle / 100) * bH
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
  })
  ctx.stroke()

  // brake fill
  ctx.fillStyle = 'rgba(220,30,30,0.22)'
  ctx.beginPath()
  ctx.moveTo(PL, bY + bH)
  points.forEach((p) => {
    ctx.lineTo(PL + p.d * (W - PL - PR), bY + bH - (p.brake / 100) * bH)
  })
  ctx.lineTo(W - PR, bY + bH)
  ctx.closePath()
  ctx.fill()

  ctx.strokeStyle = 'rgb(220,50,50)'
  ctx.lineWidth = 1.5
  ctx.lineJoin = 'round'
  ctx.beginPath()
  points.forEach((p, i) => {
    const x = PL + p.d * (W - PL - PR)
    const y = bY + bH - (p.brake / 100) * bH
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
  })
  ctx.stroke()

  // divider between sections
  ctx.strokeStyle = '#222'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(PL, SPLIT + GAP / 2)
  ctx.lineTo(W - PR, SPLIT + GAP / 2)
  ctx.stroke()
}

export default function SpeedChart({ points, lapTimeFmt }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => { if (ref.current) draw(ref.current, points) }, [points])

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-gray-500 text-xs uppercase tracking-wide">Mejor vuelta</span>
        <span className="text-green-400 font-bold text-sm font-mono">{lapTimeFmt}</span>
      </div>
      <canvas ref={ref} width={900} height={380} className="w-full border border-gray-800" style={{ background: '#111' }} />
      <div className="flex items-center gap-6 mt-2 text-xs text-gray-500">
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-5 h-px" style={{ background: '#d4d4d4' }} />
          <span>Velocidad</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-1.5 rounded" style={{ background: 'rgb(0,200,70)' }} />
          <span>Throttle</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-1.5 rounded" style={{ background: 'rgb(220,50,50)' }} />
          <span>Brake</span>
        </div>
      </div>
    </div>
  )
}
