"""
Scraper de noticias de despidos y cierres de empresas en Argentina.

Modos:
  --mode batch   -> corre desde 2024-01-01 hasta hoy via Google News RSS
                    (chunkeado por mes) + los RSS directos de cada medio.
                    Pensado para correr una vez, o de nuevo si cambias la
                    config estructuralmente. Es idempotente: no duplica ni
                    pisa noticias ya publicadas.
  --mode daily   -> corre solo la ventana de las ultimas --hours horas
                    (default 48) contra RSS directos + Google News.
                    Pensado para el cron diario.

Uso:
  python scraper.py --mode batch
  python scraper.py --mode daily --hours 48
"""
import argparse
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser
import requests

from utils import (
    load_sources, load_keywords, load_provincias,
    is_relevant, tag_provincia, tag_departamento,
    make_id, now_iso, load_raw, save_raw, dedupe_merge,
)

GOOGLE_NEWS_SEARCH = "https://news.google.com/rss/search?q={q}&hl=es-419&gl=AR&ceid=AR:es-419"
TOPIC_QUERIES = [
    '("despidos" OR "despido masivo" OR "suspensiones de personal" OR "cesantias") Argentina',
    '("cierre de planta" OR "cierre de fabrica" OR "cierre de sucursal" OR "quiebra" OR "concurso preventivo") Argentina',
]
USER_AGENT = "Mozilla/5.0 (compatible; ArgentinaDespidosTracker/1.0)"
REQUEST_TIMEOUT = 20
SLEEP_BETWEEN_REQUESTS = 1.5


def fetch_feed(url):
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except Exception as e:
        print(f"  [WARN] no se pudo bajar {url}: {e}")
        return None


def parse_entry_date(entry):
    for field in ("published_parsed", "updated_parsed"):
        val = getattr(entry, field, None)
        if val:
            return datetime(*val[:6], tzinfo=timezone.utc)
    return None


def extract_medio(entry, fallback_name):
    # Google News mete el medio real en entry.source.title; si no, usamos el
    # nombre de la fuente que estamos consultando.
    src = getattr(entry, "source", None)
    if src and getattr(src, "title", None):
        return src.title
    # a veces viene como " - Medio" al final del titulo
    if " - " in entry.title:
        possible = entry.title.rsplit(" - ", 1)[-1].strip()
        if 0 < len(possible) < 40:
            return possible
    return fallback_name


def build_item(entry, source, keywords_cfg, provincias_lookup, fallback_medio):
    title = getattr(entry, "title", "").strip()
    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
    link = getattr(entry, "link", "").strip()
    if not title or not link:
        return None

    relevant, topic = is_relevant(title, summary, keywords_cfg)
    if not relevant:
        return None

    entry_date = parse_entry_date(entry)
    date_iso = entry_date.isoformat() if entry_date else now_iso()

    provincia = tag_provincia(title, summary, source, provincias_lookup)
    departamento = tag_departamento(title, summary, source, provincias_lookup)
    medio = extract_medio(entry, fallback_medio)

    return {
        "id": make_id(link),
        "title": title,
        "medio": medio,
        "lugar": provincia or "Nacional",
        "provincia": provincia,
        "departamento": departamento,
        "topic": topic,
        "snippet": (summary or "")[:280],
        "url": link,
        "date": date_iso,
        "scraped_at": now_iso(),
        "status": "pendiente",  # pendiente | descartado (publicado vive en curated_data.json)
        "status_at": None,
    }


def scrape_source_rss(source, keywords_cfg, provincias_lookup):
    items = []
    if not source.get("rss_url") or not source.get("active", True):
        return items
    print(f"  RSS directo: {source['name']}")
    feed = fetch_feed(source["rss_url"])
    if not feed:
        return items
    for entry in feed.entries:
        item = build_item(entry, source, keywords_cfg, provincias_lookup, source["name"])
        if item:
            items.append(item)
    time.sleep(SLEEP_BETWEEN_REQUESTS)
    return items


