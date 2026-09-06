# Research: Recursos Humanos

**Feature**: `011-recursos-humanos` | **Date**: 2026-09-06

## Decisión 1: `acciones_retencion` como única tabla nueva de esta feature

**Decisión**: Se crea `acciones_retencion` (`accion_id`, `empleado_id` FK, `fecha`, `descripcion`) — la única tabla nueva de toda la feature. Ninguna de las 4 tablas de RRHH ya reservadas (`capacitaciones`, `empleado_capacitacion`, `clima_laboral`, `plan_sucesion`) modela una acción de retención sobre un empleado.

**Razón**: `spec.md` (versión original) asumía que esta feature no necesitaría ninguna tabla nueva — al construir este documento se verificó, tabla por tabla, que ninguna de las 4 reservadas tiene ese propósito (`capacitaciones`/`empleado_capacitacion` son sobre formación, `clima_laboral` es una encuesta agregada por tienda, `plan_sucesion` es candidatos, no acciones aplicadas). FR-002 exige explícitamente poder "registrar una acción de retención (fecha, descripción) para un empleado, consultable en cualquier momento" — sin una tabla que lo modele, ese requisito quedaría sin poder implementarse. Se corrigió la Assumption de `spec.md` para reflejar esto explícitamente en vez de dejarlo en silencio (Principio IX).

**Alternativas consideradas**: Forzar la acción de retención dentro de `plan_sucesion` (agregando una columna `tipo`) — rechazada porque mezclaría dos conceptos de negocio distintos (una acción aplicada a un empleado vs. un candidato propuesto para un puesto) en una tabla cuya forma (asociada a `puesto_id`, no directamente pensada para narrar una acción con fecha/descripción sobre un empleado cualquiera) no encaja naturalmente.

## Decisión 2: Fan-out de capacitación por rol reutiliza `empleado_capacitacion`, sin tabla intermedia `capacitacion_rol`

**Decisión**: Al programar una capacitación dirigida a uno o más roles (FR-003), el servicio resuelve, en ese momento, todos los `empleado_id` con cuenta de usuario activa (`usuarios`, 008) cuyo `role_id` esté entre los roles objetivo, e inserta una fila en `empleado_capacitacion` por cada uno (`fecha_completado = NULL`). No se crea una tabla `capacitacion_rol` que persista la asociación capacitación↔rol.

**Razón**: La asociación "esta capacitación es para estos roles" solo importa en el momento de programarla, para decidir a quién asignarla — una vez asignada, lo que hay que consultar después es el cumplimiento por empleado (`empleado_capacitacion`, ya reservada), no la lista de roles original. Persistir la relación con roles agregaría una tabla sin un caso de uso propio que la consulte después (Principio VIII). Un empleado que obtiene su cuenta de usuario (008) después de programada la capacitación no queda incluido retroactivamente — consistente con el Edge Case ya documentado en `spec.md` de que la retención/sucesión no reconstruye historial retroactivo cuando un puesto se marca crítico después.

**Alternativas consideradas**: Tabla `capacitacion_rol` (`capacitacion_id`, `role_id`) — rechazada por no tener ningún consumidor después del momento de asignación; el fan-out inmediato hacia `empleado_capacitacion` ya deja el estado necesario para todo lo que FR-004/FR-005 requieren consultar después.

## Decisión 3: Tasa de rotación calculada on-the-fly por tienda/periodo, sin tabla ni columna nueva

**Decisión**: La tasa de rotación de una tienda en un periodo semestral (ej. `'2026-S2'`) se calcula como `(empleados de esa tienda con fecha_baja dentro del rango de fechas del periodo) / (empleados de esa tienda activos o registrados al inicio del periodo) × 100`. El `periodo` (`clima_laboral.periodo`, formato `'AAAA-Sn'`) se parsea a un rango de fechas (`S1` = enero-junio, `S2` = julio-diciembre) en el backend, sin persistirse como columnas de fecha separadas.

**Razón**: `spec.md` Assumptions ya establece que la rotación "no requiere una tabla nueva, solo una consulta agregada" sobre `empleados.fecha_baja` — este documento solo fija la fórmula exacta y cómo se interpreta `periodo` como rango de fechas, evitando ambigüedad al implementar (Principio VIII, DRY: reutiliza el mismo dato de baja que ya usa 007/008 en sus propios contextos).

**Alternativas consideradas**: Persistir `fecha_inicio`/`fecha_fin` en `clima_laboral` en vez de derivarlas de `periodo` — rechazada por ser redundante con la información que el propio string `periodo` ya codifica; se prefiere una función de parseo simple sobre agregar columnas.

## Decisión 4: Señalización de puestos críticos sin sucesión — consulta, no columna de estado

**Decisión**: FR-009 ("señalar explícitamente cualquier puesto crítico sin ningún candidato") se resuelve con una consulta (`roles_puesto` con `es_critico=true` y sin ninguna fila coincidente en `plan_sucesion`), no con una columna de estado persistida en `roles_puesto`.

**Razón**: El estado "sin cobertura" es derivable en todo momento de los datos ya existentes — persistirlo introduciría una columna que podría desincronizarse del estado real de `plan_sucesion` (Principio VIII, DRY).

**Alternativas consideradas**: Columna `tiene_sucesor BOOLEAN` en `roles_puesto`, actualizada por trigger — rechazada por ser una complejidad adicional (un trigger más, después del ya introducido en 008) para resolver algo que una consulta directa resuelve sin ningún riesgo de desincronización.

## Decisión 5: Resumen de cambios de BSC y RBAC

- **Sin cambio de BSC**: OE-8 completo (OT-8.1 a OT-8.4, sus 8 OO) ya estaba íntegramente documentado en `oo-objetivos-operativos.md` desde el cierre inicial — esta feature no agrega ni corrige ninguna OO, solo les asigna dueña por primera vez.
- **Sin gap de rol RBAC**: `Jefe_RRHH` y `Encargado_Tienda` ya tienen rol propio sembrado (spec.md Assumptions).
- **Extensión del módulo `RRHH`, primer uso por 008**: esta feature extiende el mismo módulo que 008 reservó por primera vez para `empleados` — mismo patrón que 006→007 con el módulo `Finanzas`. Se agrega un **nuevo acceso concedido** de solo lectura de `Encargado_Tienda` a `RRHH` (para el cumplimiento de capacitación de su propio personal, FR-005), mismo patrón que `Jefe_Marketing`→`Ventas` (005) y `Jefe_Comercial`→`Ventas` (007).
- **Boundary con 008**: el fan-out de capacitación depende de que el empleado ya tenga una cuenta de usuario (`usuarios.role_id`) — un empleado sin cuenta aún no se incluye hasta que la tenga (research.md Decisión 2).
