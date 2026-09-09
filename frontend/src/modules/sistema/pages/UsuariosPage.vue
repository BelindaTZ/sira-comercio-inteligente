<script setup>
/**
 * Cuentas de usuario (feature 008, FR-007/FR-008/FR-012). El Jefe de TI crea la
 * cuenta de un empleado ya registrado y asigna/revoca su rol con efecto
 * inmediato. El resto (incl. Gerencia) consulta. Arquetipo "Gestión" del kit.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { sistemaApi } from '@/services/sistemaApi'
import { confirm } from '@/shared/ui/dialogs'
import { useSesion } from '@/stores/sesion'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiTile from '@/shared/ui/KpiTile.vue'
import SemanticChip from '@/shared/ui/SemanticChip.vue'
import Btn from '@/shared/ui/Btn.vue'
import Icon from '@/shared/ui/Icon.vue'
import Modal from '@/shared/ui/Modal.vue'
import DataTable from '@/shared/DataTable.vue'

const sesion = useSesion()
const puedeAdministrar = computed(() => !sesion.esGerente && sesion.rol === 'Jefe_TI')

const usuarios = ref([])
const roles = ref([])
const sinCuenta = ref([])
const cargando = ref(false)
const error = ref('')
const aviso = ref('')
const busqueda = ref('')
const page = ref(1)
const size = ref(15)
const modal = ref(null) // 'crear' | { usuario } | null
const guardando = ref(false)

const nueva = reactive({ empleadoId: '', username: '', passwordInicial: '', roleId: '' })
const rolNuevo = ref('')

const kpi = computed(() => ({
  total: usuarios.value.length,
  activas: usuarios.value.filter((u) => u.activo).length,
  sinCuenta: sinCuenta.value.length,
  roles: roles.value.length,
}))

const columnas = [
  { key: 'usuario', label: 'Cuenta' },
  { key: 'empleado', label: 'Empleado', width: '180px' },
  { key: 'rol', label: 'Rol', width: '150px' },
  { key: 'ultimo', label: 'Último acceso', align: 'right', width: '160px' },
  { key: 'estado', label: 'Estado', align: 'center', width: '110px' },
  { key: 'acciones', label: '', align: 'right', width: '120px' },
]

const filtrados = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  return q
    ? usuarios.value.filter((u) =>
        `${u.username} ${u.empleado_nombre || ''} ${u.rol_nombre || ''}`.toLowerCase().includes(q),
      )
    : usuarios.value
})
const pagina = computed(() =>
  filtrados.value.slice((page.value - 1) * size.value, page.value * size.value),
)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    ;[usuarios.value, roles.value] = await Promise.all([
      sistemaApi.listarUsuarios(),
      roles.value.length ? Promise.resolve(roles.value) : sistemaApi.listarRoles(),
    ])
    if (puedeAdministrar.value) sinCuenta.value = await sistemaApi.empleadosSinCuenta().catch(() => [])
    page.value = 1
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function crear() {
  if (!nueva.empleadoId || !nueva.username.trim() || !nueva.passwordInicial || !nueva.roleId) return
  guardando.value = true
  error.value = ''
  try {
    await sistemaApi.crearUsuario({
      empleadoId: Number(nueva.empleadoId),
      username: nueva.username.trim(),
      passwordInicial: nueva.passwordInicial,
      roleId: Number(nueva.roleId),
    })
    modal.value = null
    Object.assign(nueva, { empleadoId: '', username: '', passwordInicial: '', roleId: '' })
    aviso.value = 'Cuenta creada.'
    await cargar()
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}

function abrirRol(usuario) {
  rolNuevo.value = String(usuario.role_id)
  modal.value = { usuario }
}

async function cambiarRol() {
  const u = modal.value.usuario
  if (!rolNuevo.value || Number(rolNuevo.value) === u.role_id) {
    modal.value = null
    return
  }
  const ok = await confirm({
    title: `Cambiar el rol de ${u.username}`,
    message: 'El cambio tiene efecto inmediato en la próxima petición del usuario.',
    confirmText: 'Asignar rol',
  })
  if (!ok) return
  try {
    await sistemaApi.asignarRol(u.usuario_id, Number(rolNuevo.value))
    modal.value = null
    aviso.value = `Rol de ${u.username} actualizado.`
    await cargar()
  } catch (e) {
    error.value = e.message
  }
}

const fecha = (s) => (s ? String(s).slice(0, 16).replace('T', ' ') : 'nunca')

onMounted(cargar)
</script>

<template>
  <div class="mx-auto max-w-[1500px] px-6 py-8 lg:px-8">
    <PageHeader
      titulo="Cuentas de usuario"
      subtitulo="Cuentas del sistema y su rol. El Jefe de TI crea la cuenta de un empleado ya registrado y le asigna un rol con efecto inmediato (FR-007/FR-008/FR-012)."
    >
      <template #badge>
        <SemanticChip tipo="ok">{{ kpi.activas }} activas</SemanticChip>
      </template>
      <template #acciones>
        <Btn v-if="puedeAdministrar" variant="primary" @click="modal = 'crear'">
          <Icon name="plus" :size="15" /> Crear cuenta
        </Btn>
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

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiTile label="Cuentas en el sistema" :valor="kpi.total.toLocaleString('es-EC')" variant="emerald" :microcopy="`${kpi.activas} activas`" />
      <KpiTile label="Roles definidos" :valor="kpi.roles.toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="shield" :size="16" /></template>
      </KpiTile>
      <KpiTile
        v-if="puedeAdministrar"
        label="Empleados sin cuenta"
        :valor="kpi.sinCuenta.toLocaleString('es-EC')"
        :estado-tipo="kpi.sinCuenta > 0 ? 'fifo' : 'ok'"
      >
        <template #icono><Icon name="users" :size="16" /></template>
      </KpiTile>
      <KpiTile label="Inactivas" :valor="(kpi.total - kpi.activas).toLocaleString('es-EC')" estado-tipo="neutral">
        <template #icono><Icon name="x" :size="16" /></template>
      </KpiTile>
    </section>

    <DataTable
      titulo="Directorio de cuentas"
      :columns="columnas"
      :rows="pagina"
      row-key="usuario_id"
      :loading="cargando"
      densa
      :page="page"
      :size="size"
      :total="filtrados.length"
      :search="busqueda"
      search-placeholder="Usuario, empleado o rol…"
      empty-text="Sin cuentas que coincidan"
      @update:page="page = $event"
      @update:size="((size = $event), (page = 1))"
      @update:search="((busqueda = $event), (page = 1))"
    >
      <template #cell:usuario="{ row }">
        <div class="leading-tight">
          <div class="text-[12px] font-semibold text-slate-800">{{ row.username }}</div>
          <div class="font-mono text-[11px] text-slate-400">#{{ row.usuario_id }}</div>
        </div>
      </template>
      <template #cell:empleado="{ row }">
        <span class="text-[12px] text-slate-700">{{ row.empleado_nombre || `#${row.empleado_id}` }}</span>
      </template>
      <template #cell:rol="{ row }">
        <SemanticChip tipo="neutral">{{ row.rol_nombre || `#${row.role_id}` }}</SemanticChip>
      </template>
      <template #cell:ultimo="{ row }">
        <span class="tabular-nums text-[12px] text-slate-500">{{ fecha(row.ultimo_login) }}</span>
      </template>
      <template #cell:estado="{ row }">
        <SemanticChip :tipo="row.activo ? 'ok' : 'quiebre'">
          {{ row.activo ? 'Activa' : 'Inhabilitada' }}
        </SemanticChip>
      </template>
      <template #cell:acciones="{ row }">
        <Btn
          v-if="puedeAdministrar && row.activo"
          variant="ghost"
          class="!px-2.5 !py-1 !text-[12px]"
          @click="abrirRol(row)"
        >
          Cambiar rol
        </Btn>
        <span v-else class="text-[11px] text-slate-400">—</span>
      </template>
    </DataTable>

    <!-- Modal: crear cuenta -->
    <Modal v-if="modal === 'crear'" titulo="Crear cuenta de usuario" @cerrar="modal = null">
      <form class="space-y-3" @submit.prevent="crear">
        <label class="block text-[12px] font-semibold text-slate-600">
          Empleado (sin cuenta)
          <select v-model="nueva.empleadoId" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800">
            <option value="" disabled>Elegí un empleado…</option>
            <option v-for="e in sinCuenta" :key="e.empleado_id" :value="e.empleado_id">
              {{ e.nombre }}<template v-if="e.email"> · {{ e.email }}</template>
            </option>
          </select>
        </label>
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-[12px] font-semibold text-slate-600">
            Usuario
            <input v-model="nueva.username" required maxlength="50" class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
          <label class="block text-[12px] font-semibold text-slate-600">
            Rol
            <select v-model="nueva.roleId" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800">
              <option value="" disabled>Elegí un rol…</option>
              <option v-for="r in roles" :key="r.role_id" :value="r.role_id">{{ r.nombre }}</option>
            </select>
          </label>
          <label class="col-span-2 block text-[12px] font-semibold text-slate-600">
            Contraseña inicial
            <input v-model="nueva.passwordInicial" type="password" minlength="8" required class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800" />
          </label>
        </div>
        <div class="flex justify-end gap-2.5 pt-1">
          <Btn variant="ghost" type="button" @click="modal = null">Cancelar</Btn>
          <Btn variant="primary" type="submit" :disabled="guardando">
            {{ guardando ? 'Creando…' : 'Crear cuenta' }}
          </Btn>
        </div>
      </form>
    </Modal>

    <!-- Modal: cambiar rol -->
    <Modal v-if="modal && modal !== 'crear'" :titulo="`Rol de ${modal.usuario.username}`" @cerrar="modal = null">
      <form class="space-y-3" @submit.prevent="cambiarRol">
        <label class="block text-[12px] font-semibold text-slate-600">
          Rol
          <select v-model="rolNuevo" class="mt-1 block w-full rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm text-slate-800">
            <option v-for="r in roles" :key="r.role_id" :value="String(r.role_id)">{{ r.nombre }}</option>
          </select>
        </label>
        <p class="text-[11px] text-slate-500">El cambio tiene efecto inmediato en la próxima petición del usuario.</p>
        <div class="flex justify-end gap-2.5">
          <Btn variant="ghost" type="button" @click="modal = null">Cancelar</Btn>
          <Btn variant="primary" type="submit">Asignar rol</Btn>
        </div>
      </form>
    </Modal>
  </div>
</template>
