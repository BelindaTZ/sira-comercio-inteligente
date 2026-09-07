import { http } from './http'

/**
 * Capa de servicio del módulo Forecasting (feature 004). Espeja
 * `contracts/pronostico.md`. Toda la regla (entrenamiento, WAPE, respaldo a
 * rotación reciente) vive en el backend (Principio V).
 */
export const forecastingApi = {
  // --- modelos (FR-001 a FR-005) ---
  modelos(estado) {
    return http
      .get('/api/forecasting/modelos', { params: { estado: estado || undefined } })
      .then((r) => r.data)
  },

  detalleModelo(modeloId) {
    return http.get(`/api/forecasting/modelos/${modeloId}`).then((r) => r.data)
  },

  aprobarModelo(modeloId, observaciones) {
    return http
      .post(`/api/forecasting/modelos/${modeloId}/aprobar`, {
        observaciones: observaciones || null,
      })
      .then((r) => r.data)
  },

  rechazarModelo(modeloId, observaciones) {
    return http
      .post(`/api/forecasting/modelos/${modeloId}/rechazar`, { observaciones })
      .then((r) => r.data)
  },

  /** Sólo entorno de desarrollo — fuerza el job mensual de entrenamiento. */
  forzarEntrenamiento() {
    return http.post('/api/forecasting/modelos/entrenar').then((r) => r.data)
  },

  // --- consulta de pronóstico (FR-006 a FR-010) ---
  pronostico(productId, tiendaId, { semana, anio }) {
    return http
      .get(`/api/forecasting/productos/${productId}/tiendas/${tiendaId}/pronostico`, {
        params: { semana, anio },
      })
      .then((r) => r.data)
  },

  // --- monitoreo (FR-011 a FR-013) ---
  monitoreoDeModelo(modeloId) {
    return http.get(`/api/forecasting/modelos/${modeloId}/monitoreo`).then((r) => r.data)
  },

  alertasMonitoreo() {
    return http.get('/api/forecasting/monitoreo/alertas').then((r) => r.data)
  },

  forzarMonitoreo({ semana, anio } = {}) {
    return http
      .post('/api/forecasting/monitoreo/calcular', null, {
        params: { semana: semana || undefined, anio: anio || undefined },
      })
      .then((r) => r.data)
  },

  // --- demanda perdida (FR-014) ---
  demandaPerdida({ fechaDesde, fechaHasta, tiendaId } = {}) {
    return http
      .get('/api/forecasting/reportes/demanda-perdida', {
        params: {
          fecha_desde: fechaDesde,
          fecha_hasta: fechaHasta,
          tienda_id: tiendaId ?? undefined,
        },
      })
      .then((r) => r.data)
  },

  // --- configuración ---
  configuracion() {
    return http.get('/api/forecasting/configuracion').then((r) => r.data)
  },

  actualizarConfiguracion(clave, valor) {
    return http.patch(`/api/forecasting/configuracion/${clave}`, { valor }).then((r) => r.data)
  },
}
