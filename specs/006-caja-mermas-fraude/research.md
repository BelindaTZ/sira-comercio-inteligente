# Research: Caja, Mermas y Fraude

**Feature**: `006-caja-mermas-fraude` | **Date**: 2026-09-06

## Decisión 1: Total esperado del cuadre calculado por cajero, no por caja física

**Decisión**: `total_esperado` de cada `cierre_caja` se calcula como la suma de `ventas.total` (no anuladas) del `cajero_id` del cuadre dentro de la ventana horaria correspondiente (Decisión 2), no por `caja_id`.

**Razón**: `ventas` (tabla sembrada desde el dataset Dunnhumby) no tiene columna `caja_id` — solo `cajero_id`. El dataset no modela cajas físicas como unidad de venta, solo transacciones por cajero. `apertura_caja`/`cierre_caja` sí asocian una caja física a un cajero para efectos de turno, pero la agregación de ventas para calcular el total esperado debe hacerse por el mismo criterio que existe en los datos reales (Principio VII).

**Alternativas consideradas**: Agregar una columna `caja_id` a `ventas` y retro-poblarla — rechazada por violar Principio VII (no se puede inferir con certeza a qué caja física correspondió cada transacción histórica del dataset) y por ser un cambio de esquema no aditivo sobre una tabla ya cerrada por 001.

## Decisión 2: Ventana horaria de cada cuadre = desde el cuadre anterior (o la apertura) hasta el actual

**Decisión**: La ventana horaria que cubre un `cierre_caja` va desde el `fecha_hora` del `cierre_caja` inmediatamente anterior de la misma caja (o, si es el primero del turno, desde el `fecha_hora` de su `apertura_caja`) hasta el `fecha_hora` del cuadre actual.

