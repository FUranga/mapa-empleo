"""
actualizar.py
Corre en GitHub Actions. Verifica si hay datos nuevos en SRT y OEDE,
los baja, regenera los JSONs y los guarda en el repo.
"""

import requests
import openpyxl
import json
import os
import sys
from datetime import datetime
from io import BytesIO

# ── URLs de las fuentes ───────────────────────────────────────────
URL_SRT_JURISDICCION = (
    'https://www.srt.gob.ar/estadisticas/series/co/up/'
    'Serie_historica_Segun_Jurisdiccion - Ubicacion Persona Trabajadora - UP.xlsx'
)
URL_SRT_SECTOR = (
    'https://www.srt.gob.ar/estadisticas/series/co/up/'
    'Serie_historica_Segun_Sector_de_actividad_economica_CIIUrev4 - UP.xlsx'
)

# OEDE publica en una URL fija que sobreescribe con cada actualización
# Verificar esta URL con cada publicación nueva
URL_OEDE = (
    'https://www.trabajo.gob.ar/downloads/estadisticas/'
    'observatorio/series/cuadros_empleo_privado.xlsx'
)

LOG_PATH    = 'log.json'
EMP_PATH    = 'data.json'
EMP_PATH_E  = 'empresas.json'

# ── Logging ───────────────────────────────────────────────────────
def load_log():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            return json.load(f)
    return {}

def save_log(log):
    with open(LOG_PATH, 'w') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def get_last_modified(url):
    """HEAD request para ver fecha de modificación del archivo remoto."""
    try:
        r = requests.head(url, timeout=20, allow_redirects=True)
        return r.headers.get('Last-Modified') or r.headers.get('ETag') or ''
    except Exception as e:
        print(f'  ⚠ No se pudo verificar {url}: {e}')
        return None

def download(url):
    """Descarga un archivo y devuelve sus bytes."""
    print(f'  Descargando: {url[:80]}...')
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return r.content

# ── Generador de empresas.json ────────────────────────────────────
def build_empresas(bytes_juris, bytes_sector):
    from datetime import datetime as dt

    def pct(base, curr):
        if base and base > 0:
            return round((curr - base) / base * 100, 1)
        return None

    # Jurisdicción
    wb_j = openpyxl.load_workbook(BytesIO(bytes_juris), data_only=True)
    ws_j = wb_j['Cuadro 6.2']
    rows_j = list(ws_j.iter_rows(values_only=True))
    header = rows_j[4]
    periodos = [v.strftime('%Y-%m') for v in header[1:] if isinstance(v, dt)]

    SKIP = {'Sin datos', None,
        'Parte empleadora afiliada de unidades productivas con personas trabajadoras declaradas *',
        'Parte empleadora afiliada y aportante de casas particulares con personas trabajadoras declaradas **',
        'Parte empleadora afiliada de casas particulares con personas trabajadoras declaradas ***'}

    prov_data = {}
    for row in rows_j[5:]:
        nombre = row[0]
        if not isinstance(nombre, str) or nombre in SKIP: continue
        if nombre.startswith('Debido') or nombre.startswith('*') or nombre.startswith('Fuente'): continue
        vals = row[1:len(periodos)+1]
        if not any(isinstance(v, (int, float)) for v in vals): continue
        prov_data[nombre] = {periodos[i]: int(v) for i, v in enumerate(vals) if isinstance(v, (int, float))}

    # Sectores
    wb_s = openpyxl.load_workbook(BytesIO(bytes_sector), data_only=True)
    ws_s = wb_s['Cuadro 2.2']
    rows_s = list(ws_s.iter_rows(values_only=True))
    header_s = rows_s[4]
    periodos_s = [v.strftime('%Y-%m') for v in header_s[1:] if isinstance(v, dt)]

    SKIP_SEC = {
        'Parte empleadora afiliada de unidades productivas con personas trabajadoras declaradas  (1) *',
        'Parte empleadora afiliada y aportante de casas particulares con personas trabajadoras declaradas (2) **',
        'Parte empleadora afiliada de casas particulares con personas trabajadoras declaradas (3)***',
        'Parte empleadora afiliada con personas trabajadoras declaradas = (1) + (3)',
        'Total parte empleadora afiliada del sistema****', 'Sin datos',
    }

    SECTOR_CORTO = {
        'Agricultura, ganaderia, caza, silvicultura y pesca': 'Agro y pesca',
        'Explotacion de minas y canteras': 'Minería',
        'Industria manufacturera': 'Industria',
        'Suministro de electricidad, gas, vapor y aire acondicionado': 'Energía eléctrica',
        'Suministro de agua, cloacas, gestion de residuos y recuperacion de materiales y saneamiento publico': 'Agua y saneamiento',
        'Construccion': 'Construcción',
        'Comercio al por mayor y al por menor; reparacion de vehiculos automotores y motocicletas': 'Comercio',
        'Servicio de transporte y almacenamiento': 'Transporte',
        'Servicios de alojamiento y servicios de comida': 'Alojamiento y gastronomía',
        'Informacion y comunicaciones': 'Info. y comunicaciones',
        'Intermediacion financiera y servicios de seguros': 'Finanzas y seguros',
        'Servicios inmobiliarios': 'Inmobiliario',
        'Servicios profesionales, cientificos y tecnicos': 'Servicios profesionales',
        'Actividades administrativas y servicios de apoyo': 'Serv. administrativos',
        'Administracion publica, defensa y seguridad social obligatoria': 'Administración pública',
        'Enseñanza': 'Enseñanza',
        'Salud humana y servicios sociales': 'Salud',
        'Servicios artisticos, culturales, deportivos y de esparcimiento': 'Arte y esparcimiento',
        'Servicios de asociaciones y servicios personales': 'Asoc. y serv. personales',
        'Servicios de organizaciones y organos extraterritoriales': 'Org. extraterritoriales',
    }

    sec_data = {}
    total_nac_s = {}
    for row in rows_s[5:]:
        nombre = row[0]
        if not isinstance(nombre, str) or nombre in SKIP_SEC: continue
        if nombre.startswith('*') or nombre.startswith('Un total') or nombre.startswith('Fuente'): continue
        # Total nacional
        if 'Parte empleadora afiliada de unidades productivas con personas trabajadoras declaradas  (1)' in nombre:
            for i, v in enumerate(row[1:len(periodos_s)+1]):
                if isinstance(v, (int, float)):
                    total_nac_s[periodos_s[i]] = int(v)
            continue
        vals = row[1:len(periodos_s)+1]
        if not any(isinstance(v, (int, float)) for v in vals): continue
        corto = SECTOR_CORTO.get(nombre, nombre)
        sec_data[corto] = {periodos_s[i]: int(v) for i, v in enumerate(vals) if isinstance(v, (int, float))}

    ULTIMO = periodos[-1]
    PRESIDENCIAS = {
        'Fernández': {'inicio': '2019-11', 'fin': '2023-11'},
        'Milei':     {'inicio': '2023-11', 'fin': ULTIMO},
    }

    serie_nac = [{'t': t, 'v': total_nac_s.get(t)} for t in periodos]
    sectores_list = [
        {'sector': nombre, 'serie': [{'t': t, 'v': serie.get(t)} for t in periodos_s]}
        for nombre, serie in sec_data.items()
    ]
    provincias_obj = {
        nombre: {'serie': [{'t': t, 'v': serie.get(t)} for t in periodos]}
        for nombre, serie in prov_data.items()
    }

    return {
        'meta': {
            'ultimo': ULTIMO,
            'periodos': periodos,
            'periodos_sec': periodos_s,
            'presidencias': PRESIDENCIAS,
            'fuente': 'SRT — Superintendencia de Riesgos del Trabajo',
            'actualizado': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        },
        'pais': {'serie': serie_nac, 'sectores': sectores_list},
        'provincias': provincias_obj,
    }

