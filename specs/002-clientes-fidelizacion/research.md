# Research: Clientes y Fidelización (002-clientes-fidelizacion)

**Fase 0 de `/speckit-plan`** — Todas las decisiones de Technical Context ya venían resueltas por `constitution.md` (no quedó ningún `[NEEDS CLARIFICATION]`); este documento cubre las decisiones técnicas concretas que la constitución no fija literalmente y que esta feature sí necesita para pasar a `data-model.md`/`tasks.md`. Incluye, en particular, las dos decisiones que `spec.md` dejó explícitamente diferidas a este documento: la fórmula de CLV (FR-005) y los multiplicadores de severidad de churn (FR-010).

## 1. Fórmula del CLV compuesto (FR-005, FR-006)

- **Decision**: `clv_score` (0 a 1) = `0.5 × frecuencia_norm + 0.5 × margen_norm`, calculado sobre una ventana móvil de 180 días de historial de compras de cada cliente. `frecuencia_norm` = (número de compras del cliente en la ventana) / (percentil 95 de número de compras entre todos los clientes activos en la misma ventana), truncado a 1.0. `margen_norm` = análogo, pero con la suma de margen real (Σ `precio_venta - costo` por línea vendida) en vez de número de compras. El nivel de fidelización se asigna comparando este score contra los umbrales configurables de FR-007.
- **Rationale**: cumple el requisito duro de FR-005 (nunca gasto bruto puro) combinando dos señales independientes y ya disponibles en el esquema (`ventas`/`venta_detalle` de 001). Normalizar contra el percentil 95 — no el máximo absoluto — evita que un solo cliente atípico comprima la escala para todos los demás (más robusto que un min-max simple). Los pesos 50/50 son una heurística MVP fija y explicable (Principio VIII, KISS); FR-007 delega al Jefe de Marketing el ajuste de los **umbrales de nivel**, no de estos pesos — es una decisión de alcance ya fijada en el spec, no una limitación de este documento.
- **Alternatives considered**: RFM completo (Recencia+Frecuencia+Monetario) — el propio spec excluye la variable "Monetario" (gasto bruto) como único criterio, así que un RFM clásico violaría FR-005; un modelo predictivo (regresión) de valor futuro — desproporcionado para el MVP y no lo pide el spec, a diferencia de 004 que sí es forecasting con ML.
- **Nota**: un cliente con menos de 1 compra en la ventana no tiene `clv_score` calculable — queda sin nivel de fidelización hasta su primera compra (ya documentado como Edge Case en `spec.md`, no un caso nuevo).

## 2. Ciclo de compra individual y severidad de riesgo de fuga (FR-009, FR-010)

- **Decision**: `ciclo_compra_dias(cliente)` = promedio de los intervalos en días entre compras consecutivas, calculado sobre las últimas 10 compras del cliente (o todas, si tiene menos de 10) — evita que compras muy antiguas distorsionen el ciclo si el hábito del cliente cambió. `dias_desde_ultima_compra` = fecha de cálculo − fecha de la última compra registrada. Severidad:
  - **en_riesgo**: `dias_desde_ultima_compra > 1.5 × ciclo_compra_dias`.
  - **inactivo**: `dias_desde_ultima_compra > 3 × ciclo_compra_dias`.
  - Sin severidad (no aparece como en riesgo): dentro de su ciclo normal.
- **Rationale**: ambos multiplicadores son relativos al ciclo propio de cada cliente, nunca un umbral fijo de días igual para todos (requisito duro de FR-009/FR-010). 1.5x da margen antes de alarmar por una variación normal del hábito de compra; 3x indica abandono sostenido, más allá de cualquier variación esperada de su propio patrón — mismo criterio heurístico simple y explicable ya usado en 001 para el punto de reposición dinámico (Principio VIII).
- **Alternatives considered**: análisis de supervivencia (survival analysis) para una probabilidad de churn — más preciso pero desproporcionado para el MVP y no lo pide el spec (a diferencia de 004); un único nivel de riesgo sin distinguir `inactivo` — no resuelve el requisito de distinguir abandono reciente de abandono prolongado que motivó esta ronda de cambios.
- **Nota**: un cliente con menos de 2 compras no tiene `ciclo_compra_dias` calculable — queda sin score de churn hasta su segunda compra, análogo a la nota de CLV arriba.

## 3. Jobs periódicos — cálculo semanal de CLV/churn y evento diario de hitos (FR-005, FR-009, FR-010, FR-012)

