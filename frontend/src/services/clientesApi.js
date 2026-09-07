import { http } from './http'

/** Capa de servicio del módulo Clientes/Fidelización (feature 002). */
export const clientesApi = {
  listar(params = {}) {
    return http.get('/api/clientes', { params }).then((r) => r.data)
  },

  detalle(householdId) {
    return http.get(`/api/clientes/${householdId}`).then((r) => r.data)
  },

  crear({
    nombre,
    email,
    telefono,
    documentoIdentidad,
    fechaNacimiento,
    consentimientoDatos,
    datosDemograficos,
  }) {
    return http
      .post('/api/clientes', {
        nombre,
        email,
        telefono: telefono || null,
        documento_identidad: documentoIdentidad || null,
        fecha_nacimiento: fechaNacimiento || null,
        consentimiento_datos: consentimientoDatos,
        datos_demograficos: datosDemograficos || null,
      })
      .then((r) => r.data)
  },

  actualizar(householdId, patch) {
    return http.patch(`/api/clientes/${householdId}`, patch).then((r) => r.data)
  },

  darDeBaja(householdId) {
    return http.delete(`/api/clientes/${householdId}`).then((r) => r.data)
  },

  // --- niveles de fidelización (US2) ---
  niveles() {
    return http.get('/api/clientes/niveles-fidelizacion').then((r) => r.data)
  },

  ajustarUmbral(nivelId, umbralClvMin) {
    return http
      .patch(`/api/clientes/niveles-fidelizacion/${nivelId}`, { umbral_clv_min: umbralClvMin })
      .then((r) => r.data)
  },

  // --- riesgo de fuga (US3) ---
  riesgoFuga({ severidad, page, size } = {}) {
    return http
      .get('/api/clientes/riesgo-fuga', {
        params: { severidad: severidad || undefined, page, size },
      })
      .then((r) => r.data)
  },

  // --- campañas por hito (US4) ---
  tasaRedencion(tipoEvento) {
    return http
      .get('/api/clientes/cupones/tasa-redencion', {
        params: { tipo_evento: tipoEvento || undefined },
      })
      .then((r) => r.data)
  },

  eventosCliente(householdId) {
    return http.get(`/api/clientes/${householdId}/eventos`).then((r) => r.data)
  },

  // --- campañas de reactivación (US5) ---
  listarCampanas(categoriaSira) {
    return http
      .get('/api/clientes/campanas', { params: { categoria_sira: categoriaSira || undefined } })
      .then((r) => r.data)
  },

  detalleCampana(campaignId) {
    return http.get(`/api/clientes/campanas/${campaignId}`).then((r) => r.data)
  },

  crearCampana({ startDate, endDate, miembros }) {
    return http
      .post('/api/clientes/campanas', {
        categoria_sira: 'reactivacion',
        start_date: startDate,
        end_date: endDate,
        miembros,
      })
      .then((r) => r.data)
  },

  enviarCampana(campaignId) {
    return http.post(`/api/clientes/campanas/${campaignId}/enviar`).then((r) => r.data)
  },

  cerrarCampana(campaignId) {
    return http.post(`/api/clientes/campanas/${campaignId}/cerrar`).then((r) => r.data)
  },

  decidirCampana(campaignId, decision) {
    return http
      .post(`/api/clientes/campanas/${campaignId}/decision`, { decision })
      .then((r) => r.data)
  },
}
