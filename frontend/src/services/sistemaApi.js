import { http } from './http'

/** Capa de servicio del módulo Sistema (feature 008) — cuentas, RBAC, auditoría. */
export const sistemaApi = {
  crearUsuario({ empleadoId, username, passwordInicial, roleId }) {
    return http
      .post('/api/sistema/usuarios', {
        empleado_id: empleadoId,
        username,
        password_inicial: passwordInicial,
        role_id: roleId,
      })
      .then((r) => r.data)
  },

  obtenerUsuario(usuarioId) {
    return http.get(`/api/sistema/usuarios/${usuarioId}`).then((r) => r.data)
  },

  listarUsuarios(search) {
    return http
      .get('/api/sistema/usuarios', { params: { search: search || undefined } })
      .then((r) => r.data)
  },

  listarRoles() {
    return http.get('/api/sistema/roles').then((r) => r.data)
  },

  empleadosSinCuenta() {
    return http.get('/api/sistema/empleados-sin-cuenta').then((r) => r.data)
  },

  asignarRol(usuarioId, roleId) {
    return http
      .patch(`/api/sistema/usuarios/${usuarioId}/rol`, { role_id: roleId })
      .then((r) => r.data)
  },

  permisosModulo(roleId) {
    return http.get(`/api/sistema/roles/${roleId}/permisos-modulo`).then((r) => r.data)
  },

  definirPermisoModulo(roleId, moduloId, { puedeVer, puedeEditar }) {
    return http
      .put(`/api/sistema/roles/${roleId}/permisos-modulo/${moduloId}`, {
        puede_ver: puedeVer,
        puede_editar: puedeEditar,
      })
      .then((r) => r.data)
  },

  permisosTabla(roleId, moduloId) {
    return http
      .get(`/api/sistema/roles/${roleId}/permisos-tabla`, {
        params: { modulo_id: moduloId ?? undefined },
      })
      .then((r) => r.data)
  },

  definirPermisoTabla(roleId, moduloId, nombreTabla, permisos) {
    return http
      .put(
        `/api/sistema/roles/${roleId}/permisos-tabla/${moduloId}/${encodeURIComponent(nombreTabla)}`,
        {
          can_select: !!permisos.canSelect,
          can_insert: !!permisos.canInsert,
          can_update: !!permisos.canUpdate,
          can_delete: !!permisos.canDelete,
        }
      )
      .then((r) => r.data)
  },

  reporteAuditoria({ mes, anio }) {
    return http
      .get('/api/sistema/auditoria/reporte-mensual', { params: { mes, anio } })
      .then((r) => r.data)
  },
}
