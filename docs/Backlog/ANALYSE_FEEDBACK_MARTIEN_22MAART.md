# Analyse — Feedback Martien 22 maart 2026 (email)
**Status: ANALYSE — acties per punt**

---

## Beslissingen (B1-B6) — Martien's antwoorden

### B1 — Buigradius per segment: UITBREIDEN
**Martien zegt:**
- Verschillende Rv is belangrijk (niet alleen intree/uittree)
- Andere pakketten kunnen ook verticale bochten in het horizontale deel (lokaal onder/over een leiding)
- Schuin op/aflopend horizontaal deel (maaiveld volgen bij lang tracé)
- Horizontaal: minimaal 4 bochten met verschillende radii (nu 3 in Excel)

**Impact:** Grote refactor van `bereken_boorprofiel()`. Het 5-segment model wordt een N-segment model met configureerbare Rv per segment. Dit is een fundamentele architectuurwijziging.

**Actie:** 🔴 HOOG — nieuw profiel-engine ontwerp nodig. Aparte taak.

---

### B2 — Bundelfactor: JA + verbetering
**Martien zegt:** Ja graag. Extra: bij meerdere buizen → Dg berekenen op basis van gemiddelde diameter (niet per se De van de grootste buis).

**Actie:** 🟠 Implementeren. Boring model uitbreiden met `aantal_buizen` en `bundel_diameters`.

---

### B3 — Ruimfactoren: JA + instelbaar
**Martien zegt:** Ja graag. Parameter moet instelbaar zijn als ze willen afwijken van default.

**Actie:** 🟠 Implementeren. Past bij ADM-5 (systeeminstellingen in admin panel).

---

### B4 — Boormachine: WEL op tekening
**Martien zegt:** Hoeft geen AutoCAD block te zijn, maar machine + boorgat weergeven op de tekening is belangrijk.

**Actie:** 🟡 Machine-selectie per boring + weergave in DXF/PDF bovenaanzicht.

---

### B5 — Type W: NEE, geen boringtype
**Martien zegt:** Werkplan is geen boringtype. Het is uitbreiding van documentatie bij B/N/Z/C.

**Actie:** ✅ Geen wijziging nodig. Werkplan blijft op order-niveau. Bij migratie: W-rijen uit Excel worden overgeslagen of als notitie opgeslagen.

---

### B6 — Standaard K&L dieptes: JA maar geen waarschuwing
**Martien zegt:**
- Iedereen weet dat KLIC indicatief is
- Waarschuwing niet nodig — is al in OPMERKINGEN
- KLIC is 2D, dieptes staan in annotatie/maatvoering-laag of als PDF bijlage
- As-Built tekeningen van geboorde leidingen tonen alleen lengteprofiel → Z-waarden daaruit halen is een uitdaging

**Impact:** Standaard dieptes mogen als fallback zonder extra waarschuwing. De uitdaging is het "lezen" van PDF bijlagen voor Z-waarden — dat is AI/OCR werk, toekomstig.

**Actie:** 🟠 Standaard dieptes implementeren als fallback in conflictcheck (zonder waarschuwingstekst).

---

## Verrijkingen (V1-V6)

### V1 — Klantcodes: COMPLETE LIJST (50 klanten!)
**Martien levert 50 klantcodes** met contactpersoon + logo-naam. Dit bevestigt ADM-2 (klantbeheer naar DB).

**Actie:** 🔴 Direct verwerken. Klantcodes updaten naar 50 entries. Logo-bestanden opvragen bij Martien.

### V2 — Boogzinker: GEEN hulptabel, berekening
**Martien zegt:** Lengte en diepte worden berekend uit R (stangradius) en P (stand 1-10). Stand P1=90° (leverancier noemt het 0°), P2=5°, ... P10=45°. De hoek op maaiveld verschilt van de hoek op 70cm boven maaiveld.

**Impact:** Onze `bereken_boorprofiel_z()` klopt niet helemaal — de hoek-input is op maaiveld, maar de leverancierstabel rekent vanaf 70cm boven maaiveld. Correctiefactor nodig.

