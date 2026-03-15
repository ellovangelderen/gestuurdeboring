# Bouwopdracht — Backlog item 2b: EV-zone DXF rendering + ontwerp-workflow

**HDD Ontwerp Platform · LeanAI Software Factory**
Versie: 1.0 | 2026-03-15
Opgesteld door: Architect Agent

---

## 1. Doel

Visualiseer Eis Voorzorgsmaatregel (EV) zones in de DXF-output en bied een ontwerp-workflow waarmee de gebruiker kan bevestigen dat het tracé buiten de EV-zonering blijft. EV-detectie in de KLIC-parser (backlog 1 uitbreiding) levert de data. Dit backlog item voegt de DXF-laag, de UI-workflow en de PDF-output toe.

**Urgentie: WETTELIJK KRITISCH.** Niet-afgemelde EV-leidingen leiden tot hoge boetes van het Agentschap Telecom. Martien's praktijk: altijd buiten EV-zonering ontwerpen. Als dat niet mogelijk is: mailconversatie voeren en meeleveran bij ontwerp.

**Afhankelijkheid:** Backlog 1 inclusief EV-detectie (TC-klic-Q t/m R) moet volledig groen zijn.

---

## 2. Scope

### Wel in scope

- Nieuwe DXF-laag `EV-ZONE` met EV-zonepolygonen (kleur ACI=1 rood, lijntype `DASHDOT`)
- DXF-laag altijd aanwezig — leeg als er geen EV-leidingen zijn, geen crash
- UI-check op review-pagina: als EV-leidingen aanwezig → blokkerende WAARSCHUWING met checklist
- Checklist bevat: (1) ontwerp buiten EV-zone bevestigen, (2) optioneel: mailreferentie invullen
- Optioneel tekstveld voor registratie mailreferentie (bestandsnaam of korte beschrijving)
- PDF-situatietekening: EV-zone zichtbaar als arcering of rode contour
- PDF voetnoot bij EV: contactgegevens netbeheerder per EV-leiding

### Niet in scope

- Automatisch verzenden van mails naar netbeheerder
- Validatie of ontwerp werkelijk buiten de EV-zonering ligt (geometrische check — backlog 7)
- Uploaden van de mailconversatie als bestand (alleen tekstregistratie)
- EV-zone grootte berekenen (polygoon komt direct uit IMKL)

---

## 3. Technische keuzes

### DXF laag EV-ZONE

```python
# In NLCS_LINETYPES toevoegen:
"EV-ZONE": "EIS VOORZORGSMAATREGEL ZONE"

# Laagdefinitie:
DXF_LAAG_EV_ZONE = {
    "name":      "EV-ZONE",
    "color":     1,       # ACI rood
    "linetype":  "DASHDOT",
}
```

EV-zone geometrie: polygoon uit `EisVoorzorgsmaatregel`-element in IMKL (POLYGON WKT). Tekenen als `LWPolyline` (closed=True) met HATCH-vulling (transparant, patroon `ANSI31`, schaal 5).

### UI review-pagina

Bovenaan de review-pagina, vóór kaart en lengteprofiel, een rood WAARSCHUWING-blok tonen als `ev_count > 0`:

```html
<div class="alert alert-danger">
  <strong>EV — Eis Voorzorgsmaatregel aanwezig</strong>
  {{ ev_count }} leid{{ 'ing' if ev_count == 1 else 'ingen' }} vereist contact met netbeheerder
  vóór aanvang werkzaamheden.
  <ul>
    {% for ev in ev_leidingen %}
    <li>{{ ev.beheerder }} — {{ ev.ev_contactgegevens }}</li>
    {% endfor %}
  </ul>
  <label>Mailreferentie (optioneel): <input name="ev_mailreferentie" type="text"></label>
</div>
```

### PDF voetnoot

In de OPMERKINGEN-sectie van de PDF, onder de bestaande KLIC-disclaimer:

```
EV-ZONE: [beheerder] — contactgegevens: [ev_contactgegevens]
Ontwerp ligt buiten de voorgeschreven EV-zonering. [mailreferentie indien ingevuld]
```

