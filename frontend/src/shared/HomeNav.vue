<script setup>
/**
 * Panel de inicio: índice de todas las pantallas del sistema, agrupadas por área
 * de negocio (feature). El proyecto no tiene un layout de navegación global — cada
 * feature entregó sus vistas como páginas sueltas; esta es la puerta de entrada
 * para recorrerlas. Cada enlace anota el rol que puede abrirlo (el backend
 * responde 403 si la cuenta en sesión no tiene el permiso).
 */
import { useRouter } from 'vue-router'
import { authApi } from '@/services/authApi'

const router = useRouter()

let usuarioId = null
try {
  usuarioId = localStorage.getItem('sira_usuario_id')
} catch {
  usuarioId = null
}

function salir() {
  authApi.logout()
  router.push({ name: 'auth-login' })
}

const secciones = [
  {
    titulo: 'Dirección y Datos · features 009 / 010',
    items: [
      {
        to: '/direccion/dashboard-estrategico',
        label: 'Dashboard estratégico',
        rol: 'Gerente_General',
      },
      {
        to: '/ti/dashboards/tactico',
        label: 'Dashboards tácticos por departamento',
        rol: 'cada Jefe_* / Gerente',
      },
      {
        to: '/ti/dashboards/operativos',
        label: 'Verificación de dashboards operativos',
        rol: 'Jefe_TI',
      },
      { to: '/plataforma-datos/modelo', label: 'Modelo de datos del warehouse', rol: 'Jefe_TI' },
      {
        to: '/plataforma-datos/corridas',
        label: 'Monitoreo de corridas de carga (ELT)',
        rol: 'Jefe_TI',
      },
      { to: '/plataforma-datos/politica', label: 'Política de gobierno de datos', rol: 'Jefe_TI' },
    ],
  },
  {
    titulo: 'Comercial · Pricing · feature 003',
    items: [
      { to: '/pricing', label: 'Márgenes objetivo por categoría', rol: 'Jefe_Comercial' },
      { to: '/pricing/propuestas', label: 'Propuestas de ajuste de precio', rol: 'Jefe_Comercial' },
      { to: '/pricing/reporte', label: 'Reporte de margen real', rol: 'Jefe_Comercial' },
      {
        to: '/pricing/competencia',
        label: 'Comparación con la competencia',
        rol: 'Jefe_Comercial',
      },
    ],
  },
  {
    titulo: 'Marketing y CRM · features 002 / 005',
    items: [
      { to: '/clientes', label: 'Clientes y fidelización', rol: 'Jefe_Marketing' },
      { to: '/clientes/riesgo-fuga', label: 'Riesgo de fuga (churn)', rol: 'Jefe_Marketing' },
      { to: '/clientes/campanas', label: 'Campañas de reactivación', rol: 'Jefe_Marketing' },
      { to: '/promociones', label: 'Reglas de afinidad', rol: 'Jefe_Marketing' },
      {
        to: '/promociones/liquidacion',
        label: 'Candidatos a liquidación',
        rol: 'Jefe_Marketing / Jefe_Operaciones',
      },
      { to: '/promociones/colocacion', label: 'Colocación promocional', rol: 'Jefe_Marketing' },
    ],
  },
  {
    titulo: 'Operaciones · Inventario · Compras · features 001 / 004 / 012',
    items: [
      {
        to: '/inventario',
        label: 'Inventario, lotes y alertas',
        rol: 'Encargado_Tienda / Reponedor',
      },
      {
        to: '/compras',
        label: 'Órdenes de compra y cuentas por pagar',
        rol: 'Jefe_Operaciones / Jefe_Finanzas',
      },
      { to: '/catalogo', label: 'Catálogo de productos', rol: 'Jefe_Comercial' },
      {
        to: '/operaciones/traslados',
        label: 'Traslados de stock entre tiendas',
        rol: 'Jefe_Operaciones / Encargado_Tienda',
      },
      {
        to: '/forecasting',
        label: 'Modelos de pronóstico de demanda',
        rol: 'Jefe_TI / Jefe_Operaciones',
      },
      {
        to: '/forecasting/demanda-perdida',
        label: 'Demanda perdida por quiebre de stock',
        rol: 'Jefe_Operaciones',
      },
    ],
  },
  {
    titulo: 'Finanzas · Caja · Pagos · features 006 / 007',
    items: [
      { to: '/caja', label: 'Cuadre de caja', rol: 'Cajero / Jefe_Finanzas' },
      { to: '/caja/datafonos', label: 'Datáfonos y firmware', rol: 'Jefe_TI / Jefe_Finanzas' },
      {
        to: '/caja/reporte-diferencias',
        label: 'Reporte de diferencias de caja',
        rol: 'Jefe_Finanzas',
      },
      { to: '/caja/incidentes', label: 'Incidentes de fraude', rol: 'Jefe_Finanzas' },
      { to: '/caja/protocolo', label: 'Protocolo de escalamiento', rol: 'Jefe_Finanzas' },
      {
        to: '/caja/seguimiento-merma',
        label: 'Seguimiento de merma',
        rol: 'Jefe_Operaciones / Reponedor',
      },
      {
        to: '/caja/incidentes-seguridad',
        label: 'Incidentes de seguridad de pago',
        rol: 'Jefe_Finanzas',
      },
      {
        to: '/caja/politica-seguridad',
        label: 'Política de seguridad de pagos',
        rol: 'Jefe_Finanzas',
      },
      { to: '/ventas/medios-pago', label: 'Medios de pago', rol: 'Jefe_Finanzas' },
      {
        to: '/ventas/tiempo-cobro',
        label: 'Tiempo de cobro',
        rol: 'Encargado_Tienda / Jefe_Comercial',
      },
    ],
  },
  {
    titulo: 'Punto de venta · feature 001',
    items: [{ to: '/pos', label: 'Punto de venta (POS)', rol: 'Cajero / Encargado_Tienda' }],
  },
  {
    titulo: 'Recursos Humanos · feature 011',
    items: [
      { to: '/rrhh/empleados', label: 'Empleados', rol: 'Jefe_RRHH' },
      { to: '/rrhh/puestos-criticos', label: 'Puestos críticos', rol: 'Jefe_RRHH' },
      { to: '/rrhh/retencion', label: 'Acciones de retención', rol: 'Jefe_RRHH' },
      { to: '/rrhh/capacitaciones', label: 'Capacitaciones', rol: 'Jefe_RRHH' },
      { to: '/rrhh/clima-laboral', label: 'Clima laboral y rotación', rol: 'Jefe_RRHH' },
      { to: '/rrhh/plan-sucesion', label: 'Plan de sucesión', rol: 'Jefe_RRHH' },
    ],
  },
  {
    titulo: 'Sistema · feature 008',
    items: [
      { to: '/sistema/usuarios', label: 'Usuarios', rol: 'Jefe_TI' },
      { to: '/sistema/roles-permisos', label: 'Roles y permisos (RBAC)', rol: 'Jefe_TI' },
      { to: '/sistema/auditoria', label: 'Auditoría — reporte mensual', rol: 'Jefe_TI' },
    ],
  },
]
</script>

