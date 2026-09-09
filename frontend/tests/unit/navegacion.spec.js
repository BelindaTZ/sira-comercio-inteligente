import { describe, it, expect } from 'vitest'
import { CATEGORIAS, categoriasVisibles, itemVisible } from '@/shared/navegacion'

describe('navegacion - visibilidad por rol', () => {
  const crearSesion = ({ rol, modulos = [], tablas = [] }) => ({
    rol,
    esGerente: rol === 'Gerente_General',
    miModulo: ['Jefe_Finanzas', 'Jefe_Comercial', 'Jefe_Operaciones', 'Jefe_TI', 'Jefe_Marketing', 'Jefe_RRHH'].includes(rol) ? rol.replace('Jefe_', '') : null,
    puedeVer(mod) {
      if (this.esGerente) return true
      return modulos.includes(mod)
    },
    puedeLeerTabla(mod, tbl) {
      if (this.esGerente) return true
      return tablas.includes(`${mod}/${tbl}`)
    },
  })

  it('no muestra "Finanzas & BI" para el rol Cajero', () => {
    const sesionCajero = crearSesion({
      rol: 'Cajero',
      modulos: ['Ventas', 'Finanzas'],
      tablas: [
        'Ventas/ventas',
        'Ventas/venta_detalle',
        'Ventas/devoluciones',
        'Finanzas/apertura_caja',
        'Finanzas/cierre_caja',
      ],
    })

    const cats = categoriasVisibles(sesionCajero)
    const labels = cats.map((c) => c.label)

    expect(labels).not.toContain('Finanzas & BI')
    expect(labels).toContain('Punto de Venta')
  })

  it('el ítem "Tiempo de cobro" no es visible para el Cajero', () => {
    const sesionCajero = crearSesion({
      rol: 'Cajero',
      modulos: ['Ventas', 'Finanzas'],
      tablas: ['Ventas/ventas', 'Finanzas/cierre_caja'],
    })

    const catFinanzas = CATEGORIAS.find((c) => c.label === 'Finanzas & BI')
    const grupoCaja = catFinanzas.grupos.find((g) => g.titulo === 'Caja')
    const itemTiempoCobro = grupoCaja.items.find((it) => it.to === '/ventas/tiempo-cobro')

    expect(itemVisible(itemTiempoCobro, sesionCajero)).toBe(false)
  })

  it('permite ver "Finanzas & BI" y "Tiempo de cobro" para el Encargado de Tienda', () => {
    const sesionEncargado = crearSesion({
      rol: 'Encargado_Tienda',
      modulos: ['Ventas', 'Operaciones', 'Comercial', 'Finanzas', 'Marketing_CRM'],
      tablas: ['Finanzas/cierre_caja', 'Finanzas/incidentes_fraude'],
    })

    const cats = categoriasVisibles(sesionEncargado)
    const labels = cats.map((c) => c.label)

    expect(labels).toContain('Finanzas & BI')
    const catFinanzas = cats.find((c) => c.label === 'Finanzas & BI')
    expect(catFinanzas.items.some((it) => it.to === '/ventas/tiempo-cobro')).toBe(true)
  })

  it('permite ver "Finanzas & BI" para el Jefe de Finanzas', () => {
    const sesionFinanzas = crearSesion({
      rol: 'Jefe_Finanzas',
      modulos: ['Finanzas'],
      tablas: ['Finanzas/cierre_caja', 'Finanzas/datafonos', 'Finanzas/ajustes_inventario'],
    })

    const cats = categoriasVisibles(sesionFinanzas)
    const labels = cats.map((c) => c.label)

    expect(labels).toContain('Finanzas & BI')
  })

  it('permite ver "Finanzas & BI" para el Gerente General', () => {
    const sesionGerente = crearSesion({
      rol: 'Gerente_General',
      modulos: [],
      tablas: [],
    })

    const cats = categoriasVisibles(sesionGerente)
    const labels = cats.map((c) => c.label)

    expect(labels).toContain('Finanzas & BI')
  })
})
