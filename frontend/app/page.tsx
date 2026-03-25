import Link from 'next/link'
import { getRacingSessions } from './lib/api'

export default async function Dashboard() {
  const sessions = await getRacingSessions()

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Sesiones</h1>
          <p className="text-gray-500 text-sm mt-1">
            {sessions.length} sesión{sessions.length !== 1 ? 'es' : ''} registrada{sessions.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Link
          href="/racing-sessions/new"
          className="bg-f1red hover:bg-red-700 text-white px-4 py-2 text-sm font-bold transition-colors"
        >
          + NUEVA SESIÓN
        </Link>
      </div>

      {sessions.length === 0 ? (
        <div className="border border-gray-800 p-12 text-center">
          <p className="text-gray-500 mb-4">Sin sesiones todavía.</p>
          <Link href="/upload" className="text-f1red hover:underline text-sm">
            Subir tu primer CSV →
          </Link>
        </div>
      ) : (
        <div className="border border-gray-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
                <th className="text-left px-4 py-3">Pista</th>
                <th className="text-left px-4 py-3">Auto</th>
                <th className="text-left px-4 py-3">Sim</th>
                <th className="text-left px-4 py-3">Fecha</th>
                <th className="text-right px-4 py-3">Vueltas</th>
                <th className="text-right px-4 py-3">Mejor tiempo</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s, i) => (
                <tr
                  key={s.id}
                  className={`border-b border-gray-900 hover:bg-gray-900 transition-colors ${
                    i % 2 === 0 ? '' : 'bg-gray-950'
                  }`}
                >
                  <td className="px-4 py-3 text-white">{s.track}</td>
                  <td className="px-4 py-3 text-gray-400">{s.car}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs bg-gray-800 px-2 py-0.5 text-gray-300">
                      {s.simulator}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{s.session_date || '—'}</td>
                  <td className="px-4 py-3 text-right text-gray-400">{s.lap_count}</td>
                  <td className="px-4 py-3 text-right font-bold text-green-400">
                    {s.best_lap_fmt}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/racing-sessions/${s.id}`}
                      className="text-f1red hover:underline text-xs"
                    >
                      Ver →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