**Actie:** 🟠 Boogzinker berekening verfijnen met 70cm offset.

### V3 — Logo's: JA, eindopdrachtgever
**Martien:** Naam + adres eindopdrachtgever, eventueel logo. Al eerder overwogen.

**Actie:** 🟡 Past bij ADM-2 klantbeheer + PDF titelblok 3e logo.

### V4 — EV handmatig: VERDUIDELIJKT
**Martien begreep de vraag niet.** We bedoelden: EV-partijen handmatig kunnen invoeren als er geen KLIC is. Martien's gebruik: standaard mail templates op basis van KLIC contactgegevens, maar liever met bekende vaste contacten die hij vaker gebruikt.

**Actie:** 🟡 "Favoriete contacten" per EV-beheerder. Platform leert welke contacten vaak gebruikt worden en suggereert die.

### V5 — Email contacten: SLIMME SUGGESTIES
**Martien zegt:** KLIC heeft soms verouderde contactgegevens. Als hij regelmatig een bepaald contact bij een gemeente gebruikt, wil hij dat het platform dat "leert" en suggereert.

**Actie:** 🟡 Contactpersonen-database die per beheerder bijhoudt welk contact het laatst/vaakst gebruikt is. Toekomstig.

### V6 — PDOK URLs: OK
**Geen verdere vragen.**

---

## Toekomstige items (T1-T5)

### T2 — AutoCAD script: KOMT TE VERVALLEN
**Martien:** "Die zou komen te vervallen als de nieuwe tool goed werkt."

**Actie:** ✅ Gebouwd maar niet prioriteit. Kan als fallback dienen.

### T3 — Bocht check: GEEN WAARSCHUWING nodig
**Martien:** "Dit is iets wat de engineer zelf beoordeelt, niet zwart-wit. Soms kies je bewust een krappere radius."

**Actie:** ✅ Gebouwd als utility. Geen harde warnings, alleen informatief.

### T4 — InfraCAD scripts: NIET nodig
**Martien:** "Ik dacht dat het de bedoeling is dat de tool dat overneemt."

**Actie:** ✅ Correct — het platform vervangt InfraCAD Map workflow. T4 geschrapt.

### T5 — CC-Master: NIET MEER IN GEBRUIK
**Martien:** "Dat is alweer een poosje geleden. We zijn werk kwijtgeraakt."

**Actie:** ✅ Geschrapt.

---

## SnelStart
**Martien:** Facturatie heeft niet de hoogste prio. Hij maakt nu maandoverzichten in Excel per opdrachtgever. Per order factureren zou handig zijn maar niet urgent. Excel overzicht kan niet naar SnelStart gekopieerd worden — dat is de reden dat hij nooit vanuit SnelStart factureert.

**Actie:** 🟡 Laag prio. Eventueel maandoverzicht per opdrachtgever als PDF/Excel genereren (vergelijkbaar met statusmail maar dan met bedragen).

---

## Klantcodes (50 stuks — compleet)

