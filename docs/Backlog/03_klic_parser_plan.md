# Implementatieplan: Backlog 3 — KLIC IMKL 2.0 Parser

**Datum:** 2026-03-18
**Status:** In uitvoering

---

## Doel
Volledige KLIC IMKL 2.0 parser met EV-detectie, diepte uit tekstvelden, materiaalregel sleufloze techniek, en Formaat B (enkel GML) support.

## Wat al bestaat
- `app/geo/klic_parser.py` — ZIP parser (Formaat A) met basale leiding-extractie + bijlage-heuristiek sleufloze
- `KLICLeiding` model met beheerder, type, geometrie, diepte, sleufloze_techniek, dxf_laag
- Upload + verwerk routes in `app/order/router.py`
- 16 bestaande tests in `tests/test_klic_parser.py`
- IJmuiden testdata: GML V2 + ZIP beschikbaar

## Wat erbij moet

### Database (6 nieuwe kolommen op KLICLeiding)
- `diepte_bron` (String) — "imkl" | "tekstveld_onzeker" | None
- `mogelijk_sleufloze` (Boolean) — staal = onzeker
- `ev_verplicht` (Boolean) — EV-leiding markering
- `ev_contactgegevens` (String) — "Pipeline Control | 088-186 4022 | email"
- `label_tekst` (Text) — ruwe label uit Maatvoering/Annotatie
- `toelichting_tekst` (Text) — ruwe toelichting

### Stappen
1. Alembic migratie + model update
2. `_build_ev_index()` — parse AanduidingEisVoorzorgsmaatregel elementen
3. `_extract_diepte_uit_tekst()` — regex patronen voor NAP/diepte
4. `_detect_materiaal_sleufloze()` — PE→sleufloze, staal→mogelijk, PVC→nee
5. `_parse_gml_file()` uitbreiden met EV, diepte, materiaal
6. Formaat B support — enkel GML bestand (niet ZIP)
7. Upload route: accepteer .xml/.gml naast .zip
8. Brondata template: EV-waarschuwing blok
9. Tests schrijven (TC-klic-C t/m F + materiaal + EV brondata)

### Testcases
- TC-klic-C: EV-leidingen → ev_verplicht=True + contactgegevens (Petrogas/Pipeline Control)
- TC-klic-D: Diepte uit tekstveld → diepte_bron="tekstveld_onzeker"
- TC-klic-E: IJmuiden GML V2 → beheerders geparsed
- TC-klic-F: HDD11 ZIP → 11 beheerders, 1127 leidingen (skip als testdata ontbreekt)
- TC-klic-materiaal: PE→sleufloze, PVC→niet, staal→mogelijk

### Aandachtspunten
- HDD11 testdata ontbreekt in repo — IJmuiden data als primaire testbasis
- Materiaalinfo vaak afwezig in IMKL — bijlage-heuristiek blijft primair
- EV-detectie via AanduidingEisVoorzorgsmaatregel + inNetwork href matching