<template>
  <main class="mx-auto max-w-5xl px-6 py-10">
    <header class="mb-8 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-3xl font-bold text-primary-container">SIRA</h1>
        <p class="mt-1 text-sm text-on-surface-variant">
          Sistema Inteligente de Retail Adaptativo — índice de pantallas
          <span v-if="usuarioId"> · sesión #{{ usuarioId }}</span>
        </p>
      </div>
      <button
        class="rounded-lg border border-outline-variant px-3 py-1.5 text-sm text-on-surface hover:bg-surface-container-high"
        @click="salir"
      >
        Cerrar sesión
      </button>
    </header>

    <section v-for="s in secciones" :key="s.titulo" class="mb-8">
      <h2 class="mb-3 text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
        {{ s.titulo }}
      </h2>
      <ul class="grid gap-2 sm:grid-cols-2">
        <li v-for="it in s.items" :key="it.to">
          <RouterLink
            :to="it.to"
            class="block rounded-xl border border-outline-variant bg-surface-container-lowest p-3 transition hover:border-primary hover:bg-surface-container-high"
          >
            <span class="block text-sm font-medium text-on-surface">{{ it.label }}</span>
            <span class="mt-0.5 block text-xs text-on-surface-variant">{{ it.rol }}</span>
          </RouterLink>
        </li>
      </ul>
    </section>
  </main>
</template>
