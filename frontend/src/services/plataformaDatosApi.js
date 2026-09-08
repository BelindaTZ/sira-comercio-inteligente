import { http } from './http'

/**
 * Capa de servicio del módulo Plataforma de Datos (feature 010). Espeja
 * `contracts/plataforma-datos.md`. Toda la regla (carga incremental,
 * idempotencia, reglas de calidad) vive en `data_platform/` — el frontend sólo
 * consulta el control del pipeline (Principio V).
 */
const BASE = '/api/plataforma-datos'

export const plataformaDatosApi = {
  // --- US1: modelo de datos único ---
  modelo() {
    return http.get(`${BASE}/modelo`).then((r) => r.data)
  },

  registrarEntidad({ nombreEntidad, tipo, tablaOrigenPostgres, descripcion }) {
    return http
      .post(`${BASE}/modelo`, {
        nombre_entidad: nombreEntidad,
        tipo,
        tabla_origen_postgres: tablaOrigenPostgres,
        descripcion: descripcion || null,
      })
      .then((r) => r.data)
  },

  actualizarEntidad(entidadId, { activa, descripcion } = {}) {
    const payload = {}
    if (activa !== undefined) payload.activa = activa
    if (descripcion !== undefined) payload.descripcion = descripcion
    return http.patch(`${BASE}/modelo/${entidadId}`, payload).then((r) => r.data)
  },

  // --- US2/US3: monitoreo de corridas ---
  corridas({ entidadId, estado } = {}) {
    return http
      .get(`${BASE}/corridas`, {
        params: { entidad_id: entidadId || undefined, estado: estado || undefined },
      })
      .then((r) => r.data.corridas)
  },

  calidadDeCorrida(corridaId) {
    return http.get(`${BASE}/corridas/${corridaId}/calidad`).then((r) => r.data)
  },

  /** Sólo entorno de desarrollo — fuerza una corrida sin esperar la cadencia diaria. */
  forzarCorrida({ entidadId, tipoCarga = 'incremental' }) {
    return http
      .post(`${BASE}/corridas/forzar`, { entidad_id: entidadId, tipo_carga: tipoCarga })
      .then((r) => r.data)
  },

  // --- US4: política de gobierno de datos ---
  politicaVigente() {
    return http.get(`${BASE}/politica`).then((r) => r.data)
  },

  politicaHistorial() {
    return http.get(`${BASE}/politica/historial`).then((r) => r.data)
  },

  registrarPolitica(texto) {
    return http.post(`${BASE}/politica`, { texto }).then((r) => r.data)
  },
}
