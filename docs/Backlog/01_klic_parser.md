# Builder Task — Backlog 1: KLIC IMKL 2.0 GML Parser
**HDD Ontwerp Platform · Backlog item 1**
Versie: 1.0 | 2026-03-15

---

## 1. Doel

Parseer het IMKL 2.0 GML-bestand uit de reeds opgeslagen KLIC ZIP (`KLICUpload.bestandspad`) en sla de gevonden kabels en leidingen op als `KLICLeiding`-records met geometrie (WKT, RD New EPSG:28992). Na verwerking verschijnen de leidingen als geometrie op de juiste NLCS-laag in de DXF output. Dit vervangt de placeholder leidingen uit de walking skeleton.

---

## 2. Scope

**Wel gebouwd:**
- Uitpakken KLIC ZIP naar tijdelijke map
- Detecteren en parsen van IMKL 2.0 GML-bestanden via `lxml`
- Per leiding extraheren: beheerder, leidingtype, geometrie (LineString of Polygon als WKT, RD New), diepte indien aanwezig
- Detectie sleufloze leidingen: mantelbuis zonder diepte + PDF-bijlage aanwezig → `sleufloze_techniek=True`
- Opslaan als `KLICLeiding`-records gekoppeld aan `project_id`
- `KLICUpload.verwerkt = True` na succesvolle verwerking
- Tonen van leidingen op brondata-pagina (tabel: beheerder, leidingtype, aantal, sleufloze_techniek)
- DXF generator uitbreiden: `KLICLeiding`-records tekenen als LWPolyline op de juiste NLCS-laag
- POST-route om verwerking handmatig te triggeren
- Waarschuwing tonen als alle dieptes ontbreken

**Niet gebouwd:**
- Conflictcheck 3D (backlog 7)
- PDF-bijlagen inhoudelijk parsen (backlog 5)
- AHN5 maaiveld (backlog 2)
- Kaart/Leaflet visualisatie van leidingen
- Verwijderen van eerder geparsede leidingen via UI

---

## 3. Technische keuzes

**Parser library:** `lxml` — robuust voor grote GML-bestanden (HDD11 ZIP = 13MB, 1127 leidingen).

**GML geometrie:** `shapely` voor WKT-conversie van GML LineString/Polygon-coördinaten. Coördinaten staan in RD New in IMKL 2.0 — geen projectie nodig, rechtstreeks opslaan.

**ZIP uitpakken:** `zipfile` (stdlib). Uitpakken naar `tempfile.TemporaryDirectory`, na verwerking opruimen. Originele ZIP blijft bewaard op `KLICUpload.bestandspad`.

**GML detectie:** Zoek in uitgepakte map naar bestanden met extensie `.xml` of `.gml`. Filter op IMKL namespace in root-element. Verwerk alle gevonden bestanden.

**Leidingtype mapping naar DXF-laag:**
```python
IMKL_THEMA_TO_LAYER = {
    "elektriciteit":  "LAAGSPANNING",   # verfijning via spanning hieronder
    "gas":            "LD-GAS",
    "water":          "WATERLEIDING",
    "riool":          "RIOOL-VRIJVERVAL",
    "telecom":        "LAAGSPANNING",
    "warmte":         "WATERLEIDING",
    "overig":         "LAAGSPANNING",
}

SPANNING_TO_LAYER = {
    "laagspanning":   "LAAGSPANNING",
    "middenspanning": "MIDDENSPANNING",
    "hoogspanning":   "HOOGSPANNING",
}
```

**Sleufloze leiding detectie:**
```python
# sleufloze_techniek=True als:
# 1. leidingtype bevat "mantelbuis" OF thema bevat "mantelbuis"
# 2. EN diepte_m IS NULL
# 3. EN er is een PDF-bijlage gelinkt in hetzelfde GML-feature
```

**DXF integratie:** Nieuwe functie `_draw_klic_leidingen(msp, project, db)` in `app/documents/dxf_generator.py`.

---

## 4. Datamodel

### Nieuw model: `KLICLeiding`

Toevoegen aan `app/project/models.py`:

