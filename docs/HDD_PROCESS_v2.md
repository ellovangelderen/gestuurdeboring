# HDD Ontwerp Platform — Procesoverzicht
**Versie 2.0 | 2026-03-17**

---

## Cockpit-centraal

Het platform is geen stap-voor-stap wizard. De cockpit is het startpunt. Elke order is vanaf de cockpit in één klik bereikbaar.

```
┌─────────────────────────────────────────────┐
│                 COCKPIT                       │
│  Alle orders · Status · Deadlines · EV       │
│                                               │
│  [Order] → één klik naar:                    │
│    ├─ Tekening (per boring)                  │
│    ├─ Berekening (per boring)                │
│    ├─ Werkplan (per boring)                  │
│    ├─ KLIC data                              │
│    ├─ Kaart (PDOK / Waterschap)              │
│    └─ Correspondentie                        │
└─────────────────────────────────────────────┘
```

---

## Orderlevenscyclus

```
Order received → In progress → Delivered → Waiting for approval → Done
                                                                  ↘ Cancelled
```

| Status | Betekenis | Wie |
|---|---|---|
| Order received | Order ontvangen, nog niet gestart | Nid/Martien |
| In progress | Tekenaar werkt aan de order | Tekenaar |
| Delivered | Ontwerp opgeleverd aan opdrachtgever | Martien |
| Waiting for approval | Geleverd maar geen akkoord ontvangen | Systeem |
| Done | Akkoord ontvangen, order afgerond | Martien |
| Cancelled | Order geannuleerd | Martien |

---

## Werkproces per order

### 1. Order intake
- Order ontvangen via opdrachtgever (telefoon/email)
- Nid maakt order aan in cockpit
- Klantcode, locatie, ordernummer, deadline
- Type boringen (B/N/Z/C) + aantal
- Tekenaar toewijzen (default Martien)

### 2. KLIC aanvragen
- KLIC melding doen bij Kadaster
- Type: oriëntatiegraving (> 4 weken) of graafmelding (≤ 4 weken)
- Wachten op levering Kadaster
- ZIP uploaden in platform → gekoppeld aan order
- Bij hermelding: nieuwe versie uploaden

### 3. Brondata verzamelen
- KLIC verwerken: leidingen, EV-zones, sleufloze leidingen
- Maaiveld: AHN5 automatisch of handmatig invoeren
- Grondtype: GEF/CPT of handmatig
- Eisenprofiel selecteren (RWS/Waterschap/Provincie/Gemeente/ProRail)
- GWSW riooldata: upload of gemeente opvragen
- Topotijdreis: historische kaarten checken

### 4. Ontwerp (per boring)
- Tracé invoeren (RD-coördinaten + tussenpunten)
- Boorprofiel:
  - B/N: 5 segmenten (intreehoek, Rv_in, horizontaal, Rv_uit, uittreehoek)
  - Z: boogzinker (booghoek + stand)
  - C: geen profiel (alleen berekeningen)
- Conflictcheck K&L
- Review op kaart + lengteprofiel

### 5. Output genereren
- DXF tekening (per boring)
- PDF tekening (per boring)
- Werkplan (per boring, Claude API)
- Sigma berekening (indien gevraagd)
- Bestandsnamen: {ordernummer}-{volgnummer:02d}-rev.{n}

### 6. Oplevering
- Tekeningen downloaden of via Drive sync
- Status → Delivered
- Wekelijkse statusmail: herinnering aan opdrachtgever voor akkoord
- Na akkoord: status → Done
- Facturatie via SnelStart (toekomst)

---

## Vier boringtypen

| Type | Naam | Profiel | Output | Wanneer |
|---|---|---|---|---|
| B | Gestuurde boring | 5 segmenten | DXF + PDF + werkplan | Standaard |
| N | Nano boring | 5 segmenten (kleiner) | DXF + PDF + werkplan | Kleine boringen |
| Z/BZ | Boogzinker | 1 boog (5°/7,5°/10°) | DXF + PDF + werkplan | Vereenvoudigde boring |
| C | Calculatie | Geen | Sigma berekeningen (PDF) | Alleen berekeningen, geen tekening |

---

## Meerdere boringen per order

Een order kan meerdere boringen bevatten, elk met eigen type en KLIC:

```
Order 3D26V810
  ├─ Boring 01 (B) → KLIC 26O0185752 v2
  ├─ Boring 02 (B) → KLIC 26O0185752 v2 (zelfde KLIC)
  └─ Boring 03 (Z) → KLIC 26O0185761 (andere KLIC)
```

Extreme voorbeeld uit praktijk: EN26V201 Leidschendam → 7 boringen (B) + 3 boogzinkers (Z) op 1 order.

---

## Gebruikers

| Gebruiker | Rol | Werkzaamheden |
|---|---|---|
| Martien Luijben | Eigenaar, hoofdtekenaar | Reviewt en accordeert alle ontwerpen |
| Nid (Sopa Choychod) | Orderadministratie, tekenaar | Houdt orderlijst bij, maakt uitwerkingen |
| Michel Visser | 3D-Drilling contactpersoon | Reviewt output, niet actief in platform |

---

## Wekelijkse statusmail

Elke maandag automatisch per opdrachtgever:
- Openstaande akkoorden (langer dan X weken)
- Recent geleverde orders zonder bevestiging
- Opdrachtgever kan antwoorden → mail bij Martien

Doel: orders schoonhouden, sneller afrekenen.
