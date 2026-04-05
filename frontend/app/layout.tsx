import type { Metadata } from 'next'
import './globals.css'
import AuthGuard from './components/AuthGuard'
import NavUser from './components/NavUser'
import AdminNavLink from './components/AdminNavLink'
import TechNavLink from './components/TechNavLink'

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
          <TechNavLink />
          <AdminNavLink />
          <a
            href="/delta_guia_usuario.pdf"
            target="_blank"
            className="ml-auto text-gray-500 hover:text-white text-xs border border-gray-800 hover:border-gray-600 px-3 py-1.5 transition-colors"
          >
            📄 Guía
          </a>
          <NavUser />
        </nav>
        <main className="max-w-5xl mx-auto px-6 py-8">
          <AuthGuard>{children}</AuthGuard>
        </main>
      </body>
    </html>
  )
}
