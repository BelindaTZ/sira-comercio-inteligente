/**
 * Home de cada rol (feature 013). `/` redirige al home del rol — su dashboard o
 * pantalla principal, NO un menú de botones (la navegación vive en el shell).
 */
export const HOME_POR_ROL = {
  Gerente_General: '/direccion/dashboard-estrategico',
  Jefe_TI: '/ti/dashboards/tactico',
  Jefe_Comercial: '/ti/dashboards/tactico',
  Jefe_Marketing: '/ti/dashboards/tactico',
  Jefe_Operaciones: '/ti/dashboards/tactico',
  Jefe_Finanzas: '/ti/dashboards/tactico',
  Jefe_RRHH: '/ti/dashboards/tactico',
  Encargado_Tienda: '/inventario',
  Reponedor: '/inventario',
  Cajero: '/pos',
}

/** Ruta de aterrizaje para un rol; `/` si no hay una definida. */
export function homeDe(rol) {
  return HOME_POR_ROL[rol] ?? null
}
