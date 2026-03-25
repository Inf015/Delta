import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'SimTelemetry Pro',
  description: 'Análisis de telemetría para sim racing',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="bg-dark text-white min-h-screen font-mono">
        <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6">
          <a href="/" className="text-f1red font-bold text-lg tracking-wider">
            DELTA
          </a>
          <a href="/" className="text-gray-400 hover:text-white text-sm transition-colors">
            Sesiones
          </a>
          <a href="/racing-sessions/new" className="text-gray-400 hover:text-white text-sm transition-colors">
            Nueva sesión
          </a>
          <a href="/compare" className="text-gray-400 hover:text-white text-sm transition-colors">
            Comparar
          </a>
        </nav>
        <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  )
}
