'use client'

import Link from 'next/link'
import { SessionReport, LapRow, TrackInfo, trackMapUrl, sessionPdfUrl } from '../lib/api'

// ── Helpers ──────────────────────────────────────────────────────────────────

function SectionHeader({ num, title }: { num: number; title: string }) {
  return (
    <div className="mb-4 mt-10 first:mt-0">
      <div className="flex items-baseline gap-3">
        <span className="text-f1red font-bold text-lg">{num}.</span>
        <h2 className="text-white font-bold text-base uppercase tracking-wide">{title}</h2>
      </div>
      <div className="h-px bg-f1red/40 mt-2" />
    </div>
  )
}

function MetricRow({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <tr className="border-b border-gray-900">
      <td className="px-4 py-2 text-gray-400 text-sm">{label}</td>
      <td className={`px-4 py-2 text-sm text-right font-mono ${highlight ? 'text-green-400 font-bold' : 'text-white'}`}>{value}</td>
    </tr>
  )
}

function TwoColTable({ headers, rows }: {
  headers: string[]
  rows: Array<Array<{ value: string; color?: string }>>
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border border-gray-800">
        <thead>
          <tr className="bg-gray-900">
            {headers.map((h, i) => (
              <th key={i} className="px-3 py-2 text-gray-500 uppercase tracking-wide text-left font-normal">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 0 ? 'bg-gray-950' : ''}>
              {row.map((cell, ci) => (
                <td
                  key={ci}
                  className="px-3 py-2 font-mono"
                  style={cell.color ? { backgroundColor: cell.color + '33', color: '#fff' } : { color: '#9ca3af' }}
                >
                  {cell.value}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function NoData({ msg }: { msg: string }) {
  return <p className="text-gray-600 text-sm italic border border-gray-800 px-4 py-3">{msg}</p>
}

function BulletList({ items, color = 'text-gray-300' }: { items: string[]; color?: string }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className={`text-sm ${color} flex gap-2`}>
          <span className="text-f1red mt-0.5 shrink-0">•</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

function tyreColor(v: number) {
  if (v < 50)  return '#3b82f6'
  if (v < 75)  return '#60a5fa'
  if (v < 105) return '#22c55e'
  if (v < 120) return '#f97316'
  return '#ef4444'
}

function brakeColor(v: number) {
  if (v < 200) return '#3b82f6'
  if (v < 550) return '#22c55e'
  if (v < 720) return '#f97316'
  return '#ef4444'
}

function deltaColor(delta: number, isBest: boolean) {
  if (isBest) return '#22c55e'
  if (delta > 5) return '#ef4444'
  return undefined
}

// ── Section components ───────────────────────────────────────────────────────

function Section0({ track, sessionId }: { track: TrackInfo; sessionId: string }) {
  const typeBadge = track.track_type === 'real'
    ? 'bg-green-900 text-green-400 border-green-800'
    : track.track_type === 'fictional'
    ? 'bg-purple-900 text-purple-400 border-purple-800'
    : 'bg-gray-800 text-gray-400 border-gray-700'
  const typeLabel = track.track_type === 'real' ? 'REAL' : track.track_type === 'fictional' ? 'MOD / FICTICIO' : 'DESCONOCIDO'
  const sourceBadge = track.source === 'claude' ? ' · Generado por IA' : ''

  return (
    <div className="mb-8">
      <div className="border border-gray-800 p-6 mb-4">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white">{track.display_name}</h2>
            <p className="text-gray-500 text-sm mt-1">
              {track.country || 'País desconocido'}
              {track.length_m ? ` · ${(track.length_m / 1000).toFixed(3)} km` : ''}
              {track.turns ? ` · ${track.turns} curvas` : ''}
              {sourceBadge}
            </p>
          </div>
          <span className={`border px-3 py-1 text-xs font-bold shrink-0 ${typeBadge}`}>{typeLabel}</span>
        </div>
        {track.characteristics.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {track.characteristics.map((c, i) => (
              <span key={i} className="bg-gray-900 border border-gray-700 text-gray-400 text-xs px-2 py-1">{c}</span>
            ))}
          </div>
        )}
        {track.has_map && (
          <div className="mb-4 border border-gray-800 overflow-hidden">
            <img src={trackMapUrl(sessionId)} alt={`Mapa de ${track.display_name}`} className="w-full object-contain max-h-72" style={{ filter: 'brightness(0.9)' }} />
          </div>
        )}
        {track.lap_record && (
          <div className="border border-gray-800 px-4 py-3 mb-4 flex items-center gap-4">
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wide mb-0.5">Récord oficial</p>
              <p className="text-white font-mono font-bold text-lg">{track.lap_record.time}</p>
            </div>
            <div className="text-gray-500 text-xs">{track.lap_record.driver} · {track.lap_record.series} · {track.lap_record.year}</div>
          </div>
        )}
      </div>
      {track.sectors.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          {track.sectors.map((sector, i) => {
            const sColors = ['border-f1red/50 bg-red-950/10', 'border-blue-800/50 bg-blue-950/10', 'border-green-800/50 bg-green-950/10']
            return <div key={i} className={`border p-4 ${sColors[i] ?? 'border-gray-800'}`}><p className="text-white text-sm">{sector}</p></div>
          })}
        </div>
      )}
      {track.key_corners.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {track.key_corners.map((corner, i) => (
            <div key={i} className="border border-gray-800 p-4">
              <div className="flex items-baseline gap-2 mb-1">
                <span className="text-white font-bold text-sm">{corner.name}</span>
                <span className="text-gray-500 text-xs">{corner.type}</span>
              </div>
              <p className="text-gray-400 text-xs">{corner.tip}</p>
            </div>
          ))}
        </div>
      )}
      {track.notes && <p className="text-gray-500 text-xs italic border-l-2 border-gray-700 pl-3 mt-4">{track.notes}</p>}
    </div>
  )
}

function Section1({ s }: { s: SessionReport['section_1_summary'] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-0 border border-gray-800">
      <table className="w-full"><tbody>
        <MetricRow label="Total de vueltas" value={String(s.total_laps)} />
        <MetricRow label="Mejor vuelta" value={s.best_lap_fmt} highlight />
        <MetricRow label="Peor vuelta" value={s.worst_lap_fmt} />
        <MetricRow label="Promedio" value={s.avg_lap_fmt} />
        <MetricRow label="Sector 1 (mejor vuelta)" value={s.best_s1_fmt} />
        <MetricRow label="Sector 2 (mejor vuelta)" value={s.best_s2_fmt} />
        <MetricRow label="Sector 3 (mejor vuelta)" value={s.best_s3_fmt} />
      </tbody></table>
      <table className="w-full"><tbody>
        {s.max_speed_kmh && <MetricRow label="Velocidad máxima" value={`${s.max_speed_kmh} km/h`} />}
        {s.throttle_avg_pct && <MetricRow label="Throttle promedio" value={`${s.throttle_avg_pct}%`} />}
        {s.throttle_full_pct && <MetricRow label="A fondo (>95%)" value={`${s.throttle_full_pct}% del tiempo`} />}
        <MetricRow label="Tiempo teórico óptimo" value={`${s.theoretical_best_fmt} (−${s.potential_gain.toFixed(3)}s potencial)`} />
        {s.fuel_used_per_lap && <MetricRow label="Combustible usado" value={`${s.fuel_used_per_lap} l/vuelta aprox.`} />}
        {s.rpm_max && <MetricRow label="RPM máximo" value={`${s.rpm_max} rpm`} />}
        {s.brake_hard_pct != null && <MetricRow label="Frenada intensa (>80%)" value={`${s.brake_hard_pct}% del tiempo`} />}
        {s.handling && <MetricRow label="Comportamiento" value={s.handling} />}
        {s.weak_sector && <MetricRow label="Sector más débil" value={s.weak_sector} />}
      </tbody></table>
    </div>
  )
}

function Section2({ laps }: { laps: LapRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border border-gray-800">
        <thead>
          <tr className="bg-gray-900 text-gray-500 uppercase tracking-wide">
            <th className="px-3 py-2 text-left font-normal">Vuelta</th>
            <th className="px-3 py-2 text-right font-normal">Tiempo</th>
            <th className="px-3 py-2 text-right font-normal">S1</th>
            <th className="px-3 py-2 text-right font-normal">S2</th>
            <th className="px-3 py-2 text-right font-normal">S3</th>
            <th className="px-3 py-2 text-right font-normal">Delta</th>
            <th className="px-3 py-2 text-left font-normal">Estado</th>
          </tr>
        </thead>
        <tbody>
          {laps.map((lap) => {
            const rowBg = lap.is_best ? 'bg-green-950/30' : lap.status === 'CALENTAMIENTO' ? 'bg-gray-900/60' : ''
            return (
              <tr key={lap.lap_number} className={`border-b border-gray-900 ${rowBg}`}>
                <td className="px-3 py-1.5 text-gray-400 font-mono">{lap.lap_number}</td>
                <td className={`px-3 py-1.5 text-right font-mono font-bold ${lap.is_best ? 'text-green-400' : 'text-white'}`}>{lap.lap_time_fmt}</td>
                <td className={`px-3 py-1.5 text-right font-mono ${lap.is_best_s1 ? 'text-purple-400 font-bold' : 'text-gray-400'}`}>{lap.s1_fmt}</td>
                <td className={`px-3 py-1.5 text-right font-mono ${lap.is_best_s2 ? 'text-purple-400 font-bold' : 'text-gray-400'}`}>{lap.s2_fmt}</td>
                <td className={`px-3 py-1.5 text-right font-mono ${lap.is_best_s3 ? 'text-purple-400 font-bold' : 'text-gray-400'}`}>{lap.s3_fmt}</td>
                <td className="px-3 py-1.5 text-right font-mono" style={{ color: deltaColor(lap.delta, lap.is_best) ?? '#6b7280' }}>
                  {lap.is_best ? '0.000' : `+${lap.delta.toFixed(3)}`}
                </td>
                <td className="px-3 py-1.5">
                  <div className="flex flex-col gap-0.5">
                    {!lap.valid ? (
                      <span className="text-xs text-red-500">✗ INVÁLIDA</span>
                    ) : (
                      <span className={`text-xs ${lap.status === 'MEJOR VUELTA' ? 'text-green-400 font-bold' : lap.status === 'MEJORANDO' ? 'text-blue-400' : lap.status === 'CALENTAMIENTO' ? 'text-yellow-600' : 'text-gray-500'}`}>
                        {lap.status === 'MEJOR VUELTA' ? '✓ MEJOR VUELTA' : lap.status === 'MEJORANDO' ? '▲ MEJORANDO' : lap.status === 'CALENTAMIENTO' ? '✗ CALENTAMIENTO' : '✓ VÁLIDA'}
                      </span>
                    )}
                    {lap.incidents && lap.incidents.length > 0 && (
                      <span className="text-xs text-orange-400 cursor-help" title={lap.incidents.map((inc) => inc.detail).join(' | ')}>
                        ⚠ {lap.incidents.length} incidente{lap.incidents.length !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="text-xs text-gray-600 mt-2">
        <span className="text-green-400">■</span> Mejor vuelta &nbsp;
        <span className="text-purple-400">■</span> Mejor sector (F1) &nbsp;
        <span className="text-red-500/70">■</span> Delta positivo
      </p>
    </div>
  )
}

function Section3({ s }: { s: SessionReport['section_3_consistency'] }) {
  const color = s.score >= 80 ? '#22c55e' : s.score >= 40 ? '#f97316' : '#ef4444'
  return (
    <div>
      <div className="flex items-baseline gap-3 mb-3">
        <span className="font-bold text-3xl font-mono" style={{ color }}>{s.score} / 100</span>
        <span className="font-bold text-lg" style={{ color }}>— {s.label}</span>
      </div>
      {s.std_dev > 0 && <p className="text-gray-400 text-sm mb-1">Desviación estándar: {s.std_dev}s entre vueltas</p>}
      {s.interpretation && <p className="text-gray-300 text-sm">{s.interpretation}</p>}
    </div>
  )
}

function Section4({ s }: { s: SessionReport['section_4_tyres'] }) {
  const corners = ['FL', 'FR', 'RL', 'RR']
  return (
    <div className="space-y-6">
      {s.temp && (
        <div>
          <TwoColTable
            headers={['Métrica', 'FL', 'FR', 'RL', 'RR']}
            rows={[
              ['Temp promedio (°C)', ...corners.map(c => { const d = s.temp?.[c]; return { value: String(d?.avg ?? '—'), color: typeof d?.avg === 'number' ? tyreColor(d.avg) : undefined } })],
              ['Temp máx (°C)', ...corners.map(c => { const d = s.temp?.[c]; return { value: String(d?.max ?? '—'), color: typeof d?.max === 'number' ? tyreColor(d.max) : undefined } })],
              ['Temp mín (°C)', ...corners.map(c => ({ value: String(s.temp![c]?.min ?? '—') }))],
              ...(s.press ? [
                ['Presión promedio (PSI)', ...corners.map(c => ({ value: String(s.press![c]?.avg ?? '—') }))],
                ['Presión máx (PSI)', ...corners.map(c => ({ value: String(s.press![c]?.max ?? '—') }))],
              ] : []),
              ...(s.slip ? [['Slip máximo (%)', ...corners.map(c => ({ value: String(s.slip![c]?.max ?? '—') }))]] : []),
            ].map(row => [{ value: row[0] as string }, ...(row.slice(1) as Array<{ value: string; color?: string }>)])}
          />
          <div className="flex gap-4 mt-2 text-xs text-gray-600">
            <span><span style={{ color: '#3b82f6' }}>■</span> Muy fría</span>
            <span><span style={{ color: '#60a5fa' }}>■</span> Calentando</span>
            <span><span style={{ color: '#22c55e' }}>■</span> Óptima</span>
            <span><span style={{ color: '#f97316' }}>■</span> Caliente</span>
            <span><span style={{ color: '#ef4444' }}>■</span> Crítica</span>
          </div>
        </div>
      )}
      {s.camber_table && s.camber_table.length > 0 && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 font-bold">Distribución por zona (diagnóstico camber):</p>
          <TwoColTable
            headers={['Goma', 'Inner (°C)', 'Middle (°C)', 'Outer (°C)', 'Diagnóstico']}
            rows={s.camber_table.map(r => [
              { value: r.corner },
              { value: String(r.inner ?? '—') },
              { value: String(r.mid ?? '—') },
              { value: String(r.outer ?? '—') },
              { value: r.diagnosis, color: r.diagnosis.startsWith('✓') ? '#22c55e' : '#f97316' },
            ])}
          />
        </div>
      )}
      {s.wear && s.wear.length > 0 && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 font-bold">Desgaste de gomas:</p>
          <TwoColTable
            headers={['Rueda', 'Desgaste med.', 'Desgaste máx.', 'Al final']}
            rows={s.wear.map(r => [
              { value: r.corner },
              { value: r.avg_pct != null ? `${r.avg_pct}%` : '—' },
              { value: r.max_pct != null ? `${r.max_pct}%` : '—' },
              { value: r.end_pct != null ? `${r.end_pct}%` : '—' },
            ])}
          />
          {s.wear_diagnosis && s.wear_diagnosis.length > 0 && (
            <p className="text-yellow-500 text-xs border border-yellow-900/50 px-3 py-2 mt-2">
              Desgaste diferencial: {s.wear_diagnosis.join(', ')}
            </p>
          )}
        </div>
      )}
      {s.overheating_risk && s.overheating_risk.length > 0 && (
        <p className="text-red-400 text-sm border border-red-900/50 px-3 py-2">
          Riesgo de sobrecalentamiento interno: {s.overheating_risk.join(', ')}
        </p>
      )}
      {s.carcass && Object.keys(s.carcass).length > 0 && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 font-bold">Temperatura de carcasa:</p>
          <TwoColTable
            headers={['Rueda', 'Prom (°C)', 'Máx (°C)']}
            rows={Object.entries(s.carcass).map(([corner, data]: [string, unknown]) => {
              const d = data as { avg?: number; max?: number }
              return [
                { value: corner },
                { value: d.avg != null ? String(d.avg) : '—', color: typeof d.avg === 'number' ? tyreColor(d.avg) : undefined },
                { value: d.max != null ? String(d.max) : '—', color: typeof d.max === 'number' ? tyreColor(d.max) : undefined },
              ]
            })}
          />
        </div>
      )}
    </div>
  )
}

function Section5({ s }: { s: SessionReport['section_5_brakes'] }) {
  const corners = ['FL', 'FR', 'RL', 'RR']
  return (
    <div className="space-y-4">
      {s.temp && (
        <div>
          <TwoColTable
            headers={['Métrica', 'FL', 'FR', 'RL', 'RR']}
            rows={[
              [{ value: 'Temp promedio (°C)' }, ...corners.map(c => ({ value: String(s.temp![c]?.avg ?? '—'), color: s.temp![c] ? brakeColor(s.temp![c].avg) : undefined }))],
              [{ value: 'Temp máxima (°C)' }, ...corners.map(c => ({ value: String(s.temp![c]?.max ?? '—'), color: s.temp![c] ? brakeColor(s.temp![c].max) : undefined }))],
            ]}
          />
        </div>
      )}
      {s.warning && <p className="text-yellow-500 text-sm border border-yellow-900/50 px-3 py-2">• {s.warning}</p>}
      {s.zones && s.zones.length > 0 && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 font-bold">Zonas de frenada detectadas:</p>
          <TwoColTable
            headers={['Punto (m)', 'Velocidad (km/h)', 'Intensidad (%)']}
            rows={s.zones.map(z => [
              { value: String(z.dist_m) },
              { value: String(z.speed_kmh) },
              { value: String(z.intensity), color: z.intensity > 90 ? '#ef4444' : z.intensity > 70 ? '#f97316' : '#22c55e' },
            ])}
          />
        </div>
      )}
    </div>
  )
}

function Section6({ s }: { s: SessionReport['section_6_dynamics'] }) {
  return (
    <div className="space-y-6">
      {s.g_forces && s.g_forces.length > 0 && (
        <TwoColTable
          headers={['Métrica', 'Valor', 'Interpretación']}
          rows={s.g_forces.map(g => [{ value: g.metric }, { value: g.value }, { value: g.interpretation }])}
        />
      )}
      {s.suspension && s.suspension.length > 0 && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 font-bold">Datos de suspensión (mejor vuelta):</p>
          <TwoColTable
            headers={['Esquina', 'Recorrido prom (mm)', 'Rango total (mm)', 'Min (mm)', 'Max (mm)']}
            rows={s.suspension.map(r => [
              { value: r.corner }, { value: String(r.avg_mm) }, { value: String(r.range_mm) },
              { value: String(r.min_mm) }, { value: String(r.max_mm) },
            ])}
          />
        </div>
      )}
      {s.ride_height && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 font-bold">Altura de carrocería (Ride Height):</p>
          <TwoColTable
            headers={['Eje', 'Altura promedio (mm)', 'Diagnóstico']}
            rows={[
              [{ value: 'Delantera' }, { value: s.ride_height.front_mm != null ? `${s.ride_height.front_mm} mm` : '—' }, { value: '' }],
              [{ value: 'Trasera' }, { value: s.ride_height.rear_mm != null ? `${s.ride_height.rear_mm} mm` : '—' }, { value: '' }],
              [{ value: 'Rake (Tras − Del)' }, { value: s.ride_height.rake_mm != null ? `${s.ride_height.rake_mm} mm` : '—' }, { value: s.ride_height.diagnosis ?? '—', color: s.ride_height.diagnosis === 'neutral' ? '#22c55e' : '#f97316' }],
            ]}
          />
        </div>
      )}
      {s.tyre_loads && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 font-bold">Cargas en rueda:</p>
          <div className="text-xs space-y-1 border border-gray-800 p-3">
            {s.tyre_loads.front_pct != null && s.tyre_loads.rear_pct != null && (
              <div className="flex items-center gap-3">
                <span className="text-gray-500 w-20 shrink-0">Delantera:</span>
                <div className="flex-1 bg-gray-900 h-3 relative">
                  <div className="absolute left-0 top-0 h-full bg-blue-600" style={{ width: `${s.tyre_loads.front_pct}%` }} />
                </div>
                <span className="text-white font-mono w-12 text-right">{s.tyre_loads.front_pct}%</span>
              </div>
            )}
            {s.tyre_loads.rear_pct != null && (
              <div className="flex items-center gap-3">
                <span className="text-gray-500 w-20 shrink-0">Trasera:</span>
                <div className="flex-1 bg-gray-900 h-3 relative">
                  <div className="absolute left-0 top-0 h-full bg-orange-500" style={{ width: `${s.tyre_loads.rear_pct}%` }} />
                </div>
                <span className="text-white font-mono w-12 text-right">{s.tyre_loads.rear_pct}%</span>
              </div>
            )}
            {s.tyre_loads.balance_diag && (
              <p className="text-gray-400 mt-1">Balance: <span className={s.tyre_loads.balance_diag === 'balanced' ? 'text-green-400' : 'text-yellow-400'}>{s.tyre_loads.balance_diag}</span></p>
            )}
          </div>
        </div>
      )}
      {s.damper_analysis && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 font-bold">Análisis de amortiguadores:</p>
          {s.damper_analysis.diagnosis && (
            <p className="text-sm mb-2">Diagnóstico: <span className={s.damper_analysis.diagnosis === 'well_damped' ? 'text-green-400' : 'text-yellow-400'}>{s.damper_analysis.diagnosis}</span></p>
          )}
          {s.damper_analysis.corners && Object.keys(s.damper_analysis.corners).length > 0 && (
            <TwoColTable
              headers={['Rueda', 'Vel. med. (m/s)', 'Vel. máx. (m/s)', 'P95 (m/s)']}
              rows={Object.entries(s.damper_analysis.corners).map(([corner, data]: [string, unknown]) => {
                const d = data as { avg_ms?: number; max_ms?: number; p95_ms?: number }
                return [
                  { value: corner },
                  { value: d.avg_ms != null ? String(d.avg_ms) : '—' },
                  { value: d.max_ms != null ? String(d.max_ms) : '—' },
                  { value: d.p95_ms != null ? String(d.p95_ms) : '—' },
                ]
              })}
            />
          )}
        </div>
      )}
      {s.yaw_rate && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 font-bold">Yaw Rate (rotación del vehículo):</p>
          <TwoColTable
            headers={['Métrica', 'Valor']}
            rows={[
              [{ value: 'Promedio (rad/s)' }, { value: String(s.yaw_rate.avg_rads ?? '—') }],
              [{ value: 'Máximo (rad/s)' }, { value: String(s.yaw_rate.max_rads ?? '—') }],
              [{ value: 'P95 (rad/s)' }, { value: String(s.yaw_rate.p95_rads ?? '—') }],
            ]}
          />
        </div>
      )}
      {s.lsd_analysis && Object.keys(s.lsd_analysis).length > 0 && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 font-bold">LSD / Diferencial:</p>
          <div className="border border-gray-800 p-3 text-sm space-y-1">
            {s.lsd_analysis.lsd_diagnosis && (
              <p>Diagnóstico: <span className={s.lsd_analysis.lsd_diagnosis === 'well_locked' ? 'text-green-400' : s.lsd_analysis.lsd_diagnosis === 'light_locking' ? 'text-yellow-400' : 'text-red-400'}>{s.lsd_analysis.lsd_diagnosis}</span></p>
            )}
            {s.lsd_analysis.accel_diff_avg != null && (
              <p className="text-gray-400 text-xs">Diferencia trasera en aceleración (prom): <span className="text-white font-mono">{s.lsd_analysis.accel_diff_avg} km/h</span></p>
            )}
            {s.lsd_analysis.accel_diff_max != null && (
              <p className="text-gray-400 text-xs">Diferencia trasera en aceleración (máx): <span className="text-white font-mono">{s.lsd_analysis.accel_diff_max} km/h</span></p>
            )}
          </div>
        </div>
      )}
      {s.steering && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 font-bold">Dirección (análisis de subviraje):</p>
          <div className="border border-gray-800 p-3 text-sm space-y-1">
            {s.steering.understeer_level && (
              <p>Nivel de subviraje: <span className={s.steering.understeer_level === 'low' ? 'text-green-400' : s.steering.understeer_level === 'medium' ? 'text-yellow-400' : 'text-red-400'}>{s.steering.understeer_level}</span></p>
            )}
            {s.steering.understeer_score != null && (
              <p className="text-gray-400 text-xs">Score: <span className="text-white font-mono">{s.steering.understeer_score}</span></p>
            )}
            {s.steering.avg_abs != null && (
              <p className="text-gray-400 text-xs">Steer promedio: <span className="text-white font-mono">{s.steering.avg_abs}%</span></p>
            )}
            {s.steering.max_abs != null && (
              <p className="text-gray-400 text-xs">Steer máximo: <span className="text-white font-mono">{s.steering.max_abs}%</span></p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function CornerGrid({ data }: { data: Record<string, unknown> }) {
  const corners = ['LF', 'RF', 'LR', 'RR']
  const labels: Record<string, string> = { LF: 'Del Izq', RF: 'Del Der', LR: 'Tra Izq', RR: 'Tra Der' }
  return (
    <div className="grid grid-cols-4 gap-1 text-xs">
      {corners.filter((c) => c in data).map((c) => (
        <div key={c} className="border border-gray-800 px-2 py-1 text-center">
          <p className="text-gray-600 text-xs">{labels[c]}</p>
          <p className="text-white font-mono">{String(data[c])}</p>
        </div>
      ))}
    </div>
  )
}

function SetupBlock({ label, data }: { label: string; data: Record<string, unknown> }) {
  const corners = ['LF', 'RF', 'LR', 'RR']
  const isCornerMap = corners.some((c) => c in data)
  return (
    <div>
      <p className="text-gray-500 text-xs uppercase tracking-wide mb-1 font-bold">{label}</p>
      {isCornerMap ? <CornerGrid data={data} /> : (
        <div className="flex flex-wrap gap-2">
          {Object.entries(data).map(([k, v]) => {
            if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
              return <div key={k} className="w-full"><p className="text-gray-600 text-xs mb-1">{k.replace(/_/g, ' ')}</p><CornerGrid data={v as Record<string, unknown>} /></div>
            }
            return <span key={k} className="text-xs border border-gray-800 px-2 py-0.5"><span className="text-gray-500">{k}: </span><span className="text-white font-mono">{String(v)}</span></span>
          })}
        </div>
      )}
    </div>
  )
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function Section7({ s }: { s: SessionReport['section_7_setup'] & { raw?: any; source?: string } }) {
  const raw = s.raw as Record<string, unknown> | undefined
  return (
    <div className="space-y-5">
      {s.note && <NoData msg={s.note} />}
      {raw && (
        <>
          {raw.electronics && <SetupBlock label="Electrónica (ABS / TC)" data={raw.electronics as Record<string, unknown>} />}
          {raw.tyres && <SetupBlock label="Neumáticos" data={raw.tyres as Record<string, unknown>} />}
          {raw.brakes && <SetupBlock label="Frenos" data={raw.brakes as Record<string, unknown>} />}
          {raw.suspension && (() => {
            const susp = raw.suspension as Record<string, unknown>
            return <div className="space-y-3"><p className="text-gray-500 text-xs uppercase tracking-wide font-bold">Suspensión</p>{Object.entries(susp).map(([key, val]) => <SetupBlock key={key} label={key.replace(/_/g, ' ')} data={val as Record<string, unknown>} />)}</div>
          })()}
          {raw.diff && <SetupBlock label="Diferencial" data={raw.diff as Record<string, unknown>} />}
          {raw.aero && <SetupBlock label="Aerodinámica" data={raw.aero as Record<string, unknown>} />}
          <div className="flex gap-4 text-xs text-gray-400">
            {raw.fuel_l !== undefined && <span><span className="text-gray-600">Combustible: </span><span className="text-white font-mono">{String(raw.fuel_l)} L</span></span>}
            {raw.final_ratio !== undefined && <span><span className="text-gray-600">Relación final: </span><span className="text-white font-mono">{String(raw.final_ratio)}</span></span>}
          </div>
        </>
      )}
      {!raw && s.tyre_pressures && s.tyre_pressures.length > 0 && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 font-bold">Presiones en pista (CSV):</p>
          <TwoColTable
            headers={['Goma', 'Promedio (PSI)', 'Mínimo', 'Máximo']}
            rows={s.tyre_pressures.map((r) => [
              { value: r.corner }, { value: String(r.avg ?? r.target ?? '—') },
              { value: String((r as {min?: number}).min ?? '—') }, { value: String((r as {max?: number}).max ?? '—') },
            ])}
          />
        </div>
      )}
    </div>
  )
}

function Section8({ s }: { s: NonNullable<SessionReport['section_8_technical']> }) {
  return (
    <div className="space-y-5">
      {(s.strengths ?? []).length > 0 && <div><p className="text-white font-bold text-sm mb-2">Fortalezas identificadas:</p><BulletList items={s.strengths ?? []} /></div>}
      {(s.improvements ?? []).length > 0 && <div><p className="text-white font-bold text-sm mb-2">Áreas de mejora:</p><BulletList items={s.improvements ?? []} /></div>}
      {(s.setup_recommendations ?? []).length > 0 && <div><p className="text-white font-bold text-sm mb-2">Recomendaciones de setup:</p><BulletList items={s.setup_recommendations ?? []} color="text-yellow-400" /></div>}
    </div>
  )
}

function Section9({ opps }: { opps: NonNullable<SessionReport['section_9_opportunities']> }) {
  return (
    <div className="space-y-4">
      {opps.map((op) => (
        <div key={op.rank} className="border border-gray-800 p-4">
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-f1red font-bold text-sm">{op.rank}.</span>
            <span className="text-white font-bold text-sm">{op.title}</span>
            <span className="text-green-400 text-xs font-mono ml-auto">(−{op.estimated_gain_s.toFixed(2)}s)</span>
          </div>
          <p className="text-gray-300 text-sm mb-1">{op.detail}</p>
          <p className="text-gray-500 text-xs">Ocurre en: {op.occurs_in}</p>
        </div>
      ))}
    </div>
  )
}

function Section10({ s }: { s: NonNullable<SessionReport['section_10_action_plan']> }) {
  return (
    <div className="space-y-5">
      <p className="text-white font-bold text-sm">■ 3 Focos principales:</p>
      {s.focuses.map((f, i) => (
        <div key={i} className="border-l-2 border-f1red pl-4">
          <p className="text-white font-bold text-sm">{f.title}</p>
          <p className="text-gray-400 text-sm mt-0.5">Ejercicio: {f.exercise}</p>
          <p className="text-gray-400 text-sm">Objetivo: {f.objective}</p>
        </div>
      ))}
      <div className="border-t border-gray-800 pt-4 space-y-1">
        {(s.target_lap_time ?? 0) > 0 && <p className="text-sm"><span className="text-f1red">■</span> Meta de tiempo: <span className="text-green-400 font-mono font-bold">{s.target_lap_time_fmt || '—'}</span></p>}
        {s.target_consistency_score > 0 && <p className="text-sm"><span className="text-f1red">■</span> Meta Consistency Score: <span className="text-white font-bold">{s.target_consistency_score}+</span></p>}
        <p className="text-sm"><span className="text-f1red">■</span> Timeline estimado: <span className="text-gray-300">{s.timeline}</span></p>
      </div>
    </div>
  )
}

function Section11({ s }: { s: NonNullable<SessionReport['section_11_engineer_diagnosis']> }) {
  return (
    <div className="space-y-5">
      {(s.what_is_working ?? []).length > 0 && <div><p className="text-white font-bold text-sm mb-2">■ LO QUE ESTÁ BIEN</p><BulletList items={s.what_is_working ?? []} /></div>}
      {(s.problems_detected ?? []).length > 0 && <div><p className="text-white font-bold text-sm mb-2">■ PROBLEMAS DETECTADOS</p><BulletList items={s.problems_detected ?? []} color="text-yellow-400" /></div>}
      {(s.driving_style ?? []).length > 0 && <div><p className="text-white font-bold text-sm mb-2">■ ESTILO DE PILOTAJE</p><BulletList items={s.driving_style ?? []} /></div>}
      {(s.setup_recommendations ?? []).length > 0 && (
        <div>
          <p className="text-white font-bold text-sm mb-2">■ RECOMENDACIONES DE SETUP</p>
          {(s.setup_recommendations ?? []).map((r, i) => <p key={i} className="text-sm text-gray-300 mb-2">{i + 1}. {r}</p>)}
        </div>
      )}
      {s.next_session_target && (
        <div className="border border-gray-700 p-4">
          <p className="text-white font-bold text-sm mb-2">■ META PARA LA PRÓXIMA SESIÓN</p>
          <p className="text-gray-300 text-sm">{s.next_session_target}</p>
        </div>
      )}
    </div>
  )
}

// ── Main export ───────────────────────────────────────────────────────────────

interface Props {
  report: SessionReport
  sessionId: string
  backHref: string
  backLabel?: string
  pilotName?: string
}

export default function ReportView({ report, sessionId, backHref, backLabel = '← Volver', pilotName }: Props) {
  const m = report.meta

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <Link href={backHref} className="text-gray-500 text-xs hover:text-white mb-2 inline-block">{backLabel}</Link>
          <h1 className="text-2xl font-bold text-white uppercase tracking-wide">Reporte de Telemetría</h1>
          {pilotName && <p className="text-blue-400 text-xs font-bold mt-0.5">Piloto: {pilotName}</p>}
          <p className="text-gray-500 text-xs mt-1">{m.simulator} · {m.session_date} · {m.tokens_used} tokens</p>
        </div>
        <a href={sessionPdfUrl(sessionId)} target="_blank" rel="noopener noreferrer" className="bg-f1red hover:bg-red-700 text-white px-4 py-2 text-sm font-bold transition-colors whitespace-nowrap">↓ PDF</a>
      </div>

      {/* Portada */}
      <div className="border border-gray-800 p-6 mb-8">
        <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-sm mb-6">
          {[
            ['Piloto', pilotName || m.pilot],
            ['Simulador', m.simulator],
            ['Pista', m.track],
            ['Auto', m.car],
            ['Evento', m.session_type],
            ['Fecha', m.session_date],
            ['Vueltas', String(report.section_1_summary.total_laps)],
            ['Compuesto', m.tyre_compound],
          ].map(([label, val]) => val && (
            <div key={label} className="flex gap-2">
              <span className="text-gray-500 font-bold w-24 shrink-0">{label}:</span>
              <span className="text-white">{val}</span>
            </div>
          ))}
        </div>
        <div className="text-center">
          <p className="text-gray-500 text-xs uppercase tracking-widest mb-1">Mejor Tiempo</p>
          <p className="text-5xl font-bold text-green-400 font-mono tracking-wide">{report.section_1_summary.best_lap_fmt}</p>
        </div>
      </div>

      {/* Section 0 */}
      {report.section_0_track && (
        <>
          <div className="flex items-baseline gap-3 mb-4"><span className="text-f1red font-bold text-lg">0.</span><h2 className="text-white font-bold text-base uppercase tracking-wide">Información del Circuito</h2></div>
          <div className="h-px bg-f1red/40 mb-4" />
          <Section0 track={report.section_0_track} sessionId={sessionId} />
        </>
      )}

      <SectionHeader num={1} title="Resumen de Sesión" /><Section1 s={report.section_1_summary} />
      <SectionHeader num={2} title="Tiempos por Vuelta" /><Section2 laps={report.section_2_lap_table} />
      <SectionHeader num={3} title="Consistency Score" /><Section3 s={report.section_3_consistency} />
      <SectionHeader num={4} title="Análisis de Gomas" />
      {Object.keys(report.section_4_tyres).length > 0 ? <Section4 s={report.section_4_tyres} /> : <NoData msg="El CSV no incluye datos de temperatura/presión de gomas." />}
      <SectionHeader num={5} title="Análisis de Frenos" />
      {Object.keys(report.section_5_brakes).length > 0 ? <Section5 s={report.section_5_brakes} /> : <NoData msg="El CSV no incluye datos de temperatura de frenos." />}
      <SectionHeader num={6} title="G-Forces y Dinámica del Vehículo" />
      {Object.keys(report.section_6_dynamics).length > 0 ? <Section6 s={report.section_6_dynamics} /> : <NoData msg="El CSV no incluye datos de G-forces o suspensión." />}
      <SectionHeader num={7} title="Setup Utilizado en Esta Sesión" /><Section7 s={report.section_7_setup} />
      {report.section_8_technical && <><SectionHeader num={8} title="Análisis Técnico Detallado" /><Section8 s={report.section_8_technical} /></>}
      {report.section_9_opportunities && report.section_9_opportunities.length > 0 && <><SectionHeader num={9} title="Top 5 Oportunidades de Mejora" /><Section9 opps={report.section_9_opportunities} /></>}
      {report.section_10_action_plan && <><SectionHeader num={10} title="Plan de Acción para la Próxima Sesión" /><Section10 s={report.section_10_action_plan} /></>}
      {report.section_11_engineer_diagnosis && <><SectionHeader num={11} title="Diagnóstico del Ingeniero de Pista" /><Section11 s={report.section_11_engineer_diagnosis} /></>}

      {/* Footer */}
      <div className="border-t border-gray-800 mt-12 pt-6 flex justify-between items-center">
        <Link href={backHref} className="text-gray-500 hover:text-white text-sm">{backLabel}</Link>
        <a href={sessionPdfUrl(sessionId)} target="_blank" rel="noopener noreferrer" className="bg-f1red hover:bg-red-700 text-white px-4 py-2 text-sm font-bold transition-colors">↓ DESCARGAR PDF</a>
      </div>
    </div>
  )
}
