# HDD Ontwerp Platform - Datamodel Specificatie v6

---

## 1. Overzicht

Entiteit-relatiediagram van het volledige datamodel:

```
Order (ordernummer, klantcode, status, tekenaar, deadline...)
  ├─ KLICUpload[] (meldingnummer + versie, op order-niveau)
  ├─ EVPartij[] (max 5)
  ├─ EmailContact[] (max 6)
  └─ Boring[] (volgnummer, type B/N/Z/C)
       ├─ BoringKLIC[] → KLICUpload (many-to-many, engineer kiest versie)
       ├─ TracePunt[] (alleen B/N/Z)
       ├─ MaaiveldOverride (alleen B/N/Z)
       ├─ Doorsnede[] (alleen B/N/Z)
       ├─ Berekening (B/N/Z/C)
       ├─ BoorProfiel (B/N: 5-segment, Z: boogzinker)
       ├─ KLICLeiding[] (via BoringKLIC)
       └─ Document[] (dxf/pdf/werkplan)
```

**Kardinaliteit:**

| Relatie | Type |
|---|---|
| Order → Boring | 1:N |
| Order → KLICUpload | 1:N |
| Order → EVPartij | 1:N (max 5) |
| Order → EmailContact | 1:N (max 6) |
| Boring ↔ KLICUpload | M:N (via BoringKLIC) |
| Boring → TracePunt | 1:N |
| Boring → MaaiveldOverride | 1:0..1 |
| Boring → Doorsnede | 1:N |
| Boring → Berekening | 1:0..1 |
| Boring → BoorProfiel | 1:0..1 |
| Boring → Document | 1:N |
| KLICUpload → KLICLeiding | 1:N |

---

## 2. Entiteiten

### 2.1 Order

Hoofdentiteit voor elke opdracht. Bevat klant- en planningsgegevens.

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| id | String (UUID4) | PK | nee | `uuid4()` | Primaire sleutel |
| workspace_id | String | FK workspaces.id | nee | - | Workspace waartoe de order behoort |
| ordernummer | String | - | nee | - | Uniek ordernummer, bijv. `"3D26V824"` |
| locatie | String | - | ja | - | Locatieomschrijving, bijv. `"Zevenhuizen, Bredeweg"` |
| klantcode | String | - | ja | - | Klantafkorting, bijv. `"3D"`, `"TM"`, `"KB"` |
| opdrachtgever | String | - | ja | - | Volledige naam, bijv. `"3D-Drilling BV"` |
| status | String | - | nee | `"order_received"` | Enum: `order_received / in_progress / delivered / waiting_for_approval / done / cancelled` |
| ontvangen_op | DateTime | - | ja | - | Datum waarop order is ontvangen |
| deadline | DateTime | - | ja | - | Gewenste leverdatum |
| geleverd_op | DateTime | - | ja | - | Werkelijke leverdatum |
| vergunning | String | - | nee | `"-"` | Vergunningtype: `P / W / R / -` |
| prio | Boolean | - | nee | `False` | Prioriteitsvlag |
| notitie | Text | - | ja | - | Vrij tekstveld voor opmerkingen |
| tekenaar | String | - | nee | `"martien"` | Toegewezen tekenaar |
| google_maps_url | String | - | ja | - | Link naar Google Maps locatie |
| pdok_url | String | - | ja | - | Link naar PDOK viewer (bevat RD-coordinaten) |
| waterkering_url | String | - | ja | - | Link naar waterkeringenkaart |
| oppervlaktewater_url | String | - | ja | - | Link naar oppervlaktewaterkaart |
| peil_url | String | - | ja | - | Link naar peilkaart |
| aangemaakt_op | DateTime | - | nee | `now()` | Tijdstip van aanmaak |

### 2.2 Boring

