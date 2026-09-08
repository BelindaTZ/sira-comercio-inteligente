<script setup>
/**
 * Administración de permisos por rol (feature 008, FR-013). Matriz de módulos y,
 * dentro de cada uno, permisos de tabla. La FK compuesta del esquema garantiza que
 * un permiso de tabla no puede existir sin el permiso de módulo (Edge Case).
 */
import { ref, watch } from 'vue'
import { sistemaApi } from '@/services/sistemaApi'

const roleId = ref('')
const permisosModulo = ref([])
const moduloSel = ref(null)
const permisosTabla = ref([])
const nuevaTabla = ref('')
const error = ref('')

async function cargarModulos() {
  error.value = ''
  permisosTabla.value = []
  moduloSel.value = null
  if (!roleId.value) return
  try {
    permisosModulo.value = await sistemaApi.permisosModulo(Number(roleId.value))
  } catch (e) {
    error.value = e.message
  }
}

async function toggleModulo(m, campo) {
  try {
    const actualizado = await sistemaApi.definirPermisoModulo(Number(roleId.value), m.modulo_id, {
      puedeVer: campo === 'puede_ver' ? !m.puede_ver : m.puede_ver,
      puedeEditar: campo === 'puede_editar' ? !m.puede_editar : m.puede_editar,
    })
    Object.assign(m, actualizado)
  } catch (e) {
    error.value = e.message
  }
}

async function verTablas(m) {
  moduloSel.value = m
  try {
    permisosTabla.value = await sistemaApi.permisosTabla(Number(roleId.value), m.modulo_id)
  } catch (e) {
    error.value = e.message
  }
}

async function guardarTabla(t) {
  try {
    const actualizado = await sistemaApi.definirPermisoTabla(
      Number(roleId.value),
      moduloSel.value.modulo_id,
      t.nombre_tabla,
      {
        canSelect: t.can_select,
        canInsert: t.can_insert,
        canUpdate: t.can_update,
        canDelete: t.can_delete,
      },
    )
    Object.assign(t, actualizado)
  } catch (e) {
    error.value = e.status === 409 ? 'El rol no tiene acceso a ese módulo' : e.message
  }
}

async function agregarTabla() {
  if (!nuevaTabla.value.trim()) return
  permisosTabla.value.push({
    nombre_tabla: nuevaTabla.value.trim(),
    can_select: false,
    can_insert: false,
    can_update: false,
    can_delete: false,
  })
  nuevaTabla.value = ''
}

watch(roleId, cargarModulos)
</script>

<template>
  <main class="mx-auto max-w-4xl px-6 py-8">
    <h1 class="mb-6 text-2xl font-bold text-primary-container">Roles y permisos</h1>

    <p v-if="error" class="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-on-error-container">
      {{ error }}
    </p>

    <label class="mb-4 block text-xs text-on-surface-variant">
      Rol (id)
      <input
        v-model="roleId"
        type="number"
        class="mt-1 block w-32 rounded-lg border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface"
      />
    </label>

    <div class="grid gap-6 lg:grid-cols-2">
      <section>
        <h2 class="mb-2 text-sm font-semibold text-on-surface">Módulos</h2>
        <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-outline-variant text-left text-on-surface-variant">
                <th class="px-3 py-2 font-semibold">Módulo</th>
                <th class="px-3 py-2 text-center font-semibold">Ver</th>
                <th class="px-3 py-2 text-center font-semibold">Editar</th>
                <th class="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in permisosModulo" :key="m.modulo_id" class="border-b border-outline-variant last:border-0">
                <td class="px-3 py-2">{{ m.nombre }}</td>
                <td class="px-3 py-2 text-center">
                  <input type="checkbox" :checked="m.puede_ver" @change="toggleModulo(m, 'puede_ver')" />
                </td>
                <td class="px-3 py-2 text-center">
                  <input type="checkbox" :checked="m.puede_editar" @change="toggleModulo(m, 'puede_editar')" />
                </td>
                <td class="px-3 py-2 text-right">
                  <button
                    type="button"
                    class="rounded-lg bg-primary-container px-2 py-1 text-xs font-semibold text-on-primary-container"
                    @click="verTablas(m)"
                  >
                    Tablas
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="moduloSel">
        <h2 class="mb-2 text-sm font-semibold text-on-surface">
          Tablas de «{{ moduloSel.nombre }}»
        </h2>
        <div class="mb-2 flex items-end gap-2">
          <input
            v-model="nuevaTabla"
            placeholder="nombre_tabla"
            class="rounded-lg border border-outline-variant bg-surface px-2 py-1.5 text-sm text-on-surface"
          />
          <button type="button" class="rounded-lg bg-primary-container px-3 py-1.5 text-xs font-semibold text-on-primary-container" @click="agregarTabla">
            Agregar
          </button>
        </div>
        <div class="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-outline-variant text-left text-on-surface-variant">
                <th class="px-3 py-2 font-semibold">Tabla</th>
                <th class="px-2 py-2 text-center font-semibold">Sel</th>
                <th class="px-2 py-2 text-center font-semibold">Ins</th>
                <th class="px-2 py-2 text-center font-semibold">Upd</th>
                <th class="px-2 py-2 text-center font-semibold">Del</th>
                <th class="px-2 py-2" />
              </tr>
            </thead>
            <tbody>
              <tr v-if="!permisosTabla.length">
                <td colspan="6" class="px-3 py-6 text-center text-on-surface-variant">Sin permisos de tabla</td>
              </tr>
              <tr v-for="t in permisosTabla" :key="t.nombre_tabla" class="border-b border-outline-variant last:border-0">
                <td class="px-3 py-2">{{ t.nombre_tabla }}</td>
                <td class="px-2 py-2 text-center"><input v-model="t.can_select" type="checkbox" /></td>
                <td class="px-2 py-2 text-center"><input v-model="t.can_insert" type="checkbox" /></td>
                <td class="px-2 py-2 text-center"><input v-model="t.can_update" type="checkbox" /></td>
                <td class="px-2 py-2 text-center"><input v-model="t.can_delete" type="checkbox" /></td>
                <td class="px-2 py-2 text-right">
                  <button type="button" class="rounded-lg bg-primary-container px-2 py-1 text-xs font-semibold text-on-primary-container" @click="guardarTabla(t)">
                    Guardar
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </main>
</template>
