# despidos-tracker

Tracker de noticias de despidos, suspensiones, cierres de planta y quiebras en Argentina. Arquitectura hermana de `retail-news-tracker`: scraping automatizado sin AI, curación manual antes de publicar, tablero público estático en GitHub Pages.

Vive como **subcarpeta dentro del repo de `mapa-empleo`** (no como repo separado), para facilitar la integración futura con el tablero de empleo.

## Estructura (dentro de `mapa-empleo/despidos-tracker/`)

```
config/
  sources_config.json      # 60 medios (nacional/sectorial/provincial), editable sin tocar código
  keywords_config.json     # keywords de tema + señales de ruido a excluir
  provincias_lookup.json   # diccionario provincia -> aliases/ciudades para geo-tagging
data/
  raw_data.json            # TODO lo scrapeado (interno, nunca público)
  curated_data.json        # solo lo publicado (esto lee el tablero público)
scripts/
  scraper.py                # --mode batch | --mode daily
  cleanup.py                 # purga semanal de raw no publicado +7 días
  utils.py
.github/workflows/
  despidos_batch.yml           # manual (workflow_dispatch)
  despidos_daily.yml           # cron 2x/día
  despidos_weekly_cleanup.yml  # cron domingos
index.html                   # tablero público (GitHub Pages)
admin/index.html             # panel de curación interno (noindex, no linkeado)
```

Los workflows tienen prefijo `despidos_` y el bot commitea como `despidos-tracker-bot` para no chocar con los workflows que ya tenga `mapa-empleo`.

## Setup inicial

1. Copiá toda la carpeta `despidos-tracker/` (con su `.github/workflows/` — esos tres archivos se mergean con los que ya tenga el repo, no los reemplazan) adentro del repo local de `mapa-empleo`, en la raíz.
2. `git add`, commit y push como harías con cualquier cambio en ese repo.
3. Como `mapa-empleo` ya tiene GitHub Pages activado, no hace falta configurar nada nuevo:
   - Tablero público: `https://<usuario>.github.io/mapa-empleo/despidos-tracker/`
   - Panel de curación: `https://<usuario>.github.io/mapa-empleo/despidos-tracker/admin/` (no lo linkees desde ningún lado público)
4. Instalá dependencias localmente si querés correr el scraper a mano:
   ```
   pip install -r despidos-tracker/scripts/requirements.txt
   ```

## Correr el batch inicial

Podés correrlo local o disparar el workflow manual desde GitHub Actions (tab "Actions" → "Despidos Tracker - Batch (manual)" → "Run workflow").

Local (desde la raíz del repo `mapa-empleo`):
```
cd despidos-tracker/scripts
python scraper.py --mode batch --since 2024-01-01
```

Esto scrapea:
- El RSS directo de cada medio en `sources_config.json` (lo que tengan disponible ahora)
- Google News RSS search, chunkeado mes a mes desde `--since` hasta hoy, con las queries de `TOPIC_QUERIES` en `scraper.py`

Es **idempotente**: si volvés a correrlo después de agregar una fuente nueva o cambiar keywords, hace merge por `id` (hash del link) sin duplicar ni pisar el estado (`pendiente`/`descartado`/`publicado`) que ya tenga una noticia existente. Todo lo nuevo entra con `status: "pendiente"`.

## El diario

Corre solo via GitHub Actions (`daily.yml`, 2 veces al día). Scrapea la ventana de las últimas 48hs (RSS directo + Google News) y appendea solo lo nuevo a `raw_data.json`.

## La limpieza semanal

`weekly_cleanup.yml` corre los domingos y borra de `raw_data.json` solo las **pendientes** (nunca revisadas) de más de 7 días. Las **descartadas** se conservan siempre — son reversibles a propósito. Lo publicado en `curated_data.json` nunca se toca.

## Modelo de estados

Cada noticia scrapeada arranca en `status: "pendiente"`, dentro de `raw_data.json`. Desde ahí solo hay dos caminos, y los dos son reversibles:

