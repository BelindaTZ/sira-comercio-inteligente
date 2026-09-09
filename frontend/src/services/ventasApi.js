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

  /** Asocia (o quita, con null) un cliente a la venta en curso — sirve con líneas ya cargadas. */
  vincularCliente(ventaId, householdId) {
    return http
      .patch(`/api/ventas/${ventaId}/cliente`, { household_id: householdId ?? null })
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

  removerLinea(ventaId, lineaId, { autorizaEmpleadoId, autorizaPin, motivo }) {
    return http
      .delete(`/api/ventas/${ventaId}/lineas/${lineaId}`, {
        data: {
          autoriza_empleado_id: autorizaEmpleadoId ?? undefined,
          autoriza_pin: autorizaPin || undefined,
          motivo,
        },
      })
      .then((r) => r.data)
  },

  /**
   * FR-009/FR-010 (feature 003) — descuento manual con autorización obligatoria
   * de un Encargado_Tienda (o superior) distinto del cajero, sin excepción por
   * monto. El autorizador se identifica por su PIN (feature 018).
   */
  aplicarDescuento(
    ventaId,
    lineaId,
    { tipo, valor, motivo, empleadoAplicaId, empleadoAutorizaId, autorizaPin }
  ) {
    return http
      .post(`/api/ventas/${ventaId}/lineas/${lineaId}/descuento`, {
        tipo,
        valor,
        motivo,
        empleado_aplica_id: empleadoAplicaId,
        empleado_autoriza_id: empleadoAutorizaId ?? undefined,
        autoriza_pin: autorizaPin || undefined,
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

  /**
   * Descarga el comprobante (PDF) autenticado y devuelve un blob URL para abrirlo
   * o imprimirlo. `window.open` directo no sirve: el endpoint exige el JWT y el
   * navegador no lo adjunta en una pestaña nueva.
   */
  async comprobanteBlobUrl(ventaId) {
    const r = await http.get(`/api/ventas/${ventaId}/comprobante`, { responseType: 'blob' })
    return URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }))
  },

  /** Envía el comprobante (PDF) al correo del cliente registrado en la venta. */
  enviarComprobanteEmail(ventaId) {
    return http.post(`/api/ventas/${ventaId}/comprobante/email`).then((r) => r.data)
  },

  listar(params = {}) {
    return http.get('/api/ventas', { params }).then((r) => r.data)
  },

  // --- feature 007: medios de pago, datáfono disponible, tiempo de cobro ---
  mediosPagoDisponibles() {
    return http.get('/api/ventas/medios-pago/disponibles').then((r) => r.data)
  },

  mediosPago(aprobado) {
    return http
      .get('/api/ventas/medios-pago', { params: { aprobado: aprobado ?? undefined } })
      .then((r) => r.data)
  },

  altaMedioPago(nombre) {
    return http.post('/api/ventas/medios-pago', { nombre }).then((r) => r.data)
  },

  bajaMedioPago(medioPagoId) {
    return http.patch(`/api/ventas/medios-pago/${medioPagoId}/baja`).then((r) => r.data)
  },

  datafonoDisponible(cajaId) {
    return http.get(`/api/ventas/cajas/${cajaId}/datafono-disponible`).then((r) => r.data)
  },

  cajas(tiendaId) {
    return http
      .get('/api/ventas/cajas', { params: { tienda_id: tiendaId ?? undefined } })
      .then((r) => r.data)
  },

  /** Grid de productos del POS (registro rápido) — con precio y stock en la tienda. */
  catalogo({ tiendaId, search, categoria, page = 1, size = 24 } = {}) {
    return http
      .get('/api/ventas/catalogo', {
        params: {
          tienda_id: tiendaId ?? undefined,
          search: search || undefined,
          categoria: categoria || undefined,
          page,
          size,
        },
      })
      .then((r) => r.data)
  },

  catalogoCategorias(tiendaId) {
    return http
      .get('/api/ventas/catalogo/categorias', { params: { tienda_id: tiendaId ?? undefined } })
      .then((r) => r.data)
  },

  tiempoCobroSemanal(cajaId, { semana, anio } = {}) {
    return http
      .get(`/api/ventas/cajas/${cajaId}/tiempo-cobro-semanal`, {
        params: { semana, anio: anio ?? undefined },
      })
      .then((r) => r.data)
  },

  tiempoCobroMensual({ mes, anio }) {
    return http
      .get('/api/ventas/tiendas/tiempo-cobro-mensual', { params: { mes, anio } })
      .then((r) => r.data)
  },
}
