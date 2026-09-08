import { http } from './http'

/**
 * Capa de servicio de `ti/dashboards` (feature 009, US2/US3). Espeja
 * `contracts/dashboards-multinivel.md` #2-#5. Sólo lectura de snapshots
 * publicados; el trigger de FR-010 sólo existe fuera de producción.
 */
const BASE = '/api/ti/dashboards'

export const tiDashboardsApi = {
  /** Dashboard táctico de un departamento (`modulo_nombre` ∈ los 6 con Jefe propio). */
  dashboardTactico(moduloNombre) {
    return http.get(`${BASE}/tactico/${encodeURIComponent(moduloNombre)}`).then((r) => r.data)
  },

  /** Verificación diaria de disponibilidad de los dashboards operativos de tienda. */
  verificacionOperativos() {
    return http.get(`${BASE}/operativos/verificacion`).then((r) => r.data)
  },

  /** Sólo los dashboards operativos marcados como no disponibles (alerta del Jefe_TI). */
  alertasOperativos() {
    return http.get(`${BASE}/operativos/alertas`).then((r) => r.data)
  },

  /** Sólo entorno de desarrollo — fuerza la publicación sin esperar el job diario. */
  forzarPublicacion(tipo, { moduloNombre } = {}) {
    return http
      .post(
        `${BASE}/${tipo}/forzar-publicacion`,
        moduloNombre ? { modulo_nombre: moduloNombre } : {}
      )
      .then((r) => r.data)
  },
}
