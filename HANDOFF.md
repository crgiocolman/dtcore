# HANDOFF.md — Estado actual operativo

Memoria operativa del proyecto DTCore. Leer esto primero al retomar después de una pausa.

**Última actualización:** 2026-05-22 — diseño cerrado, sin código todavía.

---

## Fase actual

**Fase 0 — Setup y fundaciones** (no iniciada)

Próximo bloque a ejecutar: **0.1 — Estructura del proyecto** (ver `docs/roadmap.md` y `docs/prompts.md`).

---

## Estado del diseño

- ✅ Modelo de datos completo (`docs/erd.md`)
- ✅ Decisiones de diseño documentadas (`docs/design-decisions.md`)
- ✅ Reglas de proyecto (`CLAUDE.md`)
- ✅ Roadmap por fases (`docs/roadmap.md`)
- ✅ Prompts por bloque (`docs/prompts.md`)
- ⏳ Sin código todavía

---

## Estado BD local

- Sin BD creada todavía. Se creará en bloque 0.1 con `docker compose up -d`.
- Sin migraciones todavía. Primera migración se genera en bloque 0.3.

---

## Variables de entorno (.env local)

A definir al iniciar bloque 0.1. Plantilla esperada:

```
DATABASE_URL=postgresql+asyncpg://admin:admin123@localhost:5432/dtcore_db
JWT_SECRET=<generar al instalar>
STORAGE_PATH=./storage
BACKUP_DRIVE_REMOTE_PATH=<configurar al desplegar>
```

---

## Arranque del entorno local

Documentar al completar bloque 0.1.

---

## Próximo paso concreto

Iniciar **Fase 0, bloque 0.1 — Estructura del proyecto**. Ver prompt en `docs/prompts.md`.

---

## Historial de fases cerradas

(Vacío — primer cierre será al completar Fase 0.)

---

## Documentación del proyecto

| Archivo                          | Para qué                            | Frecuencia de cambio |
| -------------------------------- | ----------------------------------- | -------------------- |
| `CLAUDE.md`                      | Reglas activas del proyecto         | Bajo                 |
| `HANDOFF.md` (este)              | Estado operativo actual             | Alto                 |
| `docs/erd.md`                    | Modelo de datos detallado           | Bajo                 |
| `docs/roadmap.md`                | Fases y bloques                     | Bajo                 |
| `docs/prompts.md`                | Prompts por bloque para Claude Code | Bajo                 |
| `docs/design-decisions.md`       | Historial de por qué                | Bajo                 |
| `docs/common-patterns.md`        | Patrones de código                  | Medio                |
| `docs/comandos.md`               | Referencia de comandos              | Bajo                 |

---

## Cómo retomar después de pausa

1. Leer este archivo (HANDOFF.md) primero
2. `git log --oneline -20` para ver últimos commits
3. Verificar entorno local: `docker ps`, venv activado, `alembic current`
4. Abrir Claude Code en la raíz del proyecto

---

## Cómo actualizar este archivo

Al cerrar un bloque o fase:
1. Mover el bloque/fase de "actual" a "cerrado" con fecha
2. Actualizar "Próximo paso concreto" al siguiente bloque
3. Agregar notas relevantes (decisiones que surgieron, fixes notables, deuda técnica)
4. Actualizar "Última actualización" arriba

Mantener el archivo conciso. Detalle largo va a otros docs (`design-decisions.md` para porqués, `common-patterns.md` para patrones).
