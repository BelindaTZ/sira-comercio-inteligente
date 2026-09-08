<script setup>
/** Barra inferior emerald de la referencia (`screen.png` del Dashboard Ejecutivo). */
const anio = new Date().getFullYear()
</script>

<template>
  <footer
    class="mt-auto border-t border-[#072623] bg-primary-container px-6 py-3 text-[11px] text-primary-fixed-dim lg:px-8"
  >
    <div class="mx-auto flex max-w-[1720px] flex-wrap items-center justify-between gap-2">
      <span>© {{ anio }} SIRA — Marzú Retail Group SpA</span>
      <span class="flex items-center gap-2">
        <span class="inline-block h-1.5 w-1.5 rounded-full bg-tertiary-fixed" />
        Operativo · PostgreSQL 16
      </span>
    </div>
  </footer>
</template>
