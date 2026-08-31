---
name: reescribir-titular
description: Reescribe título y bajada de una noticia de despidos/suspensiones/cierres/quiebras en Argentina en tono directo y noticioso (estilo La Nación, WSJ, NYT, FT), a partir de un link que pasa el usuario. Convierte titulares clickbait en titulares informativos que van directo al dato más importante. Avisa si la nota es de mala calidad, muy corta o le falta lo básico de una noticia, y en ese caso sugiere buscar otro medio que la haya cubierto en vez de forzar una reescritura. Usar cuando el usuario pasa uno o varios links de noticias y pide reescribir/mejorar el título y la bajada, o "sacarle el clickbait" a una nota, para el tracker de despidos y empleo.
---

# Reescribir titular y bajada

Contexto del proyecto: `despidos-tracker` es un tablero de noticias de despidos, suspensiones, cierres de planta y quiebras en Argentina (ver `README.md`). Las notas se scrapean automáticamente desde ~60 medios (`config/sources_config.json`) y muchos títulos de origen son puro clickbait ("la truculenta decisión que dejó a cientos en la calle") sin el dato concreto arriba. Este skill sirve para, dado el link de una noticia puntual, devolver un título y una bajada como los escribiría un diario serio — directo, con el hecho principal arriba, sin relleno emocional.

## Proceso

1. **Traer la nota.** Usar WebFetch sobre el link (o los links, si el usuario pasa varios — procesar cada uno independientemente y devolver un bloque de resultado por cada uno). Extraer: título original, bajada/copete original si existe, y el cuerpo disponible (puede ser solo el primer párrafo si hay paywall — ver README: "el scraper solo toma título + bajada del RSS, nunca intenta bypassear el paywall", así que a veces vas a tener poco para trabajar).
   - Si el link es un redirect de Google News (`news.google.com/rss/articles/...`), seguí el fetch igual; si no resuelve al artículo real y solo da metadata mínima, tratalo como información insuficiente en el filtro de calidad (paso 2), no como error. Síntoma típico de que no va a resolver nunca por WebFetch: un loop redirigiendo a `consent.google.com` una y otra vez (la página de consentimiento de cookies de Google, que no se puede pasar sin sesión). Ahí no sigas reintentando — pedile directamente al usuario el título de la nota o la URL real del medio.
   - **iProfesional (y sitios con el mismo problema) suele devolver "Content truncated due to length" aunque la nota exista** — sus páginas pesan >1,5MB de HTML (mucho ad-tech), y WebFetch no llega a extraer el cuerpo. No es que falte cobertura ahí — es una limitación técnica puntual de esa herramienta contra ese sitio. Cuando pase, no lo descartes como "sin datos": reconstruí el artículo cruzando 2-3 queries de WebSearch (nombre de la empresa + cifras/monto que ya conozcas del título) en vez de forzar el fetch de nuevo. Clarín y La Voz del Interior devuelven 403 directo (bloqueo de bot) — mismo tratamiento.
   - Cadena de origen: si un medio nota que la información viene de otro (ej. "Atribución: IProfesional" dentro de una nota de InfoGremiales o similar), buscá si el medio original la cubrió — suele tener más detalle y ser más citable. Esto pasa seguido con diarios hiperlocales que ni siquiera están en `config/sources_config.json` (ej. El Periódico de San Francisco, La Voz de San Justo, El Ciudadano de Rosario, elentrerios.com): son la fuente real detrás de coberturas más grandes (BAE Negocios, La Gaceta) que solo las reproducen citándolas. Buscalos activamente por nombre/dominio aunque no estén en el listado curado — si el usuario prefiere citar el original hiperlocal en vez del que lo reprodujo, es una elección legítima, avisale igual que no está en el listado.

