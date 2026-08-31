---
name: auditar-fuentes
description: Audita entradas ya publicadas en despidos-tracker (data/curated_data.json) para detectar si existe una fuente mejor o más completa para el MISMO hecho ya cubierto — no para agregar una etapa nueva de la historia (eso lo maneja depurar-pendientes/reescribir-titular). Usar cuando el usuario pide "revisar fuentes publicadas", "auditar el tracker", "chequear si hay mejor cobertura de lo ya cargado", o mantenimiento periódico de calidad de fuentes sobre notas que ya están en el sitio.
---

# Auditar fuentes de notas ya publicadas

Contexto: `despidos-tracker` es un tablero cronológico — cada entrada de `data/curated_data.json` es un hecho fechado, no un perfil de empresa. Cuando una empresa tiene varias etapas reales (suspensión → despidos → cierre → quiebra), cada etapa merece su propia entrada: eso es la línea de tiempo funcionando bien, no duplicación. Este skill **no toca esa lógica**. Sirve para un problema distinto: una entrada ya publicada puede tener una fuente floja (un portal gremial, un digital sin trayectoria, un sitio hiperlocal) cuando en realidad existe — o apareció después — una cobertura mejor o más completa **del mismo hecho, en la misma fecha**. Reemplazar eso no reescribe la historia del tracker, solo mejora de dónde sale el dato.

No reemplaza a `reescribir-titular` — la jerarquía de fuentes, el estilo de título/bajada, moneda en letras, atribución de causas, geo, sector: todo eso se lee de ahí, no se repite acá.

## 0. Antes de tocar nada: sincronizar

Mismo chequeo que en `depurar-pendientes` — el panel admin escribe directo a GitHub y puede haber cambios ajenos en el medio:

```
git fetch origin
git status
git log --oneline -3 origin/main
```

Si `origin/main` avanzó y hay cambios locales sin commitear en `data/curated_data.json`, no hagas `git pull` a secas — primero `git stash push -m "wip" -- despidos-tracker/data/curated_data.json`, después `git pull --ff-only`, después `git stash pop`. Repetí este chequeo antes de cada commit, no solo al principio.

## 1. Elegir qué auditar

No hace falta (ni conviene) reauditar las 96+ entradas cada vez. Formas de acotar el lote, de más a menos específica:

- **El usuario pide una empresa/nota puntual** (como pasó con La Anónima, Volalá y la curtiembre de Nonogasta): auditá solo esa.
- **El usuario pide un lote** ("revisá las de sector Comercio", "las últimas 20 publicadas", "las que tienen menos de dos líneas de bajada"): filtrá `data/curated_data.json` en Python por ese criterio.
- **Sin criterio del usuario**: corré `list_medios.py` (acompaña a este skill) para ver qué medios aparecen y cuántas veces. Priorizá:
  1. Medios que no son diario nacional de peso ni el diario papel principal de la zona del hecho (revisá `provincia`/`departamento` de la entrada para saber la zona) — portales gremiales (InfoGremiales), verticales de nicho (Ladevi, REPORTUR), digitales sin trayectoria conocida.
  2. Entradas con `snippet` muy corto o genérico (poca sustancia para evaluar si la nota original pasaba el filtro de calidad).
  3. Entradas viejas (`date` de hace varios meses) — más tiempo para que haya aparecido cobertura mejor o una continuación.

  No superes ~15-20 entradas por pasada si vas a laburarlo en el hilo principal — es trabajo de búsqueda uno por uno, se llena de contexto rápido (ver paso 5 para lotes grandes).

## 2. Para cada entrada: evaluar si vale la pena buscar

Antes de gastar una búsqueda, mirá el medio actual contra la jerarquía de `reescribir-titular` (paso 2 de ese skill). Si ya es un medio nacional de peso, o el diario papel principal de la zona del hecho, **no busques** — ya está en el techo de la jerarquía, buscar no va a mejorar nada. Reservá la búsqueda para medios de nivel más bajo.

## 3. Buscar y decidir

1. **WebSearch** con la empresa + el hecho concreto (no genérico: "despidos" solo trae ruido si la empresa tuvo varias etapas — usá también una cifra o palabra clave específica del hecho actual, ej. "morosidad", "concurso preventivo", el monto, la ubicación).
2. **Antes de comparar fuentes, confirmá que es el mismo hecho.** Fijate la fecha del candidato nuevo contra la `date` de la entrada publicada:
   - Si es la misma fecha/hecho con más detalle o mejor medio → sigue en el paso 4 (reemplazo).
   - **Si es una fecha posterior con información nueva** (más despidos, un paso judicial siguiente, un desenlace) → **no la uses para reemplazar esta entrada.** Es una etapa nueva de la historia: avisale al usuario y ofrecé sumarla como entrada aparte (flujo de `depurar-pendientes`/`reescribir-titular`), no pises la entrada existente con eso.
   - Si no aparece nada mejor, dejá la entrada como está — no fuerces un cambio por cambiar.
3. **Si hay reemplazo**, aplicá las reglas de reescritura del paso 3 de `reescribir-titular` (título, bajada, moneda en letras, atribución de causas, sin acumular datos de trámite como juzgado/expediente/juez, sujeto = empresa) sobre el contenido nuevo. Actualizá `medio` y `url`; actualizá `title`/`snippet`/`provincia`/`departamento`/`sector` solo si el dato nuevo es mejor que el que ya estaba (no bajes calidad). Actualizá `status_at` a la fecha/hora actual del cambio; **no toques `date`** salvo que la fecha original estuviera mal (eso sí se corrige).
4. **Si dos fuentes se contradicen en un dato**, mismo criterio que el paso 7 de `reescribir-titular`: no lo resuelvas en silencio, avisale al usuario la discrepancia.

## 4. Validar antes de commitear

Mismo chequeo que `depurar-pendientes` (paso 6 de ese skill): sin ids duplicados, sin `$` en título/snippet, y ningún id publicado que siga figurando `pendiente` en `raw_data.json` — **salvo que el usuario haya pedido explícitamente dejar ese id en pendiente para revisarlo él mismo** (como pasó con Rafael G. Albanesi y ART); en ese caso el chequeo de overlap va a fallar a propósito, no lo "arregles" solo sin preguntar.

```python
import json
c = json.load(open('despidos-tracker/data/curated_data.json', encoding='utf-8'))
assert len(c) == len(set(i['id'] for i in c)), "ids duplicados en curated"
assert not any('$' in (i.get('title','')+i.get('snippet','')) for i in c), "signo $ sin convertir a letras"
print('OK —', len(c), 'publicadas')
```

## 5. Commit, push y lotes grandes

Un commit por entrada o por lote chico (no uno gigante). Mensaje: qué entrada, medio viejo → medio nuevo, y por qué (mejor jerarquía / más completa / dato corregido). Repetí el chequeo de sync del paso 0 antes de cada push.

Si el usuario pide auditar un lote grande (muchas entradas de una), delegá a uno o más forks — mismo patrón que el paso 5 de `depurar-pendientes`: nunca dos forks escribiendo `curated_data.json` en paralelo, lanzalos secuenciales o con `isolation: "worktree"` y mergeá después. Dale a cada fork la lista de ids+títulos+medio actual a revisar y este documento completo.
