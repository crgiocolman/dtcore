# HANDOFF.md — Estado actual operativo

Memoria operativa del proyecto DTCore. Leer esto primero al retomar después de una pausa.

**Última actualización:** 2026-06-15 — Fase 7 casi cerrada; pendientes 7.9, 7.10 y limpieza final.

---

## Fase actual

**Fase 7 en ejecución avanzada.** Cerrados en orden: 7.2 → 7.3 → 7.4 → 7.5 + 7.5b → 7.6 (N/A) → 7.7 → 7.1 (tests). En curso: **7.8 — Acompañamiento**. Pendientes: **7.9 — Edición de fecha**, **7.10 — Ordenamiento de listas**.

---

## Estado del código

- **Backend completo:** stock + CPP, compras draft→confirm→cancel, ventas con lock pesimista, ajustes, reportes (6 funciones), excepciones custom, logs estructurados. 32 tests unitarios + regresión pasando.
- **Frontend completo:** layout dark, auth, admin, productos, contactos, compras, POS, ventas, ajustes, dashboard con 4 métricas + gráficos + stock bajo + valor inventario, reportes con 5 tabs + CSV. Sidebar colapsable con secciones agrupadas. Responsive `md` con hamburguesa.
- **Producción:** sistema en cliente desde 2026-06-03. Capacitación realizada.
- Migraciones aplicadas hasta head. Ver `alembic current`.

---

## Entorno local

```bash
docker compose up -d                              # PostgreSQL
.venv\Scripts\activate && uvicorn app.main:app --reload   # Backend
npm run dev                                       # Frontend → https://localhost:5173
```

Credenciales dev: `admin` / `admin123`. Container BD: `dtcore-db`, port 5432.

`.env` mínimo:

```
DATABASE_URL=postgresql+asyncpg://admin:admin123@localhost:5432/dtcore_db
JWT_SECRET=<generar al instalar>
STORAGE_PATH=./storage
BACKUP_DRIVE_REMOTE_PATH=<configurar al desplegar>
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/backend.log
```

Para correr tests: `createdb dtcore_test` + `pytest app/tests/services/ app/tests/regressions/ -v`. Ver `docs/comandos.md`.

---

## Próximos pasos

**7.9 — Edición de fecha de transacciones (pendiente).** Solo rol admin sobre ventas/compras/ajustes `confirmed`. Endpoint `PATCH /{id}/date` con `{new_date, reason}`. Validaciones: año calendario actual, motivo ≥10 chars. Audit log con acción `date_edit`. UI: botón "Editar fecha" en vista detalle → modal con date picker + textarea.

**7.10 — Ordenamiento de listas (pendiente).** Componente `SortableHeader` reutilizable. Aplicar en productos, contactos, ventas, compras, ajustes. Ciclo asc → desc → sin orden. Persistir en query string `?sort=&dir=`. Backend: cada endpoint de listado acepta `?sort=&dir=`.

---

## Historial de fases

### Fase 7 — Pulido y entrega (en curso desde 2026-06-03)

- **7.1 — Tests backend (cerrado 2026-06-15):** 32 tests en `app/tests/services/` y `app/tests/regressions/`. Cubren caminos críticos (CPP, lock pesimista, confirm/cancel de purchases/sales) + 19 regresiones por cada bug de QA con docstring trazable. Setup con BD `dtcore_test`, conftest con rollback por test. QA manual cruzado contra BD confirmó coherencia ledger vs cache.
- **7.2 — Errores y validaciones:** excepciones custom en `app/exceptions.py`, helper `parseApiError` en frontend, toasts consistentes en español, logs estructurados con rotación.
- **7.3 — Sidebar colapsable:** 3 estados (expandido/colapsado/oculto), `localStorage`, agrupación por secciones (Operación / Catálogo / Inventario / Reportes / Configuración).
- **7.4 — Responsive:** breakpoint `md` (768px), drawer en móvil, dashboard apilado vertical. POS y formularios sin rediseño (operación móvil = v2).
- **7.5 + 7.5b — Deployment:** `docs/deployment.md` (Docker) + `docs/deployment_windows.md` (NSSM nativo). Smoke test de 15 verificaciones, plan de rollback, procedimiento de actualizaciones.
- **7.6 — Datos iniciales:** N/A. Negocio nuevo, carga manual desde la UI.
- **7.7 — Capacitación:** sesión completada. Documentos entregados. PWA instalada en dispositivos del cliente.
- **7.8 — Acompañamiento:** en curso (3 meses post-entrega). Canal: WhatsApp. Revisión semanal de logs y backups el primer mes.

### Post-Fase 6 — Olas de bugs cerrados durante QA cruzado (2026-06-02 a 2026-06-12)

Bugs detectados en QA cruzado contra BD y cerrados antes de avanzar a Fase 7:

