# Deployment Guide — HDD Ontwerp Platform
**Versie: 22 maart 2026**

---

## Architectuur

```
GitHub repo: gestuurdeboring
├── main branch       → Staging  (hdd-staging.inodus.nl)
└── production branch → Productie (hdd.inodus.nl)
```

| Omgeving | Branch | URL | Doel |
|----------|--------|-----|------|
| Staging | `main` | hdd-staging.inodus.nl | Testen door team |
| Productie | `production` | hdd.inodus.nl | Live voor Martien |

---

## Stap 1 — Production branch (DONE)

De `production` branch is al aangemaakt en gepusht. Identiek aan `main` op dit moment.

---

## Stap 2 — Railway services aanmaken

### 2a. Productie service

1. Ga naar **railway.app** → je HDD project
2. De bestaande service → **Settings** → **Source**
3. Wijzig **Branch** naar `production`
4. Noteer de Railway URL (bijv. `hdd-app-production.up.railway.app`)

### 2b. Staging service

1. In hetzelfde Railway project → klik **+ New** → **GitHub Repo**
2. Selecteer repo `ellovangelderen/gestuurdeboring`
3. Kies branch: `main`
4. Railway bouwt automatisch — noteer de Railway URL
5. **Belangrijk:** zorg dat de staging service een eigen **Volume** heeft
   - Settings → Volumes → Add Volume → Mount path: `/data`

### 2c. Volumes checken

Beide services hebben een Volume nodig op `/data` voor de SQLite database:
- Productie: Settings → Volumes → mount path `/data`
- Staging: Settings → Volumes → mount path `/data`

---

## Stap 3 — Environment variables instellen

### Productie service

Ga naar de productie service → **Variables** tab → voeg toe:

```
ENV=production
DATABASE_URL=sqlite:///./data/hdd.db
USER_MARTIEN_PASSWORD=<sterk wachtwoord>
USER_VISSER_PASSWORD=<sterk wachtwoord>
USER_SOPA_PASSWORD=<sterk wachtwoord>
USER_LUCAS_PASSWORD=<sterk wachtwoord>
ANTHROPIC_API_KEY=<anthropic api key>
```

**LET OP:** `USER_TEST_PASSWORD` NIET instellen in productie.

### Staging service

Ga naar de staging service → **Variables** tab → voeg toe:

```
ENV=staging
DATABASE_URL=sqlite:///./data/hdd.db
USER_MARTIEN_PASSWORD=staging123
USER_VISSER_PASSWORD=staging123
USER_SOPA_PASSWORD=staging123
USER_LUCAS_PASSWORD=staging123
USER_TEST_PASSWORD=test123
ANTHROPIC_API_KEY=<anthropic api key>
```

---

## Stap 4 — Cloudflare DNS records

Ga naar **dash.cloudflare.com** → inodus.nl → **DNS** → **Records** → **Add record**

### Record 1: Productie

| Veld | Waarde |
|------|--------|
| Type | CNAME |
| Name | `hdd` |
| Target | `<productie-railway-url>.up.railway.app` |
| Proxy status | DNS only (grijs wolkje) |

### Record 2: Staging

| Veld | Waarde |
|------|--------|
| Type | CNAME |
| Name | `hdd-staging` |
| Target | `<staging-railway-url>.up.railway.app` |
| Proxy status | DNS only (grijs wolkje) |

**Let op:** Gebruik "DNS only" (grijs wolkje), niet "Proxied" (oranje). Railway handelt SSL zelf af. Met Cloudflare proxy kan er een dubbele SSL-laag ontstaan die problemen geeft.

---

## Stap 5 — Railway custom domains koppelen

### Productie service

1. Railway → productie service → **Settings** → **Networking**
2. Klik **Custom Domain** → voeg toe: `hdd.inodus.nl`
3. Railway valideert het CNAME record automatisch
4. SSL certificaat wordt automatisch gegenereerd

### Staging service

1. Railway → staging service → **Settings** → **Networking**
2. Klik **Custom Domain** → voeg toe: `hdd-staging.inodus.nl`
3. Wacht op validatie + SSL

---

## Stap 6 — Testdata laden op staging

Via Railway CLI (in de terminal die Railway toegang heeft):

```bash
railway link  # selecteer staging service
railway run python3 scripts/seed_full.py
```

Of via de Railway shell in het dashboard:
1. Staging service → **Settings** → **Railway Shell**
2. Run: `python3 scripts/seed_full.py`

---

## Stap 7 — Verifiëren

### Staging
```bash
curl -s https://hdd-staging.inodus.nl/health
# Verwacht: {"status":"ok"}

curl -s -u martien:staging123 https://hdd-staging.inodus.nl/orders/ -o /dev/null -w "%{http_code}"
# Verwacht: 200
```

### Productie
```bash
curl -s https://hdd.inodus.nl/health
# Verwacht: {"status":"ok"}

curl -s -u martien:<wachtwoord> https://hdd.inodus.nl/orders/ -o /dev/null -w "%{http_code}"
# Verwacht: 200
```

---

## Dagelijkse workflow

### Nieuwe feature ontwikkelen
```bash
# Werk op main branch
git checkout main
# ... code wijzigen ...
git add . && git commit -m "Feature X"
git push origin main
# → auto-deploy naar hdd-staging.inodus.nl
```

### Testen op staging
1. Open https://hdd-staging.inodus.nl
2. Login met staging credentials
3. Test de nieuwe feature
4. Als OK → deploy naar productie

### Deploy naar productie
```bash
git checkout production
git merge main
git push origin production
# → auto-deploy naar hdd.inodus.nl
```

### Hotfix op productie
```bash
git checkout production
# ... fix ...
git commit -m "Hotfix: ..."
git push origin production
# → auto-deploy naar productie

# Merge hotfix terug naar main
git checkout main
git merge production
git push origin main
```

---

## Data sync tussen omgevingen

### Staging → Productie (of andersom)

Via Railway CLI:
```bash
# Download database van staging
railway link  # selecteer staging
railway run cat /data/hdd.db > /tmp/hdd-staging.db

# Upload naar productie
railway link  # selecteer productie
railway run bash -c "cat > /data/hdd.db" < /tmp/hdd-staging.db
```

Of via een toekomstig admin panel (ADM-4 op de backlog).

---

## Troubleshooting

### 500 Internal Server Error na deploy
Waarschijnlijk ontbrekende DB kolommen. De startup migraties in `app/main.py` lossen dit automatisch op bij herstart. Forceer herstart:
- Railway dashboard → service → **Restart**

### 401 zonder login popup
Controleer dat de error handler in `app/main.py` de `WWW-Authenticate: Basic` header meestuurt. Dit is al gefixed.

### Lege database
Seed script draaien:
```bash
railway run python3 scripts/seed_full.py
```

### SSL problemen
- Zorg dat Cloudflare DNS records op "DNS only" staan (grijs wolkje)
- Railway genereert eigen SSL certificaat
- Wacht 5-10 minuten na custom domain toevoegen

---

## Referentie

| Item | Waarde |
|------|--------|
| GitHub repo | github.com/ellovangelderen/gestuurdeboring |
| Railway project | railway.app (HDD project) |
| Cloudflare DNS | dash.cloudflare.com → inodus.nl |
| Domein registrar | Versio.nl (alleen registratie) |
| Productie URL | https://hdd.inodus.nl |
| Staging URL | https://hdd-staging.inodus.nl |
| Health check | /health |
| Productie branch | `production` |
| Staging branch | `main` |
