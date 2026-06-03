# QA Cruzado contra BD — Fase 6 (DTCore)

Guía operativa para validar que los reportes y dashboard de DTCore muestran números correctos. Se ejecuta **antes de cerrar Fase 6** y antes de pasar al QA de Fase 7.

**Tiempo estimado:** 1.5 a 2 horas si encontrás pocos bugs, 3-4 si hay varios.

**Objetivo:** validar contra la fuente de verdad (BD), no contra la UI ni contra el endpoint. Si UI = endpoint = service = BD, todos los niveles concuerdan. Si difieren, ese es el bug.

---

## ⚠️ Antes de empezar

- Tener pgAdmin o `psql` abierto y conectado a la BD.
- Tener acceso al frontend funcionando.
- Tener una planilla o documento al lado para anotar los números esperados vs obtenidos.
- **No interrumpir el flujo:** si encontrás un bug, anotalo y seguí. Arreglar al final.

---

## Setup previo — reset y datos de prueba

### Paso 0 — Reset limpio de BD

```bash
docker compose down -v
docker compose up -d
alembic upgrade head
python -m app.seed.run
```

> Si estás en setup nativo sin Docker, hacé `DROP DATABASE` + `CREATE DATABASE` desde pgAdmin, después corré `alembic upgrade head` y `python -m app.seed.run`.

### Paso 1 — Catálogo mínimo

Cargar 5 productos en categorías distintas:

| SKU    | Nombre          | Categoría | Unidad base | Tax | Precio PYG |
| ------ | --------------- | --------- | ----------- | --- | ---------- |
| CAJ001 | Caja 40x40      | Cajas     | unit        | 10% | 1.300      |
| BOL001 | Bolsa kraft     | Bolsas    | unit        | 10% | 800        |
| CIN001 | Cinta embalaje  | Cintas    | roll        | 10% | 5.000      |
| PAP001 | Papel manila    | Papeles   | unit        | 10% | 2.500      |
| ETI001 | Etiqueta blanca | Etiquetas | pack        | 10% | 1.800      |

- Asignar `low_stock_threshold` = 10 a todos.
- A `CAJ001` agregarle también precio en USD (ej. 0.20 USD), para probar moneda mixta.
- Crear proveedor: **"Distribuidora Test"**.
- Crear clientes: **"Cliente A"** y **"Cliente B"**.

### Paso 2 — Inventario inicial

Cargar 100 unidades de cada producto, con costos distintos:

| SKU    | Cantidad inicial | Costo unitario | Valor inicial |
| ------ | ---------------- | -------------- | ------------- |
| CAJ001 | 100              | 1.000          | 100.000       |
| BOL001 | 100              | 600            | 60.000        |
| CIN001 | 100              | 3.800          | 380.000       |
| PAP001 | 100              | 2.000          | 200.000       |
| ETI001 | 100              | 1.200          | 120.000       |

**Valor total esperado del inventario inicial: 860.000 PYG**

### Paso 3 — Compras (cubrir casos diversos)

- **Compra 1 (PYG, confirmada):** 50 unidades de `CAJ001` a costo 1.200 c/u.
  - _Sirve para validar CPP: avg pasa de 1.000 a (100×1.000 + 50×1.200)/150 = 1.066,67_

- **Compra 2 (USD, confirmada):** 30 unidades de `BOL001` a 0.50 USD c/u, exchange_rate 7.400.
  - _Verifica conversión: `unit_cost_base_currency` debe ser 3.700 PYG (0.50 × 7.400)_

- **Compra 3 (PYG, confirmada → después cancelada):** 20 unidades de `CIN001` a 4.000 c/u.
  - _Verifica que la cancelación genera movements compensatorios y el stock vuelve a 100_

  BUG: La cantidad volvió a 100, pero el cpp quedó igual.
  "sku" "stock_actual" "cpp_actual"
  "CIN001" 100.0000 3833.3333

- **Compra 4 (PYG, draft):** sin confirmar. Sirve para verificar que reportes la ignoran.

### Paso 4 — Ventas (en distintos días)

> Para `sales_by_period`, las fechas deben caer en días diferentes. Si tu test rápido es en un mismo día, ajustá manualmente `sale_date` en BD después de crearlas (o creá durante varios días si tenés tiempo).

