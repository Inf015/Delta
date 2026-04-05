'use client'

import { useEffect, useState } from 'react'
import { getIsTechnician } from '../lib/auth'

export default function TechNavLink() {
  const [isTech, setIsTech] = useState(false)

  useEffect(() => {
    setIsTech(getIsTechnician())
  }, [])

  if (!isTech) return null

  return (
    <a
      href="/technician"
      className="text-blue-400 hover:text-blue-300 text-sm font-bold transition-colors border border-blue-400/40 px-2 py-0.5"
    >
      EQUIPO
    </a>
  )
}
