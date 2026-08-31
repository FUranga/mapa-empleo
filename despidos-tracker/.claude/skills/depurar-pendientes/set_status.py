# -*- coding: utf-8 -*-
"""Uso: python set_status.py <ids_separados_por_coma_o_archivo.txt> <descartado|pendiente>

Marca items de despidos-tracker/data/raw_data.json con el status dado,
actualizando status_at al momento actual (UTC ISO). Correr desde la raiz
del repo (mapa-empleo/), no borra nada, solo cambia el campo status.

Ids: lista separada por coma, o un archivo .txt con un id por linea,
o un archivo .json (lista simple, o dict cuyos values son listas de ids
-- se juntan todas las listas del dict).
"""
import json
import sys
from datetime import datetime, timezone

RAW_PATH = 'despidos-tracker/data/raw_data.json'


def load_ids(arg):
    if arg.endswith('.txt'):
        with open(arg, encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    if arg.endswith('.json'):
        with open(arg, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(data)
        if isinstance(data, dict):
            ids = set()
            for v in data.values():
                if isinstance(v, list):
                    ids.update(v)
            return ids
        raise ValueError('formato de json no reconocido')
    return set(arg.split(','))


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    ids_arg, new_status = sys.argv[1], sys.argv[2]
    ids = load_ids(ids_arg)
    print(f'ids a actualizar: {len(ids)} -> status={new_status}')

    with open(RAW_PATH, encoding='utf-8') as f:
        raw = json.load(f)

    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    updated = 0
    not_found = set(ids)
    for item in raw:
        if item['id'] in ids:
            item['status'] = new_status
            item['status_at'] = now
            updated += 1
            not_found.discard(item['id'])

    print(f'actualizados: {updated}')
    if not_found:
        print(f'NO encontrados ({len(not_found)}):', list(not_found)[:10])

    with open(RAW_PATH, 'w', encoding='utf-8') as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
        f.write('\n')


if __name__ == '__main__':
    main()
