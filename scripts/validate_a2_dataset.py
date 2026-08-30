#!/usr/bin/env python3
"""Validate the production A2 dataset, reports, shards, and A1 separation."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
A1 = ROOT / "data" / "a1" / "a1_all.json"
DATA = ROOT / "data" / "a2"
MASTER = DATA / "a2_all.json"
SUMMARY = DATA / "validation_summary.json"
OVERLAPS = DATA / "overlap_report.json"
REVIEW = DATA / "review_report.json"

REQUIRED = [
    "id", "german", "word_type", "gender", "plural", "english",
    "accepted_answers", "example_de", "example_en", "topic", "source", "source_url",
]
WORD_TYPES = {
    "abbreviation", "adjective", "adverb", "conjunction", "determiner", "interjection",
    "noun", "number", "phrase", "preposition", "pronoun", "proper noun", "verb",
}
GENDERS = {"der": "masculine", "die": "feminine", "das": "neuter"}
SUSPICIOUS_ENGLISH = re.compile(
    r"(?:\bsth\.?|\bso\.|\bcanditature\b|\bcontroll\b|\btestimony\b|\bhandynummer\b|\bcloths\b|\broadmap\b)",
    re.I,
)


def answer_key(value: str) -> str:
    return re.sub(r"[.!?,;:]+$", "", unicodedata.normalize("NFKC", value).casefold().strip())


def normalized_lemma(value: str) -> str:
    value = unicodedata.normalize("NFC", value).casefold().strip()
    value = value.replace("(sich)", "sich")
    value = re.sub(r"^(der|die|das)\s+", "", value)
    value = re.sub(r"^sich\s+", "", value)
    value = re.sub(r"\betwas\b", "", value)
    value = value.replace("ß", "ss")
    return re.sub(r"[^a-zäöü0-9]+", "", value)


def all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from all_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from all_strings(item)


def fail(errors: list[str]) -> None:
    if errors:
        raise SystemExit("A2 VALIDATION FAILED\n" + "\n".join(f"- {error}" for error in errors))


def main() -> None:
    cards = json.loads(MASTER.read_text(encoding="utf-8"))
    a1_cards = json.loads(A1.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    overlap_report = json.loads(OVERLAPS.read_text(encoding="utf-8"))
    review_report = json.loads(REVIEW.read_text(encoding="utf-8"))
    errors: list[str] = []

    if not isinstance(cards, list) or not cards:
        errors.append("master dataset is not a non-empty JSON array")
        fail(errors)

    ids = [card.get("id") for card in cards]
    expected_ids = [f"a2_{index:04d}" for index in range(1, len(cards) + 1)]
    if ids != expected_ids:
        errors.append("IDs are not the ordered a2_0001... sequence")
    if len(ids) != len(set(ids)):
        errors.append("duplicate IDs")

    exact_german = [card.get("german") for card in cards]
    duplicates = [value for value, count in Counter(exact_german).items() if count > 1]
    if duplicates:
        errors.append(f"duplicate exact German headwords: {duplicates}")

    reported_homographs = {
        item["normalized_lemma"]: set(item["cards"])
        for item in overlap_report.get("resolved_homographs", [])
    }
    lemma_groups: dict[str, set[str]] = {}
    for card in cards:
        lemma_groups.setdefault(normalized_lemma(card["german"]), set()).add(card["german"])
    for lemma, headwords in lemma_groups.items():
        if len(headwords) > 1 and reported_homographs.get(lemma) != headwords:
            errors.append(f"unresolved normalized homograph {lemma}: {sorted(headwords)}")

    a1_lemmas = {normalized_lemma(card["german"]) for card in a1_cards}
    cross_level = sorted({normalized_lemma(card["german"]) for card in cards} & a1_lemmas)
    if cross_level:
        errors.append(f"unresolved A1/A2 normalized overlap: {cross_level}")

    for index, card in enumerate(cards, 1):
        name = card.get("id", f"entry {index}")
        if list(card) != REQUIRED:
            errors.append(f"{name}: fields/order differ from A1 schema")
            continue
        if card["word_type"] not in WORD_TYPES:
            errors.append(f"{name}: invalid word_type {card['word_type']!r}")
        for key in ("id", "german", "word_type", "english", "example_de", "example_en", "topic", "source", "source_url"):
            if not isinstance(card[key], str) or not card[key].strip():
                errors.append(f"{name}: {key} is not a non-empty string")
        if any(unicodedata.normalize("NFC", value) != value for value in all_strings(card)):
            errors.append(f"{name}: contains non-NFC Unicode")
        if card["source"] != "Goethe A2" or card["source_url"] != summary["official_source_url"]:
            errors.append(f"{name}: source metadata mismatch")

        accepted = card["accepted_answers"]
        if not isinstance(accepted, list) or not accepted or not all(isinstance(item, str) and item.strip() for item in accepted):
            errors.append(f"{name}: accepted_answers must be a non-empty string array")
        else:
            normalized_answers = [answer_key(item) for item in accepted]
            if len(normalized_answers) != len(set(normalized_answers)):
                errors.append(f"{name}: duplicate normalized accepted answer")
            if answer_key(card["english"]) not in normalized_answers:
                errors.append(f"{name}: primary English answer is not accepted")
            if any(SUSPICIOUS_ENGLISH.search(item) or item.count("(") != item.count(")") for item in accepted):
                errors.append(f"{name}: suspicious or malformed accepted answer")
        if SUSPICIOUS_ENGLISH.search(card["example_en"]):
            errors.append(f"{name}: suspicious English example text")
        if not card["example_de"].endswith((".", "!", "?")) or not card["example_en"].endswith((".", "!", "?")):
            errors.append(f"{name}: example lacks terminal punctuation")

        if card["word_type"] == "noun":
            first = card["german"].split(" ", 1)[0]
            if first not in GENDERS:
                errors.append(f"{name}: noun lacks a definite article")
            elif " / die " in card["german"]:
                if card["gender"] != "masculine/feminine":
                    errors.append(f"{name}: paired noun gender mismatch")
            elif card["gender"] not in {GENDERS[first], "plural"}:
                errors.append(f"{name}: article/gender mismatch")
            if card["plural"] is not None and not card["plural"].startswith("die "):
                errors.append(f"{name}: plural lacks plural article")
        elif card["gender"] is not None or card["plural"] is not None:
            errors.append(f"{name}: non-noun has noun-only metadata")

        if card["word_type"] == "verb":
            infinitive = card["german"].removeprefix("sich ").replace(" über etwas ", " ")
            if not (infinitive.endswith(("en", "ern", "eln", "tun", " sein")) or infinitive in {"leidtun"}):
                errors.append(f"{name}: verb is not an infinitive: {card['german']}")
        if "(sich)" in card["german"] or card["german"].endswith("-"):
            errors.append(f"{name}: unnormalized dictionary shorthand")

    shard_cards = []
    for item in summary.get("files", []):
        path = DATA / item["file"]
        shard = json.loads(path.read_text(encoding="utf-8"))
        if len(shard) != item["entries"]:
            errors.append(f"{path.name}: manifest count mismatch")
        if any(card["topic"] != item["topic"] for card in shard):
            errors.append(f"{path.name}: contains a different topic")
        shard_cards.extend(shard)
    if shard_cards != cards:
        errors.append("topic shards do not reproduce the master ordering and contents")

    expected_summary = {
        "unique_a2_cards_added": len(cards),
        "a1_overlaps_detected_and_excluded": overlap_report.get("detected_a1_overlaps"),
        "source_variants_consolidated": overlap_report.get("source_variants_consolidated"),
        "manual_review_required": review_report.get("manual_review_required"),
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            errors.append(f"validation summary has wrong {key}")
    if summary.get("official_source_items_examined") != (
        summary.get("official_alphabetic_items_examined", 0) + summary.get("official_word_group_items_examined", 0)
    ):
        errors.append("official source item count does not equal its two sections")
    if review_report.get("excluded_uncertain_entries"):
        errors.append("review report contains unresolved entries while A2 is marked production-ready")

    fail(errors)
    print(
        f"VALID: {len(cards)} A2 cards; {len(overlap_report['resolved_overlaps'])} A1 overlaps resolved; "
        f"{len(reported_homographs)} deliberate homographs; 0 unresolved reviews; exact A1 schema"
    )


if __name__ == "__main__":
    main()
