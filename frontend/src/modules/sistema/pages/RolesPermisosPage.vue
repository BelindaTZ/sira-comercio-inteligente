<script setup>
/**
 * Administración de permisos por rol (feature 008, FR-013). Matriz de módulos y,
 * dentro de cada uno, permisos de tabla. La FK compuesta del esquema garantiza
 * que un permiso de tabla no exista sin el permiso de módulo. Arquetipo "Gestión".
 */
import { computed, onMounted, ref, watch } from 'vue'
import { sistemaApi } from '@/services/sistemaApi'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'

const sesion = useSesion()
const puedeEditar = computed(
  () => !sesion.esGerente && sesion.puedeEditarTabla('Sistema', 'role_permisos_modulo'),
)

const roles = ref([])
const roleId = ref('')
const permisosModulo = ref([])
const moduloSel = ref(null)
const permisosTabla = ref([])
const nuevaTabla = ref('')
const error = ref('')
const aviso = ref('')

const rolNombre = computed(() => roles.value.find((r) => r.role_id === Number(roleId.value))?.nombre)

async function cargarModulos() {
  error.value = ''
  permisosTabla.value = []
  moduloSel.value = null
  if (!roleId.value) {
    permisosModulo.value = []
    return
  }
  try {
    permisosModulo.value = await sistemaApi.permisosModulo(Number(roleId.value))
  } catch (e) {
    error.value = e.message
  }
}

async function toggleModulo(m, campo) {
  if (!puedeEditar.value) return
  try {
    const r = await sistemaApi.definirPermisoModulo(Number(roleId.value), m.modulo_id, {
      puedeVer: campo === 'puede_ver' ? !m.puede_ver : m.puede_ver,
      puedeEditar: campo === 'puede_editar' ? !m.puede_editar : m.puede_editar,
    })
    Object.assign(m, r)
  } catch (e) {
    error.value = e.message
  }
}

async function verTablas(m) {
  moduloSel.value = m
  error.value = ''
  try {
    permisosTabla.value = await sistemaApi.permisosTabla(Number(roleId.value), m.modulo_id)
  } catch (e) {
    error.value = e.message
  }
}

async function guardarTabla(t) {
  try {
    const r = await sistemaApi.definirPermisoTabla(
      Number(roleId.value),
      moduloSel.value.modulo_id,
      t.nombre_tabla,
      { canSelect: t.can_select, canInsert: t.can_insert, canUpdate: t.can_update, canDelete: t.can_delete },
    )
    Object.assign(t, r)
    aviso.value = `Permisos de «${t.nombre_tabla}» guardados.`
  } catch (e) {
    error.value = e.status === 409 ? 'El rol no tiene acceso a ese módulo' : e.message
  }
}

