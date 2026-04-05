'use client'

import { useEffect, useRef } from 'react'
import { LapTelemetryPoint } from '../../lib/api'

interface Props { points: LapTelemetryPoint[] }

function heatColor(norm: number): string {
  const t = Math.max(0, Math.min(1, norm))
  if (t < 0.25) {
    const f = t / 0.25
    return `rgb(0, ${Math.round(f * 200)}, 255)`
  } else if (t < 0.5) {
    const f = (t - 0.25) / 0.25
    return `rgb(0, 255, ${Math.round((1 - f) * 200)})`
  } else if (t < 0.75) {
    const f = (t - 0.5) / 0.25
    return `rgb(${Math.round(f * 255)}, 255, 0)`
  } else {
    const f = (t - 0.75) / 0.25
    return `rgb(255, ${Math.round((1 - f) * 255)}, 0)`
  }
}

function draw(canvas: HTMLCanvasElement, points: LapTelemetryPoint[]) {
  const ctx = canvas.getContext('2d')
  if (!ctx || points.length < 2) return

  const W = canvas.width, H = canvas.height, PAD = 36
  ctx.clearRect(0, 0, W, H)
  ctx.fillStyle = '#111'
  ctx.fillRect(0, 0, W, H)

  const xs = points.map((p) => p.x)
  const zs = points.map((p) => -p.z)
  const xMin = Math.min(...xs), xMax = Math.max(...xs)
  const zMin = Math.min(...zs), zMax = Math.max(...zs)
  const scale = Math.min((W - PAD * 2) / (xMax - xMin || 1), (H - PAD * 2) / (zMax - zMin || 1))
  const offX = (W - (xMax - xMin) * scale) / 2 - xMin * scale
  const offZ = (H - (zMax - zMin) * scale) / 2 - zMin * scale

  const toC = (x: number, z: number): [number, number] => [x * scale + offX, (-z) * scale + offZ]

  const speeds = points.map((p) => p.speed)
  const minS = Math.min(...speeds), maxS = Math.max(...speeds)
  const sRange = maxS - minS || 1

  const all = [...points, points[0]]

  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.lineWidth = 14
  ctx.strokeStyle = '#2a2a2a'
  ctx.beginPath()
  const [bx0, by0] = toC(all[0].x, all[0].z)
  ctx.moveTo(bx0, by0)
  for (let i = 1; i < all.length; i++) {
    const [bx, by] = toC(all[i].x, all[i].z)
    ctx.lineTo(bx, by)
  }
  ctx.stroke()

  ctx.lineWidth = 7
  ctx.shadowBlur = 6
  for (let i = 0; i < all.length - 1; i++) {
    const [x0, y0] = toC(all[i].x, all[i].z)
    const [x1, y1] = toC(all[i + 1].x, all[i + 1].z)
    const norm = (all[i].speed - minS) / sRange
    const color = heatColor(norm)
    ctx.shadowColor = color
    ctx.strokeStyle = color
    ctx.beginPath()
    ctx.moveTo(x0, y0)
    ctx.lineTo(x1, y1)
    ctx.stroke()
  }
  ctx.shadowBlur = 0
}

export default function TrackHeatmap({ points }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => { if (ref.current) draw(ref.current, points) }, [points])

  const speeds = points.map((p) => p.speed)
  const minS = Math.round(Math.min(...speeds))
  const maxS = Math.round(Math.max(...speeds))

  return (
    <div>
      <h3 className="text-white text-xs font-bold uppercase tracking-wide mb-3">Mapa de Velocidad</h3>
      <canvas ref={ref} width={900} height={520} className="w-full border border-gray-800" style={{ background: '#111' }} />
      <div className="flex items-center justify-center gap-3 mt-2">
        <span className="text-xs text-gray-500">{minS} km/h</span>
        <div className="w-48 h-2 rounded" style={{ background: 'linear-gradient(to right, rgb(0,0,255), rgb(0,255,100), rgb(255,255,0), rgb(255,0,0))' }} />
        <span className="text-xs text-gray-500">{maxS} km/h</span>
      </div>
    </div>
  )
}