2. **Filtro de calidad — antes de reescribir nada, evaluá si la nota tiene "lo básico":**
   - ¿Hay un hecho concreto identificable? (empresa/organismo + acción: despido, suspensión, cierre de planta, quiebra, concurso preventivo, retiro voluntario, etc.)
   - ¿Hay al menos un dato duro? (cantidad de personas afectadas, fecha, planta/ubicación, sector)
   - ¿Hay atribución o fuente? (comunicado de la empresa, gremio, gobierno, "trascendió", fuentes sindicales, etc. — algo más que la opinión del portal)
   - ¿El cuerpo tiene sustancia real, o es solo el título repetido en una oración vaga, o un párrafo especulativo sin ningún dato nuevo?

   Si la nota **falla dos o más** de estos puntos (o el fetch trajo tan poco texto que no se puede evaluar), **no fuerces una reescritura**. En su lugar:
   - Decí explícitamente cuál(es) de los puntos falla y por qué (ej: "no hay número de afectados ni fecha, es solo especulación sobre una posible crisis").
   - Sugerí buscar la misma noticia en otro medio. Usá WebSearch para buscar la empresa/hecho + "despidos" (o el tema que corresponda) y priorizá medios de `config/sources_config.json` (Infobae, Clarín, La Nación, El Cronista, iProfesional, El Economista, o el medio provincial de la zona si el hecho es local) que puedan tener más datos. Si encontrás una cobertura mejor, ofrecé reescribir a partir de esa en su lugar.

   **Jerarquía de fuentes (para elegir la mejor cobertura, no solo para el filtro de calidad)**: aplicá este orden de preferencia siempre que haya opciones:
   1. Un medio nacional de peso: La Nación, Clarín, Infobae, Perfil, elDiarioAR, Página/12, TN, o una agencia de noticias (Télam/NA, DIB, etc).
   2. Si el hecho es local y no hay cobertura nacional (o la nacional es floja), el diario papel principal de la zona — o el segundo/tercero si la ciudad tiene varios con peso (ej. Rosario o CABA) — antes que un portal digital sin trayectoria.
   3. Si tampoco hay diario de papel con la nota, el canal de TV o radio local principal.
   Esta jerarquía es una preferencia de calidad/alcance, no reemplaza el paso 5 (etapa más avanzada de la historia gana, aunque venga de un medio más abajo en esta lista).
   - **"Este medio SI O SI" solo cuando el hecho es realmente de esa zona.** Si el usuario pide fijar un medio local puntual (ej. "El Diario" de Paraná) como fuente obligada, confirmá primero que la noticia es efectivamente de esa localidad antes de aplicarlo — puede tratarse de un pedido hecho al pasar, sin haber visto todavía dónde ocurre el hecho. Si la empresa/planta está en otro lado (ej. Texilo es de Desvío Arijón, Santa Fe, no de Paraná/Entre Ríos), volvé a la jerarquía normal (nacional primero) en vez de forzar el medio local pedido.

   **Ojo con roundups/listados que reciclan hechos viejos como si fueran actuales**: una nota tipo "mapa de crisis de once empresas" puede mezclar, bajo el mismo paraguas temporal (ej. "se consolidó en 2026"), un hecho realmente reciente con otro de dos años atrás (pasó dos veces en un mismo roundup de Córdoba: la cifra de despidos de Mabe y de Weg que citaba como de 2026 eran en realidad de abril/mayo de 2024). Antes de reescribir a partir de un ítem de un roundup, buscá el hecho puntual por separado y confirmá la fecha real — no asumas que el marco temporal del roundup es correcto solo porque el título general lo sugiere.

   **Noticias positivas (reactivación/reapertura) fuera de contexto**: el tracker es de despidos/suspensiones/cierres/quiebras — una nota de que una empresa *reabre* o *reactiva* producción, sin relación con una historia que el tracker ya viene cubriendo, queda afuera de scope (no fuerces el título). Pero si es la reapertura de una planta cuya quiebra/cierre YA está cargada en el tracker (ej. La Suipachense reabre meses después de su quiebra), sí vale la pena sumarla como entrada propia — es el cierre del círculo de una historia que el lector ya vio, no una nota positiva aislada. En ese caso el `topic` se mantiene igual al de la historia original (ej. `cierres`), no hace falta inventar una categoría nueva para un caso puntual.

