# LEARN.md — LeanAI Factory Improvement Log
# Project: HDD Ontwerp Platform (GestuurdeBoringTekening.nl)
# Started: 2026-03-18
# Format: add entries during the project whenever something is worth noting.
# The Learn Agent reads this after every milestone.

---

## HOW TO ADD AN ENTRY

Anyone on the project can add an entry. Keep it short and factual.

```
## [date] — [short title]
Type:     PROBLEM / DECISION / INSIGHT / MISSING
Phase:    skeleton / backlog-[n] / release / general
Affect:   builder / architect / release / factory / process
What:     One sentence — what happened.
Why:      One sentence — why it matters.
Suggest:  One sentence — what should change (optional).
```

---

## ENTRIES

## 2026-03-22 — Bug gevonden? Check ALLE plekken
Type:     PROBLEM
Phase:    backlog-admin
Affect:   builder / process
What:     Kaartlinks tabel leeg op staging (BG-9) werd gefixed, maar klanten (46 stuks) en eisenprofielen (5 stuks) hadden exact hetzelfde probleem — pas gevonden nadat Ello expliciet vroeg "heb je dit ook op andere plekken gecheckt?"
Why:      Eén bug = waarschijnlijk meerdere instanties van hetzelfde patroon. Als je het patroon niet herkent, fix je alleen het symptoom.
Suggest:  Bij ELKE bugfix: (1) fix de bug, (2) grep/zoek naar hetzelfde patroon in de hele codebase, (3) fix alle instanties in één commit.

## 2026-03-22 — Referentiedata altijd auto-seeden bij startup
Type:     PROBLEM
Phase:    backlog-admin
Affect:   builder / release
What:     Drie tabellen (kaartlinks, klanten, eisenprofielen) waren leeg op staging/productie na deploy. Seed scripts bestonden maar werden niet automatisch uitgevoerd.
Why:      Losstaande seed scripts worden vergeten bij deploy. De app moet zichzelf kunnen initialiseren.
Suggest:  Patroon P5: alle referentiedata in lifespan() seeden met `if count() == 0` check. Nooit vertrouwen op handmatige scripts voor productie.

## 2026-03-22 — SQLite timezone mismatch
Type:     PROBLEM
Phase:    backlog-admin
Affect:   builder
What:     Admin systeem status toonde "0 recente orders" terwijl er net een order was toegevoegd. Oorzaak: `datetime.now(timezone.utc)` (aware) vs SQLite naive datetime — vergelijking matcht nooit.
Why:      SQLite slaat geen timezone info op. Aware vs naive vergelijking is altijd False.
Suggest:  Altijd `datetime.now(timezone.utc).replace(tzinfo=None)` bij SQLite queries.

## 2026-03-21 — Railway 500 door ontbrekende DB kolommen
Type:     PROBLEM
Phase:    release
Affect:   builder / release
What:     Productie gaf 500 na deploy. Nieuwe kolommen (variant, revisie, vergunning_checklist) waren lokaal handmatig toegevoegd maar niet op Railway.
Why:      SQLite `CREATE TABLE IF NOT EXISTS` voegt geen kolommen toe aan bestaande tabellen. Zonder migraties mist productie de nieuwe kolommen.
Suggest:  Elke nieuwe kolom → toevoegen aan startup migraties in lifespan(). Structureel: Alembic migraties bijhouden.

## 2026-03-21 — Visser was geen medewerker
Type:     PROBLEM
Phase:    release
Affect:   architect / process
What:     Michel Visser kon inloggen als user. Hij is de akkoord-contactpersoon bij 3D-Drilling, geen medewerker.
Why:      Historisch uit walking skeleton (2 users). Nooit gereviewed bij uitbreiding.
Suggest:  Gebruikerslijst regelmatig reviewen. Principle of least privilege.

## 2026-03-20 — Punt verslepen op kaart was dagelijkse frustratie
Type:     INSIGHT
Phase:    backlog-feedback
Affect:   builder / architect
What:     Martien kon tracépunten plaatsen maar niet verslepen. Dit bleek zijn grootste dagelijkse irritatie bij het testen.
Why:      Kleine UX issue met grote impact op productiviteit. Niet gevangen in tests.
Suggest:  Bij interactieve kaarten: altijd drag + click + keyboard ondersteunen. UX testen met de eindgebruiker, niet alleen functioneel.

