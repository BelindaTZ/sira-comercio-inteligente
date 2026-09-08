/**
 * Portal de inicio por rol (feature 013). `/` abre el home del rol — no un menú
 * suelto. Cada entrada define un destino de aterrizaje y las tarjetas destacadas
 * de ese rol; el resto de accesos los aporta el shell.
 *
 * `redirect`: si el "home" del rol es directamente otra pantalla (ej. Cajero → POS).
 * `destacados`: tarjetas grandes de acción rápida.
 */
export const PORTALES = {
  Gerente_General: {
    titulo: 'Dirección General',
    bienvenida: 'Vista consolidada de la red — KPIs estratégicos y tácticos.',
    destacados: [
      {
        label: 'Dashboard estratégico',
        to: '/direccion/dashboard-estrategico',
        desc: 'KPIs de toda la red por Objetivo Estratégico.',
      },
      {
        label: 'Dashboards tácticos',
        to: '/ti/dashboards/tactico',
        desc: 'El detalle de cada departamento.',
      },
      {
        label: 'Auditoría del sistema',
        to: '/sistema/auditoria',
        desc: 'Accesos y acciones del mes.',
      },
    ],
  },
  Jefe_TI: {
    titulo: 'Jefatura de TI y Datos',
    bienvenida: 'Salud de la plataforma de datos y disponibilidad de dashboards.',
    destacados: [
      {
        label: 'Mi dashboard táctico (TI)',
        to: '/ti/dashboards/tactico',
        desc: 'KPIs del área de TI.',
      },
      {
        label: 'Disponibilidad de dashboards operativos',
        to: '/ti/dashboards/operativos',
        desc: 'Estado por tienda, alertas de desactualización.',
      },
      {
        label: 'Monitoreo de corridas (ELT)',
        to: '/plataforma-datos/corridas',
        desc: 'Resultado de cada carga al warehouse.',
      },
    ],
  },
  Jefe_Comercial: {
    titulo: 'Jefatura Comercial',
    bienvenida: 'Márgenes, precios y posición frente a la competencia.',
    destacados: [
      {
        label: 'Mi dashboard táctico (Comercial)',
        to: '/ti/dashboards/tactico',
        desc: 'KPIs del área comercial.',
      },
      {
        label: 'Propuestas de ajuste de precio',
        to: '/pricing/propuestas',
        desc: 'Sugerencias abiertas para revisar.',
      },
      {
        label: 'Comparación con la competencia',
        to: '/pricing/competencia',
        desc: 'Alertas de precio fuera de rango.',
      },
    ],
  },
  Jefe_Marketing: {
    titulo: 'Jefatura de Marketing y CRM',
    bienvenida: 'Cartera de clientes, campañas y promociones.',
    destacados: [
      {
        label: 'Mi dashboard táctico (Marketing)',
        to: '/ti/dashboards/tactico',
        desc: 'KPIs de CRM.',
      },
      {
        label: 'Riesgo de fuga (churn)',
        to: '/clientes/riesgo-fuga',
        desc: 'Clientes en riesgo que requieren acción.',
      },
      {
        label: 'Campañas de reactivación',
        to: '/clientes/campanas',
        desc: 'Campañas activas y resultados.',
      },
    ],
  },
  Jefe_Operaciones: {
    titulo: 'Jefatura de Operaciones',
    bienvenida: 'Inventario de la red, compras y traslados.',
    destacados: [
      {
        label: 'Mi dashboard táctico (Operaciones)',
        to: '/ti/dashboards/tactico',
        desc: 'KPIs de operaciones.',
      },
      {
        label: 'Inventario y alertas FIFO',
        to: '/inventario',
        desc: 'Stock crítico y vencimientos.',
      },
      { label: 'Órdenes de compra', to: '/compras', desc: 'Órdenes pendientes de aprobar.' },
    ],
  },
  Jefe_Finanzas: {
    titulo: 'Jefatura de Finanzas',
    bienvenida: 'Cuadre de caja, cuentas por pagar y seguridad de pagos.',
    destacados: [
      {
        label: 'Mi dashboard táctico (Finanzas)',
        to: '/ti/dashboards/tactico',
        desc: 'KPIs de finanzas.',
      },
      {
        label: 'Reporte de diferencias de caja',
        to: '/caja/reporte-diferencias',
        desc: 'Descuadres por caja y turno.',
      },
      { label: 'Incidentes de fraude', to: '/caja/incidentes', desc: 'Casos abiertos.' },
    ],
  },
  Jefe_RRHH: {
    titulo: 'Jefatura de RRHH',
    bienvenida: 'Personal, retención, capacitación y clima laboral.',
    destacados: [
      {
        label: 'Mi dashboard táctico (RRHH)',
        to: '/ti/dashboards/tactico',
        desc: 'KPIs de personal.',
      },
      { label: 'Empleados', to: '/rrhh/empleados', desc: 'Alta, baja y actualización.' },
      {
        label: 'Clima laboral y rotación',
        to: '/rrhh/clima-laboral',
        desc: 'Resultado semestral vs. rotación.',
      },
    ],
  },
  Encargado_Tienda: {
    titulo: 'Encargado de Tienda',
    bienvenida: 'Operación diaria de tu tienda.',
    destacados: [
      {
        label: 'Inventario y lotes',
        to: '/inventario',
        desc: 'Stock, ajustes y mermas de tu tienda.',
      },
      {
        label: 'Traslados entre tiendas',
        to: '/operaciones/traslados',
        desc: 'Solicitar, aprobar y recibir.',
      },
      { label: 'Cuadre de caja', to: '/caja', desc: 'Cierre de turno.' },
    ],
  },
  Reponedor: {
    titulo: 'Reponedor',
    bienvenida: 'Control físico de góndola e inventario.',
    destacados: [
      {
        label: 'Inventario y lotes',
        to: '/inventario',
        desc: 'Conteo físico, ajustes y verificación de anaquel.',
      },
      {
        label: 'Seguimiento de merma',
        to: '/caja/seguimiento-merma',
        desc: 'Registrar y dar seguimiento a mermas.',
      },
    ],
  },
  Cajero: {
    titulo: 'Cajero',
    bienvenida: '',
    redirect: '/pos',
  },
}

export function portalDe(rol) {
  return PORTALES[rol] ?? { titulo: 'SIRA', bienvenida: 'Bienvenido.', destacados: [] }
}
