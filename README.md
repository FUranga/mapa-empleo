# Dashboard: Empleo y empresas en Argentina
**Visión Desarrollista** · [soft-cocada-6a8c87.netlify.app](https://soft-cocada-6a8c87.netlify.app)

Tablero interactivo de creación y destrucción de empleo privado registrado y empresas empleadoras en Argentina, con cobertura nacional, provincial, departamental y subregional (GBA / Resto de PBA), con desglose sectorial y comparación entre las presidencias de Alberto Fernández y Javier Milei.

---

## Estructura del repositorio

```
mapa-empleo/
├── data.json                          # Datos de empleo (generado automáticamente)
├── empresas.json                      # Datos de empresas (generado automáticamente)
├── data.json.bak / empresas.json.bak  # Backups del deploy anterior
├── log.json                           # Firmas y fechas de última actualización
├── provincias.geojson                 # Geometrías provinciales (estático)
├── departamentos.geojson              # Geometrías departamentales (estático)
├── departamento_series_empleo_y_salarios_mensual_sector_1.csv   # CSV sectores por departamento
├── departamento_serie_empleo_remuneraciones_3.xlsx              # XLSX totales por departamento
├── provinciales_serie_empleo_trimestral_2dig_6.xlsx             # XLSX sectores provinciales trimestrales
├── scripts/
│   ├── actualizar.py                  # Script principal del workflow
│   └── generar_empleo.py              # Generador de data.json
└── .github/workflows/
    └── actualizar.yml                 # GitHub Actions workflow
```

El dashboard (Netlify) sirve los archivos HTML/JS estáticos. Los JSONs de datos viven en este repo y se sirven desde `raw.githubusercontent.com`.

---

## Fuentes de datos

### Empleo (`data.json`)

El dashboard combina cuatro fuentes, cada una con distinto nivel de detalle y frecuencia:

#### 1. Informe mensual SIPA
**URL:** scrapeada dinámicamente desde  
`https://www.argentina.gob.ar/trabajo/estadisticas/situacion-y-evolucion-del-trabajo-registrado`

Patrón de nombre: `trabajoregistrado_AAMM_estadisticas.xlsx` (ej. `trabajoregistrado_2605_estadisticas.xlsx`). La URL cambia cada mes — el workflow scrapea la página para encontrar el link actual y lo compara con el guardado en `log.json`.

| Hoja | Contenido | Unidad |
|------|-----------|--------|
| A.1  | Total nacional sector privado (original y desestacionalizado) | Miles |
| A.2.1 | Sectores nacionales — con estacionalidad | Miles |
| A.2.2 | Sectores nacionales — desestacionalizado | Miles |
| A.5.1 | Total por provincia — con estacionalidad | Miles |
| A.5.2 | Total por provincia — desestacionalizado | Miles |

Los valores se multiplican por 1.000 al procesar.

**Qué alimenta en el dashboard:**
- Total nacional (original y desestacionalizado)
- Sectores nacionales: 7 macrosectores + 14 ramas finas (original y desestacionalizado)
- Total por provincia (original y desestacionalizado)

#### 2. XLSX provincial trimestral OEDE
**Archivo en repo:** `provinciales_serie_empleo_trimestral_2dig_6.xlsx`  
**Fuente original:** `https://www.argentina.gob.ar/trabajo/estadisticas/oede-estadisticas-provinciales`

Una hoja por provincia/región con sectores a 2 dígitos CIIU y subramas. Incluye hojas separadas para `Partidos de GBA`, `Capital Federal` y `Resto de Buenos Aires`.

**Qué alimenta en el dashboard:**
- Sectores provinciales (7 macros) — baseline Q4-2023, último Q4 disponible
- Detalle de subramas por provincia
- Serie trimestral, delta y sectores de GBA y Resto de PBA

**Nota:** es trimestral — los gráficos de GBA/Resto muestran puntos trimestrales, no mensuales.

#### 3. XLSX totales departamentales OEDE
**Archivo en repo:** `departamento_serie_empleo_remuneraciones_3.xlsx`  
**Fuente original:** `https://www.argentina.gob.ar/trabajo/estadisticas/oede-estadisticas-provinciales`

12 hojas (T1-T6 empleo, T7-T12 remuneraciones), una por región, con totales de empleo por departamento en puestos reales (no en miles).

**Qué alimenta en el dashboard:**
- Total por departamento (serie y delta)
- Total de GBA y Resto de PBA (sumando departamentos correspondientes)

#### 4. CSV sectores departamentales OEDE
**Archivo en repo:** `departamento_series_empleo_y_salarios_mensual_sector_1.csv`  
**URL original:** bloqueada por el gobierno (HTTP 403 desde bots)

Tiene 7 sectores por departamento en puestos reales. La columna `Provincia` incluye filas para `40 MUNICIPIOS GBA` y `RESTO DE PBA` que se usan para los sectores de esas subregiones.

**Qué alimenta en el dashboard:**
- Sectores por departamento

---

### Empresas (`empresas.json`)

**Fuente:** Superintendencia de Riesgos del Trabajo (SRT)

| Archivo | Contenido |
|---------|-----------|
| `Serie_historica_Segun_Jurisdiccion - Ubicacion Persona Trabajadora - UP.xlsx` | Por provincia — Cuadro 6.2 |
| `Serie_historica_Segun_Sector_de_actividad_economica_CIIUrev4 - UP.xlsx` | Por sector CIIU Rev.4 — Cuadro 2.2 |

El total nacional viene del Cuadro 2.2 (fila 26), no de la suma de provincias. Metodología equivalente al Monitor Mensual de Empresas de Fundar.

---

## Mapa de fuentes por panel del dashboard

| Panel | Fuente | ¿Desestacionalizado? | Período |
|-------|--------|----------------------|---------|
| Total nacional — serie | SIPA mensual (A.1) | ✅ Sí | nov-2023 → último SIPA |
| Sectores nacionales (7 macro + 14 ramas) | SIPA mensual (A.2.1/A.2.2) | ✅ Sí | nov-2023 → último SIPA |
| Total provincial — serie | SIPA mensual (A.5.1/A.5.2) | ✅ Sí | nov-2023 → último SIPA |
| Sectores provinciales (7 macro + subramas) | OEDE trimestral | ❌ No | Q4-2023 → Q4 último disponible |
| GBA — serie | OEDE trimestral (fila TOTAL) | ❌ No | Q4-2023 → Q4 último disponible |
| GBA — sectores | OEDE trimestral | ❌ No | Q4-2023 → Q4 último disponible |
| Resto de PBA — serie | OEDE trimestral (fila TOTAL) | ❌ No | Q4-2023 → Q4 último disponible |
| Resto de PBA — sectores | OEDE trimestral | ❌ No | Q4-2023 → Q4 último disponible |
| Total departamental — serie | OEDE mensual (XLSX) | ❌ No | nov-2023 → último depto |
| Sectores departamentales | OEDE mensual (CSV) | ❌ No | nov-2023 → último depto |

---

## Automatización

### Cómo decide el workflow si hay datos nuevos

El workflow corre **todos los días a las 9am (hora Argentina)** y evalúa tres fuentes:

#### SRT (empresas)
Hace un `HEAD` request a las dos URLs estables de la SRT:
```
https://www.srt.gob.ar/estadisticas/series/co/up/Serie_historica_Segun_Jurisdiccion...xlsx
https://www.srt.gob.ar/estadisticas/series/co/up/Serie_historica_Segun_Sector_de...xlsx
```
Toma el header `Last-Modified` de cada respuesta. Si alguno cambió respecto al guardado en `log.json` → descarga los archivos y regenera `empresas.json`.

#### SIPA mensual (empleo)
Scrapea la página:
```
https://www.argentina.gob.ar/trabajo/estadisticas/situacion-y-evolucion-del-trabajo-registrado
```
Busca con regex el link al archivo `trabajoregistrado_AAMM_estadisticas.xlsx`. Si la URL es distinta a la guardada en `log.json` → descarga el archivo y regenera `data.json`.

#### CSV departamental OEDE
Hace un `HEAD` request a:
```
https://www.argentina.gob.ar/sites/default/files/departamento_series_empleo_y_salarios_mensual_sector_1.csv
```
Si el `Last-Modified` cambió → manda un **mail de aviso** (no descarga automáticamente porque el gobierno bloquea el acceso desde bots).

### Triggers adicionales

El workflow también se dispara automáticamente cuando se sube alguno de estos archivos al repo:
- `departamento_series_empleo_y_salarios_mensual_sector_1.csv`
- `departamento_serie_empleo_remuneraciones_3.xlsx`
- `provinciales_serie_empleo_trimestral_2dig_6.xlsx`

### Flujo completo

```
Cron diario (9am AR)
    │
    ├─ HEAD SRT (2 URLs) → Last-Modified cambió?
    │   └─ Sí → descarga XLSXs → regenera empresas.json → commit → mail
    │
    ├─ Scrapea página SIPA → URL del XLSX cambió?
    │   └─ Sí → descarga SIPA + lee CSV/XLSX del repo → regenera data.json → commit → mail
    │
    └─ HEAD CSV departamental → Last-Modified cambió?
        └─ Sí → mail de aviso (actualización manual requerida)

Push de archivo al repo
    └─ workflow_dispatch → regenera data.json → commit → mail
```

### Tipos de notificación

**Mail automático** — cuando se procesan datos nuevos. Indica qué fuente se actualizó y el último período.

**Mail de aviso manual** — cuando el OEDE actualiza el CSV departamental. Indica qué bajar y cómo subirlo al repo.

---

## Actualización manual de archivos OEDE

Los tres archivos OEDE se actualizan semestralmente. Cuando recibís el mail de aviso:

1. Bajá los archivos desde:  
   `https://www.argentina.gob.ar/trabajo/estadisticas/oede-estadisticas-provinciales`

2. Subílos al repo **con el mismo nombre** que ya tienen:
   - `departamento_series_empleo_y_salarios_mensual_sector_1.csv`
   - `departamento_serie_empleo_remuneraciones_3.xlsx`
   - `provinciales_serie_empleo_trimestral_2dig_6.xlsx`

3. El workflow se dispara automáticamente y regenera `data.json`.

**Atención:** si el gobierno cambia el nombre del archivo (ej. `_4.xlsx` en vez de `_3.xlsx`), hay que actualizar la referencia en `scripts/actualizar.py` y `scripts/actualizar.yml`.

---

## Backup y recuperación

Antes de cada actualización el workflow guarda `data.json.bak` y `empresas.json.bak`.

Para volver a la versión anterior:
1. Abrí `data.json.bak` en GitHub → copiá el contenido → pegalo en `data.json` → commit.

Para ir más atrás: `github.com/FUranga/mapa-empleo/commits/main`.

---

## Períodos y baselines

### Empleo

| Presidencia | Baseline | Fin |
|-------------|----------|-----|
| Alberto Fernández | nov-2019 | nov-2023 |
| Javier Milei | nov-2023 | último dato SIPA |

Para sectores provinciales (trimestral): Q4-2019 → Q4-2023 (Fernández) y Q4-2023 → Q4 último disponible (Milei).

### Empresas

| Presidencia | Baseline | Fin |
|-------------|----------|-----|
| Alberto Fernández | nov-2019 | nov-2023 |
| Javier Milei | nov-2023 | último dato SRT |

Metodología equivalente al Monitor Mensual de Empresas de Fundar.

---

## Nota metodológica: sectores provinciales

Los sectores provinciales vienen del **OEDE provincial trimestral** — fuente directa y precisa. Para GBA y Resto de PBA, los sectores también vienen del trimestral (hojas `Partidos de GBA` y `Resto de Buenos Aires`).

Los sectores departamentales son estimados por suma de las filas del CSV departamental.

**Una empresa puede operar en varias jurisdicciones**: la suma de empresas por provincia no coincide con el total nacional. El total nacional de empresas se toma de la fila de total del archivo de sectores SRT (Cuadro 2.2, fila 26).

**Los puestos de trabajo no equivalen a trabajadores**: una persona puede tener más de un empleo registrado y contaría múltiples veces. El SIPA registra relaciones laborales, no individuos únicos.

**Las empresas están localizadas donde declaran al personal**, no donde están constituidas legalmente.

---

## Embeds para historias

El notebook `generador_embeds.ipynb` (Google Colab) genera 8 HTMLs autocontenidos con los datos del momento de publicación. Los datos van hardcodeados — no se actualizan con el tiempo.

**Embeds disponibles:**
- `empleo_mapa.html` — mapa provincial de empleo
- `empleo_serie.html` — evolución nacional del empleo
- `empleo_ranking.html` — ranking de provincias por empleo
- `empleo_sectores.html` — variación por sector (empleo)
- `empresas_mapa.html` — mapa provincial de empresas
- `empresas_serie.html` — evolución nacional de empresas
- `empresas_ranking.html` — ranking de provincias por empresas
- `empresas_sectores.html` — variación por sector (empresas)

---

## Mejoras pendientes

- [ ] Automatización completa del CSV departamental (bloqueado por HTTP 403 del gobierno)
- [ ] Tracker de noticias sobre empleo y cierres de empresas
- [ ] Cuando el OEDE cambia el nombre del archivo trimestral provincial, actualizar manualmente la referencia en `actualizar.py`

---

## Fuentes

- **Empleo:** Observatorio de Empleo y Dinámica Empresarial (OEDE), sobre la base del SIPA (ARCA), Ministerio de Capital Humano.
- **Empresas:** Superintendencia de Riesgos del Trabajo (SRT). Metodología equivalente al Monitor Mensual de Empresas de Fundar.