- **Venta 1 (hoy, PYG, confirmada):** 5 de `CAJ001` + 3 de `BOL001`.
- **Venta 2 (ayer, PYG, confirmada):** 10 de `PAP001`.
- **Venta 3 (anteayer, PYG, confirmada):** 2 de `CAJ001` + 1 de `ETI001`, con descuento de cabecera 10%.
- **Venta 4 (hoy, confirmada → después cancelada):** 1 de `CAJ001`.
  - _Verifica que la cancelada NO se cuenta en reportes_
    BUG: La venta cancelada No se cuenta, pero la venta en Borrador Sí está contando.

- **Venta 5 (hoy, PYG, confirmada):** vaciar stock de `ETI001` hasta dejarlo en 4 (vender 95 si quedan 99 tras venta 3).
  - _Para validar `low_stock_products` — debe quedar bajo el threshold de 10_
    BUG: No se muestra el threshold por ningun lado al cargar la venta en POS. low_stock_threshold no se esta marcando en la bd
    "sku" "name" "quantity_base" "low_stock_threshold"
    "CIN001" "Cinta embalaje" 100.0000 null
    "PAP001" "Papel manila" 90.0000 null
    "CAJ001" "Caja 40x40" 143.0000 null
    "ETI001" "Etiqueta blanca" 4.0000 null
    "BOL001" "Bolsa kraft" 125.0000 null

### Paso 5 — Ajuste de stock

- Tipo: `merma`
- Item: 2 unidades de `BOL001` con `direction=out`
- Confirmar.

_Verifica que el ajuste aparece en kardex pero NO en reportes de ventas._

---

## Resultado esperado al terminar el setup

- 5 productos con stock variado.
- 1 producto bajo threshold (`ETI001`).
- 4 ventas confirmadas + 1 cancelada.
- 3 compras confirmadas (1 cancelada después) + 1 en draft.
- 1 ajuste de merma.
- Movimientos en múltiples días.
- Una compra y sus efectos en moneda extranjera.

---

## Validaciones — Queries SQL para cada reporte

Ejecutá cada query en pgAdmin/psql. Comparalas con lo que muestra la UI (dashboard y/o reportes). **Anotá ambos números y la diferencia (debería ser 0).**

### A. Métricas del dashboard (mes actual)

**Ventas totales del mes (en PYG):**

```sql
SELECT COALESCE(SUM(total_base_currency), 0) AS total_ventas_pyg
FROM sales
WHERE status = 'confirmed'
  AND deleted_at IS NULL
  AND date_trunc('month', sale_date) = date_trunc('month', CURRENT_DATE);
```

**Cantidad de ventas del mes:**

```sql
SELECT COUNT(*) AS cant_ventas
FROM sales
WHERE status = 'confirmed'
  AND deleted_at IS NULL
  AND date_trunc('month', sale_date) = date_trunc('month', CURRENT_DATE);
```

**Ticket promedio del mes:**

```sql
SELECT AVG(total_base_currency) AS ticket_promedio
FROM sales
WHERE status = 'confirmed'
  AND deleted_at IS NULL
  AND date_trunc('month', sale_date) = date_trunc('month', CURRENT_DATE);
```

**Utilidad del mes (más delicada — usa snapshots de costo):**

```sql
SELECT
  SUM(si.total_base_currency)
    - SUM(si.quantity_base * si.unit_cost_base_at_sale) AS utilidad_pyg
FROM sale_items si
JOIN sales s ON si.sale_id = s.id
WHERE s.status = 'confirmed'
  AND s.deleted_at IS NULL
  AND date_trunc('month', s.sale_date) = date_trunc('month', CURRENT_DATE);
```

**Valor total del inventario actual:**

```sql
SELECT SUM(quantity_base * avg_cost_base) AS valor_inventario_pyg
FROM stock_current
WHERE quantity_base > 0;
```

**Productos con stock bajo:**

```sql
SELECT p.sku, p.name, sc.quantity_base, p.low_stock_threshold
FROM stock_current sc
JOIN products p ON sc.product_id = p.id
WHERE p.deleted_at IS NULL
  AND p.track_stock = TRUE
  AND sc.quantity_base <= COALESCE(p.low_stock_threshold, 0)
ORDER BY sc.quantity_base ASC;
```

_Debe aparecer `ETI001` con cantidad ≤ 10._

---

