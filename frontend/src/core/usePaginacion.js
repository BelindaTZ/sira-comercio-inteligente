import { computed, reactive, watch } from 'vue'

/**
 * Composable de paginación reutilizable (Principio XII: todo listado pagina).
 * No hace peticiones — expone el estado y el `params` que la capa de servicios
 * envía al backend.
 *
 * @param {object} opts
 * @param {number} [opts.size=25]      tamaño de página inicial
 * @param {Function} [opts.onChange]   callback al cambiar page/size (recarga)
 */
export function usePaginacion({ size = 25, onChange } = {}) {
  const state = reactive({
    page: 1,
    size,
    total: 0,
  })

  const pages = computed(() => (state.size ? Math.ceil(state.total / state.size) : 0))
  const hasPrev = computed(() => state.page > 1)
  const hasNext = computed(() => state.page < pages.value)

  const params = computed(() => ({ page: state.page, size: state.size }))

  function setTotal(total) {
    state.total = Number(total) || 0
  }

  function goTo(page) {
    const target = Math.min(Math.max(1, page), Math.max(1, pages.value))
    if (target !== state.page) state.page = target
  }

  function next() {
    if (hasNext.value) state.page += 1
  }

  function prev() {
    if (hasPrev.value) state.page -= 1
  }

  function reset() {
    state.page = 1
  }

  if (onChange) {
    watch(
      () => [state.page, state.size],
      () => onChange(params.value)
    )
  }

  return { state, params, pages, hasPrev, hasNext, setTotal, goTo, next, prev, reset }
}
