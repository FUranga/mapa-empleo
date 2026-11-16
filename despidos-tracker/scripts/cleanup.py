"""
Limpieza semanal: borra de raw_data.json las noticias PENDIENTES de mas de
N dias que ya estaban en el backlog la ultima vez que alguien curo (publicar o
descartar desde el admin o con los skills). Lo que entro despues de la ultima
curacion no se borra nunca, aunque sea viejo: si nadie revisa, no se pierde
nada (en oct-nov 2026 la purga borro 233 notas sin que nadie las viera).

Las DESCARTADAS se conservan siempre -- son reversibles a proposito -- y las
PUBLICADAS viven aparte en curated_data.json y tampoco se tocan nunca.

Uso:
  python cleanup.py
  python cleanup.py --days 7
  python cleanup.py --dry-run
"""
import argparse
from datetime import datetime, timedelta, timezone

from utils import load_raw, save_raw, load_curated


def _parse(ts):
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def last_review(items):
    """Fecha de la ultima decision editorial: max status_at entre descartadas y publicadas."""
    stamps = [i.get("status_at") for i in items if i.get("status") != "pendiente"]
    stamps += [i.get("status_at") for i in load_curated()]
    parsed = [d for d in (_parse(s) for s in stamps if s) if d]
    return max(parsed) if parsed else None


def run_cleanup(days, dry_run=False):
    items = load_raw()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    reviewed_at = last_review(items)
    if reviewed_at is None:
        print("No hay ninguna curacion registrada: no se borra nada.")
        return

    kept = []
    removed = 0
    unreviewed = 0
    for item in items:
        if item.get("status") != "pendiente":
            kept.append(item)  # descartadas: se conservan siempre
            continue
        item_date = _parse(item.get("scraped_at") or "")
        if item_date is None or item_date >= cutoff:
            kept.append(item)
        elif item_date >= reviewed_at:
            kept.append(item)  # entro despues de la ultima curacion: nadie la vio todavia
            unreviewed += 1
        else:
            removed += 1

    if not dry_run:
        save_raw(kept)
    print(
        f"Limpieza {'(dry run) ' if dry_run else ''}lista. Ultima curacion: {reviewed_at:%Y-%m-%d %H:%M} UTC. "
        f"{removed} pendientes de +{days} dias eliminadas; {unreviewed} viejas conservadas porque "
        f"entraron despues de la ultima curacion. Quedan {len(kept)} en raw_data.json."
    )
    if unreviewed:
        print(f"::warning::{unreviewed} pendientes de +{days} dias sin revisar en despidos-tracker")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_cleanup(args.days, args.dry_run)
