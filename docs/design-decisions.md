# docs/design-decisions.md — Historial de decisiones de diseño

Razonamiento detrás de las decisiones que hoy son reglas en `CLAUDE.md` y `docs/erd.md`. Referencia para entender el **por qué**, no para escribir código.

Cuando se tome una decisión nueva que merezca ir a `CLAUDE.md` como regla, agregarla acá con su razonamiento (formato al final del archivo).

---

## NUMERIC(18,4) para montos, no BIGINT

**Decisión:** Todos los montos en `NUMERIC(18,4)`. Tipos de cambio en `NUMERIC(18,6)`.

**Por qué:** Tres razones que lo justifican frente a BIGINT (que es lo que usaríamos si fuera solo PYG):

1. **Multimoneda desde v1.** USD tiene 2 decimales, otras monedas también. Usar BIGINT obligaría a almacenar todo en la unidad más chica (centavos para USD) y a hacer conversiones permanentes.
2. **Precios por unidad fraccionada.** Vender 0.350 kg a 12.500 PYG/kg da 4.375 PYG. Si trackeamos el precio en enteros, hay que guardarlo en milésimos y abrir la puerta a bugs de conversión.
3. **Tipo de cambio.** Siempre tiene decimales. Forzar enteros con escala fija complica todo el código de conversión.

`NUMERIC(18,4)` da 14 dígitos enteros y 4 decimales: suficiente para cualquier moneda razonable. La presentación se redondea según `currencies.decimal_places` (0 para PYG, 2 para USD).

**Trade-off aceptado:** NUMERIC es más lento que BIGINT en operaciones masivas. Para el volumen de un pequeño negocio (cientos de ventas/día) es irrelevante.

**Diferencia con TributarioPY:** ese proyecto usaba BIGINT porque el dominio era 100% guaraníes sin precios fraccionados. Acá no aplica.

---

## UUID v4 generado en el cliente

**Decisión:** PKs son UUID v4 generados en el frontend (`crypto.randomUUID()`).

**Por qué:** Aunque DTCore v1 no tiene offline real, generar UUIDs en cliente:

1. **Prepara multi-caja sin reescribir.** Si en v2 hay dos cajas vendiendo en simultáneo, cada una genera sus IDs sin coordinarse con el servidor. UUID v4 tiene 2^122 posibilidades — colisión matemáticamente imposible.
2. **Simplifica flujos transaccionales.** El frontend arma el carrito completo (con IDs de sale, sale_items, sale_payments todos vinculados) antes de enviar al backend. No hay que esperar la respuesta para vincular items al header.
3. **Consistencia con TributarioPY** y patrones modernos de POS.

**Trade-off aceptado:** UUIDs son más pesados que integers (16 bytes vs 4) y los índices son menos densos. Para el volumen previsto, irrelevante.

---

## Stock como ledger append-only + cache desnormalizado

**Decisión:** `stock_movements` es inmutable y append-only — toda variación de stock es un registro nuevo. `stock_current` es un cache desnormalizado con el stock actual y el costo promedio ponderado por producto+depósito.

**Por qué:**

1. **Trazabilidad real.** Cualquier discrepancia se audita recorriendo movements. Si el cliente dice "el stock está mal", se puede reconstruir minuto a minuto.
2. **Recuperación de errores.** Si `stock_current` se corrompe (bug, crash a mitad de transacción), un script recalcula desde movements. La fuente de verdad nunca se pierde.
3. **Compensaciones limpias.** Cancelar una venta no edita ni borra el movement original — agrega uno compensatorio con `movement_type='return_in'`. Auditoría completa.
4. **Performance aceptable.** Sin cache, calcular stock actual sería sumar todos los movements del producto cada vez. Con cache, es una lectura O(1).

**Trade-off aceptado:** doble escritura por movimiento (movement + cache). El lock pesimista sobre `stock_current` garantiza consistencia.

**Alternativa descartada:** sin cache, calcular siempre desde movements. Inviable en POS donde cada búsqueda de producto tiene que mostrar stock actual.

---

## Lock pesimista para escritura de stock

**Decisión:** Toda actualización de `stock_current` va precedida de `SELECT ... FOR UPDATE` sobre la fila del producto+depósito.

**Por qué:** Aunque la regla de negocio en v1 es "input desde un solo dispositivo", el sistema no puede confiar en eso. Suena el teléfono, Alejandro registra una venta rápida desde el celular mientras la notebook tiene otra abierta — dos sesiones concurrentes tocando el stock del mismo producto. Sin lock, race condition: ambas leen 5 unidades, ambas restan 3, queda 2 cuando debería quedar -1 (o rechazar la segunda).

