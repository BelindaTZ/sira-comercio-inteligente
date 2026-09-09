import { http } from './http'

/** Capa de servicio del módulo Compras (US3). Espeja `contracts/compras.md`. */
export const comprasApi = {
  sugerencias(tiendaId) {
    return http
      .get('/api/compras/sugerencias', { params: { tienda_id: tiendaId } })
      .then((r) => r.data)
  },

  proveedores() {
    return http.get('/api/compras/proveedores').then((r) => r.data)
  },

  crearProveedor(data) {
    return http.post('/api/compras/proveedores', data).then((r) => r.data)
  },

  respuestaProveedor(ordenId, { decision, canal, motivo }) {
    return http
      .post(`/api/compras/ordenes/${ordenId}/respuesta-proveedor`, { decision, canal, motivo })
      .then((r) => r.data)
  },

  actualizarProveedor(id, data) {
    return http.patch(`/api/compras/proveedores/${id}`, data).then((r) => r.data)
  },

  crearOrden({ proveedorId, tiendaId, empleadoId, tipo = 'programada', lineas, motivoDesviacion }) {
    return http
      .post('/api/compras/ordenes', {
        proveedor_id: proveedorId,
        tienda_id: tiendaId,
        empleado_id: empleadoId,
        tipo,
        lineas,
        motivo_desviacion: motivoDesviacion || null,
      })
      .then((r) => r.data)
  },

  ordenes({ tiendaId, estado } = {}) {
    return http
      .get('/api/compras/ordenes', {
        params: {
          tienda_id: tiendaId ?? undefined,
          estado: estado ?? undefined,
        },
      })
      .then((r) => r.data)
  },

  ordenDetalle(ordenId) {
    return http.get(`/api/compras/ordenes/${ordenId}`).then((r) => r.data)
  },

  /** Órdenes en estado 'recibida' — selector del registro de factura (Finanzas). */
  ordenesFacturables() {
    return http.get('/api/compras/ordenes-facturables').then((r) => r.data)
  },

  aprobarOrden(ordenId) {
    return http.post(`/api/compras/ordenes/${ordenId}/aprobar`).then((r) => r.data)
  },

  pedidoEspecial(ordenId, motivo) {
    return http
      .post(`/api/compras/ordenes/${ordenId}/pedido-especial`, { motivo })
      .then((r) => r.data)
  },

  crearFactura({
    ordenId,
    numeroFactura,
    montoTotal,
    fechaEmision,
    fechaVencimiento,
    empleadoRegistraId,
  }) {
    return http
      .post('/api/compras/facturas', {
        orden_id: ordenId,
        numero_factura: numeroFactura,
        monto_total: montoTotal,
        fecha_emision: fechaEmision,
        fecha_vencimiento: fechaVencimiento,
        empleado_registra_id: empleadoRegistraId,
      })
      .then((r) => r.data)
  },

  facturas(params = {}) {
    return http.get('/api/compras/facturas', { params }).then((r) => r.data)
  },

  resumenCuentasPorPagar(desde, hasta) {
    return http
      .get('/api/compras/facturas/resumen', { params: { desde, hasta } })
      .then((r) => r.data)
  },

  reporteAutomaticoManual(mes) {
    return http
      .get('/api/compras/reportes/automatico-vs-manual', { params: { mes } })
      .then((r) => r.data)
  },

  // --- historial proveedor↔producto (Ronda 11, FR-044) ---
  productosDeProveedor(proveedorId) {
    return http.get(`/api/compras/proveedores/${proveedorId}/productos`).then((r) => r.data)
  },

  proveedoresDeProducto(productId) {
    return http.get(`/api/compras/productos/${productId}/proveedores`).then((r) => r.data)
  },

  registrarPago(
    facturaId,
    { monto, medioPagoId, referencia, empleadoRegistraId, empleadoAutorizaId }
  ) {
    return http
      .post(`/api/compras/facturas/${facturaId}/pagos`, {
        monto,
        medio_pago_id: medioPagoId,
        referencia: referencia || null,
        empleado_registra_id: empleadoRegistraId,
        empleado_autoriza_id: empleadoAutorizaId,
      })
      .then((r) => r.data)
  },
}
