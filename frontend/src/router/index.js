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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