3. **Si pasa el filtro, reescribí título y bajada** en estilo de diario serio (La Nación / WSJ / NYT / FT):
   - **Título**: sujeto + acción + dato más importante, en ese orden. Formato: "[Empresa/organismo] [acción concreta] [cantidad/lugar/motivo si entra]". Voz activa, sin adjetivos calificativos ("escandaloso", "truculento", "devastador"), sin preguntas retóricas, sin mayúsculas de énfasis ni signos de exclamación. Si el cuerpo tiene un número exacto y el título original decía "cientos" o "decenas", usá el número exacto.
   - **Marca vs. razón social**: si la empresa opera con una marca comercial conocida por el público (ej. Rever Pass, Be Rebel) distinta de su razón social/holding legal (ej. IGT33 S.A.), el título va con la marca reconocible — es lo que el lector identifica. La razón social legal, si es relevante, va en la bajada. Si la empresa tiene varias marcas reconocibles sin que ninguna domine claramente sobre las otras (ej. una textil dueña de Zorba, Mercury y Mutz Sport), está bien nombrarlas todas en el título en vez de forzar una sola — la razón social igual queda en la bajada.
   - **Moneda siempre en letras, nunca con símbolos**: nunca "$" ni "u$s"/"US$" en título o bajada — siempre "millones de pesos", "millones de dólares", etc. ("$63.500 millones" → "63.500 millones de pesos"; "u$s350.000" → "350.000 dólares").
   - **Nada de frases de trámite o eufemismos institucionales**: evitá giros rebuscados como "recurre a esta figura judicial/legal", "en el marco de", "se vio en la necesidad de". Usá el verbo concreto: "pidió el concurso preventivo", no "recurrió a esta figura judicial".
   - **Atribución de causas**: cuando el motivo de una crisis (caída del consumo, competencia importada, etc.) viene de una explicación de la propia empresa y no de una verificación independiente, marcalo como tal ("la empresa atribuyó...", "según la compañía..."), no lo presentes como hecho objetivo.
   - **Bajada**: una o dos oraciones que agregan lo más relevante que no entró en el título (razón social si corresponde, cantidad de empleados, ubicación, causas atribuidas, próximos pasos como paritarias o negociación con el gremio). No repitas el título con otras palabras.
   - **No sobrecargar de números de trámite**: evitá acumular datos administrativos de bajo interés para el lector (número de juzgado, número de expediente/secretaría, nombre del juez) en la bajada — eso es dato de color/verificación, no lo que le importa a quien lee. Priorizá qué pasó y a cuánta gente afectó. Esos detalles administrativos pueden mencionarse solo si el usuario los pide explícitamente.
   - **Sujeto del título — y también de la bajada**: el título (y la primera oración de la bajada) arrancan con la empresa/organismo protagonista de la noticia, no con "la Justicia [ordenó/dispuso/abrió]..." ni "El Juzgado [Comercial/Civil] N°X decretó...". Aunque el hecho sea una decisión judicial, la empresa es el sujeto (ej: "Celulosa Argentina entró en concurso preventivo", no "La Justicia abrió el concurso de Celulosa Argentina"; "Deniro entró en quiebra", no "El Juzgado Nacional en lo Comercial N°27 decretó la quiebra de Deniro"). A nadie le importa qué juzgado fue — eso además choca con la regla de no sobrecargar de números de trámite de arriba.
   - **Nombres propios de personas**: evitá nombrar individuos (compradores, empresarios, jueces, funcionarios) en título y bajada salvo que la persona sea en sí misma el hecho noticioso central. Un dato como "vendida por 1 dólar" puede ir sin nombrar al comprador si el comprador no es el foco de la nota. Excepción 1: si el testimonio/cita de una persona puntual ES el ángulo de la nota (ej. un trabajador despedido que cuenta cómo se enteró), ahí sí nombrarla tiene sentido. Excepción 2 — ángulo institucional/político: si un medio grande cubrió la historia justamente por la identidad de alguien vinculado a la empresa (ej. despidos en una transportista donde el hijo de un dirigente gremial era delegado, cobrando además otros cargos rentados), el nombre es relevante aunque no sea el "hecho laboral" en sí — pero en el tracker el sujeto del título sigue siendo la empresa y el hecho concreto (despidos/cierre), y el nombre propio va como dato adicional en la bajada, salvo que el usuario pida explícitamente subirlo al título.
   - **Despidos amplios vs. una persona puntual**: cuando la nota mezcla una tanda de despidos con la salida de una figura conocida (ej. un conductor de radio, un gerente), el título va con el alcance del recorte ("Alpha Media despidió a al menos 7 trabajadores..."), no con el nombre de la persona ("Despidieron a Fulano de Radio X..."). El nombre y el rol de esa persona van en la bajada, como parte del detalle.
   - Si un dato clave (cantidad de personas, fecha, planta específica) no está disponible en la nota, no lo inventes — escribí el título con la información que sí hay y, si hace falta, señalá qué dato falta.