Individuele boring binnen een order. Een order bevat 1 of meer boringen.

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| id | String (UUID4) | PK | nee | `uuid4()` | Primaire sleutel |
| order_id | String | FK orders.id | nee | - | Referentie naar bovenliggende order |
| volgnummer | Integer | - | nee | - | Volgnummer binnen order: `01, 02, 03...` |
| type | String | - | nee | - | Boringtype: `B / N / Z / C` |
| naam | String | - | ja | - | Optionele naam, bijv. `"HDD29"`, `"BZ2"` |
| materiaal | String | - | nee | `"PE100"` | Buismateriaal (alleen B/N/Z) |
| SDR | Integer | - | nee | `11` | Standard Dimension Ratio |
| De_mm | Float | - | nee | `160.0` | Buitendiameter buis (mm) |
| dn_mm | Float | - | ja | - | Override nominale diameter (mm) |
| medium | String | - | nee | `"Drukloos"` | Transportmedium |
| Db_mm | Float | - | nee | `60.0` | Diameter boorkop (mm) |
| Dp_mm | Float | - | nee | `110.0` | Diameter pilotboring (mm) |
| Dg_mm | Float | - | nee | `240.0` | Diameter geboord gat (mm) |
| intreehoek_gr | Float | - | ja | - | Intreehoek in graden (alleen B/N) |
| uittreehoek_gr | Float | - | ja | - | Uittreehoek in graden (alleen B/N) |
| booghoek_gr | Float | - | ja | - | Booghoek in graden (alleen Z, waarden: `5 / 7.5 / 10`) |
| stand | Integer | - | ja | - | Standinstelling boogzinker (alleen Z, waarden: `1-10`) |
| status | String | - | nee | `"concept"` | Status van de boring |
| aangemaakt_door | String | - | nee | - | Gebruiker die de boring heeft aangemaakt |
| aangemaakt_op | DateTime | - | nee | `now()` | Tijdstip van aanmaak |

### 2.3 KLICUpload

KLIC-melding gekoppeld aan een order. Meerdere versies per meldingnummer mogelijk.

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| id | String (UUID4) | PK | nee | `uuid4()` | Primaire sleutel |
| order_id | String | FK orders.id | nee | - | Referentie naar order |
| meldingnummer | String | - | nee | - | KLIC-meldingnummer, bijv. `"26O0185752"` |
| versie | Integer | - | nee | `1` | Versienummer van de upload |
| type | String | - | nee | - | Type melding: `orientatie / graaf / hermelding` |
| bestandsnaam | String | - | nee | - | Oorspronkelijke bestandsnaam |
| bestandspad | String | - | nee | - | Opslaglocatie van het bestand |
| upload_datum | DateTime | - | nee | `now()` | Tijdstip van upload |
| verwerkt | Boolean | - | nee | `False` | Of het bestand succesvol verwerkt is |
| aantal_leidingen | Integer | - | ja | - | Aantal gevonden leidingen na verwerking |
| aantal_beheerders | Integer | - | ja | - | Aantal netbeheerders na verwerking |
| verwerk_fout | String | - | ja | - | Foutmelding indien verwerking mislukt |
| verwerkt_op | DateTime | - | ja | - | Tijdstip van verwerking |

### 2.4 BoringKLIC (koppeltabel)

Many-to-many relatie tussen Boring en KLICUpload. De engineer kiest welke KLIC-versie bij welke boring hoort.

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| boring_id | String | PK, FK borings.id | nee | - | Referentie naar boring |
| klic_upload_id | String | PK, FK klic_uploads.id | nee | - | Referentie naar KLIC-upload |

### 2.5 KLICLeiding

Individuele leiding uit een KLIC-melding.

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| id | String (UUID4) | PK | nee | `uuid4()` | Primaire sleutel |
| klic_upload_id | String | FK klic_uploads.id | nee | - | Referentie naar KLIC-upload |
| beheerder | String | - | nee | - | Naam netbeheerder |
| leidingtype | String | - | nee | - | Type leiding |
| thema | String | - | nee | - | KLIC-thema |
| dxf_laag | String | - | nee | - | DXF-laagnaam |
| geometrie_wkt | Text | - | nee | - | Geometrie in WKT-formaat |
| diepte_m | Float | - | ja | - | Diepte uit KLIC-data (m) |
| diepte_override_m | Float | - | ja | - | Handmatige diepte-override (m) |
| sleufloze_techniek | Boolean | - | nee | `False` | Of de leiding sleufloze techniek betreft |
| bron_pdf_url | String | - | ja | - | URL naar bron-PDF van beheerder |
| imkl_feature_id | String | - | ja | - | IMKL feature identifier |
| ev_verplicht | Boolean | - | nee | `False` | Eisvoorzorgsmaatregelen verplicht |
| ev_contactgegevens | String | - | ja | - | Contactgegevens voor EV |

### 2.6 TracePunt