---

## 4. Datamodel

### Uitbreiding `Project`

```python
ev_mailreferentie = Column(String)   # optionele referentie mailconversatie
```

### Geen nieuwe tabel nodig

EV-data zit al in `KLICLeiding.ev_verplicht` en `KLICLeiding.ev_contactgegevens` (backlog 1).

### Alembic-migratie

Eén ADD COLUMN op `projects` tabel voor `ev_mailreferentie`.

---

## 5. Routes

### Gewijzigd

```
GET /api/v1/projecten/{project_id}/review
```

Levert nu `ev_leidingen` (lijst van KLICLeiding waar ev_verplicht=True) mee aan template.

```
POST /api/v1/projecten/{project_id}/ev-mailreferentie
```

Slaat `ev_mailreferentie` op op het project. Body: `{ "mailreferentie": "..." }`. Retourneert redirect naar review-pagina.

---

## 6. Acceptatiecriteria

```
TC-ev-A  DXF na KLIC met EV-leidingen → laag "EV-ZONE" aanwezig, bevat LWPolyline of HATCH entiteiten
TC-ev-B  DXF zonder EV-leidingen → laag "EV-ZONE" aanwezig maar leeg (geen crash, geen KeyError)
TC-ev-C  DXF → laag "EV-ZONE" kleur=1 (rood), lijntype="DASHDOT"
TC-ev-D  Review-pagina met EV-leidingen → rood WAARSCHUWING-blok zichtbaar (text bevat "EV")
TC-ev-E  Review-pagina met EV-leidingen → contactgegevens netbeheerder zichtbaar in blok
TC-ev-F  Review-pagina zonder EV-leidingen → geen WAARSCHUWING-blok
TC-ev-G  PDF met EV-leidingen → tekst "EV-ZONE" aanwezig in PDF
TC-ev-H  PDF met EV-leidingen → contactgegevens netbeheerder aanwezig in PDF voetnoot
TC-ev-I  POST ev-mailreferentie → opgeslagen op project, zichtbaar in review-pagina
TC-ev-J  DXF regressie → alle bestaande lagen nog aanwezig na toevoeging EV-ZONE (TC-dxf-B)
```

---

## 7. Testdata

Mock KLIC met EV-leiding (unit test):
```python
EV_MOCK_LEIDING = KLICLeiding(
    beheerder="Liander",
    ev_verplicht=True,
    ev_contactgegevens="Liander Storingen: 0800-9009",
    geometrie_wkt="POLYGON((103890 489280, 103910 489280, 103910 489300, 103890 489300, 103890 489280))",
    dxf_laag="LAAGSPANNING",
)
```

Voor live test: KLIC HDD11 (`Levering_25O0136974_1.zip`) — controleer of EV-leidingen aanwezig zijn in dit bestand (onbekend — toevoegen als `pytest.mark.external`).

---

## 8. Bouwvolgorde

1. Alembic migratie (`ev_mailreferentie` op `projects`)
2. DXF-laag `EV-ZONE` toevoegen aan `dxf_generator.py` — TC-ev-A t/m C
3. Review-pagina WAARSCHUWING-blok — TC-ev-D t/m F
4. PDF voetnoot — TC-ev-G t/m H
5. POST route `ev-mailreferentie` — TC-ev-I
6. Regressie DXF volledig draaien — TC-ev-J
7. Volledige testsuite — bestaande tests groen houden

---

## 9. Nieuwe en gewijzigde bestanden

| Bestand | Status |
|---------|--------|
| `app/documents/dxf_generator.py` | EV-ZONE laag toevoegen |
| `app/project/models.py` | +1 kolom `ev_mailreferentie` op `Project` |
| `app/project/router.py` | review-route + nieuwe POST ev-mailreferentie |
| `app/templates/project/review.html` | WAARSCHUWING-blok + mailreferentie formulier |
| `app/templates/project/pdf_tekening.html` | EV voetnoot in OPMERKINGEN |
| `alembic/versions/xxxx_ev_mailreferentie.py` | Nieuw |
| `tests/test_ev_zone.py` | Nieuw |
