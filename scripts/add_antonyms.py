import json
import os
from collections import defaultdict

BASE_DIR = "/Users/edodanilyan/Documents/german-flashcard"

A1_DIR = os.path.join(BASE_DIR, "data", "a1")
A2_DIR = os.path.join(BASE_DIR, "data", "a2")

A1_ALL = os.path.join(A1_DIR, "a1_all.json")
A2_ALL = os.path.join(A2_DIR, "a2_all.json")

A1_VALIDATION = os.path.join(A1_DIR, "validation_summary.json")
A2_VALIDATION = os.path.join(A2_DIR, "validation_summary.json")

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

def main():
    # 1. Load both datasets
    a1_data = load_json(A1_ALL)
    a2_data = load_json(A2_ALL)
    
    all_entries = a1_data + a2_data
    
    # 4. Look up words by EXACT german field
    word_set = {entry['german'] for entry in all_entries}
    
    # 2. Define curated list
    curated_pairs = [
        # Adjective/Adverb
        ("alt", "jung"),
        ("alt", "neu"),
        ("groß", "klein"),
        ("gut", "schlecht"),
        ("heiß", "kalt"),
        ("kalt", "warm"),
        ("lang", "kurz"),
        ("schnell", "langsam"),
        ("teuer", "billig"),
        ("leicht", "schwer"),
        ("schwer", "einfach"),
        ("richtig", "falsch"),
        ("laut", "leise"),
        ("voll", "leer"),
        ("früh", "spät"),
        ("früher", "später"),
        ("hell", "dunkel"),
        ("oben", "unten"),
        ("links", "rechts"),
        ("immer", "nie"),
        ("viel", "wenig"),
        ("glücklich", "traurig"),
        ("stark", "schwach"),
        ("dick", "dünn"),
        ("schön", "hässlich"),
        ("sauber", "schmutzig"),
        ("draußen", "drinnen"),
        ("hinten", "vorne"),
        ("gesund", "krank"),
        ("freundlich", "böse"),
        ("langweilig", "interessant"),
        ("lustig", "traurig"),
        ("hoch", "niedrig"),
        ("breit", "eng"),
        ("modern", "alt"),
        ("hart", "weich"),
        ("fleißig", "faul"),
        ("klug", "dumm"),
        ("gefährlich", "sicher"),
        ("geöffnet", "geschlossen"),
        ("frei", "besetzt"),
        ("männlich", "weiblich"),
        ("verheiratet", "ledig"),
        ("hier", "dort"),
        ("hinein", "hinaus"),
        ("herein", "heraus"),
        ("hin", "her"),
        ("an", "aus"),
        ("auf", "zu"),
        # Verb pairs
        ("kaufen", "verkaufen"),
        ("kommen", "gehen"),
        ("anfangen", "aufhören"),
        ("beginnen", "aufhören"),
        ("fragen", "antworten"),
        ("aufmachen", "zumachen"),
        ("öffnen", "schließen"),
        ("anmachen", "ausmachen"),
        ("einsteigen", "aussteigen"),
        ("geben", "nehmen"),
        ("finden", "suchen"),
        ("gewinnen", "verlieren"),
        ("lachen", "weinen"),
        ("schlafen", "aufwachen"),
        ("lieben", "hassen"),
        ("singen", "schweigen"),
        # Noun pairs
        ("der Anfang", "das Ende"),
        ("die Frage", "die Antwort"),
        ("der Tag", "die Nacht"),
        ("der Morgen", "der Abend"),
        ("der Mann", "die Frau"),
        ("der Junge", "das Mädchen"),
        ("der Vater", "die Mutter"),
        ("der Sohn", "die Tochter"),
        ("der Bruder", "die Schwester"),
        ("der Eingang", "der Ausgang"),
        ("die Ankunft", "die Abfahrt"),
        ("das Problem", "die Lösung")
    ]
    
    antonym_map = defaultdict(list)
    skipped_pairs = []
    linked_pairs = 0
    
    # Build bidirectional map
    for w1, w2 in curated_pairs:
        if w1 in word_set and w2 in word_set:
            if w2 not in antonym_map[w1]:
                antonym_map[w1].append(w2)
            if w1 not in antonym_map[w2]:
                antonym_map[w2].append(w1)
            linked_pairs += 1
        else:
            skipped_pairs.append((w1, w2))
    
    print(f"Total pairs processed: {len(curated_pairs)}")
    print(f"Pairs successfully linked: {linked_pairs}")
    print(f"Pairs skipped (missing words): {len(skipped_pairs)}")
    for w1, w2 in skipped_pairs:
        print(f"  - Skipped: {w1} ↔ {w2}")
        if w1 not in word_set:
            print(f"    '{w1}' is missing")
        if w2 not in word_set:
            print(f"    '{w2}' is missing")
            
    # Process entries to add the new fields
    entries_updated = 0
    
    # Required order of fields
    FIELD_ORDER = [
        "id", "german", "word_type", "gender", "plural", "english", 
        "accepted_answers", "example_de", "example_en", "topic", 
        "source", "source_url", "antonym", "accepted_antonyms"
    ]
    
    def process_data(data):
        nonlocal entries_updated
        new_data = []
        for entry in data:
            word = entry['german']
            antonyms = antonym_map.get(word, [])
            
            if antonyms:
                entry['antonym'] = antonyms[0]
                entry['accepted_antonyms'] = antonyms
                entries_updated += 1
            else:
                entry['antonym'] = None
                entry['accepted_antonyms'] = None
                
            # Reorder
            reordered = {}
            for field in FIELD_ORDER:
                if field in entry:
                    reordered[field] = entry[field]
            # Copy over any extra fields that might exist just in case (none expected based on instructions)
            for k, v in entry.items():
                if k not in reordered:
                    reordered[k] = v
            new_data.append(reordered)
        return new_data

    a1_data_new = process_data(a1_data)
    a2_data_new = process_data(a2_data)
    
    print(f"\nEntries updated with antonyms: {entries_updated}")
    
    # Save master files
    save_json(A1_ALL, a1_data_new)
    save_json(A2_ALL, a2_data_new)
    
    # Write shards
    def write_shards(data, validation_file, base_dir):
        val = load_json(validation_file)
        files = val.get('files', [])
        
        # Group by topic
        grouped = defaultdict(list)
        for entry in data:
            topic = entry.get('topic')
            grouped[topic].append(entry)
            
        for shard in files:
            topic = shard['topic']
            filename = shard['file']
            filepath = os.path.join(base_dir, filename)
            save_json(filepath, grouped[topic])
            
    write_shards(a1_data_new, A1_VALIDATION, A1_DIR)
    write_shards(a2_data_new, A2_VALIDATION, A2_DIR)
    print("Shard files written.")

if __name__ == "__main__":
    main()