## 2026-03-18 — WeasyPrint rendert geen inline SVG in tabel-cellen
Type:     PROBLEM
Phase:    backlog-9
Affect:   builder
What:     PDF was leeg — bovenaanzicht, lengteprofiel en doorsnede werden niet gerenderd. HTML zag er correct uit.
Why:      WeasyPrint heeft significante beperkingen bij SVG en data URIs die niet gedocumenteerd zijn in hun docs.
Suggest:  SVG altijd via cairosvg → PNG → tijdelijk bestand. Altijd de daadwerkelijke PDF openen en controleren.

## 2026-03-18 — Download bestanden zonder extensie
Type:     PROBLEM
Phase:    release
Affect:   builder
What:     PDF en DXF downloads kregen geen extensie. Browser sloeg ze op als extensieloos bestand.
Why:      Content-Disposition header miste quotes rond filename. Bij spaties/komma's in de naam snapt de browser het niet.
Suggest:  Altijd quotes: `filename="naam.pdf"`. Test met bestandsnamen die spaties en komma's bevatten.

## 2026-03-18 — Topotijdreis Nu laag incompatibel tiling scheme
Type:     PROBLEM
Phase:    backlog-11
Affect:   builder
What:     Historische kaarten (ArcGIS) werkten, maar de "Nu" laag (PDOK BRT) toonde een lege kaart. Drie pogingen nodig om de juiste combinatie te vinden.
Why:      Verschillende tile services hebben verschillende tiling schemes (origin, resoluties, CRS). Je kunt ze niet zomaar mixen op één Leaflet kaart.
Suggest:  Bij custom tile sources: altijd origin, resoluties en CRS verifiëren vóór integratie. Test met echte tiles, niet alleen de metadata.

## 2026-03-18 — 18 backlog items in 1 dag
Type:     INSIGHT
Phase:    general
Affect:   factory / process
What:     Alle 18 originele backlog items + PDF redesign + security hardening in één dag gebouwd en getest (99 commits, 239 tests).
Why:      Modulaire monoliet + walking skeleton aanpak werkt. Elke feature is geïsoleerd testbaar.
Suggest:  Dit tempo is niet houdbaar voor complexe items (B1 N-segment profiel). Snelheid ≠ kwaliteit bij architectuurwijzigingen.

## 2026-03-18 — OWASP security review vóór productie
Type:     DECISION
Phase:    release
Affect:   process / release
What:     OWASP Top 10 assessment uitgevoerd op verse checkout. 3 MUST FIX items gevonden (file size limits, logging, deps).
Why:      Security review na bouwen is effectiever dan security-by-design bij een MVP. Je weet wat er is en kunt gericht fixen.
Suggest:  OWASP check als standaard stap vóór eerste productie deploy.

## 2026-03-18 — Martien's Excel is de requirements bron
Type:     INSIGHT
Phase:    general
Affect:   architect
What:     Martien's Excel werkboek (2300 rijen) bevat de complete domeinkennis: bundelfactoren, ruimfactoren, standaard dieptes, boogzinker standen, boormachines. Analyse hiervan leverde 6 beslissingen + 6 verrijkingen + 5 toekomstige items op.
Why:      De Excel IS de huidige applicatie. Het platform moet minimaal alles kunnen wat de Excel kan.
Suggest:  Bij elk project: bestaande tools (Excel, Word, email) als requirements bron analyseren vóór architectuur.

## 2026-03-22 — Startup cleanup wist DB waarden op container platform
Type:     PROBLEM
Phase:    release
Affect:   builder / release
What:     Startup code in lifespan() wiste `logo_bestand` waarden voor klanten waarvan het logo-bestand niet op disk stond. Op Railway werden volumes async gemount, waardoor de cleanup draaide vóórdat de bestanden beschikbaar waren.
Why:      DB cleanup op basis van filesystem state is onbetrouwbaar op container platforms. Volumes, network mounts en copy-operaties zijn niet gegarandeerd klaar bij startup.
Suggest:  Nooit DB-waarden wissen op basis van ontbrekende bestanden. Als cleanup nodig is, maak het een expliciete admin-actie, niet een automatische startup-stap.

## 2026-03-22 — Logo management op persistent volumes
Type:     PROBLEM
Phase:    release
Affect:   builder / release
What:     Logo's werden opgeslagen in `static/logos/` (ephemeral container filesystem). Na elke Railway redeploy waren alle uploads weg. Verplaatst naar `data/logos/` (persistent volume) met fallback serve route.
Why:      Container filesystems zijn ephemeral by design. Alle user-uploaded bestanden moeten op een persistent volume staan.
Suggest:  Bij ELKE file-upload feature: (1) sla op naar persistent volume, niet naar app directory, (2) serve route moet meerdere paden checken voor backward compatibility, (3) test met container restart.

---

## PROCESSED ENTRIES
<!-- Learn Agent moves processed entries here after each milestone run -->
