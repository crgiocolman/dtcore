# docs/design-system.md — Sistema visual de DTCore

Fuente de verdad del sistema visual. Consultar antes de implementar cualquier UI nueva o modificar existente.

**Stack visual:** Tailwind CSS 3 + CSS variables para tokens semánticos + Inter como tipografía.

---

## Filosofía

**Dark mode profundo con fondos azulados.** No negro puro, no grises clínicos. La paleta está calibrada para uso prolongado (8 horas/día en POS) — los fondos son menos contrastantes que un dark mode genérico, el texto principal no es blanco puro (#E8EEF7 en lugar de #FFFFFF) para reducir halo visual y fatiga.

**Sin light mode en v1.** Los tokens están estructurados con CSS variables, lo que permitirá activar light mode en v2 sin refactor de componentes. Para activarlo, basta con redefinir las variables en una clase `.light` sobre `<html>`.

**Inspirado en TributarioPY**, ajustado para uso intensivo. Mismas decisiones cromáticas base (azul como primario, fondos azulados, alta legibilidad) con diferencias específicas:

- Texto principal ligeramente menos brillante (E8EEF7 vs blanco puro)
- Reservamos un **acento cyan** para acciones críticas del POS, separándolas visualmente de acciones generales en azul
- Números en POS y reportes usan variantes tabulares para alineación vertical en columnas

---

## Tokens de color

### Fondos (jerarquía de superficies)

| Token            | RGB      | Hex     | Uso                                               |
| ---------------- | -------- | ------- | ------------------------------------------------- |
| `bg-bg-base`     | 11 18 32 | #0B1220 | Fondo de la app (body)                            |
| `bg-bg-surface`  | 17 26 46 | #111A2E | Sidebar, header, cards principales                |
| `bg-bg-elevated` | 26 36 64 | #1A2440 | Modales, dropdowns, popovers, botones secundarios |
| `bg-bg-input`    | 22 32 58 | #16203A | Inputs, textareas, selects                        |

**Regla:** los fondos suben gradualmente. Lo más oscuro está abajo (bg-base), lo más elevado más arriba (bg-elevated). Esto crea profundidad sin bordes marcados.

### Bordes

| Token                  | RGB        | Hex     | Uso                                                |
| ---------------------- | ---------- | ------- | -------------------------------------------------- |
| `border-border-subtle` | 31 44 74   | #1F2C4A | Divisores tenues (entre filas de tabla, secciones) |
| `border-border`        | 42 58 92   | #2A3A5C | Bordes de inputs, cards                            |
| `border-border-focus`  | 59 130 246 | #3B82F6 | Input enfocado, foco de teclado                    |

### Texto

| Token                 | RGB         | Hex     | Uso                                      |
| --------------------- | ----------- | ------- | ---------------------------------------- |
| `text-text-primary`   | 232 238 247 | #E8EEF7 | Texto principal, headings, valores       |
| `text-text-secondary` | 148 163 184 | #94A3B8 | Labels, texto secundario, metadata       |
| `text-text-muted`     | 100 116 139 | #64748B | Placeholders, texto deshabilitado, hints |

**Regla:** nunca usar `text-white` directo. Usar siempre `text-text-primary`.

### Primary (azul) — Acciones generales

Acciones estándar del sistema: Guardar, Confirmar (compra/ajuste), enlaces activos en sidebar, foco general.

| Token         | Hex              |
| ------------- | ---------------- |
| `primary-500` | #3B82F6          |
| `primary-600` | #2563EB (hover)  |
| `primary-700` | #1D4ED8 (active) |

### Accent (cyan) — RESERVADO para acción crítica del POS

**Solo se usa en el botón "Cobrar" del POS (F4) y otras confirmaciones de venta.** Crea diferenciación visual aprendida: el cajero asocia el cyan con "completar venta".

| Token        | Hex              |
| ------------ | ---------------- |
| `accent-500` | #06B6D4          |
| `accent-600` | #0891B2 (hover)  |
| `accent-700` | #0E7490 (active) |

**Si encontrás cyan en cualquier otro lado que no sea POS-Cobrar, está mal aplicado.**

### Semánticos

| Token         | Hex     | Uso                                                    |
| ------------- | ------- | ------------------------------------------------------ |
| `success-500` | #10B981 | Confirmaciones, stock OK, valores positivos            |
| `warning-500` | #F59E0B | Stock bajo, advertencias no bloqueantes                |
| `danger-500`  | #EF4444 | Errores, acciones destructivas, stock crítico/negativo |
| `info-500`    | #6366F1 | Información neutra, mensajes informativos              |

**Distinción importante:** `warning` para alertas (algo que el usuario debería atender), `danger` para errores reales o acciones destructivas. Si todo es rojo, nada destaca.

---

## Tipografía

**Familia:** Inter (cargada desde Google Fonts), con fallback a system-ui.

**Por qué Inter:**

- Excelente legibilidad en pantalla a cualquier tamaño
- Variantes tabulares para alineación de números en columnas (crítico en POS y reportes)
- Gratuita, hospedable localmente si se quiere

### Jerarquía sugerida

| Uso                      | Clase Tailwind                    | Tamaño |
| ------------------------ | --------------------------------- | ------ |
| Heading página (h1)      | `text-2xl font-semibold`          | 24px   |
| Heading sección (h2)     | `text-lg font-semibold`           | 18px   |
| Heading sub-sección (h3) | `text-base font-medium`           | 16px   |
| Texto cuerpo             | `text-sm`                         | 14px   |
| Labels y metadata        | `text-sm text-text-secondary`     | 14px   |
| Texto auxiliar / hints   | `text-xs text-text-muted`         | 12px   |
| Totales destacados (POS) | `text-3xl font-bold tabular-nums` | 30px   |

### Números tabulares

En **POS, reportes, y cualquier columna numérica de tabla**, aplicar `tabular-nums` (font-variant-numeric: tabular-nums). Hace que cada dígito ocupe el mismo ancho, alineando verticalmente las columnas de totales.

```tsx
<td className="tabular-nums text-right">{formatCurrency(item.total)}</td>
<div className="text-3xl font-bold tabular-nums">{formatCurrency(saleTotal)}</div>
```

### Font features de Inter

`index.css` activa `cv11` (1 con serifa pequeña) y `ss01` (alfa de un solo piso). Mejora legibilidad sutilmente. Si en algún caso particular se ven mal, se desactivan localmente.

---

## Componentes base

Definidos como clases `@layer components` en `index.css`. Documentados acá con su uso.

### Botones

| Clase            | Cuándo usar                                                                         | Apariencia                          |
| ---------------- | ----------------------------------------------------------------------------------- | ----------------------------------- |
| `.btn-primary`   | Acción principal de la pantalla: Guardar, Confirmar (compra/ajuste), Iniciar sesión | Azul lleno                          |
| `.btn-accent`    | **Solo "Cobrar" del POS** y confirmaciones de venta. No usar para nada más          | Cyan lleno, más grande y prominente |
| `.btn-secondary` | Acciones no destacadas: Cancelar (en modal), Volver, Guardar como borrador          | Fondo elevado con borde             |
| `.btn-danger`    | Acciones destructivas: Eliminar, Cancelar compra/venta confirmada                   | Rojo lleno                          |
| `.btn-ghost`     | Iconos en barras, acciones sutiles, menús contextuales                              | Sin fondo, hover sutil              |

**Regla:** una sola `.btn-primary` por pantalla. Si hay dos acciones primarias visibles, una debe degradarse a secondary.

**Combinación típica en formularios:**

```tsx
<div className="flex gap-2 justify-end">
  <button className="btn-secondary">Cancelar</button>
  <button className="btn-primary">Guardar</button>
</div>
```

**Botón Cobrar en POS (caso único):**

```tsx
<button className="btn-accent w-full text-lg" onClick={handleCheckout}>
  Cobrar (F4)
</button>
```

### Inputs

```tsx
<div>
  <label className="label">Nombre del producto</label>
  <input className="input" type="text" />
</div>
```

Clases:

- `.label` — label de input (text-sm, color secundario)
- `.input` — input/textarea/select con estilos consistentes

Para inputs con error, agregar `border-danger-500 focus:ring-danger-500` (o crear `.input-error` si se repite mucho).

### Cards

```tsx
<div className="card">
  <h3 className="text-lg font-semibold mb-2">Título</h3>
  <p className="text-text-secondary">Contenido</p>
</div>
```

`.card` = `bg-bg-surface` + borde subtle + padding + rounded-lg.

---

## Patrones de layout

### Anchos máximos

- Formularios estándar: `max-w-2xl` (672px)
- Listados con tablas: `max-w-full` con padding lateral
- POS: pantalla completa, sin max-width

### Espaciado consistente

- Entre secciones de una página: `space-y-6`
- Entre campos de un formulario: `space-y-4`
- Entre elementos relacionados (label + input): `space-y-1.5`
- Padding de cards: `p-4` (estándar) o `p-6` (cards principales)

### Border radius

- Default: 6px (configurado en tailwind como `rounded`)
- Cards y modales: 8px (`rounded-lg`)
- Inputs: 6px (`rounded`)
- Botones: 6px (`rounded`)
- Avatares y círculos: `rounded-full`

---

## Reglas de oro (qué NUNCA hacer)

1. **Nunca usar `text-white` directo** → usar `text-text-primary`
2. **Nunca usar `bg-slate-*`, `bg-gray-*`, `bg-zinc-*` directo** → usar tokens `bg-bg-*`
3. **Nunca hardcodear hex de color** en componentes → usar tokens
4. **Nunca usar el cyan/accent fuera del POS-Cobrar** → es la única excepción visual del sistema
5. **Nunca dos `.btn-primary` visibles en la misma pantalla** → jerarquía clara
6. **Nunca olvidar `tabular-nums` en columnas de números** → alinea totales correctamente
7. **Nunca usar emojis como iconos funcionales** → usar Lucide React (a definir cuando aparezca el primer uso)
8. **Nunca text-xs para texto importante** → 12px es solo para hints, metadata, breadcrumbs

---

## Estados visuales

### Loading

A definir cuando aparezca el primer componente que lo necesite. Sugerencia inicial: skeleton screens con `bg-bg-elevated animate-pulse` para listados y formularios; spinner inline para botones (`<Loader2 className="animate-spin" />`).

### Empty states

A definir cuando aparezca el primer listado vacío. Sugerencia inicial: icono grande + título + descripción + acción primaria centrada.

### Error states

A definir. Sugerencia inicial: usar `border-danger-500` en inputs con error + mensaje de error abajo en `text-danger-500 text-xs`.

---

## Iconografía

**Librería:** Lucide React (`lucide-react`). Instalada desde Fase 0.6.

### Tamaños estándar

| Contexto                          | Tamaño                    | Clase       |
| --------------------------------- | ------------------------- | ----------- |
| Sidebar, navegación principal     | 20px                      | `w-5 h-5`   |
| Botones (al lado de texto)        | 16px                      | `w-4 h-4`   |
| Botones de acción solos (toolbar) | 20px                      | `w-5 h-5`   |
| Empty states (placeholder grande) | 48px                      | `w-12 h-12` |
| Inline con texto                  | 14-16px según el contexto |             |

### Color

Los iconos heredan el color del texto vía `currentColor`. Se controlan con clases `text-*`:

```tsx
<Home className="w-5 h-5 text-text-secondary" />
<ShoppingCart className="w-5 h-5 text-primary-500" />  {/* link activo */}
```

### Mapeo del sidebar (referencia)

Mantener consistencia con esta selección de iconos para los módulos principales:

| Módulo     | Icono Lucide   |
| ---------- | -------------- |
| Inicio     | `Home`         |
| POS        | `ShoppingCart` |
| Ventas     | `Receipt`      |
| Compras    | `Truck`        |
| Productos  | `Package`      |
| Contactos  | `Users`        |
| Inventario | `Boxes`        |
| Reportes   | `BarChart3`    |
| Admin      | `Settings`     |
| Salir      | `LogOut`       |

### Reglas

- **Nunca usar emojis** como iconos funcionales. Siempre Lucide.
- **Iconos para acciones, no decoración.** Un icono debe representar la acción/concepto. No agregar iconos solo para llenar espacio.
- **Consistencia:** el mismo concepto debe usar el mismo icono en todo el sistema. Si "eliminar" es `Trash2` en un lugar, lo es en todos lados.
- **Iconos comunes para acciones recurrentes:** `Plus` (agregar), `Trash2` (eliminar), `Edit` o `Pencil` (editar), `Search` (buscar), `X` (cerrar), `Check` (confirmar), `ChevronDown` (expandir), `AlertCircle` (warning), `AlertTriangle` (danger).

---

## Cómo extender el sistema

Cuando aparezca un componente recurrente nuevo (modal, badge, datepicker, etc.):

1. **Definirlo en `index.css` como clase `@layer components`** si va a usarse en múltiples lugares
2. **Documentarlo acá** en una sección "Componentes" apropiada
3. **Si es muy específico de un módulo**, dejarlo como componente React en `src/features/<modulo>/components/`

Cuando aparezca una decisión visual nueva (ej. "los tooltips siempre van debajo del elemento"):

1. **Agregarla a "Reglas de oro"** si es una restricción dura
2. **Agregarla a la sección correspondiente** si es una guía positiva

---

## Activación de light mode (preparado para v2)

Para activar light mode en v2, basta con:

1. Definir una clase `.light` en `index.css` con valores invertidos para los tokens:

```css
.light {
  --color-bg-base: 248 250 252;
  --color-bg-surface: 255 255 255;
  /* ... etc */
}
```

2. Agregar un toggle en la UI que aplique/quite la clase `.light` en `<html>`
3. Persistir la preferencia en `localStorage` o en `settings` del backend

**No hacer esto en v1.** Solo dejar la estructura preparada.