- **Publicar** → sale de `raw_data.json` y entra a `curated_data.json` (lo que lee el tablero público). Reversible con "Unpublish" (vuelve a pendiente).
- **Descartar** → se queda en `raw_data.json` pero con `status: "descartado"`. No aparece en "Pendientes", pero podés ir a la pestaña "Descartadas" y revertir la decisión en cualquier momento — no se borra sola con la limpieza semanal.

## Panel de curación (`admin/index.html`)

1. Abrí `admin/index.html` en el navegador (local o vía GitHub Pages).
2. Ingresá tu usuario de GitHub, nombre del repo, y un **Personal Access Token fine-grained** con permiso `Contents: Read and write` scopeado solo a este repo (GitHub → Settings → Developer settings → Fine-grained tokens).
3. El token queda guardado en `localStorage` de tu navegador — nunca se manda a ningún lado más que a `api.github.com`. Podés revocarlo cuando quieras desde GitHub.
4. Tab "Pendientes": tildás noticias y elegís **Publish** (pasa al tablero público) o **Descartar** (se guarda aparte, no se borra).
5. Tab "Publicadas": **Unpublish** para dar de baja algo que se publicó por error (vuelve a pendiente).
6. Tab "Descartadas": **Revertir a pendiente** para reconsiderar algo que descartaste.
7. El tablero público (`index.html`) lee `curated_data.json` — el cambio se refleja en ~30-60seg (tiempo de build de Pages).

## Curación editorial (skills de Claude Code)

Además del panel admin, hay tres skills en `.claude/skills/` que automatizan el trabajo editorial:

- **`depurar-pendientes`**: pasa completo sobre el backlog de `raw_data.json` — descarta ruido (no-Argentina, sector público no estatal, "quiebra" en sentido no empresarial), agrupa duplicados entre medios, y publica una entrada prolija por historia real con la mejor fuente disponible.
- **`reescribir-titular`**: dado un link puntual, reescribe título y bajada en tono de diario serio (sujeto + acción + dato, sin clickbait), y define la jerarquía de fuentes que usan también los otros dos skills (medio nacional de peso → diario papel principal de la zona → TV/radio local), moneda siempre en letras, atribución de causas, geo y sector.
- **`auditar-fuentes`**: revisa entradas **ya publicadas** en `curated_data.json` para detectar si existe una fuente mejor o más completa del mismo hecho (no agrega etapas nuevas de una historia — eso es trabajo de los otros dos skills). Incluye `list_medios.py` para priorizar qué auditar según qué medios aparecen más y con qué jerarquía.

La lógica del tracker es de **línea de tiempo, no de perfil de empresa**: cuando una empresa tiene varias etapas reales (suspensión → despidos → cierre → quiebra), cada etapa es su propia entrada — eso es la cronología funcionando bien, no duplicación. `auditar-fuentes` solo reemplaza una entrada cuando es el mismo hecho con mejor fuente, o cuando aparece el desenlace de una historia que el tracker ya venía cubriendo (ver ejemplo del Hospital Español de Temperley, ago. 2026).

## Sectores (taxonomía propia)

`config/keywords_config.json` → `sector_keywords` define una taxonomía propia del tracker (no la de `mapa-empleo`, demasiado genérica para este dominio), armada de abajo hacia arriba a partir de los rubros que fueron apareciendo publicados: Metalúrgica, Textil, Alimenticia, Calzado, Papel, Química, Agro, Transporte, Comercio, Electrodomésticos, Ecommerce, Construcción, Medios, Seguros, Salud, Minería, Energía, Aeronáutica, Gastronomía, Entretenimiento, y "Otros" como catch-all sin keywords propias (a la fecha, agosto 2026). Se va ampliando a mano — si aparece un rubro nuevo, se propone como categoría en vez de forzarlo en "Otros" (así se sumaron Salud, Ecommerce, Energía y Electrodomésticos).

## Filtro geográfico y conexión con `mapa-empleo`

