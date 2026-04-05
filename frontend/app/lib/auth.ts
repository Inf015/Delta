const TOKEN_KEY  = 'delta_token'
const EMAIL_KEY  = 'delta_email'
const ADMIN_KEY  = 'delta_admin'
const ROLE_KEY   = 'delta_role'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(EMAIL_KEY)
  localStorage.removeItem(ADMIN_KEY)
  localStorage.removeItem(ROLE_KEY)
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

export function getEmail(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(EMAIL_KEY)
}

export function setEmail(email: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(EMAIL_KEY, email)
}

export function getIsAdmin(): boolean {
  if (typeof window === 'undefined') return false
  return localStorage.getItem(ADMIN_KEY) === 'true'
}

export function setIsAdmin(value: boolean): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(ADMIN_KEY, value ? 'true' : 'false')
}

export function getRole(): string {
  if (typeof window === 'undefined') return 'pilot'
  return localStorage.getItem(ROLE_KEY) || 'pilot'
}

export function setRole(role: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(ROLE_KEY, role)
}

export function getIsTechnician(): boolean {
  return getRole() === 'technician'
}
