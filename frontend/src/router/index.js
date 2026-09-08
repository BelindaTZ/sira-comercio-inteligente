import { createRouter, createWebHistory } from 'vue-router'
import { authApi } from '@/services/authApi'

// Las rutas de cada módulo (pos, inventario, catalogo, compras) se agregan en
// sus fases respectivas de tasks.md. Este archivo solo define el router base.
const routes = [
  {
    path: '/auth/login',
    name: 'auth-login',
    component: () => import('@/modules/auth/pages/LoginPage.vue'),
    meta: { publica: true },
  },
  {
    path: '/auth/recuperar',
    name: 'auth-recuperar',
    component: () => import('@/modules/auth/pages/RecuperarPasswordPage.vue'),
    meta: { publica: true },
  },
  {
    path: '/sistema/usuarios',
    name: 'sistema-usuarios',
    component: () => import('@/modules/sistema/pages/UsuariosPage.vue'),
  },
  {
    path: '/sistema/roles-permisos',
    name: 'sistema-roles-permisos',
    component: () => import('@/modules/sistema/pages/RolesPermisosPage.vue'),
  },
  {
    path: '/sistema/auditoria',
    name: 'sistema-auditoria',
    component: () => import('@/modules/sistema/pages/AuditoriaPage.vue'),
  },
  {
    path: '/rrhh/empleados',
    name: 'rrhh-empleados',
    component: () => import('@/modules/rrhh/pages/EmpleadosPage.vue'),
  },
  {
    path: '/rrhh/puestos-criticos',
    name: 'rrhh-puestos-criticos',
    component: () => import('@/modules/rrhh/pages/PuestosCriticosPage.vue'),
  },
  {
    path: '/rrhh/retencion',
    name: 'rrhh-retencion',
    component: () => import('@/modules/rrhh/pages/RetencionPage.vue'),
  },
  {
    path: '/rrhh/capacitaciones',
    name: 'rrhh-capacitaciones',
    component: () => import('@/modules/rrhh/pages/CapacitacionesPage.vue'),
  },
  {
    path: '/rrhh/clima-laboral',
    name: 'rrhh-clima-laboral',
    component: () => import('@/modules/rrhh/pages/ClimaLaboralPage.vue'),
  },
  {
    path: '/rrhh/plan-sucesion',
    name: 'rrhh-plan-sucesion',
    component: () => import('@/modules/rrhh/pages/PlanSucesionPage.vue'),
  },
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
  {
    path: '/operaciones/traslados',
    name: 'operaciones-traslados',
    component: () => import('@/modules/operaciones/TrasladosPage.vue'),
  },
  {
    path: '/plataforma-datos/modelo',
    name: 'plataforma-datos-modelo',
    component: () => import('@/modules/plataforma-datos/pages/ModeloDatosWarehousePage.vue'),
  },
  {
    path: '/plataforma-datos/corridas',
    name: 'plataforma-datos-corridas',
    component: () => import('@/modules/plataforma-datos/pages/MonitoreoCorridasPage.vue'),
  },
  {
    path: '/plataforma-datos/politica',
    name: 'plataforma-datos-politica',
    component: () => import('@/modules/plataforma-datos/pages/PoliticaGobiernoDatosPage.vue'),
  },
  {
    path: '/direccion/dashboard-estrategico',
    name: 'direccion-dashboard-estrategico',
    component: () => import('@/modules/direccion/DashboardEstrategico.vue'),
  },
  {
    path: '/ti/dashboards/tactico',
    name: 'ti-dashboard-tactico',
    component: () => import('@/modules/ti/DashboardTactico.vue'),
  },
  {
    path: '/ti/dashboards/operativos',
    name: 'ti-dashboards-operativos',
    component: () => import('@/modules/ti/VerificacionDashboardsOperativos.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Guard de navegación (feature 008): toda ruta fuera de `/auth` exige un JWT
// válido en localStorage. La validez real la comprueba el backend en cada
// request; aquí sólo se evita mostrar vistas autenticadas sin sesión.
router.beforeEach((to) => {
  if (to.meta.publica) return true
  if (authApi.estaAutenticado()) return true
  return { name: 'auth-login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
})

export default router
