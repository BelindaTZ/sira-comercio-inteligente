import { http } from './http'

/**
 * Capa de servicio del módulo Ventas (T034). Espeja `contracts/ventas.md`.
 * Toda la lógica de negocio vive en el backend (Principio V): aquí sólo se
 * traduce llamada ↔ endpoint.
 */
export const ventasApi = {
  iniciar({ tiendaId, cajeroId, householdId = null }) {
    return http
      .post('/api/ventas', {
        tienda_id: tiendaId,
        cajero_id: cajeroId,
        household_id: householdId,
      })
      .then((r) => r.data)
  },

  agregarLinea(ventaId, { productId = null, codigoBarras = null, cantidad }) {
    return http
      .post(`/api/ventas/${ventaId}/lineas`, {
        product_id: productId,
        codigo_barras: codigoBarras,
        cantidad,
      })
      .then((r) => r.data)
  },

  removerLinea(ventaId, lineaId, { autorizaEmpleadoId, motivo }) {
    return http
      .delete(`/api/ventas/${ventaId}/lineas/${lineaId}`, {
        data: { autoriza_empleado_id: autorizaEmpleadoId, motivo },
      })
      .then((r) => r.data)
  },

  pagoTarjeta(ventaId, { monto, escenario = 'aprobado' }) {
    return http
      .post(`/api/ventas/${ventaId}/pago-tarjeta`, { monto, escenario })
      .then((r) => r.data)
  },

  confirmar(ventaId, { medioPagoId, tipoComprobante = 'nota_venta', identificacion, razonSocial }) {
    return http
      .post(`/api/ventas/${ventaId}/confirmar`, {
        medio_pago_id: medioPagoId,
        tipo_comprobante: tipoComprobante,
        identificacion_comprador: identificacion || null,
        razon_social_comprador: razonSocial || null,
      })
      .then((r) => r.data)
  },

  anular(ventaId, { empleadoId, motivo }) {
    return http
      .post(`/api/ventas/${ventaId}/anular`, { empleado_id: empleadoId, motivo })
      .then((r) => r.data)
  },

  /** URL del comprobante — se abre en pestaña nueva al confirmar (FR-004, SC-011). */
  comprobanteUrl(ventaId) {
    const base = import.meta.env.VITE_API_BASE_URL || ''
    return `${base}/api/ventas/${ventaId}/comprobante`
  },

  listar(params = {}) {
    return http.get('/api/ventas', { params }).then((r) => r.data)
  },
}