El lock pesimista cuesta una línea de código si se diseña desde el día 1. Agregarlo retroactivamente es doloroso (hay que auditar todos los flujos que tocan stock).

**Trade-off aceptado:** posible contención si en el futuro hay muchas cajas vendiendo el mismo producto. Para escalas mayores (multi-sucursal con concurrencia alta) habría que rediseñar hacia reservas de stock con eventual consistency — v3 o cuando duela.

---

## CPP (costo promedio ponderado) en lugar de FIFO

**Decisión:** Costo de inventario se calcula como CPP, recalculado en cada compra.

**Fórmula:** `nuevo_avg = (stock_actual × avg_actual + qty_nueva × costo_nuevo) / (stock_actual + qty_nueva)`

**Por qué:** CPP es más simple de implementar (un solo número por producto), suficientemente preciso para reportes de utilidad, y comprensible para el usuario. FIFO requiere trackear lotes con sus costos individuales y consumirlos en orden, lo que complica el modelo y la UI.

**Trade-off aceptado:** En contextos con alta inflación o productos con costos muy variables, FIFO sería más preciso. Para v1 y este negocio, no se justifica. Si un cliente futuro lo pide, se evalúa.

---

## CPP no se recalcula hacia atrás en cancelaciones

**Decisión:** Cancelar una compra confirmada genera movimientos compensatorios pero **no recalcula** el `avg_cost_base` retroactivamente.

**Por qué:** Recalcular CPP hacia atrás obligaría a reproducir toda la secuencia histórica de compras y ventas para llegar al valor "correcto". Pero "correcto" es ambiguo — ¿qué pasa con las ventas que ya se hicieron usando el CPP viejo? Sus snapshots de costo (`unit_cost_base_at_sale`) ya están guardados. Cambiar el CPP no las modifica.

Aceptar el costo histórico como inmutable simplifica el modelo y se alinea con cómo lo hacen los sistemas contables tradicionales.

---

## Precios de venta históricos (`product_prices` append-only)

**Decisión:** Cada cambio de precio de venta crea un nuevo registro en `product_prices`. El precio vigente es el de mayor `effective_from <= hoy` para `product_unit_id + currency_code`.

**Por qué:** Permite reportes históricos correctos. Si un producto se vendió en marzo a 10.000 y en abril el precio subió a 12.000, los reportes de margen de marzo tienen que usar el precio de marzo, no el actual.

**Trade-off aceptado:** Tabla crece con cada cambio de precio. Para un negocio que cambia precios decenas de veces al año por inflación, esto crece, pero sigue siendo despreciable.

**Snapshot en items:** además del histórico, `sale_items.unit_price` y `purchase_items.unit_cost` guardan el valor exacto del momento de la transacción. Doble seguro contra reescrituras de historia.

---

## Snapshots en items de compra/venta

**Decisión:** Los items copian valores clave al confirmar: `quantity_base`, `unit_cost_base_at_sale`, `tax_rate`, `tax_included`, `unit_cost_base_currency`. La cabecera copia `exchange_rate`.

**Por qué:** Los reportes históricos no deben cambiar si cambia la configuración. Si mañana el IVA pasa al 12%, las ventas de hoy siguen reportando 10%. Si cambia el factor de conversión de una unidad (corrección de error), las ventas pasadas siguen reportando la cantidad que efectivamente se vendió.

Sin snapshots, todo se calcularía dinámicamente y cualquier cambio en catálogo distorsionaría el pasado.

---

## Productos con múltiples unidades de venta

**Decisión:** Cada producto tiene una `base_unit` (en la que se trackea el stock) y N `product_units` con factor de conversión a la base. Precios se guardan por `product_unit`, no por producto.

**Por qué:** Rincón de Embalajes vende productos que físicamente se manejan en distintas presentaciones — un rollo de cinta puede venderse por rollo o por metro. Un producto puede tener stock en una unidad granular (gramos, metros) y venderse en presentaciones (caja, rollo, docena).

Modelar esto como un campo "unidad" en el producto no funciona: el mismo rollo tiene dos precios distintos (precio por rollo ≠ 50 × precio por metro), y el stock debe descontarse correctamente independientemente de la unidad usada al vender.

**Trade-off aceptado:** Modelo más complejo. La UI debe hacer al usuario seleccionar la unidad al vender y al fijar precios. Vale la pena: cubre todos los casos reales del negocio sin refactor.