| Nr | Naam | Contact | Code | Logo |
|----|------|---------|------|------|
| 1 | 3D-Drilling | M.Visser | 3D | logo_3D |
| 2 | Verbree Boogzinkers | M.Verbree | VB | Verbree_logo |
| 3 | van Baarsen Buisleidingen | M.Visser | 3D | Baarsen_logo |
| 4 | Hogenhout | A.Hogenhout | HI | logo_Hogenhout |
| 5 | Liander | W.Meijer | LI | logo_Liander |
| 6 | RenD | M.v.Hoolwerff | RD | logo_RenD |
| 7 | Direxta | S.Battaioui | DX | logo_direxta |
| 8 | Kappert Boogzinkers | A.Kappert | KB | logo_kappert |
| 9 | VTV | H.vd.Bighelaar | VV | logo_VTV |
| 10 | NeijhofVisser | B.Neijhof | NV | logo_NeijhofVisser |
| 11 | RovoR | R.Bláha | — | logo_Rovor |
| 12 | Circet Nederland | T.v.Rooten | CN | logo_Circet |
| 13 | Artemis | E.Chatzidaki | AR | logo_Artemis |
| 14 | Eljes | H.Heiwegen | EI | logo_Eljes |
| 15 | Heuvel | D.Schafrat | HG | logo_Heuvel |
| 16 | Van Gelder | R.Aouragh | VG | logo_VanGelder |
| 17 | VWTelecom | M.v.Donselaar | VW | logo_VWT |
| 18 | BAM Infra | G.Kranenburg | BI | logo_BAM |
| 19 | Dmissi Energy | D.Brijder | DE | logo_DE |
| 20 | a.hak | T.Peeman | AH | logo_ahak |
| 21 | APK | T.vd Sloot | RA | logo_apk |
| 22 | MKC | F.Kleijn | — | logo_MKC |
| 23 | MIR Infratechniek | Ali (MIR) | — | MIR_logo |
| 24 | VanVulpen | N.Slagbom | VU | logo_vanVulpen |
| 25 | Polderzon | F.v.Pelt | PZ | logo_polderzon |
| 26 | VSH | L.Gorman | VS | logo_VSH |
| 30 | BTL | P.Visscher | BT | logo_BTLdrilling |
| 31 | TM | E.Heijnekamp | TM | logo_Tmtechniek |
| 32 | Talsma Infra | S.Talsma | TI | logo_Talsma |
| 33 | Quint&vanGinkel | A.Mikic | QG | logo_QuintvG |
| 34 | Euronet | N.Japenga | EN | logo_Euronet |
| 35 | Bruton Boortechniek | A.Hogenhout | BH | logo_Bruton |
| 36 | Fiberunie | A.Beelen | FU | logo_Fiberunie |
| 37 | MHT | F.Mouhout | MT | logo_MHT |
| 38 | KorfKB | K.Korf | KK | logo_KorfKB |
| 39 | HVI Infra | B.Hamers | HV | logo_HVI |
| 40 | FUES | R.Düztepe | FS | logo_FUES |
| 41 | C&C | G.Peker | CC | logo_C&C |
| 42 | Darico | B.Verweij | DI | logo_DI |
| 43 | BAAS | L.d.Dulk | BA | logo_BA |
| 44 | InfraKennis | K.Yilmaz | IK | Logo_InfraKennis |
| 45 | Generation Green | E.vd.Vlist | GG | logo_GG |
| 46 | Peek | R.Entrop | PK | logo_PK |
| 47 | DMMB | R.Wit | DM | logo_dmmb |
| 48 | Hanab | R.Kaman | HN | logo_HN |
| 49 | FonsBakker | E.Elsgeest | FB | logo_FB |

**Let op:** Nr 3 (van Baarsen) gebruikt klantcode "3D" — zelfde als 3D-Drilling. Nr 11, 22, 23 hebben geen klantcode.

---

## Nieuwe prioritering

### 🔴 Direct
| Item | Wat |
|------|-----|
| V1 | 50 klantcodes in systeem laden |
| B2 | Bundelfactor + Dg berekening |
| B3 | Ruimfactoren instelbaar |
| B6 | Standaard K&L dieptes als fallback (zonder waarschuwing) |

### 🟠 Korte termijn
| Item | Wat |
|------|-----|
| B1 | N-segment profiel engine (grote refactor) |
| V2 | Boogzinker 70cm offset correctie |
| B4 | Machine + boorgat op tekening |
| ADM-2 | Klantbeheer in admin panel (logo's, contacten) |

### 🟡 Later
| Item | Wat |
|------|-----|
| V5 | Slimme contact-suggesties per beheerder |
| V3 | Eindopdrachtgever logo op titelblok |
| B5 | Geen actie (werkplan ≠ boringtype) |

### ✅ Geschrapt
| Item | Reden |
|------|-------|
| T4 | Platform vervangt InfraCAD |
| T5 | CC-Master niet meer in gebruik |
