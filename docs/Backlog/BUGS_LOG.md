# Bug Log — HDD Ontwerp Platform
**Bijgehouden vanaf 18 maart 2026**

---

## Opgeloste bugs

### BG-1 — Download bestanden zonder extensie
**Datum:** 22 maart 2026
**Gemeld door:** Martien (productie)
**Symptoom:** PDF en DXF downloads kregen geen extensie in de bestandsnaam.
**Oorzaak:** `Content-Disposition` header miste quotes rond filename. Bij spaties/komma's in de naam snapt de browser het niet.
**Fix:** Quotes toevoegen: `filename="{naam}.pdf"` + boring naam + locatie in filename.
**Les:** Altijd quotes om filenames in Content-Disposition headers.

---

### BG-2 — Railway 500 bij ontbrekende DB kolommen
**Datum:** 21 maart 2026
**Gemeld door:** Ello (productie)
**Symptoom:** 500 Internal Server Error op Railway na deploy.
**Oorzaak:** Nieuwe kolommen (`variant`, `revisie`, `vergunning_checklist`) waren handmatig toegevoegd lokaal maar niet op Railway. SQLite `CREATE TABLE IF NOT EXISTS` maakt geen nieuwe kolommen in bestaande tabellen.
**Fix:** Startup migraties in `lifespan()` die `ALTER TABLE ADD COLUMN` uitvoeren (met `try/except` voor als kolom al bestaat).
**Les:** Elke nieuwe kolom moet in de startup migraties lijst. Structureel: Alembic migraties up-to-date houden (QUA-3 op backlog).

---

### BG-3 — Systeem status toont 0 recente orders
**Datum:** 22 maart 2026
**Gemeld door:** Ello (staging)
**Symptoom:** Admin → Systeem status toont "Geen orders in de laatste 7 dagen" terwijl er net een order is toegevoegd.
**Oorzaak:** Timezone mismatch. `datetime.now(timezone.utc)` is timezone-aware, maar SQLite slaat `ontvangen_op` als naive datetime op. De vergelijking `naive >= aware` matcht nooit.
**Fix:** `datetime.now(timezone.utc).replace(tzinfo=None)` voor vergelijking met naive datetime uit SQLite.
**Les:** SQLite slaat geen timezone info op. Altijd naive datetime gebruiken bij SQLite queries, of consistente timezone hantering afdwingen.

---

### BG-4 — Kaartlinks tabel leeg na deploy
**Datum:** 22 maart 2026
**Gemeld door:** Ello
**Symptoom:** Admin → Externe kaartlinks is leeg. De hardcoded links in vergunningscheck werken wel maar de admin-beheerbare tabel is leeg.
**Oorzaak:** `KaartLink` tabel werd aangemaakt bij startup maar niet geseeded. De kaartlinks staan hardcoded in `router.py`, niet in de DB.
**Fix:** Seed script met 9 standaard kaartlinks.
**Les:** Nieuwe DB tabellen die referentiedata bevatten moeten een seed script hebben. Of: de tabel wordt gevuld bij eerste gebruik vanuit de hardcoded defaults.

---

### BG-5 — Visser als gebruiker (is klant, niet medewerker)
**Datum:** 21 maart 2026
**Gemeld door:** Ello
**Symptoom:** Michel Visser kon inloggen als user. Hij is de akkoord-contactpersoon bij 3D-Drilling, geen medewerker.
**Oorzaak:** Historisch: bij de walking skeleton waren er 2 users (martien + visser). Visser werd nooit verwijderd.
**Fix:** Visser verwijderd uit auth, config, dependencies. `Config.extra = "ignore"` zodat oude .env bestanden met `USER_VISSER_PASSWORD` niet crashen.
**Les:** Gebruikerslijst regelmatig reviewen. Principle of least privilege — alleen medewerkers krijgen toegang.

---

### BG-6 — Railway 401 zonder login popup
**Datum:** 20 maart 2026
**Gemeld door:** Martien (productie)
**Symptoom:** Browser toont "401 Niet ingelogd" pagina in plaats van de login popup.
**Oorzaak:** Custom error handler renderde HTML voor 401, waardoor de browser de `WWW-Authenticate: Basic` header negeerde en geen popup toonde.
**Fix:** 401 responses sturen JSON terug met de `WWW-Authenticate` header, niet HTML.
**Les:** HTTPBasic auth vereist dat de 401 response de `WWW-Authenticate` header correct meestuurt. Custom error handlers mogen dit niet overriden.

---

### BG-7 — Topotijdreis "Nu" laag toont lege kaart
**Datum:** 18 maart 2026
**Gemeld door:** Ello (lokaal)
**Symptoom:** De slider op "Nu" toont een lege grijze kaart, historische kaarten werken wel.
**Oorzaak:** De "Nu" laag gebruikte een PDOK WMTS/WMS service met een ander tiling scheme (origin/resoluties) dan de ArcGIS historische tiles. Twee incompatibele CRS-en op dezelfde Leaflet kaart.
**Fix:** "Nu" verwijderd — 2015 is het meest recente jaar. Alle lagen gebruiken nu hetzelfde ArcGIS tiling scheme.
**Les:** Bij custom tile sources altijd verifiëren dat origin, resoluties en CRS overeenkomen. Verschillende tile servers mixen in één kaart vereist reprojectie.

