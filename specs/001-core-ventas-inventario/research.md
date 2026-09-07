# Research: Core de Ventas e Inventario (001-core-ventas-inventario)

**Fase 0 de `/speckit-plan`** — Todas las decisiones de Technical Context ya venían resueltas por `constitution.md` (no quedó ningún `[NEEDS CLARIFICATION]`); este documento cubre las decisiones técnicas concretas que la constitución no fija literalmente y que esta feature sí necesita para poder pasar a `data-model.md`/`tasks.md`.

## 1. ORM y acceso a datos (backend)

- **Decision**: SQLAlchemy 2.0 (modo async) + `asyncpg` como driver, con Alembic para migraciones incrementales sobre `01_operativo_postgres.sql`.
- **Rationale**: la constitución fija PostgreSQL y FastAPI pero no un ORM. SQLAlchemy 2.0 async es el estándar de facto en el ecosistema FastAPI, soporta bien el patrón repository (Principio XI) y Alembic permite versionar los 7 cambios de esquema de esta feature como migraciones explícitas y reproducibles (importante porque el esquema ya está en producción conceptual con datos sembrados).
- **Alternatives considered**: (a) SQL crudo con `psycopg` — más simple pero repite mapeo objeto-tabla en cada repository, viola DRY (Principio VIII) dado que son 50+ tablas; (b) Tortoise ORM — más ligero pero con comunidad/soporte menor y peor integración con Alembic-style migrations.

## 2. Autenticación JWT

- **Decision**: `PyJWT` para firmar/validar tokens; el propio middleware de RBAC (dependencia de FastAPI) se construye sobre `role_permisos_modulo`/`role_permisos_tabla` ya existentes.
- **Rationale**: librería madura, sin dependencias pesadas, suficiente para HS256/RS256 según se defina en 008.
- **Alternatives considered**: `python-jose` (funcionalmente equivalente, pero PyJWT tiene mejor mantenimiento activo a la fecha).
- **Nota de dependencia**: 001 implementa el *consumo* del JWT (decodificar, extraer rol, verificar permiso) contra un token de prueba; la *emisión* real (login) la entrega 008. Esto no bloquea el desarrollo de 001 (Constitution Check ya lo documentó).

## 3. Testing

- **Decision**: Backend: `pytest` + `pytest-asyncio` + `httpx.AsyncClient` (tests de contrato e integración contra la API real, sin mocks de PostgreSQL — se prueba contra una base de test real vía Docker). Frontend: `Vitest` + `@vue/test-utils`.
- **Rationale**: Principio X exige cobertura obligatoria en lógica crítica (FIFO/FEFO, punto de reposición, cálculo de totales, RBAC). `httpx.AsyncClient` permite probar los endpoints FastAPI de forma async nativa sin levantar un servidor aparte. Vitest comparte configuración con Vite, cero fricción adicional.
- **Alternatives considered**: `unittest` puro (más verboso, sin fixtures async cómodas); Jest para frontend (funciona, pero Vitest está pensado para el ecosistema Vite que ya se usa).

## 4. Concurrencia al descontar inventario por lote (evitar sobreventa)

- **Decision**: al confirmar una venta, la selección y descuento del lote se hace dentro de una única transacción con `SELECT ... FOR UPDATE` sobre las filas de `lotes` candidatas (mismo `product_id`/`tienda_id`, `cantidad_disponible > 0`, ordenadas por `fecha_vencimiento ASC NULLS LAST, cantidad_recibida ASC, lote_id ASC` — este último orden es el criterio determinístico de desempate que ya pide el edge case del spec).
- **Rationale**: dos cajeros vendiendo el mismo producto al mismo tiempo podrían leer el mismo stock "disponible" antes de que el otro confirme, causando sobreventa (viola FR-006). `SELECT FOR UPDATE` bloquea la fila del lote hasta que la transacción del primer cajero termina, forzando al segundo a leer el stock ya actualizado.
- **Alternatives considered**: nivel de aislamiento `SERIALIZABLE` en toda la transacción de venta — más seguro en teoría pero implica manejar reintentos por fallos de serialización en cada venta, complejidad innecesaria (Principio VIII) para el volumen esperado de un punto de venta de tienda física.

## 5. Cálculo del punto de reposición dinámico (FR-020) — versión MVP de esta feature

