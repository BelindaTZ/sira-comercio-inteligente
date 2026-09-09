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

  /** KPIs de la cabecera del Catálogo Maestro. */
  resumen() {
    return http.get('/api/catalogo/resumen').then((r) => r.data)
  },

  /** Matriz de precios: producto + margen real vs. objetivo + estado. */
  matrizPrecios({ search, categoria, margen, activo, page = 1, size = 25 } = {}) {
    return http
      .get('/api/catalogo/precios', {
        params: {
          search: search || undefined,
          categoria: categoria || undefined,
          margen: margen || undefined,
          activo: activo === undefined ? undefined : activo,
          page,
          size,
        },
      })
      .then((r) => r.data)
  },

  /** Reglas de recargo por canal (Tienda Física / Delivery App / E-Commerce). */
  canales() {
    return http.get('/api/catalogo/precios/canales').then((r) => r.data)
  },

  actualizarCanal(canal, { markupPct, activo } = {}) {
    return http
      .patch(`/api/catalogo/precios/canales/${canal}`, {
        markup_pct: markupPct ?? undefined,
        activo: activo ?? undefined,
      })
      .then((r) => r.data)
  },

  /** Simulador de impacto: proyecta margen y ganancia mensual ante un cambio de PVP. */
  simularPrecio(productId, deltaPct) {
    return http
      .post(`/api/catalogo/productos/${productId}/simular-precio`, { delta_pct: deltaPct })
      .then((r) => r.data)
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

  /** Asigna una foto genérica de Unsplash por el nombre del producto. */
  imagenAuto(productId) {
    return http.post(`/api/catalogo/productos/${productId}/imagen-auto`).then((r) => r.data)
  },

  /** Sube una imagen propia (File) al bucket y la fija como imagen del producto. */
  subirImagen(productId, file) {
    const fd = new FormData()
    fd.append('archivo', file)
    return http
      .post(`/api/catalogo/productos/${productId}/imagen`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  darDeBaja(productId) {
    return http.delete(`/api/catalogo/productos/${productId}`).then((r) => r.data)
  },
}
