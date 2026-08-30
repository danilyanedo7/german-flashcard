# A2 source note

Primary source: Goethe-Institut, *Goethe-Zertifikat A2 - Wortliste* (2016, PDF revised 2026).

- Official URL: https://www.goethe.de/pro/relaunch/prf/de/Goethe-Zertifikat_A2_Wortliste.pdf
- Accessed: 2026-08-30
- Downloaded PDF SHA-256: `c9ca0c96c4adb252f253e1cc648b95ea031e417911565db07f7102bccdbdb19e`
- Count examined: 1,214 alphabetic transcription items plus 230 word-group items (1,444 source candidates). Numeric date and clock examples were not counted as headwords.

The source is cumulative in practice. Its alphabetic section repeats ordinary A1 entries such as `ab`, `aber`, `abgeben`, and `abholen`, and its word groups repeat A1 numbers, colors, calendar terms, and other basic vocabulary. The build performs an NFC/case-folded lemma comparison that removes articles and reflexive/formatting differences. Ordinary A1 repetitions are excluded; genuinely new fixed expressions, separable compounds, word classes, or meanings are retained and documented in `overlap_report.json`.

Verification references:

- Goethe-Institut, *Deutsch Online A2 - Glossary, Chapters 1 to 18* (English): https://lernen.goethe.de/deutschonline/A2/PDF/EN/Wortschatz_A2_alpabetisch_EN.pdf (accessed 2026-08-30; SHA-256 `ddc8731eb71dabba3021f36ee18280cf364f6b0ee385bd5c94524d3cf292aa72`). This was used to cross-check natural English meanings and A2 usage.
- Duden online dictionary: https://www.duden.de/ (accessed 2026-08-30), used for spelling, word class, gender, and plural checks where the Goethe shorthand was absent or ambiguous.
- LEO German-English dictionary: https://dict.leo.org/englisch-deutsch/ (accessed 2026-08-30), used for bilingual ambiguity checks such as `sympathisch` -> `likeable`/`nice`, not ordinary English `sympathetic`.

The Markdown transcription used by the build is an extraction aid only. Every production card retains the official Goethe URL as its source; uncertain items are excluded and must be recorded in `review_report.json`.
