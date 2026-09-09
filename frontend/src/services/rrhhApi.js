import { http } from './http'

/**
 * Capa de servicio del módulo RRHH.
 * - Feature 008: CRUD base de empleado.
 * - Feature 011: puestos críticos, retención, capacitación (con fan-out), clima
 *   laboral cruzado con rotación y plan de sucesión.
 */
export const rrhhApi = {
  crearEmpleado({ nombre, puestoId, tiendaId, email, telefono, fechaContratacion }) {
    return http
      .post('/api/rrhh/empleados', {
        nombre,
        puesto_id: puestoId,
        tienda_id: tiendaId ?? null,
        email: email || null,
        telefono: telefono || null,
        fecha_contratacion: fechaContratacion,
      })
      .then((r) => r.data)
  },

  obtenerEmpleado(empleadoId) {
    return http.get(`/api/rrhh/empleados/${empleadoId}`).then((r) => r.data)
  },

  listarEmpleados({ search, activo } = {}) {
    return http
      .get('/api/rrhh/empleados', {
        params: { search: search || undefined, activo: activo === undefined ? undefined : activo },
      })
      .then((r) => r.data)
  },

  listarPuestos() {
    return http.get('/api/rrhh/puestos').then((r) => r.data)
  },

  actualizarEmpleado(empleadoId, cambios) {
    return http.patch(`/api/rrhh/empleados/${empleadoId}`, cambios).then((r) => r.data)
  },

  darBajaEmpleado(empleadoId, fechaBaja) {
    return http
      .patch(`/api/rrhh/empleados/${empleadoId}/baja`, { fecha_baja: fechaBaja })
      .then((r) => r.data)
  },

  // --------------------------------------------------- 011: puestos críticos / retención
  marcarPuestoCritico(puestoId, esCritico) {
    return http
      .patch(`/api/rrhh/puestos/${puestoId}/critico`, { es_critico: esCritico })
      .then((r) => r.data)
  },

  registrarAccionRetencion({ empleadoId, fecha, descripcion }) {
    return http
      .post('/api/rrhh/acciones-retencion', {
        empleado_id: empleadoId,
        fecha,
        descripcion,
      })
      .then((r) => r.data)
  },

  accionesRetencion(empleadoId) {
    return http.get(`/api/rrhh/empleados/${empleadoId}/acciones-retencion`).then((r) => r.data)
  },

  // --------------------------------------------------- 011: capacitación
  capacitaciones(tiendaId) {
    return http
      .get('/api/rrhh/capacitaciones', { params: { tienda_id: tiendaId || undefined } })
      .then((r) => r.data)
  },

  rolesSistema() {
    return http.get('/api/rrhh/roles').then((r) => r.data)
  },

  tiendas() {
    return http.get('/api/rrhh/tiendas').then((r) => r.data)
  },

  programarCapacitacion({ nombre, descripcion, roleIds }) {
    return http
      .post('/api/rrhh/capacitaciones', {
        nombre,
        descripcion: descripcion || null,
        role_ids: roleIds,
      })
      .then((r) => r.data)
  },

  completarCapacitacion(empleadoId, capacitacionId, fechaCompletado) {
    return http
      .patch(`/api/rrhh/empleado-capacitacion/${empleadoId}/${capacitacionId}/completar`, {
        fecha_completado: fechaCompletado,
      })
      .then((r) => r.data)
  },

  cumplimientoCapacitacionTienda(tiendaId) {
    return http.get(`/api/rrhh/tiendas/${tiendaId}/cumplimiento-capacitacion`).then((r) => r.data)
  },

  // --------------------------------------------------- 011: clima laboral / rotación
  registrarClima({ tiendaId, periodo, resultadoPromedio }) {
    return http
      .post('/api/rrhh/clima-laboral', {
        tienda_id: tiendaId,
        periodo,
        resultado_promedio: resultadoPromedio,
      })
      .then((r) => r.data)
  },

  climaRotacion(tiendaId, periodo) {
    return http
      .get(`/api/rrhh/tiendas/${tiendaId}/clima-rotacion`, { params: { periodo } })
      .then((r) => r.data)
  },

  // --------------------------------------------------- 011: plan de sucesión
  registrarCandidatoSucesion({ puestoId, empleadoCandidatoId }) {
    return http
      .post('/api/rrhh/plan-sucesion', {
        puesto_id: puestoId,
        empleado_candidato_id: empleadoCandidatoId,
      })
      .then((r) => r.data)
  },

  coberturaSucesion() {
    return http.get('/api/rrhh/plan-sucesion/cobertura').then((r) => r.data)
  },
}