El geo-tagging actual (`provincias_lookup.json`) es a nivel provincia por keyword matching sobre título+bajada, con fallback a la provincia/localidad propia de la fuente si es un medio provincial. El nivel de **departamento** hoy es aproximado (usa el campo `departamento` de cada fuente como proxy).

Pendiente de integración: reemplazar `provincias_lookup.json` por el mismo lookup geográfico (geojson/tabla INDEC) que ya usa `FUranga/mapa-empleo`, para que ambos tableros compartan taxonomía exacta y se pueda linkear por query param (`?provincia=Santa+Fe`) entre uno y otro, o embeber la sección de noticias como panel integrado en la página de `mapa-empleo` (fetch cross-repo del `curated_data.json` publicado acá).

## Agregar/sacar una fuente

Editá `config/sources_config.json` — agregá un objeto con `name`, `tier` (`nacional`/`sectorial`/`provincial`), `provincia`, `departamento`, `tipo`, `url`, `rss_url` (o `null` si no tiene), `paywall`, `active`. Si no tiene RSS propio, igual la va a cubrir el barrido de Google News mientras el nombre del medio aparezca en los resultados — no hace falta nada más.

## Ideas a futuro

### Línea de tiempo por empresa

Idea (planteada agosto 2026, sin desarrollar todavía): que cada noticia permita ver un resumen cronológico de la empresa involucrada — origen, hitos macro, conflictos anteriores, hasta el hecho más reciente — no solo la nota puntual. Siempre debería mostrar el estado más reciente de la empresa, sin importar si se entró desde una noticia vieja o nueva. Los hitos deberían salir, en lo posible, de la página oficial de la empresa y de las noticias ya curadas del tracker que mencionen el conflicto anterior; si no hay suficiente información, ir hacia atrás con lo que haya.

Es viable, pero el trabajo real no es la vista de línea de tiempo (eso es trivial una vez que los datos están bien modelados) — es resolver la identidad de "empresa" como entidad propia, que hoy no existe: `curated_data.json` es una lista plana de noticias sin un id que agrupe, por ejemplo, "Aires del Sur" + "Electra" + "Fedders" como la misma empresa. Haría falta:

- Un campo `empresa_id` (o similar) en cada entrada de `curated_data.json`, poblado a mano/con criterio editorial igual que `sector` hoy — matching automático de texto es riesgoso porque los nombres de marca varían demasiado (holding vs. marca comercial, razón social vs. nombre de fantasía).
- Un registro liviano de empresas (nombre canónico, alias, 2-3 líneas de origen/contexto), capturado una vez por empresa cuando aparece — no auto-generado en vivo scrapeando la página oficial de cada una en cada visita: es frágil (cada sitio corporativo tiene estructura distinta) y muchas empresas ni tienen una página con historia institucional.
- Backfillear las entradas ya publicadas con ese `empresa_id` (a agosto 2026, unas 98).

Con eso resuelto, la regla de "siempre mostrar lo más reciente" es directa: la vista se linkea por `empresa_id`, no por artículo puntual, y se ordena por fecha descendente — cualquier entrada de esa empresa lleva a la misma línea de tiempo actualizada.

## Pendientes / notas de la investigación de fuentes

- Varios medios provinciales quedaron con `rss_url: null` (no se pudo confirmar el feed) — se cubren vía Google News por ahora. Ir probando patrones `/feed/` (WordPress) o `/arc/outboundfeeds/rss/?outputType=xml` (Arc XP, grupo Clarín) a mano y actualizando el config.
- Radio Continental: activa pero con fragilidad financiera reportada (venta feb 2025, atrasos salariales) — revisar periódicamente si sigue operativa.
- "El Chaqueño" (Chaco) no se pudo verificar como medio distinto — están en su lugar Diario Norte y alternativas (DataChaco, Diario Chaco) por confirmar.
- Los paywalls "soft" limitan el scraping de cuerpo completo — el scraper solo toma título + bajada del RSS, nunca intenta bypassear el paywall.