---

### BG-8 — PDF bovenaanzicht en lengteprofiel niet zichtbaar
**Datum:** 18 maart 2026
**Gemeld door:** Ello (lokaal)
**Symptoom:** PDF toont alleen tekst, geen SVG afbeeldingen (bovenaanzicht, lengteprofiel, doorsnede).
**Oorzaak:** WeasyPrint rendert inline SVG niet betrouwbaar in `<table>` cells. Ook `data:` URIs voor `<img>` tags werken niet.
**Fix:** SVG's converteren naar PNG via cairosvg, opslaan als tijdelijk bestand, laden via `file://` URL. Kaart (JPG) ook als tijdelijk bestand.
**Les:** WeasyPrint heeft significante beperkingen bij SVG en data URIs. Altijd testen met de daadwerkelijke PDF output, niet alleen de HTML.

---

### BG-16 — Logo upload via browser werkt niet op staging/productie
**Datum:** 22 maart 2026
**Gemeld door:** Ello (staging + productie)
**Symptoom:** Logo uploaden via de browser voor klant FB (FonsBakker) werkt niet. Via API/script werkt de upload wel (303 redirect, bestand correct opgeslagen en ophaalbaar).
**Oorzaak:** Wordt onderzocht. API test met Origin/Referer headers slaagt. Mogelijke oorzaken:
- Browser stuurt een andere Origin/Referer (bijv. via proxy/redirect)
- Form `enctype="multipart/form-data"` probleem
- CSRF middleware blokkeert op een subtiele manier
- Railway reverse proxy/load balancer strippen headers
**Status:** Open — API werkt, browser niet. Nader onderzoek nodig.

---

### BG-15 — Logo's verdwijnen na Railway restart
**Datum:** 22 maart 2026
**Gemeld door:** Ello (staging + productie)
**Symptoom:** Logo upload werkte lokaal, maar na deploy op Railway waren alle logo's weg. Na handmatig kopiëren naar het volume verdwenen de `logo_bestand` DB-waarden alsnog bij elke restart.
**Oorzaak:** Drie samenhangende problemen:
1. Logo's werden opgeslagen in `static/logos/` (ephemeral filesystem) i.p.v. persistent volume (`data/logos/`).
2. Upload zonder bestand geselecteerd gaf 400 i.p.v. redirect (BG-11).
3. Startup cleanup in `lifespan()` wiste `logo_bestand` voor klanten waarvan het bestand niet op disk stond — maar de bestanden stonden op het volume dat pas NA de cleanup gemount was, of waren nog niet gekopieerd door de ops agent.
**Fix:**
- Logo opslag verplaatst naar `data/logos/` (Railway persistent volume).
- Serve route checkt beide directories (`data/logos/` + `static/logos/`).
- Lege upload geeft redirect i.p.v. 400.
- **Startup cleanup volledig verwijderd** — was te agressief en wiste geldige waarden.
- Seed zet `logo_bestand=None` voor nieuwe klanten (logo uploaden via admin UI).
**Les:** Startup cleanup van DB-waarden gebaseerd op filesystem state is gevaarlijk op container platforms waar volumes async gemount worden. Nooit DB-waarden wissen op basis van ontbrekende bestanden — het bestand kan op een ander pad of volume staan.

---

## Patronen / terugkerende issues

### P1 — SQLite timezone handling
Bugs: BG-3
SQLite heeft geen native timezone support. Timestamps worden opgeslagen als text/float zonder timezone. Bij vergelijkingen altijd naive datetime gebruiken.

### P2 — Nieuwe kolommen niet op productie
Bugs: BG-2
Bij elke nieuwe kolom: toevoegen aan de startup migraties lijst. Langetermijn: Alembic migraties structureel bijhouden.

### P3 — WeasyPrint rendering beperkingen
Bugs: BG-8
WeasyPrint ondersteunt geen: inline SVG in tabel-cellen, data: URIs, CSS grid. Altijd SVG→PNG via cairosvg + tijdelijke bestanden.

### P4 — Content-Disposition headers
Bugs: BG-1
Altijd quotes om filenames. Altijd extensie in de filename. Test met bestandsnamen die spaties en komma's bevatten.

### P5 — Referentiedata seeden bij startup
Bugs: BG-4, BG-9, BG-10
Alle referentietabellen (kaartlinks, klanten, eisenprofielen) seeden in `lifespan()` met `if count() == 0` check. Nooit afhankelijk zijn van handmatige seed scripts.

### P6 — Geen DB cleanup op basis van filesystem state
Bugs: BG-15
Op container platforms (Railway, Docker) worden volumes async gemount. Startup code mag nooit DB-waarden wissen omdat bestanden niet gevonden worden — het bestand kan op een volume staan dat nog niet klaar is.