- **Edición de precios:** permitir editar/eliminar precios sin ventas asociadas (con validación `can_edit_price`). Mensaje 409 estructurado si tiene ventas.
- **Centralización de "precio vigente":** función única `get_current_price` en backend con parámetro `as_of_date`. POS y ficha consumen el mismo endpoint, sin lógica de fechas en frontend.
- **Flexibilización de fechas (opción B):** cualquier fecha de vigencia es válida. Único constraint: UNIQUE en (product_id, unit_id, currency_code, effective_from).
- **Bug crítico de timezone:** ventanas de vigencia y reportes diarios calculaban en UTC, no en hora local. Venta de las 21:15 PYT caía en día UTC siguiente. Fix sistémico con setting `business_timezone` (default `America/Asuncion`), aplicado a `can_edit_price`, `sales_by_period`, `top_products`, `profit_by_product`, filtros de fecha de listados.
- **Decimales cosméticos:** formato de precios USD respeta `currency.decimal_places`, factor de unidades sin trailing zeros.

Ver detalle de decisiones en `docs/design-decisions.md`.

### Fase 6 — Ajustes de stock + reportes (cerrada 2026-06-02)

`stock_adjustments` con draft→confirm→cancel + razones tipadas. `report_service.py` con 6 funciones (sales_by_period, top_products, profit_by_product, low_stock, stock_value, kardex). Dashboard `/` con métricas del mes + gráficos. Reportes `/reportes` con 5 tabs + CSV.

### Fase 5 — Ventas (POS) (cerrada 2026-06-01)

`sale_service.py` con lock pesimista, snapshot de costos, `sale_number` correlativo nullable hasta confirmación. POS full-screen con shortcuts F1-F9 (hook reutilizable `useKeyboardShortcuts`), búsqueda con debounce 200ms, carrito en memoria, selector de cliente, descuentos, pagos mixtos. Lista de ventas con filtros y cancelación con motivo obligatorio.

### Fase 4 — Compras + Inventario (cerrada 2026-06-01)

Ledger append-only `stock_movements` + cache `stock_current` con lock pesimista. CPP en entradas. Compras draft→confirm→cancel con audit log. Inventario inicial con detección de productos con movements previos. UI completa de compras + formulario con autocomplete + cancelación.

### Fase 3 — Productos (cerrada 2026-05-28)

Catálogo completo: categorías jerárquicas, productos con búsqueda fuzzy (`pg_trgm`), unidades múltiples con factor de conversión, precios históricos append-only, catálogo normalizado `units_catalog`. Soft delete con índices UNIQUE parciales (SKU/barcode/categorías). Refactors importantes documentados en `docs/design-decisions.md`.

### Fase 2 — Contactos (cerrada 2026-05-26)

CRUD de contactos (clientes/proveedores/ambos), búsqueda, paginación server-side, soft delete. PATCH semántico. Filtro `contact_type=customer` incluye `both`.

### Fase 1 — Panel admin + Settings (cerrada 2026-05-25)

Settings key-value tipadas con cache 60s. Monedas con `exchange_rates` editables solo si son la última y no usadas. `RequireAuth` preserva ruta tras F5.

### Fase 0 — Setup y fundaciones (cerrada 2026-05-25)

Backend/frontend, Docker Compose con Postgres 16, Alembic async, schema completo (~20 tablas, 14 enums), seeds, auth JWT con bcrypt, layout dark + tokens semánticos, PWA + HTTPS con mkcert, scripts de backup/restore.

---

## Documentación del proyecto

| Archivo                      | Para qué                         | Frecuencia |
| ---------------------------- | -------------------------------- | ---------- |
| `CLAUDE.md`                  | Reglas activas del proyecto      | Bajo       |
| `HANDOFF.md` (este)          | Estado operativo actual          | Alto       |
| `docs/erd.md`                | Modelo de datos                  | Bajo       |
| `docs/roadmap.md`            | Fases y bloques                  | Bajo       |
| `docs/prompts.md`            | Prompts por bloque               | Bajo       |
| `docs/design-decisions.md`   | Historial de por qué             | Bajo       |
| `docs/design-system.md`      | Sistema visual                   | Bajo       |
| `docs/common-patterns.md`    | Patrones de código               | Medio      |
| `docs/comandos.md`           | Referencia de comandos           | Bajo       |
| `docs/deployment.md`         | Deployment Docker                | Bajo       |
| `docs/deployment_windows.md` | Deployment Windows nativo (NSSM) | Bajo       |

---

## Cómo retomar después de pausa

1. Leer este archivo
2. `git log --oneline -20`
3. `docker ps` + `alembic current`
4. Abrir Claude Code en la raíz

---

## Tips operativos

**IP del contenedor BD desde host (Windows + bridge network):**

```powershell
docker network connect bridge dtcore-db
docker inspect dtcore-db | Select-String '"IPAddress"'
```

**Reset completo de BD para QA limpio:**

```bash
docker compose down -v && docker compose up -d
alembic upgrade head && python -m app.seed.run
```

**Correr tests:**

```bash
cd backend && pytest app/tests/services/ app/tests/regressions/ -v
```

---

## Cómo actualizar este archivo

Al cerrar un bloque o fase:

1. Actualizar "Próximos pasos"
2. Si cerraste una fase: agregar entrada concisa en "Historial de fases" (3-5 líneas)
3. Actualizar la fecha de arriba

**Regla:** nunca pasar de ~120 líneas. Detalle granular va a `design-decisions.md`, `common-patterns.md`, o queda implícito en `git log`. Si te ves listando archivo por archivo, parate y resumí.
