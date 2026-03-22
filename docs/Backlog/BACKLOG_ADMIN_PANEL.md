# Backlog — Admin Panel
**Datum: 22 maart 2026**
**Status: TODO — ontwerp + implementatie**

---

## Doel

Een beheer-tab in het platform, alleen zichtbaar voor admins, waar alle systeemconfiguratie en databeheer kan plaatsvinden zonder code-wijzigingen of CLI-commando's.

---

## Toegang

- Alleen zichtbaar voor users met admin-rol
- Initieel: `martien` en `ello` (of een aparte `admin` user)
- Niet zichtbaar voor `sopa`, `lucas`, `visser` tenzij admin-rechten

---

## Modules

### ADM-1 — Gebruikersbeheer
- ✅ Overzicht van alle users met rollen (DONE — read-only)
- ❌ Nieuwe user aanmaken via admin portal (username, wachtwoord, rol)
- ❌ User deactiveren/inactief maken (niet verwijderen)
- ❌ Wachtwoord wijzigen via admin portal
- ❌ Rol toekennen: `admin` / `tekenaar` / `viewer`
- **Huidige situatie:** Users staan in `.env` — moet naar DB tabel
- **Vereist:** User model met wachtwoord hash (bcrypt), session management
- **Effort:** 4-6 uur (grote refactor van auth systeem)

### ADM-2 — Opdrachtgevers / Klantbeheer
- CRUD voor klanten (code, naam, contactpersoon, logo)
- Logo uploaden per klant (wordt gebruikt in PDF titelblok)
- Contactpersoon per klant (akkoord_contact)
- Email adressen per klant
- **Huidige situatie:** Hardcoded in `klantcodes.py` — moet naar DB

### ADM-3 — Data Import
- Excel upload (Order overview) — al gebouwd
- KLIC ZIP upload — al gebouwd per order
- GEF bestanden uploaden per boring
- Validatie + preview vóór import
- Wis-optie (reset database)

### ADM-4 — Data Export / Backup
- Database download (SQLite bestand)
- CSV export alle orders — al gebouwd
- CSV export klantlijst
- Volledige backup als ZIP (DB + uploads + logo's)

### ADM-5 — Systeeminstellingen
- Platform naam / versie
- Standaard tekenaar
- Standaard dekking (min meters)
- Bundelfactoren (1/2/3/4 buizen) — uit Excel analyse B2
- Ruimfactoren (enkelbuis/bundel/boogzinker) — uit Excel analyse B3
- Standaard K&L indicatieve dieptes — uit Excel analyse B6
- Boormachines (VermeerD40, Pers) — uit Excel analyse B4

### ADM-6 — Eisenprofielen beheer
- CRUD voor eisenprofielen (beheerder, dekking_weg, dekking_water, Rmin)
- Nu als seed data — moet bewerkbaar zijn
- Versie/datum per profiel

### ADM-7 — Externe kaartlinks beheer
- Beheer lijst van externe kaarten per type
- RWS, ProRail, waterschap URLs
- Gemeente-specifieke portalen (bijv. kaart.haarlem.nl)
- URLs veranderen regelmatig — admin moet ze kunnen bijwerken

### ADM-8 — Logging / Audit
- Recente login pogingen (gelukt + mislukt)
- Recente wijzigingen (wie, wat, wanneer)
- Systeem status (DB grootte, aantal orders, uptime)

---

## Prioritering

| Prio | ID | Item | Effort |
|------|-----|------|--------|
| 🔴 | ADM-2 | Klantbeheer (code, naam, contact, logo) | 3-4 uur |
| 🔴 | ADM-4 | Data export / backup download | 1 uur |
| 🟠 | ADM-1 | Gebruikersbeheer | 4-6 uur (users naar DB) |
| 🟠 | ADM-3 | Data import (Excel, GEF) | 2 uur (deels gebouwd) |
| 🟠 | ADM-5 | Systeeminstellingen | 2-3 uur |
| 🟡 | ADM-6 | Eisenprofielen beheer | 1-2 uur |
| 🟡 | ADM-7 | Externe kaartlinks beheer | 1-2 uur |
| 🟡 | ADM-8 | Logging / audit | 2-3 uur |

---

## Technische aanpak

### Route structuur
```
/admin/                     Dashboard (overzicht)
/admin/users                Gebruikersbeheer
/admin/klanten              Klantbeheer + logo's
/admin/import               Data import
/admin/export               Data export / backup
/admin/instellingen         Systeeminstellingen
/admin/eisenprofielen       Eisenprofielen
/admin/kaartlinks           Externe kaartlinks
/admin/logs                 Logging / audit
```

### Auth
- Nieuwe kolom `rol` op user (admin/tekenaar/viewer)
- Middleware check: `/admin/*` routes alleen voor admin
- Of simpeler: admin users lijst in settings

### Data migratie
- Klantcodes van `klantcodes.py` → DB tabel `klanten`
- Users van `.env` → DB tabel `users` (met wachtwoord hash)
- Eisenprofielen zijn al in DB

---

## Afhankelijkheden

- ADM-1 (users naar DB) is een grotere refactor van auth systeem
- ADM-2 (klanten naar DB) vereist migratie van hardcoded klantcodes
- ADM-4 (export) is onafhankelijk — kan als eerste
- ADM-5 (instellingen) lost B2/B3/B6 beslissingen op (configureerbaar ipv hardcoded)
