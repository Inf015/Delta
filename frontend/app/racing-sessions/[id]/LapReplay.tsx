'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { LapTelemetryPoint } from '../../lib/api'

interface Props {
  points: LapTelemetryPoint[]
  lapTimeFmt: string
  lapTime: number
}

const GEAR_COLORS = ['#444', '#1144dd', '#0099ff', '#00ccaa', '#00cc44', '#cccc00', '#ff8800', '#ff2200', '#ff00aa']

function gearColor(g: number) { return GEAR_COLORS[Math.max(0, Math.min(8, g))] ?? '#444' }

function buildLayout(points: LapTelemetryPoint[], W: number, H: number, PAD: number) {
  const xs = points.map((p) => p.x)
  const zs = points.map((p) => -p.z)
  const xMin = Math.min(...xs), xMax = Math.max(...xs)
  const zMin = Math.min(...zs), zMax = Math.max(...zs)
  const scale = Math.min((W - PAD * 2) / (xMax - xMin || 1), (H - PAD * 2) / (zMax - zMin || 1))
  const offX = (W - (xMax - xMin) * scale) / 2 - xMin * scale
  const offZ = (H - (zMax - zMin) * scale) / 2 - zMin * scale
  const toC = (x: number, z: number): [number, number] => [x * scale + offX, (-z) * scale + offZ]
  return { toC }
}

function drawBase(ctx: CanvasRenderingContext2D, points: LapTelemetryPoint[], toC: (x: number, z: number) => [number, number]) {
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

  ctx.lineWidth = 6
  ctx.strokeStyle = '#333'
  ctx.beginPath()
  ctx.moveTo(bx0, by0)
  for (let i = 1; i < all.length; i++) {
    const [bx, by] = toC(all[i].x, all[i].z)
    ctx.lineTo(bx, by)
  }
  ctx.stroke()
}

export default function LapReplay({ points, lapTimeFmt, lapTime }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef   = useRef<number | null>(null)
  const startRef  = useRef<number | null>(null)
  const progressRef = useRef(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(8)
  const [idx, setIdx] = useState(0)

  const speedLabel = (s: number) => `${s}×`

  const render = useCallback((progress: number) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = canvas.width, H = canvas.height
    const { toC } = buildLayout(points, W, H, 36)

    ctx.clearRect(0, 0, W, H)
    ctx.fillStyle = '#111'
    ctx.fillRect(0, 0, W, H)

    drawBase(ctx, points, toC)

    const i = Math.min(Math.floor(progress * (points.length - 1)), points.length - 1)
    const p = points[i]
    const [cx, cy] = toC(p.x, p.z)

    // Dot glow
    const color = gearColor(p.gear)
    ctx.shadowBlur = 18
    ctx.shadowColor = color
    ctx.beginPath()
    ctx.arc(cx, cy, 9, 0, Math.PI * 2)
    ctx.fillStyle = color
    ctx.fill()
    ctx.shadowBlur = 0

    // White center
    ctx.beginPath()
    ctx.arc(cx, cy, 4, 0, Math.PI * 2)
    ctx.fillStyle = '#fff'
    ctx.fill()

    // HUD overlay
    const hudX = 16, hudY = 16
    ctx.fillStyle = 'rgba(0,0,0,0.7)'
    ctx.fillRect(hudX, hudY, 160, 80)

    ctx.font = 'bold 20px monospace'
    ctx.fillStyle = '#22c55e'
    ctx.textAlign = 'left'
    ctx.fillText(`${Math.round(p.speed)} km/h`, hudX + 10, hudY + 28)

    ctx.font = '11px monospace'
    ctx.fillStyle = '#aaa'
    ctx.fillText(`Marcha: ${p.gear || '—'}`, hudX + 10, hudY + 48)
    ctx.fillStyle = 'rgb(0,200,70)'
    ctx.fillText(`Gas: ${Math.round(p.throttle)}%`, hudX + 10, hudY + 64)
    ctx.fillStyle = 'rgb(220,50,50)'
    ctx.fillText(`Freno: ${Math.round(p.brake)}%`, hudX + 90, hudY + 64)

    // Progress bar
    const barW = W - 32
    ctx.fillStyle = '#222'
    ctx.fillRect(16, H - 20, barW, 6)
    ctx.fillStyle = '#e10600'
    ctx.fillRect(16, H - 20, barW * progress, 6)

    setIdx(i)
  }, [points])

  const stop = useCallback(() => {
    if (animRef.current !== null) {
      cancelAnimationFrame(animRef.current)
      animRef.current = null
    }
    startRef.current = null
    setPlaying(false)
  }, [])

  const animate = useCallback((ts: number) => {
    if (startRef.current === null) startRef.current = ts
    const elapsed = (ts - startRef.current) / 1000
    const duration = lapTime / speed
    const progress = Math.min(elapsed / duration, 1)
    progressRef.current = progress
    render(progress)

    if (progress < 1) {
      animRef.current = requestAnimationFrame(animate)
    } else {
      // loop
      startRef.current = null
      animRef.current = requestAnimationFrame(animate)
    }
  }, [lapTime, speed, render])

  const play = useCallback(() => {
    startRef.current = null
    setPlaying(true)
    animRef.current = requestAnimationFrame(animate)
  }, [animate])

  // Re-draw static frame when not playing
  useEffect(() => {
    if (!playing) render(progressRef.current)
  }, [playing, render])

  // Initial render
  useEffect(() => { render(0) }, [render])

  useEffect(() => {
    return () => { if (animRef.current !== null) cancelAnimationFrame(animRef.current) }
  }, [])

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-gray-500 text-xs uppercase tracking-wide">Replay — {lapTimeFmt}</span>
        <div className="flex items-center gap-3">
          <span className="text-gray-600 text-xs">Velocidad:</span>
          {[2, 4, 8, 16].map((s) => (
            <button
              key={s}
              onClick={() => { setSpeed(s); if (playing) { stop(); setTimeout(play, 10) } }}
              className={`text-xs px-2 py-0.5 border transition-colors ${
                speed === s ? 'border-f1red text-f1red' : 'border-gray-700 text-gray-500 hover:border-gray-500'
              }`}
            >
              {speedLabel(s)}
            </button>
          ))}
          <button
            onClick={playing ? stop : play}
            className="bg-f1red hover:bg-red-700 text-white text-xs px-4 py-1.5 font-bold transition-colors ml-2"
          >
            {playing ? '⏸ Pausar' : '▶ Play'}
          </button>
        </div>
      </div>
      <canvas
        ref={canvasRef}
        width={900}
        height={520}
        className="w-full border border-gray-800"
        style={{ background: '#111' }}
      />
      <div className="flex items-center gap-6 mt-2 text-xs text-gray-500">
        <span>Punto {idx + 1}/{points.length}</span>
        <span>·</span>
        <span>{Math.round(points[idx]?.speed ?? 0)} km/h</span>
        {points[idx]?.gear > 0 && <span>· {points[idx].gear}ª marcha</span>}
      </div>
    </div>
  )
}
