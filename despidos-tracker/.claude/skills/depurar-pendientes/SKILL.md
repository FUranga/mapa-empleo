---
name: depurar-pendientes
description: Depura el backlog de pendientes de despidos-tracker (data/raw_data.json) — descarta ruido (no-Argentina, sector público no estatal, uso no empresarial de "quiebra"), detecta cuando la misma historia aparece varias veces entre distintos medios, y para cada historia real busca la mejor fuente y publica una entrada nueva en data/curated_data.json. Usar cuando el usuario pide "revisar los pendientes", "buscar duplicados en el backlog", "limpiar el ruido del scraper", o algo similar al mantenimiento periódico del tracker (no para reescribir una nota puntual que el usuario ya identificó — para eso usar el skill reescribir-titular).
---

# Depurar pendientes del tracker

Contexto: `despidos-tracker` scrapea automáticamente decenas de medios (`config/sources_config.json`) por palabras clave (`config/keywords_config.json`). Eso genera mucho ruido — notas de otros países, "quiebra" usado como modismo emocional/deportivo, sector público, y la misma historia cubierta por 3-4 medios distintos — que se acumula en `data/raw_data.json` con `status: "pendiente"`. Este skill hace el pase completo: limpiar el ruido, agrupar duplicados, y publicar una entrada prolija por cada historia real que todavía no esté en `data/curated_data.json`.

No reemplaza al skill `reescribir-titular` — para el estilo de título/bajada, la jerarquía de fuentes, sector, geo-localización, etc. **este skill delega en esas reglas**, no las repite. Leelas de ahí antes de escribir cualquier entrada nueva.

## 0. Antes de tocar nada: sincronizar

El panel admin (`admin/index.html`) escribe directo a GitHub vía API — alguien puede estar publicando/descartando desde ahí mientras vos trabajás acá. **Siempre**, antes de la primera edición y antes de cada commit:

```
git fetch origin
git status
git log --oneline -3 origin/main
```

Si `origin/main` avanzó y vos ya tenés cambios locales sin commitear en los mismos archivos (`data/curated_data.json` o `data/raw_data.json`), no hagas `git pull` directo — vas a pisar tu propio trabajo o el ajeno. Primero:

```
git stash push -m "wip" -- despidos-tracker/data/curated_data.json despidos-tracker/data/raw_data.json
git pull --ff-only origin main
git stash pop
```

Si el pull trae cambios en un archivo que vos no tocaste, se hace `--ff-only` sin stash. Repetí este chequeo de sync antes de cada commit, no solo al principio — sesiones largas (varios forks, varias horas) pueden acumular commits ajenos en el medio.

## 1. Detectar duplicados dentro de pendientes (análisis local, sin red)

Corré el script que acompaña a este skill:

```
python despidos-tracker/.claude/skills/depurar-pendientes/cluster_dupes.py
```

Agrupa `data/raw_data.json` (solo `status: "pendiente"`) por proximidad de fecha (±2 días) + solapamiento de palabras del título (Jaccard sobre tokens, excluyendo stopwords y palabras genéricas del dominio). No escribe nada, solo imprime los clusters candidatos para revisar en el paso 3. Esperá algunos falsos positivos (coincidencia de vocabulario sin relación real) — revisalos a mano o con un fork antes de tratarlos como duplicados.

## 2. Clasificar y descartar ruido (análisis local, sin red)

Sobre el total de pendientes (no solo los clusters), clasificá con regex estas tres categorías de ruido — son las que más volumen generan:

