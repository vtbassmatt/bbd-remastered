#!/usr/bin/env python
import csv
import json
import sys
from pathlib import Path
from urllib.request import urlopen

# Output path relative to repo root
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "battlebond_cards.csv"

SEARCH_URL = (
    "https://api.scryfall.com/cards/search"
    "?order=set&q=e%3Abbd+lang%3Aen&unique=cards"
)


def fetch_all(url: str):
    while url:
        with urlopen(url) as resp:
            payload = json.load(resp)
        for c in payload.get("data", []):
            yield c
        url = payload.get("next_page") if payload.get("has_more") else None


def join_faces(card, field):
    faces = card.get("card_faces") or []
    vals = []
    for f in faces:
        v = f.get(field) or ""
        vals.append(v)
    return " // ".join(vals).strip()


def get_text(card):
    if card.get("card_faces"):
        return join_faces(card, "oracle_text")
    return card.get("oracle_text") or ""


def get_mana_cost(card):
    if card.get("card_faces"):
        return join_faces(card, "mana_cost")
    return card.get("mana_cost") or ""


def get_type_line(card):
    if card.get("card_faces"):
        return join_faces(card, "type_line")
    return card.get("type_line") or ""


def get_stats(card):
    # Prefer power/toughness when present, else loyalty, else empty
    if card.get("card_faces"):
        # Join per-face stats if present
        parts = []
        for f in card.get("card_faces") or []:
            if f.get("power") is not None and f.get("toughness") is not None:
                parts.append(f"{f.get('power')}/{f.get('toughness')}")
            elif f.get("loyalty") is not None:
                parts.append(str(f.get("loyalty")))
            else:
                parts.append("")
        # Collapse to single string, trimming empty trailing separators
        return " // ".join(parts).strip(" /")

    power = card.get("power")
    tough = card.get("toughness")
    if power is not None and tough is not None:
        return f"{power}/{tough}"
    loyalty = card.get("loyalty")
    if loyalty is not None:
        return str(loyalty)
    return ""


def main():
    rows = []
    for card in fetch_all(SEARCH_URL):
        rows.append({
            "Name": card.get("name", ""),
            "Mana Cost": get_mana_cost(card),
            "Type Line": get_type_line(card),
            "Oracle Text": get_text(card),
            "Power/Toughness/Loyalty": get_stats(card),
            "Rarity": (card.get("rarity") or "").lower(),
        })

    # Sort by collector_number if available, else name
    def sort_key(r):
        return (
            (r["Name"] or ""),
        )

    rows.sort(key=sort_key)

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Name",
                "Mana Cost",
                "Type Line",
                "Oracle Text",
                "Power/Toughness/Loyalty",
                "Rarity",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Wrote {len(rows)} cards to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
