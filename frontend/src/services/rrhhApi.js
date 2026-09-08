import { http } from './http'

/** Capa de servicio del módulo RRHH (feature 008) — CRUD base de empleado. */
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

  actualizarEmpleado(empleadoId, cambios) {
    return http.patch(`/api/rrhh/empleados/${empleadoId}`, cambios).then((r) => r.data)
  },

  darBajaEmpleado(empleadoId, fechaBaja) {
    return http
      .patch(`/api/rrhh/empleados/${empleadoId}/baja`, { fecha_baja: fechaBaja })
      .then((r) => r.data)
  },
}
