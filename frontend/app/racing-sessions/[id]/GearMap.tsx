'use client'

import { useEffect, useRef } from 'react'
import { LapTelemetryPoint } from '../../lib/api'

interface Props { points: LapTelemetryPoint[] }

const GEAR_COLORS = [
  '#444444', // 0 - neutral/unknown
  '#1144dd', // 1st
  '#0099ff', // 2nd
  '#00ccaa', // 3rd
  '#00cc44', // 4th
  '#cccc00', // 5th
  '#ff8800', // 6th
  '#ff2200', // 7th
  '#ff00aa', // 8th
]

function gearColor(gear: number): string {
  return GEAR_COLORS[Math.max(0, Math.min(8, gear))] ?? '#444'
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
    const color = gearColor(all[i].gear)
    ctx.shadowColor = color
    ctx.strokeStyle = color
    ctx.beginPath()
    ctx.moveTo(x0, y0)
    ctx.lineTo(x1, y1)
    ctx.stroke()
  }
  ctx.shadowBlur = 0
}

export default function GearMap({ points }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => { if (ref.current) draw(ref.current, points) }, [points])

  const usedGears = Array.from(new Set(points.map((p) => p.gear))).filter((g) => g > 0).sort()

  return (
    <div>
      <h3 className="text-white text-xs font-bold uppercase tracking-wide mb-3">Mapa de Marchas</h3>
      <canvas ref={ref} width={900} height={520} className="w-full border border-gray-800" style={{ background: '#111' }} />
      <div className="flex items-center justify-center gap-4 mt-2 flex-wrap">
        {usedGears.map((g) => (
          <div key={g} className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: gearColor(g) }} />
            <span className="text-xs text-gray-500">{g}ª</span>
          </div>
        ))}
      </div>
    </div>
  )
}
