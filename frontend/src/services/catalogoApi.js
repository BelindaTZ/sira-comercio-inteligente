import { http } from './http'

/** Capa de servicio del módulo Catálogo (US4). Espeja `contracts/catalogo.md`. */
export const catalogoApi = {
  listar(params = {}) {
    return http.get('/api/catalogo/productos', { params }).then((r) => r.data)
  },

  /** Categorías existentes (valores distintos de `product_category`). */
  categorias() {
    return http.get('/api/catalogo/categorias').then((r) => r.data)
  },

  crear({
    codigoBarras,
    nombre,
    categoria,
    marca,
    costo,
    precioBase,
    esPerecedero,
    vidaUtilDias,
    clasificacion,
  }) {
    return http
      .post('/api/catalogo/productos', {
        codigo_barras: codigoBarras,
        nombre: nombre || null,
        categoria: categoria || null,
        marca: marca || null,
        costo,
        precio_base: precioBase,
        es_perecedero: esPerecedero,
        vida_util_dias: vidaUtilDias || null,
        clasificacion,
      })
      .then((r) => r.data)
  },

  actualizar(productId, patch) {
    return http.patch(`/api/catalogo/productos/${productId}`, patch).then((r) => r.data)
  },

  darDeBaja(productId) {
    return http.delete(`/api/catalogo/productos/${productId}`).then((r) => r.data)
  },
}
