# Disaster Recovery — HDD Ontwerp Platform

## Overzicht

| Metric | Waarde |
|---|---|
| **RPO** (max dataverlies) | < 24 uur (dagelijkse backup) |
| **RTO** (max downtime) | < 15 minuten |
| **Backup locatie** | Cloudflare R2 bucket `hdd-backups` |
| **Wat wordt gebackupt** | SQLite database + logo bestanden |
| **Retentie** | 30 dagen |

## Scenario's

### 1. Railway volume corrupt / kwijt
**Symptoom:** 502 of lege database na deploy.
**Herstel:**
1. Ga naar `/admin/export` → "Restore vanuit R2"
2. Laat datum leeg (pakt laatste backup) of vul specifieke datum in
3. Klik "Restore" → bevestig
4. Database + logo's worden hersteld

### 2. Railway service niet bereikbaar
**Symptoom:** Site helemaal down.
**Herstel:**
1. Check Railway dashboard: https://railway.app
2. Als service crasht: bekijk logs, fix code, redeploy
3. Na redeploy: restore vanuit R2 als data kwijt is (zie scenario 1)

### 3. Per ongeluk data gewist
**Symptoom:** Orders of klanten verdwenen.
**Herstel:**
1. Restore vanuit R2 met datum van vóór het wissen
2. Let op: alle wijzigingen na die datum zijn verloren

### 4. Volledige rebuild (nuclear option)
**Symptoom:** Alles kapot, nieuwe Railway service nodig.
**Stappen:**
1. Maak nieuwe Railway service aan vanuit git repo
2. Mount volume op `/data`
3. Stel env vars in (zie `docs/DEPLOYMENT_GUIDE.md`)
4. Deploy → app start met lege DB
5. Ga naar `/admin/export` → "Restore vanuit R2"
6. Klaar — alle data hersteld

## CLI Restore (via Railway shell)

```bash
# Toon beschikbare backups
python -m app.core.restore --list

# Restore laatste backup
python -m app.core.restore

# Restore specifieke datum
python -m app.core.restore --datum 2026-03-22
```

## Backup verificatie

### Handmatig checken
- `/admin/export` → "Backup nu" knop
- `/admin/backup/status` → JSON met alle backups in R2

### Ops endpoint
```
GET /api/ops/health?key=<OPS_KEY>
→ {"healthy": true, "db": true, "volume": true}
```

## Belangrijk

- **Restore overschrijft de huidige database** — maak eerst een backup als je twijfelt
- De app maakt automatisch een `.bak` kopie van de huidige DB vóór restore
- Na restore moet de app herstart worden om de nieuwe DB te laden (Railway doet dit automatisch bij redeploy)
- Logo's worden ook hersteld naar `/data/logos/`
