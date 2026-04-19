/**
 * Proxy catch-all: reenvía todas las peticiones /api/* al backend FastAPI.
 * Corre server-side, por lo que el browser nunca ve http://api:8000.
 * Sigue redirects internamente para evitar que lleguen al browser.
 */
import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.API_URL || 'http://api:8000'

async function proxy(request: NextRequest): Promise<NextResponse> {
  const url = `${API_URL}${request.nextUrl.pathname}${request.nextUrl.search}`

  const headers = new Headers(request.headers)
  headers.delete('host')
  headers.delete('connection')

  const isBodyMethod = !['GET', 'HEAD'].includes(request.method)
  const body = isBodyMethod ? await request.blob() : undefined

  const res = await fetch(url, {
    method: request.method,
    headers,
    body,
    redirect: 'follow',
  })

  const resHeaders = new Headers(res.headers)
  resHeaders.delete('content-encoding')
  resHeaders.delete('transfer-encoding')

  return new NextResponse(res.body, {
    status: res.status,
    headers: resHeaders,
  })
}

export const GET     = proxy
export const POST    = proxy
export const PUT     = proxy
export const PATCH   = proxy
export const DELETE  = proxy
export const OPTIONS = proxy