- **No-Argentina**: título o snippet menciona un país extranjero (Estados Unidos, España, Brasil, Chile, México, Uruguay, Paraguay, etc.) y NO menciona Argentina/una provincia/ciudad argentina. Cuidado con falsos positivos: instituciones con nombre de país en el nombre propio (Hospital Italiano, Banco Francés) o menciones de pasada (una empresa argentina con un socio/dueño de otra nacionalidad, ej. Bioceres con "el uruguayo Juan Sartori").
- **Sector público no estatal**: ministerios, hospitales públicos, universidades nacionales, organismos como CONICET/INTA/PAMI/ANSES/SMN. Regla de alcance ya acordada con el usuario: **se excluye toda la administración pública, salvo empresas de propiedad estatal con estructura de empresa** (Aerolíneas Argentinas, YPF, Banco Nación, AySA, ARSAT, Correo Argentino, entidades binacionales tipo EBY/Yacyretá o Caminos del Río Uruguay si afectan trabajadores del lado argentino). Ante la duda de si algo es "empresa estatal" o "administración pública", dejalo pendiente y preguntale al usuario en el reporte final en vez de decidir en silencio.
- **"Quiebra"/"despido" en sentido no empresarial**: contiene la palabra pero sin ningún marcador de negocio (empresa, planta, trabajador, concurso preventivo, cheque, sindicato, etc.) — típicamente modismo emocional ("se quiebra en vivo llorando"), deportivo (un club de fútbol, un récord), o de una persona particular sin relación laboral.

Con volumen alto (varios cientos de candidatos), delegá la revisión de falsos positivos a un fork: pasale las listas título+medio generadas por la regex y pedile que separe verdaderos positivos (descartar) de rescates (dejar pendiente, con motivo). La regex sola comete errores sistemáticos (nombres propios con substrings de países, snippets ambiguos) — no la apliques en bruto sin ese repaso.

## 3. Para cada cluster/historia real: buscar la mejor fuente y publicar

Con los clusters del paso 1 (o los rescates del paso 2) ya limpios de ruido, para cada historia distinta:

1. **Mirá qué hay ya scrapeado.** El campo `snippet` de un item scrapeado vía Google News RSS suele ser basura (`<a href="...">` vacío, sin texto real) — necesitás **WebFetch al `url` real** para sacar el contenido. Si el `url` es un redirect de `news.google.com/rss/articles/...`, primero intentá resolverlo con WebFetch igual; si no da texto útil, buscá el artículo real con WebSearch (título exacto + medio).
2. **Elegí la mejor fuente entre los candidatos.** Aplicá la jerarquía de `reescribir-titular` (nacional de peso > diario local principal > TV/radio local). Si ninguno de los ya scrapeados alcanza, o para verificar que no exista una cobertura mejor o más reciente, hacé WebSearch — no te limites a lo que el scraper ya trajo.
3. **Antes de escribir, filtrá si la historia encaja en el alcance del tracker:**
   - Empresa argentina (privada o estatal) con un hecho concreto: despido, cierre, quiebra, concurso preventivo, suspensión. Sí encaja.
   - **Final positivo** (la empresa evitó la quiebra, fue rescatada, salió del concurso, un pedido de quiebra fue rechazado): normalmente NO encaja como entrada nueva — el tracker es de despidos/cierres, no de buenas noticias — salvo que sea el cierre del círculo de una historia que el tracker ya viene cubriendo (ver regla del paso 6 de `reescribir-titular` sobre reaperturas).
   - **Empresa extranjera con "presencia en Argentina"** pero la nota es sobre la quiebra en el exterior sin cierre/despido local confirmado (ej. una marca que se declara en quiebra en EEUU y el título argentino solo especula "¿qué pasará acá?"): normalmente NO encaja, salvo que confirmes con WebSearch que hay una operación/filial argentina con despidos o cierre concretos (ahí sí, como PDVSA Argentina o Avianca Argentina).
   - **Fraude al consumidor o estafa sin despidos**: no encaja aunque use la palabra "quiebra".
