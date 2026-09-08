import { http } from './http'

/**
 * Capa de servicio del módulo Caja (feature 006). Espeja
 * `contracts/caja-mermas-fraude.md`. Toda la regla (diferencia de cuadre,
 * conformidad de datáfonos, % de merma) vive en el backend (Principio V).
 */
export const cajaApi = {
  // --- apertura y cuadre (FR-001 a FR-005) ---
  registrarApertura({ cajaId, fondoInicial }) {
    return http
      .post('/api/caja/apertura', { caja_id: cajaId, fondo_inicial: fondoInicial })
      .then((r) => r.data)
  },

  registrarCierre({ cajaId, totalRegistrado }) {
    return http
      .post('/api/caja/cierre', { caja_id: cajaId, total_registrado: totalRegistrado })
      .then((r) => r.data)
  },

  cierres({ tiendaId, fecha } = {}) {
    return http
      .get('/api/caja/cierres', {
        params: { tienda_id: tiendaId ?? undefined, fecha: fecha || undefined },
      })
      .then((r) => r.data)
  },

  // --- datáfonos (FR-006 a FR-008) ---
  datafonos(estado) {
    return http
      .get('/api/caja/datafonos', { params: { estado: estado || undefined } })
      .then((r) => r.data)
  },

  actualizarDatafono(datafonoId, versionFirmwareNueva) {
    return http
      .patch(`/api/caja/datafonos/${datafonoId}/actualizar`, {
        version_firmware_nueva: versionFirmwareNueva,
      })
      .then((r) => r.data)
  },

  configuracionSeguridad() {
    return http.get('/api/caja/configuracion-seguridad-pagos').then((r) => r.data)
  },

  definirEstandarSeguridad(versionMinimaFirmware) {
    return http
      .put('/api/caja/configuracion-seguridad-pagos', {
        version_minima_firmware: versionMinimaFirmware,
      })
      .then((r) => r.data)
  },

  // --- reporte mensual de patrones y escalamiento (FR-009 a FR-011) ---
  reporteDiferencias({ mes, anio }) {
    return http.get('/api/caja/reporte-diferencias', { params: { mes, anio } }).then((r) => r.data)
  },

  abrirIncidente({ empleadoId, cierreId, ajusteId, descripcion }) {
    return http
      .post('/api/caja/incidentes-fraude', {
        empleado_id: empleadoId,
        cierre_id: cierreId ?? null,
        ajuste_id: ajusteId ?? null,
        descripcion,
      })
      .then((r) => r.data)
  },

  // --- incidentes y protocolo (FR-012 a FR-016) ---
  incidentes(estado) {
    return http
      .get('/api/caja/incidentes-fraude', { params: { estado: estado || undefined } })
      .then((r) => r.data)
  },

  protocolo() {
    return http.get('/api/caja/protocolo-escalamiento').then((r) => r.data)
  },

  definirProtocolo(texto) {
    return http.put('/api/caja/protocolo-escalamiento', { texto }).then((r) => r.data)
  },

  aplicarProtocolo(incidenteId, accionesTomadas) {
    return http
      .patch(`/api/caja/incidentes-fraude/${incidenteId}/aplicar-protocolo`, {
        acciones_tomadas: accionesTomadas,
      })
      .then((r) => r.data)
  },

  cerrarIncidente(incidenteId, resultado) {
    return http
      .patch(`/api/caja/incidentes-fraude/${incidenteId}/cerrar`, { resultado })
      .then((r) => r.data)
  },

  // --- umbral de merma y seguimiento semanal (FR-017 a FR-019) ---
  umbralesMerma() {
    return http.get('/api/caja/umbral-merma').then((r) => r.data)
  },

  definirUmbralMerma(productCategory, porcentajeUmbral) {
    return http
      .put(`/api/caja/umbral-merma/${encodeURIComponent(productCategory)}`, {
        porcentaje_umbral: porcentajeUmbral,
      })
      .then((r) => r.data)
  },

  seguimientoMermaSemanal(tiendaId, { semana, anio } = {}) {
    return http
      .get(`/api/caja/tiendas/${tiendaId}/seguimiento-merma-semanal`, {
        params: { semana, anio: anio ?? undefined },
      })
      .then((r) => r.data)
  },

  // --- feature 007: disponibilidad de datáfonos, incidentes de seguridad, política ---
  datafonoFueraServicio(datafonoId) {
    return http.patch(`/api/caja/datafonos/${datafonoId}/fuera-servicio`).then((r) => r.data)
  },

  datafonoRestablecer(datafonoId) {
    return http.patch(`/api/caja/datafonos/${datafonoId}/restablecer`).then((r) => r.data)
  },

  incidentesSeguridad(estado) {
    return http
      .get('/api/caja/incidentes-seguridad-pago', { params: { estado: estado || undefined } })
      .then((r) => r.data)
  },

  registrarIncidenteSeguridad({ datafonoId, descripcion }) {
    return http
      .post('/api/caja/incidentes-seguridad-pago', {
        datafono_id: datafonoId ?? null,
        descripcion,
      })
      .then((r) => r.data)
  },

  transicionarIncidenteSeguridad(incidenteId, estadoNuevo) {
    return http
      .patch(`/api/caja/incidentes-seguridad-pago/${incidenteId}/transicionar`, {
        estado_nuevo: estadoNuevo,
      })
      .then((r) => r.data)
  },

  conteoIncidentesSeguridad({ desde, hasta } = {}) {
    return http
      .get('/api/caja/incidentes-seguridad-pago/conteo', {
        params: { desde: desde || undefined, hasta: hasta || undefined },
      })
      .then((r) => r.data)
  },

  politicaSeguridad() {
    return http.get('/api/caja/politica-seguridad-pagos').then((r) => r.data)
  },

  politicaSeguridadPorId(politicaId) {
    return http.get(`/api/caja/politica-seguridad-pagos/${politicaId}`).then((r) => r.data)
  },

  definirPoliticaSeguridad(texto) {
    return http.put('/api/caja/politica-seguridad-pagos', { texto }).then((r) => r.data)
  },
}