def scrape_google_news(query, keywords_cfg, provincias_lookup, pseudo_source, after=None, before=None):
    items = []
    q = query
    if after:
        q += f" after:{after}"
    if before:
        q += f" before:{before}"
    url = GOOGLE_NEWS_SEARCH.format(q=quote(q))
    print(f"  Google News: {q}")
    feed = fetch_feed(url)
    if not feed:
        return items
    for entry in feed.entries:
        item = build_item(entry, pseudo_source, keywords_cfg, provincias_lookup, "Google News")
        if item:
            items.append(item)
    time.sleep(SLEEP_BETWEEN_REQUESTS)
    return items


def month_chunks(start_date, end_date):
    chunks = []
    cur = start_date.replace(day=1)
    while cur <= end_date:
        nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        chunk_end = min(nxt - timedelta(days=1), end_date)
        chunks.append((cur, chunk_end))
        cur = nxt
    return chunks


def run_batch(since_str):
    sources = load_sources()
    keywords_cfg = load_keywords()
    provincias_lookup = load_provincias()
    pseudo_source = {"tier": "nacional", "provincia": None, "departamento": None}

    all_items = []

    # 1) RSS directos de cada medio (cubren lo mas reciente que tengan)
    print("== RSS directos ==")
    for source in sources:
        all_items.extend(scrape_source_rss(source, keywords_cfg, provincias_lookup))

    # 2) Google News chunkeado por mes desde 'since' hasta hoy (cobertura historica)
    print("== Google News historico ==")
    since = datetime.strptime(since_str, "%Y-%m-%d")
    today = datetime.now(timezone.utc).replace(tzinfo=None)
    for start, end in month_chunks(since, today):
        after = start.strftime("%Y-%m-%d")
        before = (end + timedelta(days=1)).strftime("%Y-%m-%d")
        for query in TOPIC_QUERIES:
            all_items.extend(
                scrape_google_news(query, keywords_cfg, provincias_lookup, pseudo_source, after=after, before=before)
            )

    existing = load_raw()
    merged, added = dedupe_merge(existing, all_items)
    save_raw(merged)
    print(f"\nBatch listo. {added} noticias nuevas agregadas. Total en raw_data.json: {len(merged)}")


def run_daily(hours):
    sources = load_sources()
    keywords_cfg = load_keywords()
    provincias_lookup = load_provincias()
    pseudo_source = {"tier": "nacional", "provincia": None, "departamento": None}

    all_items = []

    print("== RSS directos (ventana diaria) ==")
    for source in sources:
        all_items.extend(scrape_source_rss(source, keywords_cfg, provincias_lookup))

    print("== Google News (ventana diaria) ==")
    for query in TOPIC_QUERIES:
        all_items.extend(scrape_google_news(query, keywords_cfg, provincias_lookup, pseudo_source))

    # filtramos por ventana horaria (solo lo scrapeado via RSS trae fecha real;
    # como salvaguarda extra, si no hay fecha confiable lo dejamos pasar y el
    # dedupe por id evita duplicarlo en corridas futuras)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    windowed = []
    for item in all_items:
        try:
            item_date = datetime.fromisoformat(item["date"])
        except Exception:
            windowed.append(item)
            continue
        if item_date >= cutoff:
            windowed.append(item)

    existing = load_raw()
    merged, added = dedupe_merge(existing, windowed)
    save_raw(merged)
    print(f"\nDaily listo. {added} noticias nuevas en la ventana de {hours}h. Total en raw_data.json: {len(merged)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["batch", "daily"], required=True)
    parser.add_argument("--since", default="2024-01-01", help="Solo para --mode batch")
    parser.add_argument("--hours", type=int, default=48, help="Solo para --mode daily")
    args = parser.parse_args()

    if args.mode == "batch":
        run_batch(args.since)
    else:
        run_daily(args.hours)