4. **Localización.** Si el usuario pide provincia/ubicación para geo-tagging, identificá la ciudad/localidad concreta de la noticia y mapeala a la provincia (para empresas multi-planta o holdings sin una sede única, usá "Nacional" en vez de forzar una provincia). Lo mismo aplica cuando una crisis puntual pega en plantas de la misma empresa repartidas en varias provincias a la vez (ej. Granja Tres Arroyos con conflictos simultáneos en Córdoba, Buenos Aires y Entre Ríos, o SanCor licitando plantas en Santa Fe y Córdoba juntas): ahí también "Nacional" describe mejor el alcance que forzar una sola provincia. Chequeá `config/provincias_lookup.json`: si la localidad no está en los aliases de esa provincia, avisá y ofrecé agregarla (no lo hagas sin avisar).

5. **Sector.** Asigná uno de los sectores fijos del tracker (definidos en `config/keywords_config.json` → `sector_keywords`, y ya usados en `data/curated_data.json`): Metalúrgica, Textil, Alimenticia, Calzado, Papel, Química, Agro, Transporte, Comercio, Electrodomésticos, Ecommerce, Construcción, Medios, Seguros, Salud, Minería, Energía, Aeronáutica, Gastronomía, Entretenimiento, Otros. Es una taxonomía propia del tracker (no la de mapa-empleo, que es demasiado genérica para este dominio), armada de abajo hacia arriba a partir de los rubros que ya aparecieron publicados.
   - Elegí el sector por la actividad concreta de la empresa o planta afectada, no por el rubro del holding controlante si es distinto (ej. Pampa Energía es una petrolera, pero la planta que cerró fabricaba caucho sintético — el sector es Química, no Minería).
   - **Electrodomésticos (fabricante) vs. Comercio (cadena que vende)**: una fábrica de heladeras/aires acondicionados/línea blanca es Electrodomésticos; una cadena minorista que vende electrodomésticos (Frávega, Megatone) es Comercio.
   - Si la nota es un roundup/estadística nacional sin empresa puntual (paso 8), dejá el sector vacío.
   - Si el rubro no encaja bien en ninguno de los 17 sectores concretos, usá "Otros" y avisale al usuario — si ese mismo rubro vuelve a aparecer en notas futuras, vale la pena proponer sumarlo como categoría nueva en `sector_keywords` en vez de seguir metiéndolo en "Otros".
   - **El campo es solo para el filtro — el texto tiene que nombrar el rubro en criollo.** Además de asignar el sector como dato aparte, el título o la bajada tienen que nombrar el tipo de negocio en lenguaje natural ("la metalúrgica Apholos", "la textil dueña de Zorba, Mercury y Mutz Sport", "la fabricante de maquinaria agrícola"), no solo mencionar la categoría abstracta — así una búsqueda de texto por "metalúrgica" o "textil" encuentra la nota aunque nadie filtre por sector.

