# -*- coding: utf-8 -*-
"""Uso: python list_medios.py [--min-count N]

Lista los medios usados en despidos-tracker/data/curated_data.json,
ordenados por cantidad de apariciones descendente, para ayudar a elegir
que entradas priorizar en una auditoria de fuentes (skill auditar-fuentes).
No modifica nada. Correr desde la raiz del repo (mapa-empleo/).
"""
import json
import sys
from collections import Counter

CURATED_PATH = 'despidos-tracker/data/curated_data.json'


def main():
    min_count = 1
    if '--min-count' in sys.argv:
        idx = sys.argv.index('--min-count')
        min_count = int(sys.argv[idx + 1])

    with open(CURATED_PATH, encoding='utf-8') as f:
        curated = json.load(f)

    counts = Counter(i.get('medio') or '(sin medio)' for i in curated)
    by_medio = {}
    for i in curated:
        medio = i.get('medio') or '(sin medio)'
        by_medio.setdefault(medio, []).append(i)

    print(f'{len(curated)} entradas publicadas, {len(counts)} medios distintos\n')
    for medio, count in counts.most_common():
        if count < min_count:
            continue
        print(f'{count:3d}  {medio}')
        for item in by_medio[medio][:3]:
            print(f'       - {item.get("title","")[:90]}  [{item.get("id")}]')
        if count > 3:
            print(f'       ... y {count - 3} mas')


if __name__ == '__main__':
    main()
