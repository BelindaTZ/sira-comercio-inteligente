import { http } from './http'

/**
 * Capa de servicio del módulo Promociones (feature 005). Espeja
 * `contracts/promociones.md`. Toda la regla (afinidad, ABC, liquidación) vive en
 * el backend (Principio V).
 */
export const promocionesApi = {
  // --- afinidad (FR-001 a FR-005) ---
  reglasAfinidad(estado) {
    return http
      .get('/api/promociones/reglas-afinidad', { params: { estado: estado || undefined } })
      .then((r) => r.data)
  },

  desactivarRegla(reglaId, motivo) {
    return http
      .post(`/api/promociones/reglas-afinidad/${reglaId}/desactivar`, { motivo: motivo || null })
      .then((r) => r.data)
  },

  /** Recomendación de cross-sell para el carrito actual (consumida por el POS). */
  recomendacionCrossSell(productIds) {
    return http
      .get('/api/promociones/recomendacion-cross-sell', {
        params: { product_ids: (productIds || []).join(',') },
      })
      .then((r) => r.data)
  },

  forzarCalculoAfinidad() {
    return http.post('/api/promociones/reglas-afinidad/calcular').then((r) => r.data)
  },

  // --- cupón de afinidad (FR-006 a FR-008) ---
  cuponesAfinidad(householdId) {
    return http
      .get('/api/promociones/cupones-afinidad', {
        params: { household_id: householdId ?? undefined },
      })
      .then((r) => r.data)
  },

  tasaRedencionAfinidad() {
    return http.get('/api/promociones/cupones-afinidad/tasa-redencion').then((r) => r.data)
  },

  // --- clasificación ABC (FR-009, FR-010) ---
  cambiosAbc(cambiosDesde) {
    return http
      .get('/api/promociones/clasificacion-abc', {
        params: { cambios_desde: cambiosDesde || undefined },
      })
      .then((r) => r.data)
  },

  forzarClasificacionAbc() {
    return http.post('/api/promociones/clasificacion-abc/calcular').then((r) => r.data)
  },

  // --- liquidación (FR-011 a FR-014) ---
  reglaLiquidacion() {
    return http.get('/api/promociones/liquidacion/reglas').then((r) => r.data)
  },

  actualizarReglaLiquidacion({ rotacionMinima, descuento } = {}) {
    return http
      .patch('/api/promociones/liquidacion/reglas', {
        rotacion_minima_liquidacion_semanal: rotacionMinima ?? undefined,
        descuento_liquidacion_pct: descuento ?? undefined,
      })
      .then((r) => r.data)
  },

  candidatosLiquidacion({ tiendaId, semana, anio } = {}) {
    return http
      .get('/api/promociones/liquidacion/candidatos', {
        params: {
          tienda_id: tiendaId ?? undefined,
          semana: semana ?? undefined,
          anio: anio ?? undefined,
        },
      })
      .then((r) => r.data)
  },

  ejecutarCandidato(candidatoId) {
    return http
      .post(`/api/promociones/liquidacion/candidatos/${candidatoId}/ejecutar`)
      .then((r) => r.data)
  },

  forzarCandidatos() {
    return http.post('/api/promociones/liquidacion/candidatos/calcular').then((r) => r.data)
  },

  // --- colocación promocional (FR-015, FR-016) ---
  colocaciones({ tiendaId, semana, anio } = {}) {
    return http
      .get('/api/promociones/colocaciones', {
        params: {
          tienda_id: tiendaId ?? undefined,
          semana: semana ?? undefined,
          anio: anio ?? undefined,
        },
      })
      .then((r) => r.data)
  },

  registrarColocacion({ productId, tiendaId, displayLocation, mailerLocation, semana, anio }) {
    return http
      .post('/api/promociones/colocaciones', {
        product_id: productId,
        tienda_id: tiendaId,
        display_location: displayLocation || null,
        mailer_location: mailerLocation || null,
        semana,
        anio,
      })
      .then((r) => r.data)
  },

  efectoColocacion(promocionId) {
    return http.get(`/api/promociones/colocaciones/${promocionId}/efecto`).then((r) => r.data)
  },
}