```python
class KLICLeiding(Base):
    __tablename__ = "klic_leidingen"

    id                 = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id         = Column(String, ForeignKey("projects.id"), nullable=False)
    klic_upload_id     = Column(String, ForeignKey("klic_uploads.id"), nullable=False)
    beheerder          = Column(String)
    leidingtype        = Column(String)
    thema              = Column(String)
    dxf_laag           = Column(String)
    geometrie_wkt      = Column(Text)
    diepte_m           = Column(Float)
    diepte_override_m  = Column(Float)
    sleufloze_techniek = Column(Boolean, default=False)
    bron_pdf_url       = Column(String)
    imkl_feature_id    = Column(String)
```

### Uitbreiding: `KLICUpload`

```python
    aantal_leidingen  = Column(Integer)
    aantal_beheerders = Column(Integer)
    verwerk_fout      = Column(String)
    verwerkt_op       = Column(DateTime)
```

### Relaties

- `Project`: voeg `klic_leidingen` relatie toe via `KLICLeiding.project_id` (cascade delete)
- `KLICUpload`: voeg `leidingen` relatie toe naar `KLICLeiding` (cascade delete)

---

## 5. Routes

| Methode | Pad | Beschrijving |
|---|---|---|
| `POST` | `/api/v1/projecten/{project_id}/klic/{upload_id}/verwerken` | Trigger KLIC parsing. Synchroon. Redirect naar brondata. |
| `GET`  | `/api/v1/projecten/{project_id}/klic/status` | JSON: `{verwerkt, aantal_leidingen, aantal_beheerders, diepte_waarschuwing, sleufloze_count}` |

Bestaande upload-route blijft ongewijzigd.
Brondata-pagina uitbreiden: tabel met leidingen per beheerder + type + aantal na verwerking, plus waarschuwing als `diepte_m IS NULL` voor alle leidingen.

---

## 6. Acceptatiecriteria

```
TC-klic-A  HDD11 ZIP parsen → KLICUpload.verwerkt=True, verwerk_fout=None
TC-klic-B  HDD11 ZIP parsen → aantal_beheerders=11 (exact)
TC-klic-C  HDD11 ZIP parsen → aantal_leidingen=1127 (exact)
TC-klic-D  KL1040 Liander aanwezig → minstens 1 leiding thema="elektriciteit", dxf_laag correct
TC-klic-E  KL1049 Reggefiber → sleufloze_techniek=True op minstens 1 leiding
TC-klic-F  Alle 1127 leidingen HDD11 → diepte_m IS NULL (dieptePeil=GEEN is structureel)
TC-klic-G  GET klic/status → diepte_waarschuwing=True als alle leidingen geen diepte hebben
TC-klic-H  Minstens 95% van leidingen heeft geometrie_wkt niet None/leeg
TC-klic-I  geometrie_wkt bevat geldige WKT: shapely.from_wkt() gooit geen exception
TC-klic-J  Leidingen in RD-bereik NL: x ∈ [0, 300000], y ∈ [300000, 625000]
TC-klic-K  DXF na KLIC → laag "LAAGSPANNING" bevat minstens 1 LWPolyline
TC-klic-L  DXF na KLIC → alle bestaande lagen nog aanwezig (geen regressie TC-dxf-B)
TC-klic-M  POST verwerken met niet-bestaande upload_id → 404
TC-klic-N  Brondata-pagina toont tabel met beheerders na verwerking
TC-klic-O  Verwerking twee keer aanroepen → geen duplicaten (oude records verwijderd)
TC-klic-P  ZIP zonder GML → verwerk_fout beschrijvend, verwerkt=False, geen crash
```

---

## 7. Verwijzingen naar testdata

**Primaire testdata:** `docs/input_data_14maart/Levering_25O0136974_1.zip`

Exacte verwachte aantallen (uit CLAUDE_v4.md sectie 9):
- 11 beheerders
- 1127 leidingen totaal
- KL1049 Reggefiber: 3 mantelbuizen + PDF-bijlagen `boogzinker_8.pdf` en `gestuurde_boring_13.pdf`
- KL1040 Liander: 476 leidingen (LS + MS + Gas + Data)
- GM0392 Gemeente Haarlem: 708 leidingen (LS + riool)
- KL1100 PWN: 72 waterleidingen
- `dieptePeil=GEEN` bij **alle** leidingen — structureel, niet een fout

**Nieuwe bestanden:**
- `app/geo/klic_parser.py`
- `tests/test_klic_parser.py`

**Alembic migratie** voor nieuwe tabel en kolommen (conform builder-hdd.md: altijd Alembic — nooit raw ALTER TABLE).