Punten op het trace van een boring (intree, tussenpunten, uittree).

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| id | String (UUID4) | PK | nee | `uuid4()` | Primaire sleutel |
| boring_id | String | FK borings.id | nee | - | Referentie naar boring |
| volgorde | Integer | - | nee | - | Volgorde van het punt op het trace |
| type | String | - | nee | - | Punttype: `intree / tussenpunt / uittree` |
| RD_x | Float | - | nee | - | Rijksdriehoek X-coordinaat |
| RD_y | Float | - | nee | - | Rijksdriehoek Y-coordinaat |
| Rh_m | Float | - | ja | - | Horizontale afstand (m) |
| label | String | - | ja | - | Label, bijv. `"A"`, `"Tv1"` |

### 2.7 MaaiveldOverride

Handmatige of berekende maaiveldhoogtes voor intree- en uitreepunt.

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| id | String (UUID4) | PK | nee | `uuid4()` | Primaire sleutel |
| boring_id | String | FK borings.id | nee | - | Referentie naar boring |
| MVin_NAP_m | Float | - | nee | - | Maaiveld intree in m NAP |
| MVuit_NAP_m | Float | - | nee | - | Maaiveld uittree in m NAP |
| bron | String | - | nee | `"handmatig"` | Bron van de waarden |
| MVin_bron | String | - | nee | `"handmatig"` | Bron intree-maaiveld |
| MVuit_bron | String | - | nee | `"handmatig"` | Bron uittree-maaiveld |
| MVin_ahn5_m | Float | - | ja | - | AHN5-waarde intree (m NAP) |
| MVuit_ahn5_m | Float | - | ja | - | AHN5-waarde uittree (m NAP) |

### 2.8 Doorsnede

Gronddoorsnede-punten langs het traceprofiel.

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| id | String (UUID4) | PK | nee | `uuid4()` | Primaire sleutel |
| boring_id | String | FK borings.id | nee | - | Referentie naar boring |
| volgorde | Integer | - | nee | - | Volgorde in de doorsnede |
| afstand_m | Float | - | nee | - | Afstand langs het trace (m) |
| NAP_m | Float | - | nee | - | Hoogte in m NAP |
| grondtype | String | - | nee | `"Zand"` | Type grond |
| GWS_m | Float | - | nee | - | Grondwaterstand (m NAP) |
| phi_graden | Float | - | nee | `35.0` | Interne wrijvingshoek (graden) |
| E_modulus | Float | - | nee | `75.0` | Elasticiteitsmodulus (MPa) |
| override_vlag | Boolean | - | nee | `True` | Of waarden handmatig zijn overschreven |

### 2.9 Berekening

Resultaat van de trekkrachtberekening voor een boring.

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| id | String (UUID4) | PK | nee | `uuid4()` | Primaire sleutel |
| boring_id | String | FK borings.id | nee | - | Referentie naar boring |
| Ttot_N | Float | - | nee | - | Totale trekkracht (Newton) |
| bron | String | - | nee | `"sigma_override"` | Bron van de berekening |
| override_datum | DateTime | - | nee | - | Datum van de berekening/override |

### 2.10 BoorProfiel

Geometrisch profiel van de boring (5-segment of boogzinker).

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| id | String (UUID4) | PK | nee | `uuid4()` | Primaire sleutel |
| boring_id | String | FK borings.id | nee | - | Referentie naar boring |
| type | String | - | nee | - | Profieltype: `5segment / boogzinker` |
| L_totaal_m | Float | - | nee | - | Totale boorlengte (m) |
| L_hor_m | Float | - | ja | - | Horizontale lengte (m), niet van toepassing voor boogzinker |
| geometrie_wkt | Text | - | nee | - | Profielgeometrie in WKT-formaat |
| sensorpunten_json | Text | - | ja | - | Sensorpunten als JSON |

### 2.11 Document

Gegenereerde documenten (tekeningen, werkplannen, berekeningen).

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| id | String (UUID4) | PK | nee | `uuid4()` | Primaire sleutel |
| boring_id | String | FK borings.id | nee | - | Referentie naar boring |
| type | String | - | nee | - | Documenttype: `pdf / dxf / werkplan / sigma` |
| versie | Integer | - | nee | `1` | Revisienummer |
| drive_url | String | - | ja | - | URL naar bestand in Google Drive |
| created_at | DateTime | - | nee | `now()` | Tijdstip van aanmaak |

### 2.12 EVPartij

Eisvoorzorgsmaatregelen-partij gekoppeld aan een order (max 5).

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| id | String (UUID4) | PK | nee | `uuid4()` | Primaire sleutel |
| order_id | String | FK orders.id | nee | - | Referentie naar order |
| naam | String | - | nee | - | Naam partij, bijv. `"Liander: HS"`, `"Nederlandse Gasunie West"` |
| volgorde | Integer | - | nee | - | Positie (1-5) |

