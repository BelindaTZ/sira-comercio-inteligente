import { http } from './http'

/**
 * Capa de servicio del módulo Pricing (feature 003). Espeja `contracts/pricing.md`.
 * Toda la regla de negocio vive en el backend (Principio V): márgenes objetivo,
 * motor de ajuste, revisión de margen bajo, comparación de competencia y config.
 */
export const pricingApi = {
  // --- márgenes objetivo / regla de ajuste (FR-001, FR-004) ---
  margenes() {
    return http.get('/api/pricing/margenes').then((r) => r.data)
  },

  actualizarMargen(productCategory, { margenObjetivoPct, factorSensibilidad } = {}) {
    return http
      .patch(`/api/pricing/margenes/${encodeURIComponent(productCategory)}`, {
        margen_objetivo_pct: margenObjetivoPct ?? undefined,
        factor_sensibilidad: factorSensibilidad ?? undefined,
      })
      .then((r) => r.data)
  },

  margenEfectivo(productId) {
    return http.get(`/api/pricing/productos/${productId}/margen-efectivo`).then((r) => r.data)
  },

  // --- propuestas de ajuste (FR-005, FR-006) ---
  propuestas({ estado, productCategory, page, size } = {}) {
    return http
      .get('/api/pricing/propuestas', {
        params: {
          estado: estado || undefined,
          product_category: productCategory || undefined,
          page,
          size,
        },
      })
      .then((r) => r.data)
  },

  aprobarPropuesta(propuestaId) {
    return http.post(`/api/pricing/propuestas/${propuestaId}/aprobar`).then((r) => r.data)
  },

  rechazarPropuesta(propuestaId, motivo) {
    return http
      .post(`/api/pricing/propuestas/${propuestaId}/rechazar`, { motivo: motivo || null })
      .then((r) => r.data)
  },

  // --- margen bajo (FR-011, FR-012) ---
  margenBajo({ tiendaId, revisado, page, size } = {}) {
    return http
      .get('/api/pricing/margen-bajo', {
        params: {
          tienda_id: tiendaId ?? undefined,
          revisado: revisado ?? undefined,
          page,
          size,
        },
      })
      .then((r) => r.data)
  },

  registrarRevision(ventaDetalleId, accionCorrectiva) {
    return http
      .post(`/api/pricing/margen-bajo/${ventaDetalleId}/revision`, {
        accion_correctiva: accionCorrectiva,
      })
      .then((r) => r.data)
  },

  // --- reporte de margen (FR-003, FR-013) ---
  reporteMargen({ fechaDesde, fechaHasta, productCategory } = {}) {
    return http
      .get('/api/pricing/reportes/margen', {
        params: {
          fecha_desde: fechaDesde,
          fecha_hasta: fechaHasta,
          product_category: productCategory || undefined,
        },
      })
      .then((r) => r.data)
  },

  // --- competencia (FR-014, FR-015, FR-016) ---
  competidores({ tipo, ciudad } = {}) {
    return http
      .get('/api/pricing/competidores', {
        params: { tipo: tipo || undefined, ciudad: ciudad || undefined },
      })
      .then((r) => r.data)
  },

  crearCompetidor({ nombre, tipo, ciudad }) {
    return http
      .post('/api/pricing/competidores', { nombre, tipo, ciudad: ciudad || null })
      .then((r) => r.data)
  },

  precioCompetencia(productId) {
    return http.get(`/api/pricing/productos/${productId}/precio-competencia`).then((r) => r.data)
  },

  registrarPrecioCompetencia(
    productId,
    { competidorId, precio, fechaCaptura, tiendaId, esPromocional }
  ) {
    return http
      .post(`/api/pricing/productos/${productId}/precio-competencia`, {
        competidor_id: competidorId,
        precio,
        fecha_captura: fechaCaptura || null,
        tienda_id: tiendaId ?? null,
        es_promocional: !!esPromocional,
      })
      .then((r) => r.data)
  },

  alertasCompetencia({ umbral, page, size } = {}) {
    return http
      .get('/api/pricing/competencia/alertas', {
        params: { umbral: umbral ?? undefined, page, size },
      })
      .then((r) => r.data)
  },

  // --- configuración (FR-004, FR-007, FR-016) ---
  configuracion() {
    return http.get('/api/pricing/configuracion').then((r) => r.data)
  },

  actualizarConfiguracion(clave, valor) {
    return http.patch(`/api/pricing/configuracion/${clave}`, { valor }).then((r) => r.data)
  },
}
