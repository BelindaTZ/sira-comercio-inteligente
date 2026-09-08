/**
 * Mapa único de navegación (feature 013). Fuente de verdad para el shell
 * (`AppShell.vue`), el mega-menú y los portales por rol.
 *
 * Categorías de primer nivel según `.specify/memory/constitution.md` (Principio
 * XII): una categoría con ≥4 sub-opciones se despliega en un mega-menú agrupado
 * por columnas temáticas (`grupos`); con <4, lista simple (`items`).
 *
 * Cada ítem declara el módulo RBAC que lo habilita (`modulo`) o una lista de la
 * que basta tener uno (`modulos`). Se muestra si el rol puede ver ese módulo;
 * `Gerente_General` ve todo. Nombres de módulo = los del seed.
 */

const TACTICOS = ['Comercial', 'Marketing_CRM', 'Operaciones', 'Finanzas', 'TI', 'RRHH']

/** Rol de Jefe → su módulo RBAC (para el dashboard táctico propio). */
export const ROL_A_MODULO = {
  Jefe_Comercial: 'Comercial',
  Jefe_Marketing: 'Marketing_CRM',
  Jefe_Operaciones: 'Operaciones',
  Jefe_Finanzas: 'Finanzas',
  Jefe_TI: 'TI',
  Jefe_RRHH: 'RRHH',
}