---

## Multimoneda desde v1, listas de precios en v2

**Decisión:** El sistema soporta múltiples monedas desde v1 (PYG, USD, BRL, ARS). Cada compra/venta puede ser en cualquier moneda activa. Las listas de precios diferenciadas (mayorista/minorista) se difieren a v2.

**Por qué multimoneda ya:** El cliente compra a proveedores en USD y registra esas compras. Sin multimoneda, tendría que pre-convertir manualmente — fuente garantizada de errores.

**Por qué listas de precios no:** Las listas de precios son una capa adicional sobre el precio base. Modelarlas significa: tabla `price_lists`, tabla `price_list_items`, selector de lista en venta, lógica de "qué lista aplica a este cliente". Para v1 alcanza con precio único por producto+unidad+moneda.

---

## Tipo de cambio snapshot por transacción

**Decisión:** Cada `purchase` y `sale` guarda el `exchange_rate` aplicado en el momento. Reportes históricos usan ese valor, no el tipo de cambio actual.

**Por qué:** Si el tipo de cambio del USD pasa de 7.500 a 7.800 PYG, las compras que hice cuando estaba a 7.500 no cambian de costo retroactivamente. El total en PYG se congela al confirmar.

Esto implica también guardar `total_base_currency` (total convertido a PYG) en la cabecera, para evitar recalcular en cada query de reporte.

---

## Settings clave-valor tipadas

**Decisión:** Tabla `settings` key-value con tipo declarado (`string`, `int`, `decimal`, `bool`, `json`).

**Por qué:** Agregar una nueva flag de configuración (ej. `enable_low_stock_alerts`) no requiere migración de schema — es un INSERT en `settings`. Los settings se editan desde un panel admin sin tocar código.

**Alternativa descartada:** columnas dedicadas en una tabla `configuration` con un solo registro. Cada nuevo flag requeriría migración. Para un producto reutilizable que va a crecer, no escala.

**Trade-off aceptado:** valores serializados como TEXT, parseo necesario al leer. El service `settings_service.py` encapsula esto con tipo correcto.

---

## Settings como mecanismo de configuración por cliente

**Decisión:** DTCore es producto reutilizable. La configuración específica de cada cliente vive en `.env` (cosas técnicas: DATABASE_URL, JWT_SECRET) o en la tabla `settings` (cosas de negocio: nombre del negocio, moneda default, flags de comportamiento).

**Por qué:** El código de DTCore no menciona "Rincón de Embalajes" en ningún lado. Al instalar para un cliente nuevo: clonar el repo, generar `.env`, correr migraciones + seed, editar `settings` desde el panel admin. Cero cambios al código.

**Implicación práctica:** el frontend muestra `settings.business_name` al lado del logo "DTCore". Nunca hardcodear el nombre del cliente.

---

## PWA instalable sin offline real

**Decisión:** Frontend es PWA instalable (manifest + Workbox para que se instale como app en celular/desktop), pero **sin offline real**. Sin conexión al servidor, la app muestra "Sin conexión".

**Por qué:** TributarioPY es offline-first porque los cálculos son locales (un solo usuario procesando sus comprobantes). DTCore es lo opuesto: el stock es compartido, la fuente de verdad **tiene que ser** el servidor. Permitir ventas offline desde el celular significa que dos dispositivos pueden vender la misma última unidad y sincronizar después con conflicto irresoluble.

Mejor mostrar "Sin conexión" que corromper el stock.

**Trade-off aceptado:** si se cae el WiFi del local, el negocio no puede vender hasta que vuelva. Para un pequeño comercio con WiFi razonablemente estable, es aceptable. Si esto deja de serlo, la solución es un UPS para el router, no offline mode.

---

## Pagos mixtos como tabla separada (v1)

**Decisión:** Tabla `sale_payments` con N filas por venta. Suma debe igualar `sales.total`. El campo `payment_method` deja de existir en `sales`.

**Por qué:** Pagos mixtos (parte efectivo + parte transferencia) son comunes y se complican si se modelan en cabecera. Una tabla separada es trivial y consistente — si solo hay un pago, hay una sola fila.

**Alternativa descartada:** mantener `payment_method` en `sales` y agregar tabla para mixtos solo cuando se necesite. Genera dos caminos de código (un pago vs varios pagos) que se evitan modelando uniforme desde v1.

---

## Descuentos en items y en cabecera

