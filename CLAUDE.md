@../ai-workbench/AGENTS.md

# CLAUDE.md

## Que es este proyecto

Dashboard interactivo de creacion y destruccion de empleo privado registrado y empresas empleadoras
en Argentina, con cobertura nacional, provincial, departamental y subregional, con desglose sectorial
y comparacion entre presidencias. Publicado en Netlify. Contexto completo en `README.md`.

## Arquitectura

- `data.json` / `empresas.json` — datos generados automaticamente por `scripts/`
- `scripts/actualizar.py` — script principal del workflow (GitHub Actions)
- `scripts/generar_empleo.py` — generador de data.json
- GeoJSONs estaticos para mapas (provincias + departamentos)
- Fuentes: SIPA mensual, OEDE trimestral, MTEySS provincial, empresas empleadoras

## Reglas de trabajo

- Los JSONs de datos se sirven desde `raw.githubusercontent.com` — no commitear backups (.bak) sin razon.
- Workflow de GitHub Actions actualiza automaticamente.