6. **Si el usuario pasa varios links sobre lo que parece "la misma" noticia**, no asumas que son la misma cobertura del mismo hecho — primero fijate la fecha de publicación de cada uno. Puede tratarse de etapas distintas de una historia que se fue desarrollando (ej: cierre de planta → pedido de concurso preventivo → designación de interventor, meses después). Si son etapas distintas, decilo explícitamente y armá la cronología en vez de recomendar "la mejor fuente" como si compitieran por el mismo hecho.
   - **Aunque el usuario pase un solo link, buscá activamente si hay una etapa más reciente y completa antes de dar el título por cerrado** — sobre todo si la nota tiene baches típicos de una etapa temprana: "pedido de quiebra" sin declarar, "cheques rechazados" sin cifra de despidos, un monto de deuda que suena bajo para el tamaño de la empresa, o un "busca evitar" en vez de un hecho consumado. Una búsqueda rápida de `[empresa] + despidos/quiebra/concurso` con el rango de fecha ampliado suele encontrar una nota posterior con datos más duros (pasó con SanCor, el Aquarium, Metalfor, La Suipachense/ARSA y Le Blé — en los cinco casos la nota que el usuario tenía a mano no era la más avanzada). Si aparece una etapa posterior, avisá y proponé reemplazar en vez de sumar.

7. **Si dos fuentes se contradicen en un dato** (nombre de una persona, cifra, fecha), no seas tú quien lo resuelve en silencio eligiendo una versión y listo — señalá la discrepancia al usuario, decí cuál versión es la que aparece más consistentemente en el resto de la cobertura si eso ayuda a mostrar cuál pesa más, pero dejá la decisión final a criterio del usuario si no queda claro.

8. **Notas de contexto/estadísticas nacionales (no son un hecho de una empresa puntual).** A veces el link no es sobre una empresa sino sobre una encuesta, informe o estadística sectorial (ej. "el 67% de las empresas argentinas despidió personal", una encuesta de Bumeran; el crecimiento de concursos preventivos según la Cámara Comercial de CABA; cifras de La Bancaria sobre cierre de sucursales bancarias). Estas notas también tienen lugar en el tracker, pero no fuerces el formato "[Empresa] [acción]":
   - Título y bajada se anclan en el dato/porcentaje principal y quién lo midió (ej. "El 67% de las empresas argentinas despidió personal en el primer semestre de 2026, según Bumeran"), no en una empresa como sujeto.
   - Van sin geo-localización específica (Nacional), salvo que el estudio sea sobre una sola provincia/ciudad, y sin sector (paso 5) salvo que el estudio sea sobre un solo sector.
   - Mismo filtro de calidad del paso 2: tienen que traer una fuente/metodología identificable (quién hizo el estudio, con qué muestra) y cifras concretas, no una opinión genérica. Un reclamo sectorial sin hecho puntual y sin estudio detrás (ej. una federación empresaria quejándose en general de embargos fiscales, sin cifras propias) no pasa el filtro — avisale al usuario que no encaja como nota individual y dejale elegir si la quiere igual o la descarta.

9. **Formato de salida**, por cada link:
   ```
   [medio, si se identifica] — [link]

   Original:
   Título: ...
   Bajada: ...

   Propuesta:
   1. Título: ...
   2. Bajada: ...
   3. Localización: ...
   4. Sector: ...
   ```
   Si la nota no pasó el filtro de calidad, reemplazá el bloque "Propuesta" por una nota corta explicando qué falta y la sugerencia de medio alternativo (o el resultado de la búsqueda si ya la hiciste).

