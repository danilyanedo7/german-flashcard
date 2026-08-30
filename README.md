# Wort für Wort

`Wort für Wort` is a dependency-free German vocabulary typing game designed for GitHub Pages. It currently enables Goethe A1 and keeps A2–C1 visible as disabled “Coming soon” levels.

## Run locally

Because the app loads JSON with `fetch`, serve the repository with a static HTTP server rather than opening `index.html` directly:

```sh
python3 -m http.server 4173
```

Open [http://localhost:4173/](http://localhost:4173/). No build step, backend, external fonts, remote assets, or runtime dependencies are required. The interface prefers the locally installed Satoshi typeface and falls back to the platform system UI font when Satoshi is unavailable.

## Existing A1 data

The app reads [data/a1/a1_all.json](data/a1/a1_all.json) directly. It is a read-only array of objects with the existing fields `id`, `german`, `word_type`, `gender`, `plural`, `english`, `accepted_answers`, `example_de`, `example_en`, `topic`, `source`, and `source_url`. The loader uses `id`, `german`, `english`, and `accepted_answers` for gameplay and reveals the other fields only after checking an answer.

At load time, malformed entries are skipped and reported with `console.warn`; missing optional `accepted_answers` falls back to the primary `english` value. The current A1 file has 799 valid entries and no malformed entries, duplicate IDs, or uncertain translations.

## Add another level later

Add a validated dataset in its own directory, then edit the single [data/levels.json](data/levels.json) configuration file:

```json
"A2": {
  "enabled": true,
  "label": "A2",
  "data": "data/a2/a2_all.json"
}
```

The loader and game logic do not need level-specific changes as long as the dataset follows the same essential fields.