- **Decision**: `punto_reposicion = (promedio de unidades vendidas por día en los últimos 14 días) × (lead time estimado en días, configurable por proveedor/categoría) + stock de seguridad (configurable, por defecto 20% del consumo del lead time)`. Se ejecuta como job diario (backend, no requiere Airflow — Principio III mantiene esto fuera de ClickHouse/ELT).
- **Rationale**: el spec (Assumptions) es explícito en que esta feature NO usa el modelo predictivo completo (eso es 004); necesita una heurística simple, explicable y accionable ya. Una media móvil de 14 días es estándar en reposición de retail para picos de corto plazo sin sobrerreaccionar a un solo día atípico.
- **Alternatives considered**: punto de reorden fijo (es exactamente lo que la constitución pide reemplazar, OT-5.1); modelo predictivo con variables exógenas (reservado a 004 por decisión explícita ya tomada).

## 6. Cobro con tarjeta — Stripe Payment Intents y simulación de los 3 resultados (FR-030/FR-031)

- **Decision**: usar la API de **Payment Intents** de Stripe (no la API de Charges, que Stripe considera legacy) en modo test. Los 3 resultados de FR-030 se simulan con números de tarjeta de prueba oficiales de Stripe, no con lógica propia inventada:
  - Aprobado: tarjeta de prueba estándar (`4242 4242 4242 4242`).
  - Rechazado por el banco: tarjetas de prueba de Stripe que fuerzan un decline específico (ej. fondos insuficientes, tarjeta perdida) — Stripe documenta un set fijo para esto.
  - Error técnico: Stripe ofrece un modo de simulación de fallos de red/API en test (o, alternativamente, se simula localmente forzando un timeout del lado del backend hacia la pasarela) para separar claramente "el banco dijo que no" de "no pudimos ni preguntarle al banco".
- **Rationale**: usar las tarjetas de prueba oficiales de Stripe en vez de inventar una simulación propia mantiene la demo fiel al comportamiento real de la pasarela (y es gratis, sin necesidad de certificarse con un banco real) — coherente con el Principio VII (no inventar donde ya existe un mecanismo real y accesible).
- **Alternatives considered**: mockear Stripe completamente en el backend sin llamarlo nunca — más simple pero no demuestra integración real con una pasarela, y el enunciado pide explícitamente medios de pago electrónicos reales (aunque en modo prueba).

## 7. Comprobante de venta en PDF

- **Decision**: `reportlab` genera el PDF server-side al confirmar la venta, se guarda su referencia (no el binario) en el registro de venta; el archivo se sirve vía un endpoint de descarga autenticado.
- **Rationale**: ya decidido en la constitución; la única decisión técnica añadida aquí es dónde persiste el archivo — se opta por el mismo bucket MinIO `producto-imagenes`... **no**, corrección: se crea un bucket separado `comprobantes-venta` (Principio III exige separar responsabilidades por bucket; mezclar comprobantes con imágenes de producto violaría esa separación).
- **Alternatives considered**: generar el PDF al vuelo en cada descarga sin persistirlo — más simple pero no cumple Principio II (el comprobante es un documento de negocio real, debe persistir tal como se emitió, no regenerarse distinto si cambian datos del producto después).
- **Decisión adicional (ronda 2 — apertura automática para impresión, FR-004/SC-011)**: `GET /api/ventas/{id}/comprobante` responde con `Content-Disposition: inline` (no `attachment`); al confirmar la venta con éxito, el frontend abre esa URL en una pestaña nueva (`window.open`) de inmediato. Esto delega la impresión/guardado al visor de PDF nativo del navegador (ya trae botones de "Imprimir" y "Guardar como PDF"), sin ninguna librería JS de impresión ni necesidad de detectar si hay impresora física conectada — si no la hay, el propio diálogo del navegador ofrece "Guardar como PDF" (comportamiento estándar del sistema operativo/navegador, no algo que SIRA deba implementar).
- **Alternativas consideradas (ronda 2)**: disparar `window.print()` sobre un blob descargado vía JS — funciona pero obliga a manejar el ciclo de vida del blob/`URL.createObjectURL` sin aportar nada sobre simplemente abrir la URL con `inline` (Principio VIII, KISS); mantener `Content-Disposition: attachment` y esperar que el cajero abra el archivo descargado manualmente — es exactamente el flujo que este gap busca evitar (velocidad de cobro, OT-4.2).
- **Logotipo en el encabezado (ronda 2, FR-004)**: `reportlab` inserta el logo vía `drawImage`/`ImageReader`, que requiere un archivo rasterizado (PNG/JPG) — no acepta SVG directamente. El logo que el usuario provea antes de `/speckit-implement` se guarda en `backend/src/assets/branding/logo.png` (fondo transparente) para el PDF, y su versión vectorial (`.svg`) en `frontend/src/assets/branding/logo.svg` para la SPA (navbar, login) — ver `design-system.md`, sección "Logotipo y Uso de Marca". Si el usuario solo provee un formato, se deriva el otro una única vez durante la implementación con una herramienta estándar de conversión, sin agregar una dependencia nueva al proyecto.

