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
 *
 * `tabla`: cuando el permiso de tabla del endpoint es más estrecho que el del
 * módulo (p. ej. `Encargado_Tienda` ve el módulo `Comercial` sólo por
 * `revision_margen_bajo`, no por `productos`), el ítem se oculta si el rol no
 * tiene `can_select` sobre esa tabla — evita que la navegación lleve a un 403.
 * Debe coincidir con el `require_permission(modulo, tabla, "select")` del router.
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
        tabla: 'dashboard_kpi',
      },
      {
        label: 'Dashboard táctico de mi área',
        to: '/ti/dashboards/tactico',
        modulos: TACTICOS,
        soloArea: true,
      },
      {
        label: 'Dashboard operativo de mi tienda',
        to: '/tienda/operativo',
        modulo: 'Finanzas',
        tabla: 'cierre_caja',
      },
      {
        label: 'Dashboards operativos',
        to: '/ti/dashboards/operativos',
        modulo: 'TI',
        tabla: 'dashboard_operativo_estado',
      },
    ],
  },
  {
    label: 'Punto de Venta',
    icon: 'cart',
    items: [
      { label: 'Registrar venta (POS)', to: '/pos', modulo: 'Ventas', tabla: 'ventas' },
      { label: 'Cuadre de caja', to: '/caja', modulo: 'Finanzas', tabla: 'cierre_caja' },
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
          { label: 'Inventario y lotes', to: '/inventario', modulo: 'Operaciones', tabla: 'lotes' },
          {
            label: 'Traslados entre tiendas',
            to: '/operaciones/traslados',
            modulo: 'Operaciones',
            tabla: 'traslados_stock',
          },
          {
            label: 'Seguimiento de merma',
            to: '/caja/seguimiento-merma',
            modulo: 'Operaciones',
            tabla: 'mermas',
          },
        ],
      },
      {
        titulo: 'Abastecimiento',
        icon: 'truck',
        items: [
          {
            label: 'Órdenes de compra',
            to: '/compras',
            modulo: 'Operaciones',
            tabla: 'ordenes_compra',
          },
          {
            label: 'Pronóstico de demanda',
            to: '/forecasting',
            modulo: 'TI',
            tabla: 'modelo_demanda',
          },
          {
            label: 'Demanda perdida',
            to: '/forecasting/demanda-perdida',
            modulo: 'Operaciones',
            tabla: 'eventos_quiebre_stock',
          },
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
          {
            label: 'Clientes y fidelización',
            to: '/clientes',
            modulo: 'Marketing_CRM',
            tabla: 'clientes',
          },
          {
            label: 'Riesgo de fuga (churn)',
            to: '/clientes/riesgo-fuga',
            modulo: 'Marketing_CRM',
            tabla: 'churn_score',
          },
        ],
      },
      {
        titulo: 'Campañas y promociones',
        icon: 'megaphone',
        items: [
          {
            label: 'Campañas de reactivación',
            to: '/clientes/campanas',
            modulo: 'Marketing_CRM',
            tabla: 'campanas',
          },
          {
            label: 'Reglas de afinidad',
            to: '/promociones',
            modulo: 'Marketing_CRM',
            tabla: 'regla_afinidad',
          },
          {
            label: 'Candidatos a liquidación',
            to: '/promociones/liquidacion',
            modulo: 'Operaciones',
            tabla: 'cambio_clasificacion_abc',
          },
          {
            label: 'Colocación promocional',
            to: '/promociones/colocacion',
            modulo: 'Marketing_CRM',
            tabla: 'cupon_enviado',
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
        items: [
          {
            label: 'Catálogo de productos',
            to: '/catalogo',
            modulo: 'Comercial',
            tabla: 'productos',
          },
        ],
      },
      {
        titulo: 'Precios y márgenes',
        icon: 'tag',
        items: [
          {
            label: 'Márgenes objetivo',
            to: '/pricing',
            modulo: 'Comercial',
            tabla: 'margenes_objetivo',
          },
          {
            label: 'Propuestas de ajuste de precio',
            to: '/pricing/propuestas',
            modulo: 'Comercial',
            tabla: 'propuesta_ajuste_precio',
          },
          {
            label: 'Reporte de margen real',
            to: '/pricing/reporte',
            modulo: 'Comercial',
            tabla: 'margenes_objetivo',
          },
          {
            label: 'Comparación con la competencia',
            to: '/pricing/competencia',
            modulo: 'Comercial',
            tabla: 'precio_competencia',
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
            tabla: 'ajustes_inventario',
          },
          {
            label: 'Datáfonos y firmware',
            to: '/caja/datafonos',
            modulo: 'Finanzas',
            tabla: 'datafonos',
          },
          {
            label: 'Medios de pago',
            to: '/ventas/medios-pago',
            modulo: 'Ventas',
            tabla: 'medios_pago',
          },
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
          {
            label: 'Incidentes de fraude',
            to: '/caja/incidentes',
            modulo: 'Finanzas',
            tabla: 'incidentes_fraude',
          },
          {
            label: 'Protocolo de escalamiento',
            to: '/caja/protocolo',
            modulo: 'Finanzas',
            tabla: 'protocolo_escalamiento',
          },
          {
            label: 'Incidentes de seguridad de pago',
            to: '/caja/incidentes-seguridad',
            modulo: 'Finanzas',
            tabla: 'incidente_seguridad_pago',
          },
          {
            label: 'Política de seguridad de pagos',
            to: '/caja/politica-seguridad',
            modulo: 'Finanzas',
            tabla: 'politica_seguridad_pagos',
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
          { label: 'Empleados', to: '/rrhh/empleados', modulo: 'RRHH', tabla: 'empleados' },
          {
            label: 'Puestos críticos',
            to: '/rrhh/puestos-criticos',
            modulo: 'RRHH',
            tabla: 'empleados',
          },
          {
            label: 'Acciones de retención',
            to: '/rrhh/retencion',
            modulo: 'RRHH',
            tabla: 'acciones_retencion',
          },
        ],
      },
      {
        titulo: 'Desarrollo',
        icon: 'academic',
        items: [
          {
            label: 'Capacitaciones',
            to: '/rrhh/capacitaciones',
            modulo: 'RRHH',
            tabla: 'empleado_capacitacion',
          },
          {
            label: 'Clima laboral y rotación',
            to: '/rrhh/clima-laboral',
            modulo: 'RRHH',
            tabla: 'clima_laboral',
          },
          {
            label: 'Plan de sucesión',
            to: '/rrhh/plan-sucesion',
            modulo: 'RRHH',
            tabla: 'plan_sucesion',
          },
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
          { label: 'Usuarios', to: '/sistema/usuarios', modulo: 'Sistema', tabla: 'usuarios' },
          {
            label: 'Roles y permisos',
            to: '/sistema/roles-permisos',
            modulo: 'Sistema',
            tabla: 'role_permisos_modulo',
          },
          {
            label: 'Auditoría',
            to: '/sistema/auditoria',
            modulo: 'Sistema',
            tabla: 'auditoria_log',
          },
        ],
      },
      {
        titulo: 'Datos e integraciones',
        icon: 'database',
        items: [
          {
            label: 'Modelo de datos del warehouse',
            to: '/plataforma-datos/modelo',
            modulo: 'TI',
            tabla: 'modelo_datos_warehouse',
          },
          {
            label: 'Monitoreo de corridas (ELT)',
            to: '/plataforma-datos/corridas',
            modulo: 'TI',
            tabla: 'corrida_carga',
          },
          {
            label: 'Política de gobierno de datos',
            to: '/plataforma-datos/politica',
            modulo: 'TI',
            tabla: 'politica_gobierno_datos',
          },
        ],
      },
    ],
  },
]

/** ¿El rol (vía el store de sesión) puede ver este ítem? */
export function itemVisible(item, sesion) {
  // El dashboard táctico "de mi área" sólo tiene sentido para un Jefe (que tiene
  // un módulo propio) o para la Gerencia (que elige el área). Un Encargado/Cajero
  // tiene visibilidad de módulos pero no un "área" → sería un callejón sin salida.
  if (item.soloArea && !sesion.miModulo && !sesion.esGerente) return false
  if (item.modulos) return item.modulos.some((m) => sesion.puedeVer(m))
  if (!sesion.puedeVer(item.modulo)) return false
  // Permiso de tabla: más fino que el de módulo — evita llevar la navegación a un 403.
  if (item.tabla) return sesion.puedeLeerTabla(item.modulo, item.tabla)
  return true
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
