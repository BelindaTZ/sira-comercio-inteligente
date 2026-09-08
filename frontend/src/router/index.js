import { createRouter, createWebHistory } from 'vue-router'

// Las rutas de cada módulo (pos, inventario, catalogo, compras) se agregan en
// sus fases respectivas de tasks.md. Este archivo solo define el router base.
const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/shared/PlaceholderHome.vue'),
  },
  {
    path: '/pos',
    name: 'punto-de-venta',
    component: () => import('@/modules/pos/PuntoDeVentaPage.vue'),
  },
  {
    path: '/inventario',
    name: 'inventario',
    component: () => import('@/modules/inventario/InventarioPage.vue'),
  },
  {
    path: '/compras',
    name: 'compras',
    component: () => import('@/modules/compras/ComprasPage.vue'),
  },
  {
    path: '/catalogo',
    name: 'catalogo',
    component: () => import('@/modules/catalogo/CatalogoPage.vue'),
  },
  {
    path: '/clientes',
    name: 'clientes',
    component: () => import('@/modules/clientes/ClientesPage.vue'),
  },
  {
    path: '/clientes/riesgo-fuga',
    name: 'riesgo-fuga',
    component: () => import('@/modules/clientes/RiesgoFugaPage.vue'),
  },
  {
    path: '/clientes/campanas',
    name: 'campanas',
    component: () => import('@/modules/clientes/CampanasPage.vue'),
  },
  {
    path: '/pricing',
    name: 'pricing-margenes',
    component: () => import('@/modules/pricing/pages/MargenesPage.vue'),
  },
  {
    path: '/pricing/propuestas',
    name: 'pricing-propuestas',
    component: () => import('@/modules/pricing/pages/PropuestasPrecioPage.vue'),
  },
  {
    path: '/pricing/reporte',
    name: 'pricing-reporte',
    component: () => import('@/modules/pricing/pages/ReporteMargenPage.vue'),
  },
  {
    path: '/pricing/competencia',
    name: 'pricing-competencia',
    component: () => import('@/modules/pricing/pages/CompetenciaPage.vue'),
  },
  {
    path: '/forecasting',
    name: 'forecasting-modelos',
    component: () => import('@/modules/forecasting/pages/ModelosPage.vue'),
  },
  {
    path: '/forecasting/demanda-perdida',
    name: 'forecasting-demanda-perdida',
    component: () => import('@/modules/forecasting/pages/DemandaPerdidaPage.vue'),
  },
  {
    path: '/promociones',
    name: 'promociones-afinidad',
    component: () => import('@/modules/promociones/pages/ReglasAfinidadPage.vue'),
  },
  {
    path: '/promociones/liquidacion',
    name: 'promociones-liquidacion',
    component: () => import('@/modules/promociones/pages/LiquidacionPage.vue'),
  },
  {
    path: '/promociones/colocacion',
    name: 'promociones-colocacion',
    component: () => import('@/modules/promociones/pages/ColocacionPromocionalPage.vue'),
  },
  {
    path: '/caja',
    name: 'caja-cuadre',
    component: () => import('@/modules/caja/pages/CuadreCajaPage.vue'),
  },
  {
    path: '/caja/datafonos',
    name: 'caja-datafonos',
    component: () => import('@/modules/caja/pages/DatafonosPage.vue'),
  },
  {
    path: '/caja/reporte-diferencias',
    name: 'caja-reporte-diferencias',
    component: () => import('@/modules/caja/pages/ReporteDiferenciasPage.vue'),
  },
  {
    path: '/caja/incidentes',
    name: 'caja-incidentes',
    component: () => import('@/modules/caja/pages/IncidentesFraudePage.vue'),
  },
  {
    path: '/caja/protocolo',
    name: 'caja-protocolo',
    component: () => import('@/modules/caja/pages/ProtocoloEscalamientoPage.vue'),
  },
  {
    path: '/caja/seguimiento-merma',
    name: 'caja-seguimiento-merma',
    component: () => import('@/modules/caja/pages/SeguimientoMermaPage.vue'),
  },
  {
    path: '/caja/incidentes-seguridad',
    name: 'caja-incidentes-seguridad',
    component: () => import('@/modules/caja/pages/IncidentesSeguridadPagoPage.vue'),
  },
  {
    path: '/caja/politica-seguridad',
    name: 'caja-politica-seguridad',
    component: () => import('@/modules/caja/pages/PoliticaSeguridadPagosPage.vue'),
  },
  {
    path: '/ventas/medios-pago',
    name: 'ventas-medios-pago',
    component: () => import('@/modules/ventas/pages/MediosPagoPage.vue'),
  },
  {
    path: '/ventas/tiempo-cobro',
    name: 'ventas-tiempo-cobro',
    component: () => import('@/modules/ventas/pages/TiempoCobroPage.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