**Decisión:** Las ventas tienen descuentos a nivel item (`sale_items.discount_amount`) Y a nivel cabecera (`sales.header_discount_amount`). Ambos se guardan también como porcentaje original si así fueron aplicados (`discount_percent`).

**Por qué:** El usuario puede descontar 10% sobre un item específico, o 5% sobre el total de la venta. Modelar solo descuentos por item obliga a distribuir el descuento de cabecera entre items (complicado, errático en redondeos). Modelarlos por separado es más claro.

**Guardar el porcentaje original** permite a la UI mostrar "10% off" en lugar de "Gs 15.000 off" — más legible para el usuario en reportes.

---

## Devoluciones como movimientos, no como entidad separada

**Decisión:** En v1, devolver una venta se modela como `stock_movement` con `movement_type='return_in'` (similar para compras con `return_out`). No hay tabla `credit_notes`.

**Por qué:** Para v1 alcanza con saber que entró/salió mercadería compensatoria. Formalizar una nota de crédito con su numeración, vínculo al documento original, motivo categorizado, impresión, etc., es trabajo de v2.

**Trade-off aceptado:** la trazabilidad existe en `stock_movements.reference_id` apuntando a la venta original, pero sin documento formal de devolución. Si el cliente lo pide para auditoría, se formaliza en v2.

---

## SQLAlchemy async con asyncpg

**Decisión:** Usar el modo async de SQLAlchemy 2.0 con driver asyncpg.

**Por qué:** FastAPI es async-native. Mezclar sync SQLAlchemy con async FastAPI funciona pero requiere `run_in_executor` implícito y pierde concurrencia. Decisión heredada de TributarioPY que funcionó bien.

---

## Roles definidos pero sin UI en v1

**Decisión:** Tabla `users` tiene campo `role` (enum admin/operator). Existe decorador `require_role` disponible para uso en services. Pero no hay UI de gestión de usuarios — el seed crea un admin único.

**Por qué:** Agregar la estructura ahora cuesta 10 minutos. Agregarla después implica migración + refactor de endpoints existentes para chequear roles + UI nueva. La base queda lista; cuando el cliente quiera crear empleados con permisos limitados, es solo construir la UI.

---

## Backups con `rclone` a Google Drive

**Decisión:** Backup diario via cron: `pg_dump` + `rclone copy` a una carpeta en Drive del cliente. Retención 30 días local / 90 días remoto.

**Por qué:**

- **Drive vs GitHub:** GitHub es para código, no datos. Versionar dumps con información de clientes en un repo es mala práctica.
- **Drive vs Backblaze/R2:** Drive es gratis hasta 15 GB (sobra por años) y el cliente ya tiene cuenta de Google. Backblaze cuesta ~1 USD/mes pero requiere tarjeta — overkill para este caso.
- **`rclone` vs API directa:** rclone es estándar, soporta múltiples backends, no requiere mantener credenciales en código.

**Riesgo operativo conocido:** el backup automatizado puede fallar silenciosamente (token expirado, disco lleno, cuota Drive). **Mitigación:** script de verificación semanal que checkea que existe un dump del día anterior. Si falla, alerta. Esto se implementa en v1, no es opcional.

---

## Audit log simple, no event sourcing

**Decisión:** Tabla `audit_log` que registra create/update/delete/cancel/confirm/restore sobre entidades transaccionales, con user_id, timestamp, y diff JSON de cambios.

**Por qué:** Event sourcing real (reconstruir estado desde eventos) es overkill para este caso. Un log de cambios resuelve el 95% de las necesidades: "quién canceló esta venta", "cuándo se modificó este precio", "qué se cambió".

**Trade-off aceptado:** no se puede reconstruir el estado completo desde el log. Pero los snapshots en items + el ledger de stock cubren la trazabilidad histórica donde más importa.

## Docker solo para PostgreSQL en desarrollo; full Docker en producción

**Decisión:** Durante desarrollo, solo PostgreSQL corre en Docker. Backend (FastAPI) y frontend (Vite) corren localmente con venv y npm respectivamente. En el deploy al cliente (Fase 7), todo va en Docker Compose: `db`, `api`, `web` (nginx con build estático + reverse proxy).

**Por qué Docker solo para BD en desarrollo:**

