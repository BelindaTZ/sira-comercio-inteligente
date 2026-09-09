import { defineStore } from 'pinia'
import { authApi } from '@/services/authApi'
import { ROL_A_MODULO } from '@/shared/navegacion'

/**
 * Sesión del usuario autenticado (feature 013). Primer store Pinia del proyecto.
 *
 * El JWT sólo transporta `usuario_id`; `GET /api/auth/me` resuelve rol, tienda,
 * empleado y los módulos que el rol puede ver — con eso el shell pinta la
 * navegación según el rol (Principio XII) y las páginas dejan de leer
 * `sira_tienda_id`/`sira_empleado_id` con fallback `|| 1`.
 */
export const useSesion = defineStore('sesion', {
  state: () => ({
    perfil: null, // { usuario_id, empleado_id, role_id, rol, tienda_id, modulos: [{nombre, puede_ver, puede_editar}] }
    cargando: false,
  }),

  getters: {
    autenticado: () => authApi.estaAutenticado(),
    rol: (s) => s.perfil?.rol ?? null,
    nombre: (s) => s.perfil?.nombre ?? null,
    username: (s) => s.perfil?.username ?? null,
    tiendaId: (s) => s.perfil?.tienda_id ?? null,
    tiendaNombre: (s) => s.perfil?.tienda_nombre ?? null,
    tiendaCodigo: (s) => s.perfil?.tienda_codigo ?? null,
    tiendaCiudad: (s) => s.perfil?.tienda_ciudad ?? null,
    empleadoId: (s) => s.perfil?.empleado_id ?? null,
    esGerente: (s) => s.perfil?.rol === 'Gerente_General',
    /** Módulo propio del Jefe (para su dashboard táctico); null para otros roles. */
    miModulo: (s) => ROL_A_MODULO[s.perfil?.rol] ?? null,
    _modulos: (s) => Object.fromEntries((s.perfil?.modulos ?? []).map((m) => [m.nombre, m])),
    /** Set de `"Modulo/tabla"` que el rol puede leer (permiso de tabla, más fino que el de módulo). */
    _tablas: (s) => new Set((s.perfil?.tablas ?? []).map((t) => `${t.modulo}/${t.nombre_tabla}`)),
    /** Set de `"Modulo/tabla"` que el rol puede editar (insert/update/delete sobre esa tabla). */
    _tablasEditables: (s) =>
      new Set(
        (s.perfil?.tablas ?? [])
          .filter((t) => t.can_editar)
          .map((t) => `${t.modulo}/${t.nombre_tabla}`)
      ),
  },

  actions: {
    /** Carga el perfil si hay token y aún no está en memoria. */
    async cargar(forzar = false) {
      if (!authApi.estaAutenticado()) {
        this.perfil = null
        return null
      }
      if (this.perfil && !forzar) return this.perfil
      this.cargando = true
      try {
        this.perfil = await authApi.me()
        // Sustituye los placeholders `|| 1` que nadie escribía (feature 008).
        try {
          if (this.perfil.tienda_id != null)
            localStorage.setItem('sira_tienda_id', String(this.perfil.tienda_id))
          if (this.perfil.empleado_id != null)
            localStorage.setItem('sira_empleado_id', String(this.perfil.empleado_id))
        } catch {
          /* almacenamiento no disponible */
        }
        return this.perfil
      } finally {
        this.cargando = false
      }
    },

    puedeVer(modulo) {
      if (!this.perfil) return false
      if (this.esGerente) return true
      return Boolean(this._modulos[modulo]?.puede_ver)
    },

    puedeEditar(modulo) {
      return Boolean(this._modulos[modulo]?.puede_editar)
    },

    /** ¿El rol puede editar esta tabla concreta? Más fino que `puedeEditar(modulo)`. */
    puedeEditarTabla(modulo, tabla) {
      if (!this.perfil) return false
      if (this.esGerente) return true
      return this._tablasEditables.has(`${modulo}/${tabla}`)
    },

    /**
     * ¿El rol puede leer esta tabla concreta del módulo? Más fino que `puedeVer`:
     * un rol puede tener el módulo visible por una sola de sus tablas (p. ej.
     * `Encargado_Tienda` ve `Comercial` sólo por `revision_margen_bajo`).
     */
    puedeLeerTabla(modulo, tabla) {
      if (!this.perfil) return false
      if (this.esGerente) return true
      return this._tablas.has(`${modulo}/${tabla}`)
    },

    logout() {
      authApi.logout()
      this.perfil = null
      try {
        localStorage.removeItem('sira_tienda_id')
        localStorage.removeItem('sira_empleado_id')
      } catch {
        /* noop */
      }
    },
  },
})
