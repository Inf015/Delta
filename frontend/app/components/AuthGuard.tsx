'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { getToken, removeToken } from '../lib/auth'

const PUBLIC_PATHS = ['/login', '/register']

/** Decodifica el payload JWT sin verificar la firma (solo para leer el exp). */
function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return typeof payload.exp === 'number' && payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    if (PUBLIC_PATHS.includes(pathname)) {
      setChecked(true)
      return
    }
    const token = getToken()
    if (!token || isTokenExpired(token)) {
      removeToken()
      router.replace('/login')
    } else {
      setChecked(true)
    }
  }, [pathname, router])

  if (!checked && !PUBLIC_PATHS.includes(pathname)) {
    return null
  }

  return <>{children}</>
}
