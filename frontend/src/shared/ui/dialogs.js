/**
 * Diálogos de confirmación / entrada rápida como modales in-app (Principio XII).
 * Reemplaza `window.confirm` / `window.prompt`, que rompen el sistema de diseño.
 *
 *   import { confirm, prompt } from '@/shared/ui/dialogs'
 *   if (!(await confirm({ title: '¿Dar de baja?', tone: 'danger' }))) return
 *   const motivo = await prompt({ title: 'Motivo', required: true })  // string | null
 *
 * `<DialogHost>` (montado una vez en App.vue) es quien los pinta.
 */
import { reactive } from 'vue'

export const dialogState = reactive({
  visible: false,
  mode: 'confirm', // 'confirm' | 'prompt'
  title: '',
  message: '',
  tone: 'default', // 'default' | 'danger'
  confirmText: 'Aceptar',
  cancelText: 'Cancelar',
  // sólo modo 'prompt'
  label: '',
  placeholder: '',
  inputType: 'text',
  required: false,
  value: '',
})

let _resolve = null

function _settle(result) {
  dialogState.visible = false
  const r = _resolve
  _resolve = null
  if (r) r(result)
}

export function accept() {
  if (dialogState.mode === 'prompt') {
    const v = dialogState.value.trim()
    if (dialogState.required && !v) return
    _settle(v)
  } else {
    _settle(true)
  }
}

export function cancel() {
  _settle(dialogState.mode === 'prompt' ? null : false)
}

/** Confirmación sí/no. Resuelve `true` al aceptar, `false` al cancelar. */
export function confirm(opts = {}) {
  return new Promise((resolve) => {
    _resolve = resolve
    Object.assign(dialogState, {
      mode: 'confirm',
      title: opts.title ?? '¿Confirmar la acción?',
      message: opts.message ?? '',
      tone: opts.tone ?? 'default',
      confirmText: opts.confirmText ?? 'Aceptar',
      cancelText: opts.cancelText ?? 'Cancelar',
      visible: true,
    })
  })
}

/** Entrada de texto corta. Resuelve el texto al aceptar, `null` al cancelar. */
export function prompt(opts = {}) {
  return new Promise((resolve) => {
    _resolve = resolve
    Object.assign(dialogState, {
      mode: 'prompt',
      title: opts.title ?? 'Ingrese un valor',
      message: opts.message ?? '',
      tone: opts.tone ?? 'default',
      label: opts.label ?? '',
      placeholder: opts.placeholder ?? '',
      inputType: opts.inputType ?? 'text',
      required: opts.required ?? false,
      value: opts.initial ?? '',
      confirmText: opts.confirmText ?? 'Aceptar',
      cancelText: opts.cancelText ?? 'Cancelar',
      visible: true,
    })
  })
}

export function useDialogs() {
  return { confirm, prompt }
}
