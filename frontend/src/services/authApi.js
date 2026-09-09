import { http } from './http'

/**
 * Capa de servicio de autenticación (feature 008). El JWT que devuelve `login`
 * transporta sólo `usuario_id`; el backend resuelve el rol y los permisos en cada
 * request (research.md Decisión 1). El token se guarda en `localStorage` bajo
 * `sira_token` y lo adjunta el interceptor de `http.js`.
 */
const TOKEN_KEY = 'sira_token'

export const authApi = {
  login(username, password) {
    return http.post('/api/auth/login', { username, password }).then((r) => {
      try {
        localStorage.setItem(TOKEN_KEY, r.data.access_token)
        localStorage.setItem('sira_usuario_id', String(r.data.usuario_id))
      } catch {
        /* almacenamiento no disponible: la sesión vive sólo en memoria de esta pestaña */
      }
      return r.data
    })
  },

  logout() {
    try {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem('sira_usuario_id')
    } catch {
      /* noop */
    }
  },

  /** Identidad de la sesión + módulos visibles para el rol (feature 013). */
  me() {
    return http.get('/api/auth/me').then((r) => r.data)
  },

  /** El propio PIN de autorización (feature 018) — `{pin, puede_autorizar}`. */
  miPin() {
    return http.get('/api/auth/mi-pin').then((r) => r.data)
  },

  token() {
    try {
      return localStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },

  estaAutenticado() {
    return Boolean(this.token())
  },

  solicitarRecuperacion(email) {
    return http.post('/api/auth/recuperar-password', { email }).then((r) => r.data)
  },

  confirmarRecuperacion(token, passwordNueva) {
    return http
      .post('/api/auth/recuperar-password/confirmar', {
        token,
        password_nueva: passwordNueva,
      })
      .then((r) => r.data)
  },

  cambiarMiPassword(passwordActual, passwordNueva) {
    return http
      .patch('/api/auth/mi-password', {
        password_actual: passwordActual,
        password_nueva: passwordNueva,
      })
      .then((r) => r.data)
  },
}
