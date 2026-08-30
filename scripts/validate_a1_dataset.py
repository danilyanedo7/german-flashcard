#!/usr/bin/env python3
"""Validate the generated A1 JSON dataset and its topic shards."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "a1"
MASTER = DATA / "a1_all.json"
SUMMARY = DATA / "validation_summary.json"
REQUIRED = {
    "id", "german", "word_type", "gender", "plural", "english",
    "accepted_answers", "example_de", "example_en", "topic", "source",
    "source_url",
}
GENDERS = {"der": "masculine", "die": "feminine", "das": "neuter"}


def main() -> None:
    cards = json.loads(MASTER.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    errors: list[str] = []

    if not 650 <= len(cards) <= 1000:
        errors.append(f"entry count outside requested range: {len(cards)}")
    ids = [c.get("id") for c in cards]
    if len(ids) != len(set(ids)):
        errors.append("duplicate IDs")
    expected_ids = {f"a1_{i:04d}" for i in range(1, len(cards) + 1)}
    if set(ids) != expected_ids:
        errors.append("IDs are not a complete a1_0001... sequence")

    normalized = lambda s: re.sub(r"[^A-Za-zÄÖÜäöüß0-9]+", " ", s).strip()
    german_counts = Counter(normalized(c["german"]) for c in cards)
    duplicates = [k for k, count in german_counts.items() if count > 1]
    if duplicates:
        errors.append(f"duplicate German entries: {duplicates}")

    for card in cards:
        name = card.get("id", "unknown")
        if set(card) != REQUIRED:
            errors.append(f"{name}: fields differ from schema")
            continue
        if not all(isinstance(card[k], str) and card[k].strip() for k in ("id", "german", "word_type", "english", "example_de", "example_en", "topic", "source")):
            errors.append(f"{name}: required string is blank")
        if not isinstance(card["accepted_answers"], list) or not card["accepted_answers"]:
            errors.append(f"{name}: accepted_answers is empty")
        elif card["english"] not in card["accepted_answers"]:
            errors.append(f"{name}: primary English answer is not accepted")
        elif len(card["accepted_answers"]) != len(set(card["accepted_answers"])):
            errors.append(f"{name}: duplicate accepted answer")
        if not card["example_de"].endswith((".", "!", "?")) or not card["example_en"].endswith((".", "!", "?")):
            errors.append(f"{name}: example lacks terminal punctuation")
        if card["source"] == "Goethe A1" and not card["source_url"]:
            errors.append(f"{name}: official entry lacks source URL")
        if card["source"] == "Everyday A1 addition" and card["source_url"] is not None:
            errors.append(f"{name}: addition should not claim an official URL")
        if "(sich)" in card["german"] or card["german"].endswith("-"):
            errors.append(f"{name}: unnormalized dictionary shorthand")

        if card["word_type"] == "noun":
            article = card["german"].split(" ", 1)[0]
            if article not in GENDERS:
                errors.append(f"{name}: noun lacks a definite article")
            elif " / die " not in card["german"] and card["gender"] not in {GENDERS[article], "plural"}:
                errors.append(f"{name}: article/gender mismatch")
            if "plural" not in card:
                errors.append(f"{name}: noun lacks plural field")
            elif card["plural"] is not None and not card["plural"].startswith("die "):
                errors.append(f"{name}: plural lacks plural article")
        elif card["gender"] is not None or card["plural"] is not None:
            errors.append(f"{name}: non-noun has noun-only metadata")

    shard_cards = []
    for item in summary["files"]:
        path = DATA / item["file"]
        shard = json.loads(path.read_text(encoding="utf-8"))
        if len(shard) != item["entries"]:
            errors.append(f"{path.name}: manifest count mismatch")
        if any(c["topic"] != item["topic"] for c in shard):
            errors.append(f"{path.name}: contains another topic")
        shard_cards.extend(shard)
    if sorted(c["id"] for c in shard_cards) != sorted(ids):
        errors.append("topic shards do not exactly partition the master file")

    factual = {
        "total_entries": len(cards),
        "official_goethe_entries": sum(c["source"] == "Goethe A1" for c in cards),
        "entries_added_beyond_official_goethe_list": sum(c["source"] != "Goethe A1" for c in cards),
        "duplicate_entries": len(duplicates),
    }
    for key, value in factual.items():
        if summary.get(key) != value:
            errors.append(f"validation summary has wrong {key}")

    if errors:
        raise SystemExit("VALIDATION FAILED\n" + "\n".join(f"- {e}" for e in errors))
    print(f"VALID: {len(cards)} entries, {len(summary['files'])} topic files, 0 duplicates, 0 schema errors")


if __name__ == "__main__":
    main()