### B. Ventas por período (reportes)

**Agrupado por día, mes actual:**

```sql
SELECT
  date_trunc('day', sale_date)::date AS dia,
  COUNT(*) AS cantidad,
  SUM(total_base_currency) AS total_pyg
FROM sales
WHERE status = 'confirmed'
  AND deleted_at IS NULL
  AND date_trunc('month', sale_date) = date_trunc('month', CURRENT_DATE)
GROUP BY dia
ORDER BY dia;
```

Comparar contra el BarChart del dashboard y la tabla del reporte "Ventas por período".

---

### C. Top productos

```sql
SELECT
  p.sku,
  p.name,
  SUM(si.quantity_base) AS cantidad_vendida,
  SUM(si.total_base_currency) AS total_pyg
FROM sale_items si
JOIN sales s ON si.sale_id = s.id
JOIN products p ON si.product_id = p.id
WHERE s.status = 'confirmed'
  AND s.deleted_at IS NULL
  AND date_trunc('month', s.sale_date) = date_trunc('month', CURRENT_DATE)
GROUP BY p.sku, p.name
ORDER BY cantidad_vendida DESC
LIMIT 10;
```

---

### D. Utilidad por producto

```sql
SELECT
  p.sku,
  p.name,
  SUM(si.total_base_currency) AS ingresos_pyg,
  SUM(si.quantity_base * si.unit_cost_base_at_sale) AS costo_pyg,
  SUM(si.total_base_currency - si.quantity_base * si.unit_cost_base_at_sale) AS utilidad_pyg
FROM sale_items si
JOIN sales s ON si.sale_id = s.id
JOIN products p ON si.product_id = p.id
WHERE s.status = 'confirmed'
  AND s.deleted_at IS NULL
  AND date_trunc('month', s.sale_date) = date_trunc('month', CURRENT_DATE)
GROUP BY p.sku, p.name
ORDER BY utilidad_pyg DESC;
```

---

### E. Kardex de un producto

Reemplazar `{PRODUCT_ID}` por el UUID real (usar `CAJ001`):

```sql
SELECT
  sm.created_at,
  sm.movement_type,
  sm.direction,
  sm.quantity_base,
  sm.unit_cost_base,
  sm.reference_type,
  sm.reference_id
FROM stock_movements sm
WHERE sm.product_id = '{PRODUCT_ID}'
ORDER BY sm.created_at ASC;
```

**Verificar:**

- La cantidad de filas debe coincidir con lo que muestra el kardex en la UI.
- El saldo acumulado de la UI debe coincidir con la suma manual de movimientos (con signo según dirección).

---

### F. Consistencia ledger vs cache ⚠️ CRÍTICA

Esta es la query más importante. Si falla, hay un bug grave de transaccionalidad.

```sql
WITH ledger_calc AS (
  SELECT
    sm.product_id,
    sm.warehouse_id,
    SUM(CASE WHEN sm.direction = 'in' THEN sm.quantity_base
             ELSE -sm.quantity_base END) AS qty_calculada
  FROM stock_movements sm
  GROUP BY sm.product_id, sm.warehouse_id
)
SELECT
  p.sku,
  p.name,
  sc.quantity_base AS qty_cache,
  COALESCE(lc.qty_calculada, 0) AS qty_ledger,
  sc.quantity_base - COALESCE(lc.qty_calculada, 0) AS diferencia
FROM stock_current sc
JOIN products p ON sc.product_id = p.id
LEFT JOIN ledger_calc lc
  ON sc.product_id = lc.product_id
  AND sc.warehouse_id = lc.warehouse_id
WHERE p.deleted_at IS NULL;
```

**La columna `diferencia` debe ser 0 para todos los productos.** Si alguno difiere, `stock_current` está desincronizado del ledger — bug crítico que debe arreglarse antes de Fase 7.

---

## Checklist operativo

Tabla para completar mientras probás. Esperado, UI dashboard, UI reportes.

