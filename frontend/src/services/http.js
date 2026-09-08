import axios from 'axios'

/**
 * Instancia Axios única para toda la app (Principio XI: ninguna vista llama a
 * `axios` directamente, todo pasa por `src/services/*Api.js`).
 */
export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 15000,
})

// El JWT (feature 008) se guarda en localStorage al iniciar sesión; transporta
// sólo `usuario_id` — el backend resuelve rol y permisos en cada request.
http.interceptors.request.use((config) => {
  let token = null
  try {
    token = localStorage.getItem('sira_token')
  } catch {
    token = null
  }
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

/** Normaliza el error del backend ({error:{code,message}}) a un Error legible. */
http.interceptors.response.use(
  (r) => r,
  (error) => {
    const payload = error.response?.data?.error
    const message = payload?.message || error.message || 'Error de red'
    const err = new Error(message)
    err.code = payload?.code
    err.status = error.response?.status
    err.details = payload?.details
    // Sesión inválida/expirada: limpia el token y manda al login (fuera de /auth).
    if (err.status === 401 && !String(error.config?.url || '').includes('/api/auth/')) {
      try {
        localStorage.removeItem('sira_token')
        localStorage.removeItem('sira_usuario_id')
      } catch {
        /* noop */
      }
      if (!window.location.pathname.startsWith('/auth')) {
        window.location.assign('/auth/login')
      }
    }
    return Promise.reject(err)
  }
)