4. **Escribí la entrada** siguiendo el paso 3 de `reescribir-titular` (título, bajada, moneda en letras, sector, geo). El sector tiene que ser uno de los que ya usa `data/curated_data.json` — a la fecha de este skill: Metalúrgica, Textil, Alimenticia, Calzado, Papel, Química, Agro, Transporte, Comercio, Electrodomésticos, Electrónica, Automotriz, Ecommerce, Construcción, Medios, Seguros, Salud, Minería, Energía, Aeronáutica, Gastronomía, Entretenimiento, Otros. Si aparece un rubro nuevo que no encaja bien en ninguno, proponele al usuario sumar una categoría (como pasó con Salud/Ecommerce/Energía/Electrodomésticos) en vez de forzarlo en "Otros" — y si la agrega, sumala también al array `SECTORES` de `admin/index.html` y a esta lista.
5. **Insertá la entrada** en `data/curated_data.json` con el mismo schema que las demás (`id`, `title`, `medio`, `lugar`, `provincia`, `departamento`, `sector`, `topic`, `snippet`, `url`, `date`, `scraped_at`, `status_at`, `manual: true`). Para el `id`, formato `manual-` + timestamp/hash corto + sufijo random (no importa la forma exacta, solo que sea único). El campo `date` es la fecha real del hecho (no la fecha en la que vos armaste la entrada); `scraped_at`/`status_at` sí van con la fecha/hora actual.
6. **Descartá todos los ids del cluster** en `data/raw_data.json` (el que usaste como fuente y los duplicados) con el script `scripts/set_status.py` que acompaña a este skill:
   ```
   python despidos-tracker/.claude/skills/depurar-pendientes/set_status.py <id1,id2,...|archivo.txt> descartado
   ```
   Actualiza `status` y `status_at` in-place, sin tocar nada más. Podés pasar una lista separada por comas o un archivo con un id por línea.

## 4. Priorizá piezas de contexto sectorial genérico

Además de historias de una empresa puntual, el usuario valora piezas de "contexto" — encuestas, estadísticas o notas tipo "mapa de crisis" sin una sola empresa protagonista (ver paso 8 de `reescribir-titular` para el formato). Si en el clustering aparece algo así ("colapso de la industria textil", "el campo argentino al borde de la quiebra", "las ART al borde del colapso", "de Garbarino a FATE: el mapa de quiebras..."), dale prioridad — es exactamente el tipo de historia que completa el panorama del tracker más allá del caso por caso. Sector queda vacío en estos casos.

## 5. Trabajar en lotes con forks

Con backlogs grandes (cientos de pendientes), no proceses todo en el hilo principal — se llena de ruido de búsquedas web que no hace falta conservar. Patrón que funcionó:

1. Un fork para el paso 2 (clasificar ruido, separar falsos positivos) — devuelve un JSON con `descartar` (ids confirmados) y `falsos_positivos` (ids + motivo de por qué no son ruido).
2. Aplicá vos mismo el `descartar` del paso anterior con `set_status.py` (mecánico, no hace falta un fork para esto).
3. Uno o más forks para el paso 3 (agrupar, buscar fuente, publicar) sobre los `falsos_positivos`/clusters restantes — dividí en lotes de ~10-20 historias por fork si son muchas, dándole a cada fork la lista completa de ids+títulos y las reglas de alcance de este documento.
4. **Nunca corras dos forks en paralelo que escriban `curated_data.json`/`raw_data.json` al mismo tiempo** — no son un worktree aislado, comparten el directorio de trabajo, y escrituras concurrentes pueden pisarse. Lanzalos secuenciales, o si necesitás paralelismo real, con `isolation: "worktree"` y mergeá después.
5. Mientras un fork corre, no edites esos dos archivos vos mismo — esperá la notificación de finalización antes de tocarlos o de commitear.

## 6. Validar antes de commitear

Antes de cada commit (no solo al final del todo el trabajo):

```python
import json
c = json.load(open('despidos-tracker/data/curated_data.json', encoding='utf-8'))
r = json.load(open('despidos-tracker/data/raw_data.json', encoding='utf-8'))
assert len(c) == len(set(i['id'] for i in c)), "ids duplicados en curated"
assert not any('$' in (i.get('title','')+i.get('snippet','')) for i in c), "signo $ sin convertir a letras"
c_ids = {i['id'] for i in c}
r_pend = {i['id'] for i in r if i.get('status') == 'pendiente'}
assert not (c_ids & r_pend), "hay ids publicados que siguen figurando como pendiente"
print('OK —', len(c), 'publicadas,', len(r), 'en raw_data.json (no debería cambiar el total, solo el status)')
```

El total de `raw_data.json` **nunca debería bajar** — nunca se borra nada, solo cambia `status` de `pendiente` a `descartado`. Si el total cambió, algo se perdió y hay que investigar antes de commitear.

## 7. Commit y push

Un commit por lote/fork terminado (no uno gigante al final — más fácil de revisar y de revertir si algo salió mal). Mensaje descriptivo: cuántas entradas nuevas, cuántos ids descartados y por qué categoría. Repetí el chequeo de sync del paso 0 antes de cada push.
