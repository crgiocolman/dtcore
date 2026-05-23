# DTCore

Sistema base de gestión de compra/venta/inventario para pequeños negocios.

## Arranque rápido

```bash
# PostgreSQL
docker compose up -d

# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
npm run dev                   # HTTPS en https://localhost:5173
```

## Documentación

| Archivo | Descripción |
|---|---|
| `docs/erd.md` | Modelo de datos (fuente de verdad del schema) |
| `docs/roadmap.md` | Fases y bloques del proyecto |
| `docs/design-decisions.md` | Historial de decisiones de diseño |
| `docs/common-patterns.md` | Patrones de código recurrentes |
| `CLAUDE.md` | Reglas del proyecto para Claude Code |
| `HANDOFF.md` | Estado operativo actual |
