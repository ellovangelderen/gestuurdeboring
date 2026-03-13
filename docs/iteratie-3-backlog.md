# Iteratie 3 — Backlog

**Status:** Toekomstig — inhoud afhankelijk van feedback na iteratie 2
**Afhankelijkheid:** Iteratie 2 compleet en in gebruik

---

## Wat iteratie 3 toevoegt

Iteratie 3 voegt de geavanceerde functies toe die de meeste bouwkost hebben en de minste directe noodzaak in het begin. Ze worden gebouwd nadat de kern bewezen bruikbaar is.

---

## Features

### AI werkplanteksten

**Wat:** AI genereert de tekstuele secties van het werkplan op basis van projectdata. Engineer controleert en past aan.

**Waarom niet eerder:** Weinig waarde t.o.v. bouwkost in iteratie 1/2. Werkplan template (iteratie 2) levert al 80% van de tijdsbesparing.

**Technisch:**
- `app/ai_assist/` module activeren (placeholder aanwezig vanaf iteratie 1)
- LLM aanroepen: OpenAI GPT-4 (configureerbaar, of Ollama lokaal)
- Prompt assembly vanuit projectdata (naam, locatie, kruising, parameters)
- Output als markdown → PDF via WeasyPrint
- "AI werkplan genereren" knop in output sectie (optioneel, naast gewoon werkplan)
- Disclaimer in document: "Door AI gegenereerd — controleer voor gebruik"

**Opmerking:** AI wordt uitsluitend voor tekst gebruikt. Kernberekeningen en ontwerpregels blijven deterministisch gecodeerd.

---

### Eisenprofiel beheerscherm

**Wat:** Beheerder kan eisenprofielen aanmaken, bewerken en verwijderen via een UI. Nieuwe beheerderseisen doorvoeren zonder code-aanpassing.

**Waarom niet eerder:** 4 hardcoded seed-profielen dekken de meeste projecten in iteratie 1/2. Beheerscherm is pas nodig als de profielenset groter en diverser wordt.

**Technisch:**
- `app/rules/` module uitbreiden met CRUD endpoints (POST/PUT/DELETE)
- Alleen toegankelijk voor beheerder rol (iteratie 2 vereiste)
- Frontend admin sectie: tabel met profielen, formulier voor aanmaken/bewerken
- Validatie: min_diepte > 0, beschermingszone ≥ 0, min_boogstraal > 0

---

### Sterkte- en slurrydrukberekening

**Wat:** Uitbreiding van berekeningen (iteratie 2) met sterktecontrole en boorvloeistofdrukanalyse.

**Waarom niet eerder:** Intrekkracht en buigstraal (iteratie 2) zijn de meest gevraagde. Sterkte en slurry zijn aanvullend voor complexe projecten.

**Technisch (sterktecontrole):**
```
σ_totaal = σ_trek + σ_buig
σ_trek = F_intrek / A_dwarsdoorsnede
σ_buig = E * (D_buiten/2) / R_min
Toelaatbaar PE-100: 6.3 MPa, staal: 0.5 * Rp0.2
Utilisation ratio = σ_totaal / σ_toelaatbaar
```

**Technisch (slurrydruk / frac-out risico):**
```
P_hydro = ρ_slurry * g * h_max
P_frac = σ_v * K0  (versimpeld)
Risico = P_hydro / P_frac
> 0.9 → hoog risico
```

- Normreferenties documenteren: NEN 7245, ASTM F1962
- Resultaten als gecertificeerde berekeningsoutput (disclaimer: "indicatief, niet als formeel ingenieursdocument")

---

### Audittrail

**Wat:** Overzicht van wie wat wanneer heeft gewijzigd per project.

**Waarom niet eerder:** Niet nodig voor een klein vertrouwd team in de eerste maanden.

**Technisch:**
- Tabel `audit_log`: `id`, `workspace_id`, `project_id`, `gebruiker_id`, `actie`, `object_type`, `object_id`, `wijzigingen` (JSONB), `tijdstip`
- SQLAlchemy event listeners op alle model wijzigingen
- Frontend: audittrail pagina per project (tijdlijn van wijzigingen)
- Beheerder-only toegang

---

### Meerdere workspaces actief

**Wat:** Meerdere klanten of teams op dezelfde installatie, volledig geïsoleerd.

**Waarom niet eerder:** Iteratie 1 heeft één workspace (Inodus klant). Meerdere workspaces zijn pas relevant als Inodus het platform aan meerdere klanten wil aanbieden.

**Technisch:**
- Workspace aanmaken via admin interface (Inodus-intern gebruik)
- Subdomein routing: `klant-a.hdd.inodus.nl` → workspace `klant-a`
- Workspace slug bepalen op basis van Host header in FastAPI middleware
- `get_current_workspace()` middleware werkt al correct — alleen routing toevoegen

---

## Wat nooit gebouwd wordt (alle iteraties)

Per CLAUDE.md en architect-input — permanent buiten scope:

- **Calculatiemodule** — kostprijsberekening van een boring
- **Offertemodule** — opmaak en verzending van offertes
- **Geautomatiseerde KLIC-aanvraag** — KLIC indienen bij Kadaster via API
- **3D visualisatie** — driedimensionaal model van het boortracé
- **Koppeling financieel pakket** — integratie met boekhoudpakket
