import { http } from './http'

/**
 * Capa de servicio del módulo Direccion (feature 009, US1). Espeja
 * `contracts/dashboards-multinivel.md` #1. El frontend sólo lee el último
 * snapshot publicado por el job diario — no recalcula ningún KPI (Principio V).
 */
const BASE = '/api/direccion'

export const direccionApi = {
  /** Dashboard estratégico consolidado: KPIs por Objetivo Estratégico + fecha de publicación. */
  dashboardEstrategico() {
    return http.get(`${BASE}/dashboard-estrategico`).then((r) => r.data)
  },
}