### 2.13 EmailContact

E-mailcontact gekoppeld aan een order (max 6).

| Kolom | Type | PK/FK | Nullable | Default | Beschrijving |
|---|---|---|---|---|---|
| id | String (UUID4) | PK | nee | `uuid4()` | Primaire sleutel |
| order_id | String | FK orders.id | nee | - | Referentie naar order |
| naam | String | - | nee | - | Naam contact, bijv. `"Gem. Ermelo"`, `"Rijkswaterstaat West-Nederland Zuid"` |
| volgorde | Integer | - | nee | - | Positie (1-6) |

---

## 3. Enumeraties

### OrderStatus

| Waarde | Beschrijving |
|---|---|
| `order_received` | Order ontvangen |
| `in_progress` | In bewerking |
| `delivered` | Geleverd |
| `waiting_for_approval` | Wacht op goedkeuring |
| `done` | Afgerond |
| `cancelled` | Geannuleerd |

### BoringType

| Waarde | Beschrijving |
|---|---|
| `B` | Gestuurde boring |
| `N` | Nano |
| `Z` | Boogzinker (BZ) |
| `C` | Calculatie |

### Vergunning

| Waarde | Beschrijving |
|---|---|
| `P` | Provincie |
| `W` | Waterschap |
| `R` | RWS / Rijk |
| `-` | Geen vergunning nodig |

### KLICType

| Waarde | Beschrijving |
|---|---|
| `orientatie` | Orientatiemelding |
| `graaf` | Graafmelding |
| `hermelding` | Hermelding |

### ProfielType

| Waarde | Beschrijving |
|---|---|
| `5segment` | 5-segmenten profiel (B/N) |
| `boogzinker` | Boogzinkerprofiel (Z) |

### DocumentType

| Waarde | Beschrijving |
|---|---|
| `pdf` | PDF-tekening |
| `dxf` | DXF-bestand |
| `werkplan` | Werkplan PDF |
| `sigma` | Sigma-berekening |

---

## 4. Bestandsnaamconventie

Alle gegenereerde bestanden volgen een vaste naamconventie:

```
{ordernummer}-{volgnummer:02d}-rev.{revisie}.dxf
{ordernummer}-{volgnummer:02d}-rev.{revisie}.pdf
{ordernummer}-werkplan-{volgnummer:02d}-rev.{revisie}.pdf
```

**Voorbeelden:**

| Bestand | Toelichting |
|---|---|
| `3D26V810-01-rev.1.dxf` | DXF-tekening, boring 01, revisie 1 |
| `3D26V810-02-rev.1.pdf` | PDF-tekening, boring 02, revisie 1 |
| `3D26V810-werkplan-01-rev.1.pdf` | Werkplan, boring 01, revisie 1 |

---

## 5. GSheets kolom-mapping

Mapping van de bestaande Google Sheets kolommen naar het nieuwe datamodel.

| GSheets kolom | Voorbeeld | Map naar | Niveau | Transformatie |
|---|---|---|---|---|
| Date | `16-3-2026` | `order.ontvangen_op` | Order | Parse DD-M-YYYY |
| Order name | `"3D26V824 Zevenhuizen, Bredeweg"` | `order.ordernummer` + `order.locatie` | Order | Split op eerste spatie |
| Client | `3D` | `order.klantcode` | Order | Direct |
| Status | `Order received` | `order.status` | Order | Map naar enum |
| Date requested | `6-Apr-2026` | `order.deadline` | Order | Parse D-Mon-YYYY |
| Date of delivery | `26-Feb-2026` | `order.geleverd_op` | Order | Parse D-Mon-YYYY |
| Type1 + Amt | `B, 1` | `boring.type` + count | Boring | Create N borings |
| Type2 + Amt | `Z, 3` | `boring.type` + count | Boring | Create N borings |
| Permit required | `P` | `order.vergunning` | Order | Direct |
| Note | `"PRIO"` or text | `order.prio` + `order.notitie` | Order | Extract PRIO flag |
| KLIC | `26O0036028` | `klic_upload.meldingnummer` | Order | Direct |
| Google Maps | URL | `order.google_maps_url` | Order | Direct |
| PDOK | URL met `x=...&y=...` | `order.pdok_url` + extract RD coords | Order | Regex `x=(\d+\.\d+)&y=(\d+\.\d+)` |
| Waterkering | URL | `order.waterkering_url` | Order | Direct |
| Oppervlaktewater | URL | `order.oppervlaktewater_url` | Order | Direct |
| Peil | URL | `order.peil_url` | Order | Direct |
| EV1-EV5 | `"Liander: HS"` | `ev_partij.naam` | Order | Create per non-empty |
| Email1-Email6 | `"Gem. Ermelo"` | `email_contact.naam` | Order | Create per non-empty |

