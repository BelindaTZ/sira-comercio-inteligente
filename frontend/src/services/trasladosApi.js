import { http } from './http'

/**
 * Capa de servicio del módulo Traslados (feature 012) — visibilidad de stock
 * entre sucursales y ciclo solicitud → resolución → despacho → recepción.
 */
export const trasladosApi = {
  tiendas() {
    return http.get('/api/traslados/tiendas').then((r) => r.data)
  },

  disponibilidadSucursales(productId) {
    return http
      .get(`/api/traslados/productos/${productId}/disponibilidad-sucursales`)
      .then((r) => r.data)
  },

  listar({ estado, tiendaOrigenId, direccion } = {}) {
    return http
      .get('/api/traslados', {
        params: {
          estado: estado || undefined,
          tienda_origen_id: tiendaOrigenId || undefined,
          direccion: direccion || undefined,
        },
      })
      .then((r) => r.data)
  },

  solicitar({ productId, tiendaOrigenId, tiendaDestinoId, cantidad }) {
    return http
      .post('/api/traslados', {
        product_id: productId,
        tienda_origen_id: tiendaOrigenId,
        tienda_destino_id: tiendaDestinoId,
        cantidad,
      })
      .then((r) => r.data)
  },

  resolver(trasladoId, decision, motivo) {
    return http
      .patch(`/api/traslados/${trasladoId}/resolucion`, { decision, motivo: motivo || null })
      .then((r) => r.data)
  },

  confirmarRecepcion(trasladoId) {
    return http.patch(`/api/traslados/${trasladoId}/recepcion`).then((r) => r.data)
  },

  cancelar(trasladoId) {
    return http.patch(`/api/traslados/${trasladoId}/cancelacion`).then((r) => r.data)
  },

  reporteSemanal({ desde, hasta }) {
    return http
      .get('/api/traslados/reporte-semanal', { params: { desde, hasta } })
      .then((r) => r.data)
  },
}