1. **Hot reload funciona sin fricción.** `uvicorn --reload` y Vite HMR detectan cambios en milisegundos. Con backend/frontend Dockerizados hay que montar volúmenes, lidiar con permisos, y la latencia degrada la experiencia de desarrollo.
2. **Debugging directo.** Breakpoints en VS Code atachados al proceso local funcionan sin configuración extra. Con Docker hay que configurar debugpy y mapear puertos.
3. **Iteración rápida.** `pip install paquete` o `npm install paquete` es instantáneo. Con Docker requiere rebuild de imagen.
4. **PostgreSQL en Docker sí tiene sentido en desarrollo:** no contamina la PC con instalación nativa, los datos persisten en un volume, se puede borrar y recrear sin afectar el host.

**Por qué Docker completo en producción:**

- La PC-servidor del cliente debe poder reiniciarse y levantar todo el stack con un solo comando (`docker compose up -d`).
- Sin Docker en producción, habría que instalar Python, Node, PostgreSQL, configurar systemd services, manejar dependencias del sistema. Mucho más frágil que un compose.
- Aislamiento: si algo se actualiza en el sistema operativo del cliente, las imágenes Docker no se ven afectadas.

**Implicación para Fase 7:**

- Dos archivos compose separados:
  - `docker-compose.yml` — desarrollo, solo `db`, puerto 5432 expuesto al host
  - `docker-compose.prod.yml` — producción, 3 servicios (`db`, `api`, `web`), sin exponer postgres al host (solo accesible internamente)
- `Dockerfile` en `backend/` (multi-stage: build con dependencias, runtime con uvicorn)
- `Dockerfile` en `frontend/` (multi-stage: build con npm, runtime nginx con el build estático y configuración de reverse proxy a `api:8000`)
- `nginx.conf` con HTTPS (certificado mkcert montado como volumen) y proxy a la API

**Trade-off aceptado:** durante desarrollo hay que mantener venv activado y procesos uvicorn/vite corriendo manualmente. A cambio se gana velocidad de iteración. Para un proyecto de este tamaño, vale claramente la pena.

---

## Sin tests E2E en v1

**Decisión:** Backend con tests unitarios en pytest (focado en services con lógica de negocio: stock, CPP, IVA, transacciones). Frontend sin tests automatizados. E2E con Playwright diferido a v2.

**Por qué:** En v1 la UI va a cambiar mucho. Tests E2E son frágiles cuando el frontend está en flujo; mantienen alta la fricción para hacer cambios. El feedback útil en v1 es prueba manual con el cliente.

Los tests unitarios del backend, en cambio, valen oro: lock pesimista, CPP, transacciones atómicas son lugares donde un bug es muy caro y muy difícil de detectar manualmente.

**Cuándo agregar E2E:** cuando los 5-10 flujos críticos (login, registrar compra, registrar venta, ajustar stock, ver reporte) estén estables. Probablemente fin de v1 o inicio de v2.

---

## Tasas de cambio editables solo si son la última y no usadas

**Decisión:** Las tasas de cambio (`exchange_rates`) siguen siendo append-only en concepto, pero se permite editar o eliminar la tasa más reciente de una moneda mientras no haya ninguna compra/venta que la haya consumido.

**Por qué:** Los tipos de cambio se cargan manualmente y los errores de tipeo son inevitables. Forzar al usuario a cargar una nueva tasa con fecha posterior cuando se equivocó hace 30 segundos genera ruido en el histórico. Pero permitir editar tasas viejas que ya fueron usadas crearía inconsistencias silenciosas con los snapshots de `exchange_rate` ya guardados en compras y ventas.

**Reglas concretas:**

- Editar/eliminar permitido solo si: (a) es la tasa con `effective_date` máximo para esa moneda Y (b) no existe ninguna `purchase` ni `sale` con esa moneda creada después del `created_at` de la tasa.
- Si alguna condición falla → 409 Conflict con mensaje claro.
- Al editar, solo se modifican `rate_to_base` y `notes`. `effective_date` y `currency_code` son inmutables.
- Eliminación es soft delete (mantener `deleted_at`) por consistencia con el resto del sistema.

**Trade-off aceptado:** un usuario malicioso con acceso al panel podría cargar una compra, después editar la tasa antes que cargue ninguna otra. Es un riesgo mínimo porque la compra ya tiene snapshot, pero conviene log en `audit_log` cada edición/eliminación de tasa para trazabilidad.

---

## Cómo agregar nuevas decisiones

Cuando se tome una decisión que merezca ir a `CLAUDE.md` como regla, agregarla acá con su razonamiento:

```
## [Nombre corto de la decisión]

**Decisión:** [Qué se decidió, una o dos oraciones]

**Por qué:** [Contexto, alternativas consideradas, justificación]

**Trade-off aceptado:** [Qué estamos resignando — opcional pero recomendado]
```
