# GSheets → Platform Migratiestrategie
**Versie 1.0 | 2026-03-17**

---

## Bron

GSheets "Order overview - Vergunning"
- ~2087 rijen
- ~2454 orders (inclusief meerdere rijen per order)
- Bijgehouden door Nid (Sopa Choychod) en Martien
- CSV export beschikbaar: `docs/Order overview - Vergunning.csv`

---

## Beslissing: Platform wordt de bron

GSheets wordt niet naast het platform gedraaid. Na migratie is het platform het systeem of record. GSheets blijft als archief-backup. Export naar CSV/Excel altijd beschikbaar vanuit het platform.

---

## Kolom-mapping

| GSheets kolom | Voorbeeld | Map naar | Transformatie |
|---|---|---|---|
| Date | 16-3-2026 | order.ontvangen_op | Parse DD-M-YYYY |
| Order name | "3D26V824 Zevenhuizen, Bredeweg" | order.ordernummer + order.locatie | Split: ordernummer = eerste woord, locatie = rest |
| Client | 3D | order.klantcode | Direct |
| Status | Order received | order.status | Enum mapping (zie onder) |
| Date requested | 6-Apr-2026 | order.deadline | Parse D-Mon-YYYY |
| Date of delivery | 26-Feb-2026 | order.geleverd_op | Parse D-Mon-YYYY, nullable |
| Type1 + Amt | B, 1 | Boring(type=B) × Amt | Create N borings |
| Type2 + Amt | Z, 3 | Boring(type=Z) × Amt | Create N borings (optioneel) |
| Permit required | P / W / R / - | order.vergunning | Direct |
| Note | "PRIO" / vrije tekst | order.prio + order.notitie | Extract "PRIO" → prio=True, rest → notitie |
| KLIC | 26O0036028 | KLICUpload.meldingnummer | Direct, versie=1 |
| Google Maps | URL | order.google_maps_url | Direct |
| PDOK | URL | order.pdok_url | Direct + extract RD coords |
| Waterkering | URL | order.waterkering_url | Direct |
| Oppervlaktewater | URL | order.oppervlaktewater_url | Direct |
| Peil | URL | order.peil_url | Direct |
| EV1-EV5 | "Liander: HS" | EVPartij[] | Per non-empty kolom 1 record |
| Email1-Email6 | "Gem. Ermelo" | EmailContact[] | Per non-empty kolom 1 record |

### Status mapping

| GSheets | Platform enum |
|---|---|
| Order received | order_received |
| In progress | in_progress |
| Delivered | delivered |
| Waiting for approval | waiting_for_approval |
| Done | done |
| Cancelled | cancelled |

---

## RD-coördinaten extractie uit PDOK URL

PDOK URLs bevatten RD New coördinaten:
```
https://app.pdok.nl/viewer/#x=101795.66&y=448606.99&z=13.6667...
```

Regex: `x=(\d+\.?\d*)&y=(\d+\.?\d*)`

Bij migratie: extraheer x,y → sla op als startcoördinaat voor de eerste boring. Dit is een initieel oriëntatiepunt, geen exact tracépunt.

---

## Meerdere rijen per order

Orders met meerdere boringen staan als aparte rijen met hetzelfde ordernummer:

```
Rij 24: 3D26V822 Velsen-Noord (HDD29)  → B, 1
Rij 25: 3D26V822 Velsen-Noord (HDD15)  → B, 1
Rij 26: 3D26V822 Velsen-Noord (BZ2)    → Z, 1
```

Migratiescript groepeert op ordernummer:
1. Eerste rij → Order aanmaken
2. Volgende rijen met zelfde ordernummer → extra Borings toevoegen
3. Boring naam extraheren uit haakjes in Order name: "(HDD29)" → naam="HDD29"

---

## Migratiestappen

### Stap 1 — Klantcodes seeden
22+ unieke klantcodes uit CSV als seed-data. Martien heeft meteen dropdown bij "Nieuwe order".

### Stap 2 — CSV parsen en importeren
Python migratiescript:
1. CSV inlezen
2. Groeperen op ordernummer
3. Per groep: Order + Borings + KLICUpload + EVPartij + EmailContact aanmaken
4. RD-coördinaten extraheren uit PDOK URLs
5. PRIO extraheren uit Note-veld

### Stap 3 — Validatie
- Aantal orders in platform = aantal unieke ordernummers in CSV
- Steekproef: 10 orders handmatig controleren
- Alle statussen correct gemapped
- Geen data verloren

### Stap 4 — Martien vult aan
Ontbrekende velden (tracé-coördinaten, leidingparameters) worden door Martien aangevuld wanneer hij een order oppakt in het platform.

---

## Risico's

| Risico | Mitigatie |
|---|---|
| Data inconsistentie in GSheets | Validatiescript rapporteert anomalieën |
| Meerdere rijen niet correct gegroepeerd | Ordernummer als groepeersleutel, handmatige check bij afwijkingen |
| PDOK URL niet altijd aanwezig | Coördinaten nullable, Martien vult later aan |
| Datumformaten inconsistent | Meerdere parse-patronen proberen |
