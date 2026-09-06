# Tasks: Pagos y Seguridad

**Input**: Design documents from `/specs/007-pagos-seguridad/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/pagos-seguridad.md, quickstart.md

**Tests**: Por Principio X, esta feature exige cobertura obligatoria en: la reevaluación de conformidad de un datáfono al restablecerlo (reutilizando la lógica de 006 sin duplicarla), la no oferta de medios de pago no aprobados/dados de baja en el punto de venta, la independencia entre un incidente de seguridad de pago y un incidente de fraude sobre el mismo datáfono, y el cálculo de duración de cobro excluyendo ventas anuladas y ventas sin `fecha_inicio_cobro` — estas pruebas están incluidas explícitamente abajo, no son opcionales.

**Organización**: Esta feature no crea módulo backend nuevo — extiende `modules/finanzas/` (006) y `modules/ventas/` (001). Reutiliza infraestructura transversal ya construida en 001-006: FastAPI, SQLAlchemy async, Alembic, RBAC, `DataTable.vue`/`WorkPanel.vue`.

## Format: `[ID] [P?] [Story] Descripción`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencia entre sí)
- **[Story]**: A qué historia de usuario pertenece (US1-US5), o ninguna etiqueta si es Setup/Foundational/Polish

---

## Phase 1: Setup

- **T001** [P] Migración Alembic: `ALTER TABLE medios_pago ADD COLUMN aprobado BOOLEAN NOT NULL DEFAULT true, ADD COLUMN aprobado_por INTEGER REFERENCES empleados(empleado_id), ADD COLUMN fecha_aprobacion TIMESTAMP, ADD COLUMN fecha_baja TIMESTAMP` (`data-model.md`).
- **T002** [P] Migración Alembic: `ALTER TABLE ventas ADD COLUMN fecha_inicio_cobro TIMESTAMP; CREATE INDEX idx_ventas_fecha_inicio_cobro ON ventas(fecha_inicio_cobro) WHERE fecha_inicio_cobro IS NOT NULL` (`data-model.md`).
- **T003** [P] Migración Alembic: crear `incidente_seguridad_pago` y `politica_seguridad_pagos` (`data-model.md` completo).
- **T004** [P] Seed de `role_permisos_tabla`: `Encargado_Tienda` (UPDATE `datafonos`, SELECT `politica_seguridad_pagos`, SELECT `ventas`), `Jefe_TI` (INSERT/UPDATE `incidente_seguridad_pago`, INSERT `politica_seguridad_pagos`, INSERT/UPDATE `medios_pago` — nuevo acceso concedido al módulo `Ventas`), `Jefe_Finanzas` (SELECT `incidente_seguridad_pago`, SELECT `politica_seguridad_pagos`), `Jefe_Comercial` (SELECT `ventas` — nuevo acceso concedido de solo lectura al módulo `Ventas`, mismo patrón que `Jefe_Marketing` en 005) (`data-model.md`, Extensión RBAC).
- **T005** [P] Frontend: crear páginas vacías `frontend/src/modules/finanzas/pages/IncidentesSeguridadPagoPage.vue`, `PoliticaSeguridadPagosPage.vue`, `frontend/src/modules/ventas/pages/MediosPagoPage.vue`, `TiempoCobroPage.vue`.

## Phase 2: Foundational (Bloqueante — ninguna user story empieza sin esto)

- **T006** [P] Modelos SQLAlchemy: `IncidenteSeguridadPago`, `PoliticaSeguridadPagos` en `models/`; extender `MedioPago` (T001) y `Venta` (T002).
- **T007** Verificar/exponer `CajaService.evaluar_conformidad_datafonos` de 006 como función reusable para un único `datafono_id` (sin duplicar su lógica) — prerrequisito de US1 (research.md Decisión 2).
- **T008** [P] Seed inicial de `politica_seguridad_pagos` (un texto inicial), para que US4 tenga un estado vigente desde el arranque.
- **T009** Montar las rutas nuevas en `finanzas.router` y `ventas.router` en `main.py`; verificar en RBAC que los accesos concedidos de T004 quedan activos.

**Checkpoint**: Migraciones aplicadas, modelos disponibles, routers montados — listo para implementar historias de usuario.

---

## Phase 3: User Story 1 - Verificación diaria de disponibilidad de datáfonos (Priority: P1) 🎯 MVP

**Goal**: El Encargado de Tienda marca y restablece la disponibilidad diaria de un datáfono sin intervención de TI; el flujo de cobro advierte antes de intentar procesar con tarjeta si el datáfono está fuera de servicio, sin bloquear otros medios de pago.

**Independent Test**: marcar un datáfono como fuera de servicio, verificar que queda visible en ese estado, y luego restablecerlo para verificar que vuelve a estar disponible (o queda no conforme si su firmware no cumple el estándar vigente).

### Tests para User Story 1 ⚠️

- **T010** [P] [US1] Unit test: al restablecer, la reevaluación de conformidad (T007) produce `activo` o `requiere_actualizacion` según `version_firmware` (FR-003, Edge Case).
- **T011** [US1] Contract test: `PATCH finanzas/datafonos/{id}/fuera-servicio`, `PATCH .../restablecer`, `GET ventas/cajas/{id}/datafono-disponible`.
- **T012** [US1] Integration test: marcar fuera de servicio → advertencia en el flujo de cobro sin bloquear otro medio de pago → restablecer → verificar estado final (Escenario 1 de `quickstart.md`).

### Implementación de User Story 1

- **T013** [US1] `FinanzasRepository` (extensión de 006): UPDATE de `datafonos.estado` a `fuera_servicio`.
- **T014** [US1] `FinanzasService.restablecer_datafono()`: invoca T007, determina `activo`/`requiere_actualizacion` (depende de T007, T010).
- **T015** [US1] Endpoints: `PATCH finanzas/datafonos/{id}/fuera-servicio`, `PATCH .../restablecer` — `contracts/pagos-seguridad.md`.
- **T016** [US1] `VentasRepository`/`VentasService` (extensión de 001): consulta de solo lectura a `datafonos.estado` de la caja (research.md Decisión 8, boundary con `modules/finanzas/`).
- **T017** [US1] Endpoint: `GET ventas/cajas/{id}/datafono-disponible`.
- **T018** [US1] `frontend/.../DatafonosPage.vue` (extensión de 006): acción marcar fuera de servicio/restablecido.
- **T019** [US1] `frontend/.../PuntoDeVentaPage.vue` (extensión de 001): advertencia visual no bloqueante cuando el datáfono de la caja no está disponible.

**Checkpoint**: MVP — un Encargado de Tienda gestiona la disponibilidad diaria de sus datáfonos sin esperar a TI, de punta a punta.

---

## Phase 4: User Story 2 - Alta y aprobación de nuevos medios de pago (Priority: P2)

**Goal**: El Jefe de TI da de alta y de baja medios de pago con aprobación explícita, sin afectar ventas ya registradas ni ofrecer en el punto de venta ningún medio no aprobado.

**Independent Test**: dar de alta un medio de pago nuevo y verificar que aparece disponible para selección; darlo de baja y verificar que deja de estar disponible sin afectar ventas ya registradas.

### Tests para User Story 2 ⚠️

- **T020** [P] [US2] Unit test: `GET medios-pago/disponibles` excluye medios no aprobados o dados de baja (FR-007).
- **T021** [US2] Integration test: alta → disponible en punto de venta → baja → ya no disponible → ventas históricas con ese medio de pago intactas (Escenario 2 de `quickstart.md`).

### Implementación de User Story 2

- **T022** [US2] `VentasRepository` (extensión de 001): CRUD de `medios_pago` (alta, baja, listado filtrable, listado de disponibles).
- **T023** [US2] `VentasService.dar_alta_medio_pago()` / `.dar_baja_medio_pago()`: completa `aprobado_por`/`fecha_aprobacion` o `fecha_baja` (depende de T022).
- **T024** [US2] Endpoints: `GET medios-pago`, `POST medios-pago`, `PATCH medios-pago/{id}/baja`, `GET medios-pago/disponibles` — `contracts/pagos-seguridad.md`.
- **T025** [US2] `frontend/.../MediosPagoPage.vue`: catálogo con acción de alta/baja para el Jefe de TI.
- **T026** [US2] Frontend: `PuntoDeVentaPage.vue` consume `GET medios-pago/disponibles` en vez de una lista fija (depende de T024).

**Checkpoint**: OO-4.1.2 completo — ningún medio de pago no aprobado aparece disponible para selección (SC-002).

---

## Phase 5: User Story 3 - Registro y seguimiento de incidentes de seguridad de pago (Priority: P3)

**Goal**: El Jefe de TI registra y da seguimiento a un incidente de seguridad de pago, distinto e independiente de un incidente de fraude interno de caja (006); el Jefe de Finanzas puede consultar el conteo del periodo.

**Independent Test**: registrar un incidente de seguridad de pago asociado a un datáfono, verificar que sigue su ciclo hasta cerrarse, y que el conteo del periodo lo refleja.

### Tests para User Story 3 ⚠️

- **T027** [P] [US3] Unit test: transición `abierto` → `en_investigacion` → `cerrado`, con `actualizado_por`/`fecha_actualizacion` completados en cada paso (FR-009).
- **T028** [P] [US3] Unit test: un `incidente_seguridad_pago` y un `incidente_fraude` (006) sobre el mismo `datafono_id` coexisten sin relación entre sí (FR-010).
- **T029** [US3] Integration test: registrar sin `datafono_id` (Edge Case) → transicionar hasta cerrado → conteo del periodo lo incluye (Escenario 3 de `quickstart.md`).

### Implementación de User Story 3

- **T030** [US3] `FinanzasRepository` (extensión de 006): CRUD de `incidente_seguridad_pago`, incluyendo `datafono_id` nullable.
- **T031** [US3] `FinanzasService.registrar_incidente_seguridad()` / `.transicionar_incidente_seguridad()` (depende de T027).
- **T032** [US3] `FinanzasService.contar_incidentes_seguridad(desde, hasta)`.
- **T033** [US3] Endpoints: `POST incidentes-seguridad-pago`, `GET incidentes-seguridad-pago`, `PATCH .../transicionar`, `GET .../conteo`.
- **T034** [US3] `frontend/.../IncidentesSeguridadPagoPage.vue`: ciclo completo del incidente, separado visualmente de `IncidentesFraudePage.vue` (006).

**Checkpoint**: OO-6.3.3 completo — el KPI secundario de OE-6 tiene una fuente de datos real (SC-003, SC-004).

---

## Phase 6: User Story 4 - Política de seguridad de pagos como documento de referencia (Priority: P4)

**Goal**: El Jefe de TI mantiene el texto vigente de la política de seguridad de pagos, versionado, consultable por Jefe de Finanzas y Encargado de Tienda.

**Independent Test**: definir el texto de la política y verificar que cualquier Encargado de Tienda puede consultarlo íntegro; actualizarlo y verificar que la versión anterior sigue siendo consultable.

### Tests para User Story 4 ⚠️

- **T035** [P] [US4] Unit test: la política vigente es siempre la fila con `fecha_creacion` más reciente; una versión anterior sigue siendo consultable por su `politica_id`.

### Implementación de User Story 4

- **T036** [US4] `FinanzasRepository` (extensión de 006): CRUD append-only de `politica_seguridad_pagos` (insert de nueva versión, consulta de la vigente, consulta por id).
- **T037** [US4] Endpoints: `GET politica-seguridad-pagos`, `PUT politica-seguridad-pagos`, `GET politica-seguridad-pagos/{id}`.
- **T038** [US4] `frontend/.../PoliticaSeguridadPagosPage.vue`: texto vigente consultable por Encargado de Tienda y Jefe de Finanzas, edición solo para Jefe de TI.

**Checkpoint**: la política de seguridad de pagos es consultable sin depender de un documento externo al sistema (SC-005).

---

## Phase 7: User Story 5 - Medición y revisión del tiempo de cobro (Priority: P5)

**Goal**: El sistema registra la duración de cada venta en vivo; el Encargado de Tienda revisa el tiempo promedio semanal por caja, y el Jefe Comercial el mensual por tienda a nivel de red.

**Independent Test**: registrar una venta en vivo de principio a fin, y verificar que su duración queda calculada y disponible tanto en la revisión semanal por caja como en la mensual por tienda.

### Tests para User Story 5 ⚠️

- **T039** [P] [US5] Unit test: cálculo de duración de cobro (`fecha_hora - fecha_inicio_cobro`), excluyendo ventas con `fecha_inicio_cobro IS NULL` y ventas anuladas (FR-015, FR-018).

### Implementación de User Story 5

- **T040** [US5] `VentasService` (extensión de 001): registrar `fecha_inicio_cobro` al iniciar el cobro dentro del flujo ya existente de `POST /api/ventas` (depende de T002).
- **T041** [US5] `VentasRepository.calcular_tiempo_cobro_semanal(caja_id, semana)` / `.calcular_tiempo_cobro_mensual_por_tienda(mes, anio)` (depende de T039).
- **T042** [US5] Endpoints: `GET ventas/cajas/{id}/tiempo-cobro-semanal`, `GET ventas/tiendas/tiempo-cobro-mensual`.
- **T043** [US5] `frontend/.../TiempoCobroPage.vue`: vista semanal por caja (Encargado de Tienda) y mensual por tienda a nivel de red (Jefe Comercial).

**Checkpoint**: OT-4.2 completo — el Encargado de Tienda y el Jefe Comercial ven el tiempo de cobro sin calcularlo manualmente (SC-006).

---

## Phase 8: Polish

- **T044** Ejecutar `/speckit-analyze` sobre esta feature y corregir cualquier inconsistencia detectada entre spec/plan/tasks.
- **T045** Correr los 5 escenarios de `quickstart.md` de punta a punta contra el entorno local.
- **T046** Revisar cobertura de Principio X: confirmar que la reevaluación de conformidad al restablecer (T010), la exclusión de medios de pago no aprobados (T020), la independencia de incidentes (T028) y el cálculo de duración de cobro (T039) tienen test unitario antes de cerrar la feature.
- **T047** Actualizar `checklists/requirements.md` con cualquier hallazgo de la revisión final.

## Dependencias clave

- Phase 2 (Foundational) bloquea todas las historias.
- US1 (T010-T019) no depende de ninguna otra historia de esta feature — reutiliza directamente la lógica de conformidad ya cerrada por 006 (T007).
- US2 (T020-T026) no depende de ninguna otra historia de esta feature — puede implementarse en paralelo a US1 una vez cerrada la Phase 2.
- US3 (T027-T034) no depende de ninguna otra historia de esta feature ni de 006 en tiempo de ejecución — solo comparte el mismo `datafono_id` como referencia opcional, sin relación funcional con `incidentes_fraude`.
- US4 (T035-T038) no depende de ninguna otra historia de esta feature.
- US5 (T039-T043) no depende de ninguna otra historia de esta feature — depende únicamente de la migración T002 (Foundational).
- La consulta de solo lectura de US1 a `datafonos.estado` (T016, boundary `ventas`→`finanzas`) no requiere ningún cambio en `modules/finanzas/` más allá de lo ya expuesto por 006.
