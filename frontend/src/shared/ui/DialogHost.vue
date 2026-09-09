<script setup>
/**
 * Punto de render de los diálogos de `dialogs.js`. Se monta una sola vez en
 * `App.vue`. Usa el `Modal` del design-system (Principio XII) en lugar de los
 * cuadros nativos del navegador.
 */
import { computed } from 'vue'
import Modal from './Modal.vue'
import { dialogState, accept, cancel } from './dialogs'

// enfoca el campo apenas aparece el diálogo de entrada
const vFocus = { mounted: (el) => el.focus() }

const promptInvalido = computed(
  () =>
    dialogState.mode === 'prompt' &&
    dialogState.required &&
    !String(dialogState.value).trim(),
)
</script>

<template>
  <Modal v-if="dialogState.visible" :titulo="dialogState.title" @cerrar="cancel">
    <form class="space-y-4" @submit.prevent="accept">
      <p v-if="dialogState.message" class="text-[13px] leading-relaxed text-slate-600">
        {{ dialogState.message }}
      </p>

      <label v-if="dialogState.mode === 'prompt'" class="block text-[12px] font-semibold text-slate-600">
        <span v-if="dialogState.label">{{ dialogState.label }}</span>
        <input
          v-model="dialogState.value"
          v-focus
          :type="dialogState.inputType"
          :placeholder="dialogState.placeholder"
          :required="dialogState.required"
          class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
        />
      </label>

      <div class="flex items-center justify-end gap-2.5 pt-1">
        <button
          type="button"
          class="rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-[13px] font-semibold text-slate-700 hover:bg-brand-50"
          @click="cancel"
        >
          {{ dialogState.cancelText }}
        </button>
        <button
          type="submit"
          :disabled="promptInvalido"
          class="rounded-xl px-4 py-2 text-[13px] font-bold text-white disabled:opacity-40"
          :class="
            dialogState.tone === 'danger'
              ? 'bg-crimson-ruby hover:brightness-95'
              : 'bg-brand-800 hover:bg-brand-700'
          "
        >
          {{ dialogState.confirmText }}
        </button>
      </div>
    </form>
  </Modal>
</template>