**Razón**: Es la única definición que no requiere una columna nueva de "hora de inicio" en `cierre_caja" y que garantiza que cada venta se cuenta exactamente en un cuadre (sin solapamiento ni huecos), consistente con Principio VIII.

**Alternativas consideradas**: Ventanas de reloj fijas (en punto, ej. 09:00–10:00) — rechazada porque un cajero puede cuadrar en momentos irregulares (edge case de FR-002, "cada hora" es una cadencia esperada, no una regla dura) y forzaría lógica adicional para cuadres tardíos o tempranos.

## Decisión 3: "Turno" del reporte mensual (FR-009) = la apertura de caja vigente, sin entidad nueva

**Decisión**: El reporte mensual agrupa por `cajero_id` + `apertura_id` (la `apertura_caja` de la misma caja vigente al momento de cada `cierre_caja`, es decir, la apertura más reciente con `fecha_hora <= cierre.fecha_hora`), no por una entidad "turno" nueva.

**Razón**: El dominio ya tiene una entidad que delimita exactamente un turno de trabajo (apertura → siguiente apertura de la misma caja) — crear una tabla `turnos` sería duplicar información ya derivable, violando Principio VIII.

**Alternativas consideradas**: Agrupar por `cajero_id` + fecha calendario — rechazada porque un turno puede cruzar la medianoche y porque ya existe una entidad (`apertura_caja`) que delimita el turno con precisión sin ambigüedad.

## Decisión 4: No conformidad de datáfono reutiliza el enum ya reservado (`requiere_actualizacion`)

**Decisión**: Un datáfono se identifica como no conforme (FR-007) comparando su `version_firmware` contra la versión mínima vigente en `configuracion_seguridad_pagos` (Decisión 5); cuando no cumple, su `estado` se actualiza a `'requiere_actualizacion'` — valor ya incluido en el `CHECK` de `datafonos.estado` desde 001, sin usarse hasta ahora.

**Razón**: El esquema de 001 ya anticipó exactamente este caso de uso con ese valor de enum. Agregar un valor nuevo (p. ej. `'no_conforme'`) sería redundante y violaría Principio VIII.

**Alternativas consideradas**: Agregar una columna booleana `es_conforme` — rechazada por duplicar información que el enum `estado` ya expresa.

**Corrección (implementación)**: el valor `'requiere_actualizacion'` (22 caracteres) nunca cupo en el `VARCHAR(20)` original de `datafonos.estado` de 001 — hubiera fallado con `StringDataRightTruncationError` al primer intento de uso real. La migración 0013 ensancha la columna a `VARCHAR(30)` (`01_operativo_postgres.sql` actualizado en el mismo commit); el enum en sí no cambia, solo el ancho de columna que lo contiene.

## Decisión 5: Nueva tabla `configuracion_seguridad_pagos` para el estándar vigente

**Decisión**: Se crea `configuracion_seguridad_pagos` (versión mínima de firmware, `vigente_desde`, quién la definió) como tabla append-only — cada cambio de estándar inserta una fila nueva; el estándar vigente es la fila con `vigente_desde` más reciente.

**Razón**: Ninguna tabla existente modela "el estándar de seguridad de pago vigente". Append-only conserva el historial de cuándo cambió el estándar, útil para auditar por qué un datáfono pasó a no conforme en una fecha determinada (relevante si luego hay una demanda o auditoría de seguridad, narrado explícitamente en el enunciado del proyecto).

**Alternativas consideradas**: Una sola fila actualizable (UPDATE in place) — rechazada porque perdería el historial de cuándo cambió el estándar, información con valor de auditoría en este dominio específico (a diferencia de `umbral_merma_categoria`, Decisión 8, donde ese historial no aporta valor operativo).

## Decisión 6: Migración aditiva sobre `incidentes_fraude`

**Decisión**: `incidentes_fraude.cierre_id` pasa de `NOT NULL` a nullable, y se agregan las columnas `ajuste_id` (FK opcional a `ajustes_inventario`, 001), `acciones_tomadas` (texto), `resultado` (`fraude_confirmado` | `descartado`, nullable hasta el cierre) y el par `actualizado_por`/`fecha_actualizacion`.

**Razón**: El esquema original de 001 solo previó un incidente originado en un cuadre de caja (`cierre_id NOT NULL`). Esta feature necesita que un incidente pueda originarse también en un ajuste de inventario anómalo (FR-010) o registrarse directamente sin patrón previo (User Story 4, Acceptance Scenario 2 no exige un cuadre de origen) — ninguno de esos dos casos tiene un `cierre_id` válido que referenciar. `acciones_tomadas` y `resultado` faltaban por completo: sin ellos no se puede cumplir FR-014 (registrar acciones) ni el Acceptance Scenario 3 de User Story 4 (dejar constancia del resultado sin acusar si no se confirma). `actualizado_por`/`fecha_actualizacion` cumplen FR-015 ("dejando constancia de quién y cuándo lo cambió de estado").

**Alternativas consideradas**: Mantener `cierre_id NOT NULL` y forzar un cuadre "sintético" para incidentes sin patrón de caja de origen — rechazada por introducir datos falsos en una tabla de registro real (violaría Principio II).

## Decisión 7: `protocolo_escalamiento` como tabla append-only de versiones de texto

**Decisión**: Igual criterio que la Decisión 5 — cada actualización del protocolo inserta una fila nueva; el protocolo vigente es la fila más reciente por `fecha_creacion`.

**Razón**: Un incidente de fraude puede seguir abierto durante semanas; si el protocolo cambia mientras un caso está en curso, conviene poder saber bajo qué versión del protocolo se actuó. Consistente con Principio II (registro real, no solo el estado actual).

## Decisión 8: `umbral_merma_categoria` como configuración simple, no append-only

**Decisión**: A diferencia de las Decisiones 5 y 7, `umbral_merma_categoria` es una tabla de una fila por categoría, actualizable in place (UPDATE, no INSERT de nueva versión).

**Razón**: El umbral de merma es un objetivo de gestión de mediano plazo (spec.md Assumptions) sin valor de auditoría en conocer versiones pasadas — a diferencia del estándar de seguridad de pagos o el protocolo de fraude, no hay un escenario narrado donde importe bajo qué umbral pasado se generó una alerta ya resuelta. Mantiene el alcance simple (Principio VIII).

## Decisión 9: Cálculo del porcentaje de merma acumulada semanal

**Decisión**: `% merma = SUM(mermas.valor)` de la categoría/tienda en la semana `÷ SUM(venta_detalle.sales_value)` de esa misma categoría/tienda en la misma semana `× 100` (join de `venta_detalle`→`productos` por `product_category`, y de `mermas`→`productos` por el mismo campo).

**Razón**: Es la definición estándar de "shrinkage as % of sales" en retail, y el dataset no distingue un "valor de inventario" separado del valor de venta — usar el valor de venta real ya sembrado respeta Principio VII sin introducir un concepto de valuación de inventario nuevo (fuera del alcance narrado).

**Alternativas consideradas**: `% merma = SUM(mermas.cantidad) ÷ SUM(ventas.cantidad)` (unidades en vez de valor) — rechazada porque el umbral se define como "porcentaje de merma aceptable" en términos económicos (la narrativa original habla de "comerse hasta el 20% de tu ganancia anual"), no en unidades físicas.

## Decisión 10: Resumen de cambios de BSC y RBAC

- **Sin cambios de BSC**: a diferencia de 005 (que agregó OO-3.5.3), esta feature no requirió ninguna Objetivo Operativo nuevo — OT-6.1 a OT-6.4 y OT-5.5 ya cubrían completamente el alcance narrado.
- **Sin gap de rol RBAC**: primera feature de la serie (001-006) donde los 5 actores (Cajero, Encargado_Tienda, Jefe_Finanzas, Jefe_TI, Jefe_Operaciones) ya tenían rol propio sembrado.
- **Módulo `Finanzas` reutilizado**: ya sembrado desde 001 en `modulos` con la descripción literal "Caja, cuadre, seguridad de pagos" — coincide exactamente con el alcance de esta feature. `Jefe_TI` requiere acceso de edición a este módulo (no solo a `TI`) para gestionar `datafonos`, ya que esa tabla vive conceptualmente en `Finanzas` (seguridad de pagos), no en `TI` (gobierno de datos) — se documenta como una concesión de acceso cruzado entre módulos, ya usada como patrón en 005 (`Jefe_Marketing` con acceso de solo lectura a `Ventas`).
