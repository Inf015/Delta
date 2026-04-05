'use client'

import { useEffect, useState } from 'react'
import { getIsAdmin } from '../lib/auth'

export default function AdminNavLink() {
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    setIsAdmin(getIsAdmin())
  }, [])

  if (!isAdmin) return null

  return (
    <a
      href="/admin"
      className="text-f1red hover:text-red-400 text-sm font-bold transition-colors border border-f1red/40 px-2 py-0.5"
    >
      ADMIN
    </a>
  )
}
