/**
 * Mapa único de navegación (feature 013). Fuente de verdad para el shell
 * (`AppShell.vue`) y los portales por rol (`portales.js`).
 *
 * Categorías de primer nivel según `.specify/memory/constitution.md` (Principio
 * XII). Cada ítem declara el módulo RBAC que lo habilita (`modulo`) o una lista
 * de módulos de los que basta tener uno (`modulos`). Una categoría se muestra si
 * al menos uno de sus ítems es visible para el rol; `Gerente_General` ve todo.
 *
 * Nombres de módulo = los del seed (`01_operativo_postgres.sql`):
 * Direccion, Comercial, Marketing_CRM, Operaciones, Ventas, Finanzas, TI, RRHH, Sistema.
 */

const TACTICOS = ['Comercial', 'Marketing_CRM', 'Operaciones', 'Finanzas', 'TI', 'RRHH']

export const CATEGORIAS = [
  {
    label: 'Dashboard',
    items: [
      {
        label: 'Dashboard estratégico',
        to: '/direccion/dashboard-estrategico',
        modulo: 'Direccion',
      },
      { label: 'Dashboard táctico de mi área', to: '/ti/dashboards/tactico', modulos: TACTICOS },
      {
        label: 'Disponibilidad de dashboards operativos',
        to: '/ti/dashboards/operativos',
        modulo: 'TI',
      },
    ],
  },
  {
    label: 'Punto de Venta',
    items: [
      { label: 'Registrar venta (POS)', to: '/pos', modulo: 'Ventas' },
      { label: 'Cuadre de caja', to: '/caja', modulo: 'Finanzas' },
    ],
  },
  {
    label: 'Inventario & FIFO',
    items: [
      { label: 'Inventario y lotes', to: '/inventario', modulo: 'Operaciones' },
      { label: 'Traslados entre tiendas', to: '/operaciones/traslados', modulo: 'Operaciones' },
      { label: 'Seguimiento de merma', to: '/caja/seguimiento-merma', modulo: 'Operaciones' },
      { label: 'Órdenes de compra', to: '/compras', modulo: 'Operaciones' },
      { label: 'Pronóstico de demanda', to: '/forecasting', modulos: ['Operaciones', 'TI'] },
      { label: 'Demanda perdida', to: '/forecasting/demanda-perdida', modulo: 'Operaciones' },
    ],
  },
  {
    label: 'Clientes / CRM',
    items: [
      { label: 'Clientes y fidelización', to: '/clientes', modulo: 'Marketing_CRM' },
      { label: 'Riesgo de fuga (churn)', to: '/clientes/riesgo-fuga', modulo: 'Marketing_CRM' },
      { label: 'Campañas de reactivación', to: '/clientes/campanas', modulo: 'Marketing_CRM' },
      { label: 'Reglas de afinidad', to: '/promociones', modulo: 'Marketing_CRM' },
      {
        label: 'Candidatos a liquidación',
        to: '/promociones/liquidacion',
        modulos: ['Marketing_CRM', 'Operaciones'],
      },
      { label: 'Colocación promocional', to: '/promociones/colocacion', modulo: 'Marketing_CRM' },
    ],
  },
  {
    label: 'Comercial',
    items: [
      { label: 'Catálogo de productos', to: '/catalogo', modulo: 'Comercial' },
      { label: 'Márgenes objetivo', to: '/pricing', modulo: 'Comercial' },
      { label: 'Propuestas de ajuste de precio', to: '/pricing/propuestas', modulo: 'Comercial' },
      { label: 'Reporte de margen real', to: '/pricing/reporte', modulo: 'Comercial' },
      { label: 'Comparación con la competencia', to: '/pricing/competencia', modulo: 'Comercial' },
    ],
  },
  {
    label: 'Finanzas & BI',
    items: [
      {
        label: 'Reporte de diferencias de caja',
        to: '/caja/reporte-diferencias',
        modulo: 'Finanzas',
      },
      { label: 'Datáfonos y firmware', to: '/caja/datafonos', modulos: ['Finanzas', 'TI'] },
      { label: 'Incidentes de fraude', to: '/caja/incidentes', modulo: 'Finanzas' },
      { label: 'Protocolo de escalamiento', to: '/caja/protocolo', modulo: 'Finanzas' },
      {
        label: 'Incidentes de seguridad de pago',
        to: '/caja/incidentes-seguridad',
        modulo: 'Finanzas',
      },
      {
        label: 'Política de seguridad de pagos',
        to: '/caja/politica-seguridad',
        modulo: 'Finanzas',
      },
      { label: 'Medios de pago', to: '/ventas/medios-pago', modulo: 'Finanzas' },
      {
        label: 'Tiempo de cobro',
        to: '/ventas/tiempo-cobro',
        modulos: ['Ventas', 'Comercial', 'Finanzas'],
      },
    ],
  },
  {
    label: 'RRHH',
    items: [
      { label: 'Empleados', to: '/rrhh/empleados', modulo: 'RRHH' },
      { label: 'Puestos críticos', to: '/rrhh/puestos-criticos', modulo: 'RRHH' },
      { label: 'Acciones de retención', to: '/rrhh/retencion', modulo: 'RRHH' },
      { label: 'Capacitaciones', to: '/rrhh/capacitaciones', modulo: 'RRHH' },
      { label: 'Clima laboral y rotación', to: '/rrhh/clima-laboral', modulo: 'RRHH' },
      { label: 'Plan de sucesión', to: '/rrhh/plan-sucesion', modulo: 'RRHH' },
    ],
  },
  {
    label: 'Sistema & Datos',
    items: [
      { label: 'Usuarios', to: '/sistema/usuarios', modulo: 'Sistema' },
      { label: 'Roles y permisos (RBAC)', to: '/sistema/roles-permisos', modulo: 'Sistema' },
      { label: 'Auditoría', to: '/sistema/auditoria', modulo: 'Sistema' },
      { label: 'Modelo de datos del warehouse', to: '/plataforma-datos/modelo', modulo: 'TI' },
      { label: 'Monitoreo de corridas (ELT)', to: '/plataforma-datos/corridas', modulo: 'TI' },
      { label: 'Política de gobierno de datos', to: '/plataforma-datos/politica', modulo: 'TI' },
    ],
  },
]

/** ¿El rol (vía el store de sesión) puede ver este ítem? */
export function itemVisible(item, sesion) {
  if (item.modulos) return item.modulos.some((m) => sesion.puedeVer(m))
  return sesion.puedeVer(item.modulo)
}

/** Categorías con sus ítems filtrados a lo que el rol puede ver. */
export function categoriasVisibles(sesion) {
  return CATEGORIAS.map((cat) => ({
    ...cat,
    items: cat.items.filter((it) => itemVisible(it, sesion)),
  })).filter((cat) => cat.items.length > 0)
}
