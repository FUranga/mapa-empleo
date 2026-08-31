# -*- coding: utf-8 -*-
"""Uso: python cluster_dupes.py

Agrupa los items "pendiente" de despidos-tracker/data/raw_data.json que
probablemente cubren la misma historia (fecha cercana +/- 2 dias, y
solapamiento de palabras del titulo). Correr desde la raiz del repo.

No escribe nada -- solo imprime los clusters encontrados (2+ items) para
revisar a mano cuales son duplicados reales de la misma historia y cuales
son coincidencias de vocabulario sin relacion.
"""
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

RAW_PATH = 'despidos-tracker/data/raw_data.json'

STOP = set("""de la el los las un una unos unas y en a por con para su sus que se al del
despidio despidieron despide entro entra cerro cierra quiebra concurso preventivo empleados
trabajadores tras mas su ano anos millones pesos dolares planta empresa nacion""".split())

JACCARD_THRESHOLD = 0.35
MIN_SHARED_TOKENS = 2
DATE_WINDOW_DAYS = 2


def norm_tokens(title):
    t = (title or '').lower()
    t = re.sub(r'[^a-záéíóúñü0-9\s]', ' ', t)
    return {w for w in t.split() if len(w) > 3 and w not in STOP}


def parse_date(d):
    try:
        return datetime.fromisoformat((d or '').replace('Z', '+00:00')).date()
    except Exception:
        return None


def main():
    with open(RAW_PATH, encoding='utf-8') as f:
        raw = json.load(f)
    pend = [i for i in raw if i.get('status') == 'pendiente']

    items = []
    for i in pend:
        items.append({
            'id': i['id'], 'title': i.get('title'), 'medio': i.get('medio'),
            'url': i.get('url'), 'date': parse_date(i.get('date')),
            'toks': norm_tokens(i.get('title')),
        })

    by_date = defaultdict(list)
    for it in items:
        if it['date']:
            by_date[it['date']].append(it)

    visited = set()
    clusters = []
    for d, base_items in by_date.items():
        window = [d + timedelta(days=k) for k in range(-DATE_WINDOW_DAYS, DATE_WINDOW_DAYS + 1)]
        candidates = [it for wd in window for it in by_date.get(wd, [])]
        for a in base_items:
            if a['id'] in visited:
                continue
            cluster = [a]
            for b in candidates:
                if b['id'] == a['id'] or b['id'] in visited:
                    continue
                if not a['toks'] or not b['toks']:
                    continue
                inter = a['toks'] & b['toks']
                union = a['toks'] | b['toks']
                jacc = len(inter) / len(union) if union else 0
                if jacc >= JACCARD_THRESHOLD and len(inter) >= MIN_SHARED_TOKENS:
                    cluster.append(b)
            if len(cluster) > 1:
                visited.update(c['id'] for c in cluster)
                clusters.append(cluster)
            else:
                visited.add(a['id'])

    print(f'Clusters de posibles duplicados encontrados: {len(clusters)}')
    print(f'Items involucrados: {sum(len(c) for c in clusters)}')
    print()
    for c in sorted(clusters, key=lambda c: c[0]['date'] or datetime.min.date(), reverse=True):
        print(f"--- {c[0]['date']} ({len(c)} items) ---")
        for it in c:
            print(f"  [{it['medio']}] {it['id']} -- {it['title']}")
        print()


if __name__ == '__main__':
    main()
