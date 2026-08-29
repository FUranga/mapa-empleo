"""
Limpieza semanal: borra de raw_data.json las noticias PENDIENTES (nunca
revisadas) de mas de N dias. Las DESCARTADAS se conservan siempre -- son
reversibles a proposito, y las PUBLICADAS viven aparte en curated_data.json
y tampoco se tocan nunca.

Uso:
  python cleanup.py
  python cleanup.py --days 7
"""
import argparse
from datetime import datetime, timedelta, timezone

from utils import load_raw, save_raw


def run_cleanup(days):
    items = load_raw()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    kept = []
    removed = 0
    for item in items:
        if item.get("status") != "pendiente":
            kept.append(item)  # descartadas: se conservan siempre
            continue
        try:
            item_date = datetime.fromisoformat(item["scraped_at"])
        except Exception:
            kept.append(item)  # si no se puede parsear, no lo borramos por las dudas
            continue
        if item_date >= cutoff:
            kept.append(item)
        else:
            removed += 1

    save_raw(kept)
    print(f"Limpieza lista. {removed} noticias pendientes de +{days} dias eliminadas (las descartadas se conservan). Quedan {len(kept)} en raw_data.json.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    run_cleanup(args.days)