### Status mapping

| GSheets waarde | Datamodel waarde |
|---|---|
| `Order received` | `order_received` |
| `In progress` | `in_progress` |
| `Delivered` | `delivered` |
| `Waiting for approval` | `waiting_for_approval` |
| `Done` | `done` |
| `Cancelled` | `cancelled` |

---

## 6. Type-specifieke regels

Niet elk boringtype heeft dezelfde velden en outputs. Onderstaande matrix toont de verschillen.

| Aspect | B (Boring) | N (Nano) | Z (Boogzinker) | C (Calculatie) |
|---|---|---|---|---|
| Profiel | 5 segmenten | 5 segmenten | 1 boog | Geen |
| Parameters | intreehoek, uittreehoek, Rv_in, Rv_uit, L_hor | idem (kleiner) | booghoek (5/7.5/10), stand (1-10) | Geen |
| TracePunten | Ja | Ja | Ja | Nee |
| DXF output | Ja | Ja | Ja (1 ARC) | Nee |
| PDF tekening | Ja | Ja | Ja | Nee |
| Werkplan | Ja | Ja | Ja | Nee |
| Berekening | Optioneel | Optioneel | Optioneel | **VERPLICHT** (= het product) |
| Document types | dxf, pdf, werkplan | dxf, pdf, werkplan | dxf, pdf, werkplan | sigma |

### Validatieregels per type

**B (Gestuurde boring):**
- `intreehoek_gr` en `uittreehoek_gr` zijn verplicht
- `booghoek_gr` en `stand` moeten `null` zijn
- BoorProfiel.type = `5segment`

**N (Nano):**
- Zelfde regels als B, maar kleinere diameters verwacht

**Z (Boogzinker):**
- `booghoek_gr` is verplicht, waarden: `5`, `7.5`, of `10`
- `stand` is verplicht, waarden: `1` t/m `10`
- `intreehoek_gr` en `uittreehoek_gr` moeten `null` zijn
- BoorProfiel.type = `boogzinker`

**C (Calculatie):**
- Geen TracePunten, MaaiveldOverride, Doorsnede, of BoorProfiel
- Berekening is **verplicht**
- Document.type = `sigma`

---

## 7. Migratie-notities

### Omvang

- Circa **2087 rijen** in Google Sheets
- Circa **2454 unieke orders** verwacht na deduplicatie

### Transformatieregels

1. **Order name splitsen:**
   - Alles voor de eerste spatie wordt `order.ordernummer`
   - Alles na de eerste spatie wordt `order.locatie`
   - Voorbeeld: `"3D26V824 Zevenhuizen, Bredeweg"` wordt ordernummer `"3D26V824"` en locatie `"Zevenhuizen, Bredeweg"`

2. **Meerdere rijen per ordernummer:**
   - Orders met hetzelfde ordernummer worden samengevoegd tot 1 Order-record
   - Elke rij levert 1 of meer Boring-records op

3. **Type1 + Type2 combinatie:**
   - Sommige rijen hebben zowel Type1 als Type2
   - Beide types genereren aparte Boring-records met oplopende volgnummers

4. **Note-veld:**
   - Als het woord `"PRIO"` voorkomt: `order.prio = True`
   - Overige tekst wordt opgeslagen in `order.notitie`

5. **RD-coordinaten uit PDOK URL:**
   - Extractie via regex: `x=(\d+\.\d+)&y=(\d+\.\d+)`
   - Kunnen worden opgeslagen als initieel TracePunt

6. **EV-partijen en Email-contacten:**
   - Alleen niet-lege velden worden als records aangemaakt
   - Volgorde correspondeert met kolomnummer (EV1=1, EV2=2, etc.)

7. **Datumformaten:**
   - `Date` kolom: `DD-M-YYYY` formaat
   - `Date requested` en `Date of delivery`: `D-Mon-YYYY` formaat (bijv. `6-Apr-2026`)
