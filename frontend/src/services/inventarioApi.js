import { http } from './http'

/** Capa de servicio del módulo Inventario (US2). Espeja `contracts/inventario.md`. */
export const inventarioApi = {
  lotes({
    productId,
    tiendaId,
    proximosAVencer = false,
    dias = 7,
    search,
    page = 1,
    size = 25,
  } = {}) {
    return http
      .get('/api/inventario/lotes', {
        params: {
          product_id: productId,
          tienda_id: tiendaId,
          proximos_a_vencer: proximosAVencer,
          dias,
          search: search || undefined,
          page,
          size,
        },
      })
      .then((r) => r.data)
  },

  /** Autocompletado de producto (nombre o id) para los formularios de operación. */
  buscarProductos(q) {
    return http.get('/api/inventario/productos', { params: { q } }).then((r) => r.data)
  },

  /** Vista de stock por SKU (pantalla principal de Inventario). */
  stock({ tiendaId, search, categoria, estado, page = 1, size = 25 } = {}) {
    return http
      .get('/api/inventario/stock', {
        params: {
          tienda_id: tiendaId,
          search: search || undefined,
          categoria: categoria || undefined,
          estado: estado || undefined,
          page,
          size,
        },
      })
      .then((r) => r.data)
  },

  /** Contadores + tasa de merma + unidades en tránsito para la fila de KPIs. */
  stockResumen(tiendaId) {
    return http
      .get('/api/inventario/stock/resumen', { params: { tienda_id: tiendaId } })
      .then((r) => r.data)
  },

  /** "Reordenar": deja una alerta de reposición y avisa al rol de compras. */
  solicitarReposicion({ productId, tiendaId, empleadoId }) {
    return http
      .post('/api/inventario/solicitudes-reposicion', {
        product_id: productId,
        tienda_id: tiendaId,
        empleado_id: empleadoId,
      })
      .then((r) => r.data)
  },

  definirUbicacion({ productId, tiendaId, pasillo, gondola, nivel, empleadoId }) {
    return http
      .put('/api/inventario/ubicacion', {
        product_id: productId,
        tienda_id: tiendaId,
        pasillo,
        gondola: gondola || null,
        nivel: nivel || null,
        empleado_id: empleadoId,
      })
      .then((r) => r.data)
  },

  recepcion({ ordenId, productId, tiendaId, cantidad, fechaVencimiento, codigoLoteProveedor }) {
    return http
      .post('/api/inventario/recepciones', {
        orden_id: ordenId,
        product_id: productId,
        tienda_id: tiendaId,
        cantidad,
        fecha_vencimiento: fechaVencimiento || null,
        codigo_lote_proveedor: codigoLoteProveedor || null,
      })
      .then((r) => r.data)
  },

  ajuste({ productId, tiendaId, cantidadFisica, empleadoId, motivo, observaciones }) {
    return http
      .post('/api/inventario/ajustes', {
        product_id: productId,
        tienda_id: tiendaId,
        cantidad_fisica: cantidadFisica,
        empleado_id: empleadoId,
        motivo: motivo || null,
        observaciones: observaciones || null,
      })
      .then((r) => r.data)
  },

  merma({ productId, tiendaId, cantidad, causa, empleadoId, loteId, destino, observaciones }) {
    return http
      .post('/api/inventario/mermas', {
        product_id: productId,
        tienda_id: tiendaId,
        cantidad,
        causa,
        empleado_id: empleadoId,
        lote_id: loteId || null,
        destino: destino || null,
        observaciones: observaciones || null,
      })
      .then((r) => r.data)
  },

  validarMerma(mermaId, { empleadoId, decision }) {
    return http
      .post(`/api/inventario/mermas/${mermaId}/validar`, {
        empleado_id: empleadoId,
        decision,
      })
      .then((r) => r.data)
  },

  // --- US3 ---
  alertas({ tipo, estado = 'pendiente', tiendaId, search, page = 1, size = 25 } = {}) {
    return http
      .get('/api/inventario/alertas', {
        params: { tipo, estado, tienda_id: tiendaId, search: search || undefined, page, size },
      })
      .then((r) => r.data)
  },

  atenderAlerta(alertaId, empleadoId) {
    return http
      .post(`/api/inventario/alertas/${alertaId}/atender`, { empleado_id: empleadoId })
      .then((r) => r.data)
  },

  jobReposicion(tiendaId) {
    return http
      .post('/api/inventario/jobs/reposicion', null, { params: { tienda_id: tiendaId } })
      .then((r) => r.data)
  },

  jobVencimiento(tiendaId) {
    return http
      .post('/api/inventario/jobs/vencimiento', null, { params: { tienda_id: tiendaId } })
      .then((r) => r.data)
  },

  registrarQuiebre({ productId, tiendaId, empleadoId, demanda }) {
    return http
      .post('/api/inventario/quiebres', {
        product_id: productId,
        tienda_id: tiendaId,
        empleado_id: empleadoId,
        demanda_estimada_no_satisfecha: demanda || null,
      })
      .then((r) => r.data)
  },

  definirStockMaximo({
    productCategory,
    tiendaId,
    cantidadMaxima,
    empleadoId,
    capacidadGondola,
    stockMinimoReorden,
    diasCobertura,
    politicaSobrestock,
  }) {
    return http
      .put('/api/inventario/stock-maximo', {
        product_category: productCategory,
        tienda_id: tiendaId,
        cantidad_maxima: cantidadMaxima,
        empleado_id: empleadoId,
        capacidad_gondola: capacidadGondola || null,
        stock_minimo_reorden: stockMinimoReorden ?? null,
        dias_cobertura: diasCobertura || null,
        politica_sobrestock: politicaSobrestock || null,
      })
      .then((r) => r.data)
  },

  stockMaximo({ tiendaId, productCategory } = {}) {
    return http
      .get('/api/inventario/stock-maximo', {
        params: { tienda_id: tiendaId, product_category: productCategory },
      })
      .then((r) => r.data)
  },

  verificacionAnaquel({
    productId,
    tiendaId,
    disponible,
    empleadoId,
    fecha,
    facingAsignado,
    facingReal,
    eslOk,
    fifoOk,
    observaciones,
  }) {
    return http
      .post('/api/inventario/verificacion-anaquel', {
        product_id: productId,
        tienda_id: tiendaId,
        disponible,
        empleado_id: empleadoId,
        fecha: fecha || null,
        facing_asignado: facingAsignado ?? null,
        facing_real: facingReal ?? null,
        esl_ok: eslOk ?? null,
        fifo_ok: fifoOk ?? null,
        observaciones: observaciones || null,
      })
      .then((r) => r.data)
  },
}