## 8. Escaneo de código de barras en el punto de venta (frontend web)

- **Decision**: soporte dual — (a) lector físico USB/Bluetooth tipo "keyboard wedge" (el estándar en retail: el lector escribe los dígitos + Enter como si fuera un teclado, se captura con un listener de input rápido seguido de Enter, sin librería adicional); (b) escaneo por cámara vía librería JS (`@zxing/browser` o la `BarcodeDetector` nativa del navegador donde esté disponible) como alternativa cuando no hay lector físico — relevante para poder hacer la demo sin hardware especial. La búsqueda manual (FR-001) siempre está disponible como tercera opción.
- **Rationale**: un lector físico es la práctica estándar en cualquier punto de venta real y no requiere ninguna integración especial (es entrada de teclado). El soporte por cámara es lo que permite demostrar el flujo completo en el sustentación sin depender de tener un lector físico a mano.
- **Alternatives considered**: exigir solo lector físico — arriesga la demo si no hay hardware disponible el día de la sustentación.

## 9. Pedido especial a proveedor por correo (FR-029)

- **Decision**: `sendgrid` (ya aprobado) con una plantilla de correo transaccional simple (proveedor, productos, cantidades, motivo); el envío queda registrado en `ordenes_compra` (`tipo = 'especial'`) independientemente de si el correo se entrega o no (Principio II: el registro de negocio no depende de un servicio externo de terceros).
- **Rationale**: reutiliza la integración ya decidida para toda la app, sin agregar un servicio nuevo (Principio VIII).

## 10. Autocompletado de producto nuevo vía Open Food Facts (FR-013)

- **Decision**: consulta REST pública `GET https://world.openfoodfacts.org/api/v2/product/{barcode}.json` (sin API key) al registrar un producto nuevo vía UI; si no hay coincidencia o el servicio no responde, el formulario queda editable manualmente sin bloquear el alta.
- **Rationale**: servicio público, gratuito, ya aprobado en la constitución; el fallback a edición manual evita que una caída del servicio externo bloquee una operación interna (Principio II).

## 11. Resolución del proveedor en la sugerencia semanal (FR-023) — versión MVP de esta feature

- **Decision**: qué productos entran a la sugerencia semanal lo decide solo el inventario (producto/tienda con `cantidad_disponible < cantidad_minima`), no el historial de compras. Para cada producto seleccionado, el proveedor se resuelve buscando la orden de compra más reciente de esa tienda que haya incluido ese producto (`ultimo_proveedor_de`); si no existe ninguna, `proveedor_id` queda en `null` en la sugerencia — el Jefe de Operaciones lo completa manualmente al crear la orden (`crear_orden` valida ese `proveedor_id` contra `proveedores` en ese momento, no contra la sugerencia).
- **Rationale**: el esquema base no tiene una tabla maestro producto→proveedor preferente; derivar el proveedor de compras reales anteriores respeta Principio II (Registro Real) en vez de inventar una asociación que no existe en los datos. Usar `manufacturer_id`/marca del producto como proxy se descartó porque el fabricante no es necesariamente quien lo suministra a la tienda (son entidades distintas en el modelo).
- **Alternatives considered**: exigir un catálogo producto→proveedor nuevo antes de generar la sugerencia — resuelve el caso de cero historial de forma más completa, pero agrega una tabla y un flujo de mantenimiento nuevos para un caso MVP (Principio VIII, se puede revisar si la demo lo requiere); bloquear la sugerencia para productos sin historial — se descarta porque el objetivo de FR-023 es priorizar reposición por rotación/demanda, no filtrar por historial de compras, y el vacío se resuelve igual de simple dejando que el Jefe de Operaciones asigne el proveedor al aprobar.
- **Adenda (Ronda 11)**: la misma relación producto↔proveedor derivada aquí (vía `ordenes_compra`/`orden_compra_detalle`) se expone ahora directamente al usuario como consulta de solo lectura — ver FR-044.
