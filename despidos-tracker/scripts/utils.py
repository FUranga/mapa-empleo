"""Utilidades compartidas para el scraper de despidos/cierres."""
import json
import hashlib
import re
import unicodedata
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent.parent
CONFIG = BASE / "config"
DATA = BASE / "data"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def strip_accents(text):
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def normalize(text):
    if not text:
        return ""
    return strip_accents(text.lower())


def make_id(url):
    return hashlib.md5(url.strip().encode("utf-8")).hexdigest()[:16]


def load_sources():
    return load_json(CONFIG / "sources_config.json")["sources"]


def load_keywords():
    return load_json(CONFIG / "keywords_config.json")


def load_provincias():
    return load_json(CONFIG / "provincias_lookup.json")["provincias"]


def is_relevant(title, summary, keywords_cfg):
    text = normalize(f"{title} {summary}")

    for signal in keywords_cfg["noise_signals"]:
        if normalize(signal) in text:
            return False, None

    for topic, kws in keywords_cfg["topic_keywords"].items():
        for kw in kws:
            if normalize(kw) in text:
                return True, topic
    return False, None


def tag_provincia(title, summary, source, provincias_lookup):
    text = normalize(f"{title} {summary}")
    for provincia, aliases in provincias_lookup.items():
        for alias in aliases:
            if normalize(alias) in text:
                return provincia
    # fallback: si la fuente es provincial y no se detecto nada en el texto,
    # asumimos la provincia de la fuente
    if source.get("tier") == "provincial" and source.get("provincia"):
        return source["provincia"]
    return None


def tag_departamento(title, summary, source, provincias_lookup):
    # Nivel departamento: por ahora solo usamos la ciudad/departamento propio
    # de la fuente (campo "departamento" en sources_config.json) como proxy.
    # TODO: reemplazar por el lookup real de mapa-empleo cuando se integre.
    text = normalize(f"{title} {summary}")
    if source.get("departamento") and normalize(source["departamento"]) in text:
        return source["departamento"]
    if source.get("tier") == "provincial" and source.get("departamento"):
        return source["departamento"]
    return None


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_raw():
    path = DATA / "raw_data.json"
    if not path.exists():
        return []
    return load_json(path)


def save_raw(items):
    save_json(DATA / "raw_data.json", items)


def load_curated():
    path = DATA / "curated_data.json"
    if not path.exists():
        return []
    return load_json(path)


def save_curated(items):
    save_json(DATA / "curated_data.json", items)


def dedupe_merge(existing_items, new_items):
    """Mergea new_items en existing_items por id, sin pisar los ya publicados."""
    by_id = {item["id"]: item for item in existing_items}
    added = 0
    for item in new_items:
        if item["id"] not in by_id:
            by_id[item["id"]] = item
            added += 1
    # orden cronologico descendente
    merged = sorted(by_id.values(), key=lambda x: x.get("date", ""), reverse=True)
    return merged, added
