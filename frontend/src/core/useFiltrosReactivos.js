import { reactive, toRefs, watch } from 'vue'

/**
 * Filtros de búsqueda reactivos (Principio XII: sin botón "Buscar"/"Filtrar",
 * se aplican al cambiar el criterio). Aplica debounce para no disparar una
 * petición por cada tecla.
 *
 * @param {object} initial            valores iniciales de cada filtro
 * @param {Function} onApply          se llama con los filtros activos (sin vacíos)
 * @param {number} [debounceMs=300]
 */
export function useFiltrosReactivos(initial, onApply, debounceMs = 300) {
  const filtros = reactive({ ...initial })
  let timer = null

  function activos() {
    return Object.fromEntries(
      Object.entries(filtros).filter(([, v]) => v !== '' && v !== null && v !== undefined)
    )
  }

  function limpiar() {
    Object.assign(filtros, initial)
  }

  watch(
    filtros,
    () => {
      clearTimeout(timer)
      timer = setTimeout(() => onApply(activos()), debounceMs)
    },
    { deep: true }
  )

  return { filtros, ...toRefs(filtros), activos, limpiar }
}