export const CATEGORIAS = [
  {
    label: 'Dashboard',
    icon: 'chart',
    items: [
      {
        label: 'Dashboard estratégico',
        to: '/direccion/dashboard-estrategico',
        modulo: 'Direccion',
      },
      { label: 'Dashboard táctico de mi área', to: '/ti/dashboards/tactico', modulos: TACTICOS },
      { label: 'Dashboards operativos', to: '/ti/dashboards/operativos', modulo: 'TI' },
    ],
  },
  {
    label: 'Punto de Venta',
    icon: 'cart',
    items: [
      { label: 'Registrar venta (POS)', to: '/pos', modulo: 'Ventas' },
      { label: 'Cuadre de caja', to: '/caja', modulo: 'Finanzas' },
    ],
  },
  {
    label: 'Inventario & FIFO',
    icon: 'cube',
    grupos: [
      {
        titulo: 'Stock',
        icon: 'cube',
        items: [
          { label: 'Inventario y lotes', to: '/inventario', modulo: 'Operaciones' },
          { label: 'Traslados entre tiendas', to: '/operaciones/traslados', modulo: 'Operaciones' },
          { label: 'Seguimiento de merma', to: '/caja/seguimiento-merma', modulo: 'Operaciones' },
        ],
      },
      {
        titulo: 'Abastecimiento',
        icon: 'truck',
        items: [
          { label: 'Órdenes de compra', to: '/compras', modulo: 'Operaciones' },
          { label: 'Pronóstico de demanda', to: '/forecasting', modulos: ['Operaciones', 'TI'] },
          { label: 'Demanda perdida', to: '/forecasting/demanda-perdida', modulo: 'Operaciones' },
        ],
      },
    ],
  },
  {
    label: 'Clientes / CRM',
    icon: 'users',
    grupos: [
      {
        titulo: 'Clientes',
        icon: 'users',
        items: [
          { label: 'Clientes y fidelización', to: '/clientes', modulo: 'Marketing_CRM' },
          { label: 'Riesgo de fuga (churn)', to: '/clientes/riesgo-fuga', modulo: 'Marketing_CRM' },
        ],
      },
      {
        titulo: 'Campañas y promociones',
        icon: 'megaphone',
        items: [
          { label: 'Campañas de reactivación', to: '/clientes/campanas', modulo: 'Marketing_CRM' },
          { label: 'Reglas de afinidad', to: '/promociones', modulo: 'Marketing_CRM' },
          {
            label: 'Candidatos a liquidación',
            to: '/promociones/liquidacion',
            modulos: ['Marketing_CRM', 'Operaciones'],
          },
          {
            label: 'Colocación promocional',
            to: '/promociones/colocacion',
            modulo: 'Marketing_CRM',
          },
        ],
      },
    ],
  },
  {
    label: 'Comercial',
    icon: 'tag',
    grupos: [
      {
        titulo: 'Catálogo',
        icon: 'cube',
        items: [{ label: 'Catálogo de productos', to: '/catalogo', modulo: 'Comercial' }],
      },
      {
        titulo: 'Precios y márgenes',
        icon: 'tag',
        items: [
          { label: 'Márgenes objetivo', to: '/pricing', modulo: 'Comercial' },
          {
            label: 'Propuestas de ajuste de precio',
            to: '/pricing/propuestas',
            modulo: 'Comercial',
          },
          { label: 'Reporte de margen real', to: '/pricing/reporte', modulo: 'Comercial' },
          {
            label: 'Comparación con la competencia',
            to: '/pricing/competencia',
            modulo: 'Comercial',
          },
        ],
      },
    ],
  },
  {
    label: 'Finanzas & BI',
    icon: 'bank',
    grupos: [
      {
        titulo: 'Caja',
        icon: 'bank',
        items: [
          {
            label: 'Reporte de diferencias de caja',
            to: '/caja/reporte-diferencias',
            modulo: 'Finanzas',
          },
          { label: 'Datáfonos y firmware', to: '/caja/datafonos', modulos: ['Finanzas', 'TI'] },
          { label: 'Medios de pago', to: '/ventas/medios-pago', modulo: 'Finanzas' },
          {
            label: 'Tiempo de cobro',
            to: '/ventas/tiempo-cobro',
            modulos: ['Ventas', 'Comercial', 'Finanzas'],
          },
        ],
      },
      {
        titulo: 'Seguridad de pagos',
        icon: 'shield',
        items: [
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
        ],
      },
    ],
  },
  {
    label: 'RRHH',
    icon: 'id',
    grupos: [
      {
        titulo: 'Personal',
        icon: 'users',
        items: [
          { label: 'Empleados', to: '/rrhh/empleados', modulo: 'RRHH' },
          { label: 'Puestos críticos', to: '/rrhh/puestos-criticos', modulo: 'RRHH' },
          { label: 'Acciones de retención', to: '/rrhh/retencion', modulo: 'RRHH' },
        ],
      },
      {
        titulo: 'Desarrollo',
        icon: 'academic',
        items: [
          { label: 'Capacitaciones', to: '/rrhh/capacitaciones', modulo: 'RRHH' },
          { label: 'Clima laboral y rotación', to: '/rrhh/clima-laboral', modulo: 'RRHH' },
          { label: 'Plan de sucesión', to: '/rrhh/plan-sucesion', modulo: 'RRHH' },
        ],
      },
    ],
  },
  {
    label: 'Sistema',
    icon: 'cog',
    grupos: [
      {
        titulo: 'Seguridad',
        icon: 'shield',
        items: [
          { label: 'Usuarios', to: '/sistema/usuarios', modulo: 'Sistema' },
          { label: 'Roles y permisos', to: '/sistema/roles-permisos', modulo: 'Sistema' },
          { label: 'Auditoría', to: '/sistema/auditoria', modulo: 'Sistema' },
        ],
      },
      {
        titulo: 'Datos e integraciones',
        icon: 'database',
        items: [
          { label: 'Modelo de datos del warehouse', to: '/plataforma-datos/modelo', modulo: 'TI' },
          { label: 'Monitoreo de corridas (ELT)', to: '/plataforma-datos/corridas', modulo: 'TI' },
          {
            label: 'Política de gobierno de datos',
            to: '/plataforma-datos/politica',
            modulo: 'TI',
          },
        ],
      },
    ],
  },
]

/** ¿El rol (vía el store de sesión) puede ver este ítem? */
export function itemVisible(item, sesion) {
  if (item.modulos) return item.modulos.some((m) => sesion.puedeVer(m))
  return sesion.puedeVer(item.modulo)
}

/** Todos los ítems de una categoría, tenga `items` o `grupos`. */
export function itemsDe(cat) {
  return cat.grupos ? cat.grupos.flatMap((g) => g.items) : (cat.items ?? [])
}

/**
 * Categorías visibles para el rol, con sus `grupos`/`items` ya filtrados y los
 * grupos/categorías vacíos descartados.
 */
export function categoriasVisibles(sesion) {
  return CATEGORIAS.map((cat) => {
    if (cat.grupos) {
      const grupos = cat.grupos
        .map((g) => ({ ...g, items: g.items.filter((it) => itemVisible(it, sesion)) }))
        .filter((g) => g.items.length > 0)
      return { ...cat, grupos, items: grupos.flatMap((g) => g.items) }
    }
    const items = (cat.items ?? []).filter((it) => itemVisible(it, sesion))
    return { ...cat, items }
  }).filter((cat) => cat.items.length > 0)
}
