# HANDOFF.md — Estado actual operativo

Memoria operativa del proyecto DTCore. Leer esto primero al retomar después de una pausa.

**Última actualización:** 2026-05-23 — Bloque 0.1 completado.

---

## Fase actual

**Fase 0 — Setup y fundaciones** (en progreso)

Próximo bloque a ejecutar: **0.2 — Base de SQLAlchemy + Alembic + settings** (ver `docs/roadmap.md`).

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

- `docker-compose.yml` creado. Correr `docker compose up -d` para iniciar PostgreSQL 16.
- Container: `dtcore-db`, DB: `dtcore_db`, user: `admin`, password: `admin123`, port: 5432.
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

```bash
# PostgreSQL
docker compose up -d

# Backend (en backend/)
.venv\Scripts\activate
pip install -r requirements.txt

# Frontend (en frontend/)
npm run dev   # → https://localhost:5173
```

---

## Próximo paso concreto

Iniciar **Fase 0, bloque 0.2 — Base de SQLAlchemy + Alembic + settings**.

---

## Historial de fases cerradas

### Bloque 0.1 — Estructura del proyecto (2026-05-23)

- Estructura `backend/` y `frontend/` creadas
- Docker Compose con PostgreSQL 16 (`dtcore-db`)
- Backend: `app/{api,services,models,schemas,seed,tests}/`, `requirements.txt`, `pyproject.toml` (ruff+black), venv Python
- Frontend: Vite 5 + React 18 + TS 5.5, Tailwind 3, React Router v6, Zustand, Recharts, vite-plugin-pwa, vite-plugin-mkcert
- Nota: Node 20.12.1 genera warnings EBADENGINE en eslint/globals; no afecta el dev server. Considerar actualizar Node a 20.19+ si genera problemas.

---

## Documentación del proyecto

| Archivo                    | Para qué                            | Frecuencia de cambio |
| -------------------------- | ----------------------------------- | -------------------- |
| `CLAUDE.md`                | Reglas activas del proyecto         | Bajo                 |
| `HANDOFF.md` (este)        | Estado operativo actual             | Alto                 |
| `docs/erd.md`              | Modelo de datos detallado           | Bajo                 |
| `docs/roadmap.md`          | Fases y bloques                     | Bajo                 |
| `docs/prompts.md`          | Prompts por bloque para Claude Code | Bajo                 |
| `docs/design-decisions.md` | Historial de por qué                | Bajo                 |
| `docs/common-patterns.md`  | Patrones de código                  | Medio                |
| `docs/comandos.md`         | Referencia de comandos              | Bajo                 |

---

## Cómo retomar después de pausa

1. Leer este archivo (HANDOFF.md) primero
2. `git log --oneline -20` para ver últimos commits
3. Verificar entorno local: `docker ps`, venv activado, `alembic current`
4. Abrir Claude Code en la raíz del proyecto

---

## Cómo obtener la ip del contenedor de la BD de docker

docker inspect dtcore-db | Select-String '"IPAddress"'

---

## Cómo actualizar este archivo

Al cerrar un bloque o fase:

1. Mover el bloque/fase de "actual" a "cerrado" con fecha
2. Actualizar "Próximo paso concreto" al siguiente bloque
3. Agregar notas relevantes (decisiones que surgieron, fixes notables, deuda técnica)
4. Actualizar "Última actualización" arriba

Mantener el archivo conciso. Detalle largo va a otros docs (`design-decisions.md` para porqués, `common-patterns.md` para patrones).