- **Decision**: `APScheduler` embebido en el propio proceso backend (no un servicio separado, no Airflow), con dos jobs: uno semanal (recalcula `clv_score` y `churn_score`/severidad para todo cliente activo con consentimiento aceptado) y uno diario (genera el evento de cumpleaños/aniversario y dispara el cupón vía SendGrid).
- **Rationale**: Principio III reserva Airflow para el flujo ELT hacia ClickHouse (features 009/010, agregación táctica/estratégica); esto es cálculo operativo directo sobre PostgreSQL (Principio II), sin necesidad de un orquestador de pipelines — mismo criterio ya aplicado en 001 para el punto de reposición dinámico (job diario embebido, sin Airflow). APScheduler es una librería Python ligera, ya idiomática en el ecosistema FastAPI, sin infraestructura adicional (Principio VIII).
- **Alternatives considered**: cron del sistema operativo llamando a un script aparte — funciona, pero separa el job del ciclo de vida/logs de la app; Celery + Redis — mucha más capacidad de la necesaria para 2 jobs periódicos simples, introduce un broker nuevo sin justificación (Principio VIII).

## 4. Gating de consentimiento de tratamiento de datos (FR-001, LOPDP)

- **Decision**: el filtro de consentimiento (excluir de CLV/churn/campañas a quien no dio consentimiento) se implementa como condición `WHERE consentimiento_datos = true` en la capa de repository de los jobs de CLV/churn y en la query de segmentación de campañas — nunca como trigger o regla a nivel de base de datos.
- **Rationale**: mantiene la regla de negocio en el backend (Principio XI: lógica de negocio en router→service→repository, no en la base de datos), consistente con dónde vive el resto de las reglas de negocio ya decididas en 001 (FIFO, punto de reposición) — todas en el backend, ninguna en PL/pgSQL.
- **Alternatives considered**: trigger o vista materializada en PostgreSQL que excluya automáticamente — más "a prueba de fallos" ante un futuro nuevo caller, pero introduce lógica de negocio en la base de datos, inconsistente con Principio XI y con el resto de la arquitectura ya decidida.

## 5. Anonimización real en baja de cliente (FR-003)

- **Decision**: al dar de baja, el servicio ejecuta un UPDATE sobre `clientes` que reemplaza `nombre` → `'CLIENTE ANONIMIZADO'`, `email` → `'anon-{household_id}@anonimizado.local'` (garantiza unicidad frente al UNIQUE existente), `telefono` → `NULL`, `fecha_nacimiento` → `NULL`, y marca `activo = false` — conservando `household_id` intacto para no romper la FK de sus ventas, CLV y churn históricos.

## 6. Identificación del cliente afiliado por cédula en punto de venta (FR-001, Ronda 5)

- **Decision**: `documento_identidad` (cédula/RUC, `VARCHAR(13)` para admitir RUC de 13 dígitos además de cédula de 10) se agrega como columna **opcional** de `clientes`, con un índice único parcial (`WHERE documento_identidad IS NOT NULL`) — permite muchos `NULL` (clientes que no lo dieron) pero rechaza duplicados cuando sí se proporciona. `GET /api/clientes?search=` lo incluye en la comparación, así el cajero busca por cédula igual que por nombre/email.
- **Rationale**: el dataset base (Dunnhumby) es un panel de hogares de EE. UU. sin ningún concepto de cédula; `household_id` es la clave natural sembrada. Pero un programa de fidelización real en Ecuador identifica al cliente por cédula en caja — más rápido y sin ambigüedad de tipeo que un email. Se agrega como opcional (no obligatorio) porque exigirlo rompería el registro rápido en caja para quien no la trae a mano, mismo criterio de "no bloquear el alta" ya usado para los datos demográficos (FR-004).
- **Alternatives considered**: reemplazar `email` por `documento_identidad` como identificador único principal — más realista para Ecuador, pero es un cambio mayor sobre `FR-001` ya implementado en Fases 1-2 (tocaría la unicidad ya sembrada por `email` en el dataset base) y el usuario decidió explícitamente mantener `email` como clave de registro y agregar la cédula como campo adicional de búsqueda.
- **Rationale**: cumple LOPDP (minimización/derecho al olvido) sin sacrificar integridad referencial ni las agregaciones históricas ya calculadas — el historial de CLV/churn pasado sigue siendo válido como dato agregado, aunque el cliente ya no sea identificable.
- **Alternatives considered**: DELETE físico del registro — rompería la FK con `ventas`/`cliente_clv`/`churn_score` históricos (violaría Principio II); solo marcar `activo = false` sin anonimizar los campos — no cumple el requisito de anonimización real que FR-003 ya exigía desde antes de esta ronda de cambios.
