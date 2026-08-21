# Dashboard: Empleo y empresas en Argentina
**Visión Desarrollista** · [bespoke-zabaione-80649f.netlify.app](https://bespoke-zabaione-80649f.netlify.app)

Tablero interactivo de creación y destrucción de empleo privado registrado y empresas empleadoras en Argentina, con cobertura nacional, provincial y departamental, desglose sectorial y comparación entre las presidencias de Alberto Fernández y Javier Milei.

---

## Estructura del repositorio

```
mapa-empleo/
├── data.json                          # Datos de empleo (generado automáticamente)
├── empresas.json                      # Datos de empresas (generado automáticamente)
├── data.json.bak                      # Backup del deploy anterior
├── empresas.json.bak                  # Backup del deploy anterior
├── log.json                           # Log de firmas y fechas de última actualización
├── provincias.geojson                 # Geometrías provinciales (estático)
├── departamentos.geojson              # Geometrías departamentales (estático)
├── departamento_series_empleo_y_salarios_mensual_sector_1.csv  # Fuente departamental (actualización manual semestral)
├── scripts/
│   ├── actualizar.py                  # Script principal del workflow
│   └── generar_empleo.py             # Generador de data.json
└── .github/
    └── workflows/
        └── actualizar.yml            # GitHub Actions workflow
```

El dashboard (Netlify) sirve los archivos HTML/JS estáticos. Los JSONs de datos viven en este repo y se sirven desde `raw.githubusercontent.com`.

---

## Fuentes de datos

### Empleo (`data.json`)

El dashboard combina tres fuentes del Ministerio de Capital Humano de Argentina, cada una con distinto nivel de detalle y frecuencia de actualización:

#### 1. Informe mensual SIPA
**URL de descarga:** scrapeada dinámicamente desde  
`https://www.argentina.gob.ar/trabajo/estadisticas/situacion-y-evolucion-del-trabajo-registrado`

El archivo se llama `trabajoregistrado_AAMM_estadisticas.xlsx` (ej. `trabajoregistrado_2605_estadisticas.xlsx` para mayo 2026). La URL cambia cada mes con el período publicado, por lo que el workflow scrapea la página para encontrar el link actual.

Se usan cuatro hojas del archivo:

| Hoja | Contenido | Unidad |
|------|-----------|--------|
| A.2.1 | Empleo por sector de actividad — con estacionalidad | Miles de personas |
| A.2.2 | Empleo por sector de actividad — desestacionalizado | Miles de personas |
| A.5.1 | Empleo por provincia — con estacionalidad | Miles de personas |
| A.5.2 | Empleo por provincia — desestacionalizado | Miles de personas |

Los valores se multiplican por 1.000 al procesar para expresarlos en puestos individuales. Los datos cubren desde enero 2009 y se actualizan mensualmente.

**Qué alimenta en el dashboard:**
- Total nacional (original y desestacionalizado)
- Sectores nacionales: 7 macrosectores + 14 ramas finas (original y desestacionalizado)
- Total por provincia (original y desestacionalizado)

#### 2. CSV departamental OEDE
**URL:** `https://www.argentina.gob.ar/sites/default/files/departamento_series_empleo_y_salarios_mensual_sector_1.csv`

Serie mensual de empleo asalariado registrado privado por departamento, con desglose sectorial. Cubre aproximadamente 485 de los ~525 departamentos del país. Se actualiza semestralmente.

**Importante:** el servidor del gobierno bloquea la descarga automática de este archivo (HTTP 403). Por eso se almacena en este repositorio y el workflow lo lee desde GitHub.

**Qué alimenta en el dashboard:**
- Total y sectores por departamento
- Sectores por provincia *(ver nota metodológica abajo)*
- Subdivisión de Buenos Aires en GBA (40 municipios) y Resto de la provincia

#### 3. Series OEDE provinciales trimestrales *(no implementado aún — ver mejoras pendientes)*
**URL:** `https://www.argentina.gob.ar/sites/default/files/provinciales_serie_empleo_trimestral_2dig_6.xlsx`

Serie trimestral de empleo por provincia y sector a 2 dígitos CIIU. La URL tiene un sufijo numérico que cambia con cada publicación.

---

### Empresas (`empresas.json`)

**Fuente:** Superintendencia de Riesgos del Trabajo (SRT)

Dos archivos descargados directamente desde el servidor de la SRT:

| Archivo | Contenido |
|---------|-----------|
| `Serie_historica_Segun_Jurisdiccion - Ubicacion Persona Trabajadora - UP.xlsx` | Parte empleadora asegurada por provincia — Cuadro 6.2 |
| `Serie_historica_Segun_Sector_de_actividad_economica_CIIUrev4 - UP.xlsx` | Parte empleadora asegurada por sector CIIU Rev.4 — Cuadro 2.2 |

El total nacional se toma del Cuadro 2.2 (fila de total del archivo de sectores), no de la suma de provincias. Esto es equivalente a la metodología utilizada por Fundar en su Monitor Mensual de Empresas. La suma de provincias sobrecontabiliza porque una misma empresa puede operar en varias jurisdicciones.

**Baseline:** noviembre 2023 (último mes antes de la asunción de Milei), equivalente a la metodología de Fundar.

---

## Nota metodológica: sectores por provincia

Los sectores que se muestran al hacer clic en una provincia **se calculan sumando los departamentos** que pertenecen a esa provincia en el CSV departamental.

Esta aproximación tiene dos limitaciones conocidas:

1. **Cobertura incompleta:** el CSV departamental cubre ~485 de los ~525 departamentos. Los departamentos no cubiertos no se incluyen en la suma, lo que puede subestimar ligeramente el total sectorial provincial.

2. **Desactualización relativa:** el CSV departamental se actualiza semestralmente, mientras que los totales provinciales se actualizan mensualmente desde el SIPA. Esto significa que los sectores provinciales pueden tener un corte temporal anterior al total provincial.

### Alternativa disponible (mejora pendiente)

El OEDE publica una serie trimestral específicamente por provincia y sector (`provinciales_serie_empleo_trimestral_2dig_6.xlsx`) que sería más precisa para los sectores provinciales. Sin embargo, esta fuente presenta una dificultad para el baseline utilizado (noviembre 2023): al ser trimestral, el período más cercano es Q4-2023 (octubre-diciembre), no noviembre exacto.

Una potencial mejora futura sería usar el archivo provincial trimestral para los sectores provinciales, usando Q4-2023 como baseline para el período Milei y Q4-2019 para el período Fernández. Esto requeriría adaptar el generador para manejar los dos cortes temporales distintos (mensual para el total, trimestral para los sectores).

---

## Automatización

### GitHub Actions workflow

El workflow corre **todos los días a las 9am (hora Argentina)** y además se dispara automáticamente cuando se sube el CSV departamental al repo.

```
Cron diario (9am AR)
    │
    ├─ Verifica SRT (empresas)
    │   └─ Si cambió → regenera empresas.json → commit → mail
    │
    ├─ Verifica SIPA (empleo)
    │   └─ Si cambió → descarga → regenera data.json → commit → mail
    │
    └─ Verifica CSV departamental en servidor OEDE
        └─ Si cambió → mail de aviso (actualización manual requerida)

Push de CSV departamental al repo
    └─ Dispara workflow → regenera data.json → commit → mail
```

### Tipos de notificación por mail

**Mail automático** (`franciscocuranga@gmail.com`): cuando el workflow detecta y procesa datos nuevos del SIPA o la SRT. Incluye qué fuente se actualizó y links al repo y al dashboard.

**Mail de aviso manual**: cuando el OEDE actualiza el CSV departamental en su servidor. Indica que hay que bajar el nuevo archivo y subirlo manualmente al repo. Una vez subido, el workflow se dispara automáticamente.

### Proceso de actualización manual del CSV departamental

Cuando recibís el mail de aviso:

1. Bajá el nuevo CSV desde:  
   `https://www.argentina.gob.ar/trabajo/estadisticas/oede-estadisticas-provinciales`
2. Subilo al repo como `departamento_series_empleo_y_salarios_mensual_sector_1.csv` (reemplazando el anterior)
3. El workflow se dispara automáticamente por el push
4. Recibís el mail de confirmación cuando termina

### Backup y recuperación

Antes de cada actualización el workflow guarda `data.json.bak` y `empresas.json.bak` en el repo.

Para volver a la versión anterior:
1. Abrí `data.json.bak` en GitHub
2. Copiá el contenido
3. Pegalo en `data.json` y hacé commit

Para ir más atrás, usá el historial de commits en `github.com/FUranga/mapa-empleo/commits/main`.

---

## Períodos y baselines

### Empleo

| Presidencia | Inicio | Fin |
|-------------|--------|-----|
| Alberto Fernández | dic 2019 | nov 2023 |
| Javier Milei | dic 2023 | último dato SIPA disponible |

### Empresas

| Presidencia | Baseline | Fin |
|-------------|----------|-----|
| Alberto Fernández | nov 2019 | nov 2023 |
| Javier Milei | nov 2023 | último dato SRT disponible |

El baseline de noviembre 2023 para empresas es equivalente al utilizado por Fundar en su Monitor Mensual de Empresas (último mes antes de la asunción de Milei).

---

## Embeds para historias

El notebook `generador_embeds.ipynb` (en Google Colab) genera 8 HTMLs autocontenidos con los datos del momento de publicación, listos para insertar en historias con `<iframe>`. Los datos van hardcodeados en el HTML — no se actualizan con el tiempo, lo que garantiza que una historia publicada hoy siempre muestre los mismos números.

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

- [ ] **Sectores provinciales desde fuente trimestral:** usar `provinciales_serie_empleo_trimestral_2dig_6.xlsx` en lugar de la suma del departamental, adaptando el baseline a Q4-2023.
- [ ] **Automatización completa del empleo:** el SIPA mensual ya se procesa automáticamente. El CSV departamental requiere intervención manual semestral.
- [ ] **Tracker de noticias:** sistema para traer noticias relevantes sobre empleo y empresas con curación manual antes de publicar.

---

## Fuentes

- **Empleo:** Observatorio de Empleo y Dinámica Empresarial (OEDE), Dirección Nacional de Estadísticas y Estudios Laborales, Secretaría de Trabajo, Empleo y Seguridad Social, Ministerio de Capital Humano, sobre la base del SIPA (ARCA).
- **Empresas:** Superintendencia de Riesgos del Trabajo (SRT). Metodología equivalente a la del Monitor Mensual de Empresas de Fundar.