## Ejemplos de reescritura (dominio despidos/empleo)

- Clickbait: "El fin de una era: la decisión que sacude a cientos de familias" →
  Noticioso: "Garbarino cierra sus locales en Argentina tras declararse en quiebra"

- Clickbait: "Pánico en la planta: la automotriz que prepara un ajuste letal" →
  Noticioso: "Ford suspende a 500 empleados en su planta de General Pacheco"
  Bajada: "La medida rige por 30 días y afecta a la línea de producción de la Ranger, según confirmó el sindicato SMATA."

- Clickbait: "Tras 40 años, una histórica marca de ropa argentina quedó al borde de la quiebra: debe más de $7.000 millones" →
  Noticioso: "La dueña de Rever Pass entra en concurso con una deuda de 7.000 millones de pesos"
  Bajada: "La empresa de indumentaria IGT33, con 40 años en el mercado y más de 100 empleados, atribuyó el deterioro del negocio a la caída del consumo, el aumento de costos y la competencia de Shein y Temu."
  (Nota: el título usa la marca reconocible —Rever Pass—, no la razón social; IGT33 y el resto del detalle van en la bajada; las causas quedan atribuidas a la empresa, no afirmadas como hecho; la deuda va en letras, nunca con "$".)

- Varias marcas sin una dominante: "Textil argentina que atravesó el colapso de 2001 hoy está al borde de la quiebra" →
  Noticioso: "La textil dueña de Zorba, Mercury y Mutz Sport entró en concurso preventivo tras más de 120 años de historia"
  Bajada: "A. Mutz y Cía., con planta en San Martín, acumula pérdidas de más de 941 millones de pesos y cheques rechazados por 69,2 millones de pesos. La empresa, fundada en 1903, atribuyó la crisis a la inflación, la caída del consumo, el aumento de tarifas y las altas tasas de interés."
  (Nota: acá ninguna de las tres marcas tapa a las otras, así que las tres van en el título; la razón social igual aparece en la bajada.)

- Nota de contexto/estadística (no es una empresa puntual): "Despidos en alza: el 67% de las empresas argentinas redujo personal durante 2026" →
  Noticioso: "El 67% de las empresas argentinas despidió personal en el primer semestre de 2026, según Bumeran"
  Bajada: "La proporción subió del 44% registrado en 2025. La reducción de costos fue el motivo más citado (61%), seguido del desempeño insuficiente (37%) y el impacto económico general (30%). Un 35% de las empresas anticipa recortes adicionales para lo que resta del año."
  (Nota: "redujo personal" es un eufemismo — la propia encuesta lo llama "empresas con despidos"; sin geo-localización específica, va como Nacional; sin sector, porque no es de un solo rubro.)

- Sector + mención en criollo: "La UOM volvió a movilizar contra 52 despidos en la histórica metalúrgica Apholos" →
  Noticioso: "La metalúrgica Apholos despide a 52 trabajadores en su planta de Villa Devoto tras un conflicto de cuatro meses con la UOM"
  Bajada: "La empresa, fundada a principios del siglo XX y que llegó a emplear a cerca de 300 personas, tramitó las cesantías mediante un Procedimiento Preventivo de Crisis. El gremio denuncia que no garantiza el pago de las indemnizaciones y atribuye el ajuste a la apertura importadora y a una gestión deficiente de la compañía."
  Localización: Villa Devoto → CABA
  Sector: Metalúrgica
  (Nota: el título ya nombra el rubro concreto —"la metalúrgica Apholos"— además de asignar el campo Sector; así una búsqueda de texto por "metalúrgica" encuentra la nota aunque nadie use el filtro.)

No hace falta que el título sea corto a toda costa — que sea directo y completo importa más que la brevedad, pero evitá relleno.