function agregarTabla() {
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
onMounted(async () => {
  roles.value = await sistemaApi.listarRoles().catch(() => [])
})
</script>

<template>
  <div class="mx-auto max-w-[1400px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Roles y permisos"
      subtitulo="Matriz RBAC de dos niveles: acceso por módulo y, dentro de cada uno, permisos de tabla (select / insert / update / delete). El cambio tiene efecto inmediato (FR-013)."
    >
      <template #badge>
        <SemanticChip v-if="rolNombre" tipo="neutral">Rol: {{ rolNombre }}</SemanticChip>
      </template>
      <template #acciones>
        <label
          class="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-slate-600"
        >
          <Icon name="shield" :size="14" class="text-brand-700" />
          <select v-model="roleId" class="bg-transparent text-slate-800 focus:outline-none">
            <option value="">Elegí un rol…</option>
            <option v-for="r in roles" :key="r.role_id" :value="r.role_id">{{ r.nombre }}</option>
          </select>
        </label>
      </template>
    </PageHeader>

    <p v-if="error" class="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-crimson-ruby" role="alert">
      {{ error }}
    </p>
    <p
      v-if="aviso"
      class="mb-4 flex items-center justify-between gap-3 rounded-lg border border-brand-200 bg-brand-50 px-4 py-2 text-sm text-brand-800"
    >
      <span>{{ aviso }}</span>
      <button class="text-brand-600 hover:text-brand-900" @click="aviso = ''"><Icon name="x" :size="14" /></button>
    </p>

    <p v-if="!roleId" class="satin-card rounded-2xl p-10 text-center text-[13px] text-slate-500 shadow-card-subtle">
      Elegí un rol para ver y ajustar sus permisos.
    </p>

    <div v-else class="grid items-start gap-6 xl:grid-cols-2">
      <section class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
        <div class="border-b border-brand-200 px-5 py-3">
          <h2 class="font-display text-[14px] font-bold text-brand-950">Acceso por módulo</h2>
        </div>
        <table class="w-full text-left text-[13px]">
          <thead>
            <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
              <th class="px-5 py-3">Módulo</th>
              <th class="px-3 py-3 text-center">Ver</th>
              <th class="px-3 py-3 text-center">Editar</th>
              <th class="px-3 py-3" />
            </tr>
          </thead>
          <tbody class="divide-y divide-brand-100/90 bg-white/80">
            <tr v-for="m in permisosModulo" :key="m.modulo_id" class="hover:bg-brand-50/70" :class="moduloSel?.modulo_id === m.modulo_id ? 'bg-brand-50' : ''">
              <td class="px-5 py-2.5 font-semibold text-slate-800">{{ m.nombre }}</td>
              <td class="px-3 py-2.5 text-center">
                <input type="checkbox" :checked="m.puede_ver" :disabled="!puedeEditar" @change="toggleModulo(m, 'puede_ver')" />
              </td>
              <td class="px-3 py-2.5 text-center">
                <input type="checkbox" :checked="m.puede_editar" :disabled="!puedeEditar" @change="toggleModulo(m, 'puede_editar')" />
              </td>
              <td class="px-3 py-2.5 text-right">
                <Btn variant="ghost" class="!px-2.5 !py-1 !text-[12px]" @click="verTablas(m)">Tablas</Btn>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="moduloSel" class="satin-card overflow-hidden rounded-2xl shadow-card-subtle">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-brand-200 px-5 py-3">
          <h2 class="font-display text-[14px] font-bold text-brand-950">Tablas de «{{ moduloSel.nombre }}»</h2>
          <div v-if="puedeEditar" class="flex items-center gap-1.5">
            <input
              v-model="nuevaTabla"
              placeholder="nombre_tabla"
              class="w-40 rounded-lg border border-brand-300 bg-white px-2.5 py-1 text-[12px] text-slate-800"
            />
            <Btn variant="ghost" class="!px-2.5 !py-1 !text-[12px]" @click="agregarTabla">Agregar</Btn>
          </div>
        </div>
        <table class="w-full text-left text-[13px]">
          <thead>
            <tr class="border-b border-brand-700 bg-gradient-to-r from-brand-800 to-brand-750 text-[10px] font-bold uppercase tracking-wider text-brand-100">
              <th class="px-5 py-3">Tabla</th>
              <th class="px-2 py-3 text-center">Sel</th>
              <th class="px-2 py-3 text-center">Ins</th>
              <th class="px-2 py-3 text-center">Upd</th>
              <th class="px-2 py-3 text-center">Del</th>
              <th v-if="puedeEditar" class="px-2 py-3" />
            </tr>
          </thead>
          <tbody class="divide-y divide-brand-100/90 bg-white/80">
            <tr v-if="!permisosTabla.length">
              <td :colspan="puedeEditar ? 6 : 5" class="px-5 py-6 text-center text-slate-400">
                Este rol no tiene permisos de tabla en este módulo.
              </td>
            </tr>
            <tr v-for="t in permisosTabla" :key="t.nombre_tabla" class="hover:bg-brand-50/70">
              <td class="px-5 py-2.5 font-mono text-[12px] text-slate-700">{{ t.nombre_tabla }}</td>
              <td class="px-2 py-2.5 text-center"><input v-model="t.can_select" type="checkbox" :disabled="!puedeEditar" /></td>
              <td class="px-2 py-2.5 text-center"><input v-model="t.can_insert" type="checkbox" :disabled="!puedeEditar" /></td>
              <td class="px-2 py-2.5 text-center"><input v-model="t.can_update" type="checkbox" :disabled="!puedeEditar" /></td>
              <td class="px-2 py-2.5 text-center"><input v-model="t.can_delete" type="checkbox" :disabled="!puedeEditar" /></td>
              <td v-if="puedeEditar" class="px-2 py-2.5 text-right">
                <Btn variant="primary" class="!px-2.5 !py-1 !text-[12px]" @click="guardarTabla(t)">Guardar</Btn>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </div>
</template>
