# Implementatieplan: Backlog 2 — Cockpit UI

**Datum:** 2026-03-18
**Status:** In uitvoering

---

## Doel
De `/orders/` pagina transformeren van een simpele ordertabel naar een volwaardige cockpit/startpagina met stats-balk, filters, zoekfunctie, sortering, quick-actions per boring, CSV export, en visuele indicatoren (EV-waarschuwing, PRIO-vlag, tekenaar-avatar).

---

## Implementatievolgorde

### Stap 1: Deadline in formulieren
- `app/order/router.py`: accepteer `deadline` als Form-parameter in create/update
- `app/templates/order/create.html`: voeg deadline date-input toe
- `app/templates/order/detail.html`: voeg deadline date-input toe

### Stap 2: Cockpit route + query helper
- `app/order/router.py`: vervang `order_lijst` door uitgebreide cockpit-route
- Query params: `filter` (alles/actief/wacht_akkoord/geleverd/mijn), `zoek`, `sorteer` (deadline/datum/klant/status), `richting` (asc/desc)
- Stats berekenen: totaal, over_deadline, urgent, in_uitvoering, wacht_akkoord
- Extraheer `_query_orders()` helper voor hergebruik

### Stap 3: Template herschrijven (`order/list.html`)
- Stats-balk: 5 klikbare kaarten (over deadline, urgent, in uitvoering, wacht akkoord, totaal)
- Toolbar: zoekbalk, filter-knoppen, sorteer-dropdown, CSV-export knop
- Ordertabel kolommen: PRIO, ordernummer, locatie, klant, boringen (type-badges), status, deadline, tekenaar (avatar), EV-warning, quick-actions
- Quick-actions dropdown per order met AlpineJS: tekening, berekening, werkplan, KLIC, kaart

### Stap 4: CSS uitbreiding (`static/css/main.css`)
- Stats-balk grid, stat-cards met kleurvarianten
- Cockpit toolbar flex layout
- Tekenaar avatar cirkel
- EV-warning en deadline-over stijlen
- Quick-action dropdown positionering

### Stap 5: CSV export endpoint
- `GET /orders/export/csv?filter=...&zoek=...`
- Hergebruik `_query_orders()` helper
- CSV met UTF-8 BOM voor Excel
- Kolommen: ordernummer, locatie, klant, boringen, status, deadline, tekenaar, prio, ev_partijen

### Stap 6: Tests (`tests/test_cockpit.py`)
- TC-cockpit-A: Na login → cockpit als eerste scherm
- TC-cockpit-B: Ordertabel toont alle orders met correcte status
- TC-cockpit-C: Quick-action links naar juiste boring
- TC-cockpit-D: Filter "wacht akkoord" → alleen relevante orders
- TC-cockpit-E: CSV export bevat alle zichtbare orders
- TC-cockpit-F: Zoeken op locatie
- TC-cockpit-G: Sorteren op deadline
- TC-cockpit-H: Stats-balk correcte tellingen
- TC-cockpit-I: EV-waarschuwing getoond
- TC-cockpit-J: PRIO-vlag zichtbaar

---

## Scope-afbakening
**NIET in scope** (eigen backlog items):
- Kaart-klik coördinateninvoer (trace-pagina feature)
- Kaartlagen BGT/DKK/KLIC/luchtfoto (kaart feature)
- Handmatige RD-invoer (bestaat al in trace-pagina)

## Aandachtspunten
- AlpineJS al geladen in base.html — gebruik `x-data`, `x-show`, `x-on:click`
- SQLite case-insensitive LIKE werkt standaard
- Geen paginering nodig bij <1000 orders
- CSV: UTF-8 BOM (`\ufeff`) voor Excel compatibiliteit