| #   | Métrica                        | Esperado (BD) | UI dashboard | UI reportes | Coincide? |
| --- | ------------------------------ | ------------- | ------------ | ----------- | --------- |
| 1   | Ventas totales del mes         | **\_**        | **\_**       | **\_**      | ⬜        |
| 2   | Cantidad de ventas del mes     | **\_**        | **\_**       | **\_**      | ⬜        |
| 3   | Ticket promedio                | **\_**        | **\_**       | **\_**      | ⬜        |
| 4   | Utilidad del mes               | **\_**        | **\_**       | **\_**      | ⬜        |
| 5   | Valor inventario               | **\_**        | **\_**       | **\_**      | ⬜        |
| 6   | Cantidad productos stock bajo  | **\_**        | **\_**       | **\_**      | ⬜        |
| 7   | Top producto (por cantidad)    | **\_**        | **\_**       | **\_**      | ⬜        |
| 8   | Top producto (por monto)       | **\_**        | **\_**       | **\_**      | ⬜        |
| 9   | Kardex de CAJ001 (cant. filas) | **\_**        | N/A          | **\_**      | ⬜        |
| 10  | Stock actual = ledger (todos)  | 0 diferencias | N/A          | N/A         | ⬜        |

---

## Casos negativos a verificar explícitamente

Estos son los que **más se rompen**. Validalos sin excepción:

- ⬜ **La venta cancelada (#4) NO aparece en:** ventas totales, top productos, utilidad, ventas por período. Si aparece, el filtro `status='confirmed'` no se está aplicando.

- ⬜ **La compra cancelada NO genera ingreso en valor de inventario** (movements compensatorios la dejan en 0 neto). Verificar que `stock_current.quantity_base` de `CIN001` sea 100 (inicial) + 0 (compra + compensación) = 100.

- ⬜ **La compra en draft (#4) NO afecta nada** — ni stock, ni reportes, ni nada.

- ⬜ **El ajuste de merma SÍ baja stock** pero NO afecta utilidad ni ventas. Aparece en kardex como movement type `adjustment_out`.

- ⬜ **Compra en USD:** el `total_base_currency` debe estar en PYG, no en USD. Si el reporte muestra "30 USD" en una columna que dice "Total PYG", hay bug.

- ⬜ **Producto sin movimientos** no debería aparecer en kardex (lista vacía) ni romper otros reportes.

- ⬜ **Recálculo de stock desde ledger** (correr `python -m app.scripts.recalculate_stock`): debe dar exactamente los mismos valores que ya están en `stock_current`. Si genera diferencias, hay un bug en la lógica incremental.

---

## Validaciones secundarias mientras probás

Aprovechá el QA para validar también el manejo de errores del 7.2:

- ⬜ **Endpoint responde con mensaje en español:** ningún error en inglés o con stack trace expuesto.
- ⬜ **Toast aparece una sola vez** por cada acción (no duplicado).
- ⬜ **Formulario preserva datos** tras error (ej: cargar venta, falla por algo, los datos siguen ahí).
- ⬜ **CSV exportado** abre correctamente en Excel/Sheets con headers en español.
- ⬜ **Backend apagado** muestra "Sin conexión con el servidor" claramente, no errores crudos.

---

## Si encontrás bugs

**Anotalos todos primero**, no frenes a arreglar en medio. Por cada bug, registrá:

- Qué reporte / métrica falla
- Valor esperado vs obtenido
- Pasos para reproducir
- ¿Es bug numérico (cálculo mal) o de presentación (formato, redondeo)?

Al final, agrupalos por módulo y armás un prompt único para Claude Code con todos juntos. **No un bug a la vez** — perdés contexto y se hace tedioso.

---

## Después del QA

Sea que todo cuadre o haya bugs, actualizar:

1. **`HANDOFF.md`** sección "Diferidos conscientes" o "Bugs encontrados en QA Fase 6" con los hallazgos.
2. **Bloque 7.1 (tests)** — cada bug encontrado debe convertirse en test de regresión.
3. **`design-decisions.md`** si surgió alguna decisión nueva durante el QA.

---

## Tiempo estimado por sección

| Sección                                        | Tiempo            |
| ---------------------------------------------- | ----------------- |
| Setup (reset + carga de datos)                 | 30-40 min         |
| Validaciones A-F (ejecutar queries + comparar) | 40-50 min         |
| Casos negativos                                | 20-30 min         |
| Validaciones secundarias                       | 10-15 min         |
| **Total**                                      | **1.5 a 2 horas** |

Si encontrás bugs, sumar 30-60 min adicionales por la documentación. **No apurar.** Este es el momento de cazar problemas antes de que el cliente confíe en estos números.