# ── Main ──────────────────────────────────────────────────────────
def main():
    log = load_log()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    updated = False

    print('=== Verificando SRT (empresas) ===')
    mod_juris  = get_last_modified(URL_SRT_JURISDICCION)
    mod_sector = get_last_modified(URL_SRT_SECTOR)
    srt_sig    = f'{mod_juris}|{mod_sector}'

    if srt_sig and srt_sig != log.get('srt_signature'):
        print('  ✓ Hay datos nuevos en SRT — descargando...')
        try:
            bytes_juris  = download(URL_SRT_JURISDICCION)
            bytes_sector = download(URL_SRT_SECTOR)
            print('  Construyendo empresas.json...')
            empresas = build_empresas(bytes_juris, bytes_sector)
            with open(EMP_PATH_E, 'w', encoding='utf-8') as f:
                json.dump(empresas, f, ensure_ascii=False, separators=(',', ':'))
            print(f'  ✓ empresas.json actualizado — último período: {empresas["meta"]["ultimo"]}')
            log['srt_signature'] = srt_sig
            log['srt_last_update'] = today
            updated = True
        except Exception as e:
            print(f'  ✗ Error en SRT: {e}')
    else:
        print(f'  Sin cambios en SRT (última actualización: {log.get("srt_last_update", "nunca")})')

    print('\n=== Verificando OEDE (empleo) ===')
    mod_oede = get_last_modified(URL_OEDE)

    if mod_oede and mod_oede != log.get('oede_signature'):
        print('  ✓ Hay datos nuevos en OEDE — descargando...')
        try:
            bytes_oede = download(URL_OEDE)
            # Por ahora lo guardamos para procesamiento manual
            # TODO: integrar el generador completo de data.json
            with open('oede_nuevo.xlsx', 'wb') as f:
                f.write(bytes_oede)
            print('  ⚠ OEDE tiene datos nuevos — procesar manualmente por ahora')
            print('  (el generador completo de data.json se agrega en la próxima iteración)')
            log['oede_signature'] = mod_oede
            log['oede_last_detected'] = today
        except Exception as e:
            print(f'  ✗ Error en OEDE: {e}')
    else:
        print(f'  Sin cambios en OEDE (última detección: {log.get("oede_last_detected", "nunca")})')

    log['last_check'] = today
    save_log(log)

    if updated:
        print(f'\n✓ Datos actualizados el {today}')
    else:
        print(f'\n— Sin cambios el {today}')

if __name__ == '__main__':
    main()
