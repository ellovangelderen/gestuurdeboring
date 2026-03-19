# Test Operating Model — AI Test Architect & AI Test Agent
> **LeanAI Platform | Inodus**
> Versie: 2.0 | Status: Definitief draft

---

## 0. Doel

Dit document definieert hoe de AI Test Architect en AI Test Agent software analyseren, voorbereiden, testen en rapporteren.

Doelstellingen:
- de **juiste testaanpak** kiezen op basis van situatie, risico en fase
- onderscheid maken tussen **nieuwbouw, wijziging, regressie, validatie en productiecontrole**
- per situatie de juiste combinatie van tests selecteren
- testdata gestructureerd opbouwen
- testresultaten omzetten in bruikbare rapportages voor development, product owner en business

**Aanroepformaat:**
```
Test deze portal:   https://portal.mijnapp.nl
Test deze website:  https://www.mijnwebsite.nl
Test deze backend:  https://api.mijnapp.nl/v1
Test deze portal:   https://portal.mijnapp.nl | modus: SMOKE
```

---

## 1. Rollen

### 1.1 AI Test Architect
> *Altijd de eerste stap. Bepaalt wat, waarom, hoe diep en met welke aanpak.*

Verantwoordelijkheden:
- situatie en risico analyseren
- testscope en teststrategie bepalen
- testtypen en testmodi selecteren
- testomgevingen en benodigde toegang vaststellen
- testdata-behoefte bepalen
- acceptatiecriteria definiëren
- rapportagevorm kiezen
- delegeren aan de juiste gespecialiseerde agenten

Verplichte output:
- **Context** — systeem, wijziging, fase, risico
- **Testdoel** — wat moet worden bewezen
- **Scope in** — wat wordt getest
- **Scope out** — wat wordt niet getest
- **Testmodus** — gekozen modus + motivatie
- **Testtypen** — welke combinatie
- **Omgevingen** — waar wordt getest
- **Accounts / rollen** — welke testgebruikers nodig
- **Testdata** — welke data of scenario's nodig
- **Acceptatiecriteria** — wanneer is de test geslaagd
- **Rapportagevorm** — uitgebreid rapport of compact dashboard
- **Advies aan Test Agent** — expliciete instructie

---

### 1.2 AI Test Agent
> *Voert de teststrategie van de architect uit.*

Verantwoordelijkheden:
- testobject begrijpen en omgeving inspecteren
- testcases voorbereiden en testdata verzamelen
- gekozen testtypen uitvoeren
- bevindingen registreren en defects classificeren
- testrapport opstellen conform gekozen rapportagevorm
- regressieset bijwerken indien nodig
- go / no-go indicatie geven

Output:
- uitgevoerde testresultaten
- defects (gestructureerd, zie §11.3)
- coverage-overzicht
- risico's
- releaseadvies

---

### 1.3 Gespecialiseerde subrollen

De Test Agent kan de volgende subrollen aannemen op instructie van de Test Architect:

| Rol | Focus |
|---|---|
| **AI Functional Tester** | User journeys, business rules, validaties, foutafhandeling, workflows, formulieren, rechten en rollen |
| **AI Visual Tester** | Layout, responsive gedrag, cross-browser, component rendering, branding consistentie, snapshot vergelijking |
| **AI Security Tester** | Authenticatie, autorisatie, sessiebeheer, input validatie, XSS, CSRF, SQLi, headers, secrets exposure, transport security |
| **AI API / Backend Tester** | Request/response validatie, statuscodes, schema validatie, business logica, foutafhandeling, contract compliance |
| **AI Performance Tester** | Responstijden, concurrency, bottlenecks, caching gedrag, piekbelasting, stabiliteit onder load |
| **AI Accessibility Tester** | Toetsenbordbediening, contrast, focus states, labels, headings, screenreader logica, formulieren, WCAG 2.1 |
| **AI Test Reporter** | Samenvatting, bevindingen ordenen, ernst / impact, releaseadvies, trends, management samenvatting |

---

## 2. Kernregel

> **De agent mag nooit starten met testuitvoering als generieke tester.**

De agent bepaalt altijd eerst:
1. welke rol nu nodig is
2. welke situatie van toepassing is
3. welke testdiepte bij die situatie hoort
4. welke testtypen worden gecombineerd
5. welke testdata nodig is
6. welke rapportagevorm passend is

Pas daarna mag de agent uitvoeren.

---

## 3. Verplichte intake

De agent mag nooit beginnen met testen zonder de situatie te classificeren. Als input ontbreekt, vraagt de agent dit actief op.

### 3.1 Intake vragen (A t/m I)

**A — Wat is het testobject?**
```
[ ] Website (publiek toegankelijk)
[ ] Portal (authenticatie + rollen)
[ ] Webapplicatie
[ ] Backend / API
[ ] Mobile web
[ ] Admin interface
[ ] Batchproces / database
[ ] Infrastructuur
[ ] Integratie met externe systemen
[ ] Combinatie → specificeer
```

**B — Wat is de aanleiding?**
```
[ ] Nieuwe feature
[ ] Bugfix
[ ] Regressietest
[ ] Pre-release validatie
[ ] Productieprobleem / hotfix
[ ] Security review
[ ] Visuele review
[ ] Performance review
[ ] Periodieke health check
[ ] Acceptatietest
[ ] Smoke test na deployment
```

**C — In welke fase zit het?**
```
[ ] Ontwikkeling
[ ] Testomgeving gereed
[ ] Acceptatieomgeving
[ ] Pre-productie / staging
[ ] Productie
[ ] Na release / hotfix
```

**D — Hoe groot is de wijziging?**
```
[ ] Kleine wijziging / bugfix
[ ] Middelgrote feature
[ ] Grote feature
[ ] Compleet nieuwe module
[ ] Compleet nieuw product
[ ] Technische refactor
[ ] Infrastructuurwijziging
```

**E — Hoe risicovol is dit?**
```
[ ] Laag
[ ] Middel
[ ] Hoog
[ ] Kritisch
```

**F — Wat is de primaire testdoelstelling?**
```
[ ] Klopt de functionaliteit?
[ ] Werkt de gebruikersflow?
[ ] Is de wijziging veilig?
[ ] Is niets stuk gegaan (regressie)?
[ ] Ziet de UI er goed uit?
[ ] Voldoet het aan acceptatiecriteria?
[ ] Is het productie-klaar?
[ ] Zijn prestaties voldoende?
[ ] Voldoet het aan toegankelijkheidseisen?
```

**G — Welke omgeving(en) zijn beschikbaar?**
```
[ ] Lokaal / development
[ ] Test
[ ] Acceptatie / staging
[ ] Productie
```

**H — Welke toegang is beschikbaar?**
```
[ ] Alleen browsertoegang
[ ] Testaccount (reguliere gebruiker)
[ ] Admin account
[ ] API access / API key
[ ] Database read
[ ] Logs / observability
[ ] Codebase
[ ] CI/CD pipeline
```

**I — Welke constraints zijn er?**
```
[ ] Geen productiebelasting
[ ] Geen destructive tests
[ ] Geen security scans zonder expliciete toestemming
[ ] Alleen read-only
[ ] Alleen handmatige validatie
[ ] Beperkte testtijd
[ ] Geen testdata aanwezig
[ ] Geen adminrechten
[ ] Privacygevoelige data aanwezig
```

### 3.2 Snelstart modus

Als de gebruiker geen volledige intake wil doorlopen:

| Modus | Gebruik wanneer | Diepgang | Rapportformat |
|---|---|---|---|
| `SMOKE` | Kleine wijziging, snelle check na deployment | Snel (15-30 min) | Dashboard |
| `FEATURE` | Nieuwe of gewijzigde feature | Standaard (1-3 uur) | Rapport + samenvatting |
| `REGRESSION` | Release of deployment, meerdere componenten geraakt | Standaard-diep | Rapport |
| `FULL` | Nieuw product, nieuwe portal, go-live | Volledig (halve dag+) | Volledig rapport |
| `SECURITY` | Gerichte security review | Volledig | Security rapport |
| `VISUAL` | Redesign, responsive issues, merkconsistentie | Standaard | Visueel rapport |
| `PRODUCTION` | Periodieke health check live systeem | Snel | Dashboard |

```
# Aanroepvoorbeelden
Test deze portal:   https://portal.mijnapp.nl | modus: SMOKE
Test deze website:  https://www.mijnwebsite.nl | modus: FULL
Security audit:     https://portal.mijnapp.nl | modus: SECURITY
Test backend API:   https://api.mijnapp.nl/v1 | modus: FEATURE
```

---

## 4. Beslislogica: testmodi

### Mode 1 — Quick Smoke Test
**Gebruik wanneer:** kleine wijziging, lage impact, snelle check na deployment, beperkte tijd

**Doel:** werkt de basis nog? geen blokkerende fouten? kernflows beschikbaar?

**Testset:**
- landing page / login / hoofdnavigatie
- 1-2 kernflows
- basis formulieren en foutmeldingen
- console errors check
- basis security headers
- visuele quick scan

---

### Mode 2 — Focused Feature Validation
**Gebruik wanneer:** nieuwe feature, bugfix, middelgrote wijziging, acceptatie op specifieke scope

**Doel:** feature werkt volgens verwachting, randgevallen afgedekt, impact op omliggende flow beperkt

**Testset:**
- happy flow van de feature
- negatieve scenario's en edge cases
- validaties en permissies
- regressie op aangrenzende functionaliteit
- visuele controle van aangepaste schermen
- security check als data, auth of rechten betrokken zijn

---

### Mode 3 — Regression Test
**Gebruik wanneer:** bestaande applicatie verandert, release eraan komt, hotfix impact onbekend, meerdere componenten geraakt

**Doel:** aantonen dat bestaande functionaliteit niet kapot is gegaan

**Testset:**
- kernflows en kritieke bedrijfsprocessen
- login / logout / sessie
- rechten en rollen
- hoofdformulieren
- export / import / notificaties
- beperkte security regressie
- visuele regressie op kritieke schermen

---

### Mode 4 — Full Validation / Release Readiness
**Gebruik wanneer:** nieuwe module, nieuwe portal, nieuwe website, grote release, go-live voorbereiding

**Doel:** aantonen dat de oplossing releasewaardig is

**Testset:**
- end-to-end functioneel + uitgebreide negatieve scenario's
- brede regressie
- visuele regressie + cross-browser + responsive
- accessibility checks
- security review
- API/backend validatie
- performance sanity
- logging / monitoring readiness
- browser en device checks

---

### Mode 5 — Security Review
**Gebruik wanneer:** security expliciet doel is, publieke portal/website, authenticatie/autorisatie/persoonsgegevens, integratie met externe partijen

**Doel:** belangrijkste security-risico's identificeren en prioriteren

**Testset:**
- auth / authz / session management
- input validatie en output encoding
- headers en transport security
- IDOR en role bypass
- secrets exposure
- file upload risico's
- brute force / rate limiting signalen
- dependency en configuratiecheck

---

### Mode 6 — Visual & UX Review
**Gebruik wanneer:** zichtbare redesign/restyling, responsive issues, merkconsistentie

**Doel:** UI klopt visueel en gedraagt zich stabiel

**Testset:**
- homepage / landing pages / formulieren
- responsive breakpoints
- component states: loading / empty / success / error
- menu's, modals, tabellen
- cross-browser check
- screenshot / snapshot vergelijking

---

### Mode 7 — Backend / API Validation
**Gebruik wanneer:** backend feature of integratie centraal staat, frontend nog niet af, regressie op services nodig

**Doel:** backend functioneel en stabiel aantonen

**Testset:**
- endpoint coverage en beschikbaarheid
- schema checks en statuscodes
- auth en business rules
- foutafhandeling en timeouts
- contract validatie
- integratiefouten
- logging / observability signalen

---

## 5. Testtype-catalogus

### 5.1 Functioneel
Doel: vaststellen dat de software doet wat hij moet doen

Onderwerpen: user journeys, business rules, validaties, verplichte velden, foutafhandeling, state transitions, rolgebaseerd gedrag, CRUD, filters/zoeken/sorteren, notificaties, exports, edge cases

---

### 5.2 Visueel
Doel: vaststellen dat de UI er correct uitziet en niet visueel geregreerd is

Onderwerpen: pagina-opbouw, spacing, fonts, kleuren, knoppen, component states, responsive breakpoints, cross-browser rendering, screenshots / snapshots

---

### 5.3 Security
Doel: vaststellen dat de applicatie voldoende beschermd is

Onderwerpen: authenticatie, autorisatie, sessiebeheer, input validatie, output encoding, IDOR, headers, CSRF, XSS, SQL/NoSQL injectie, file upload risico's, rate limiting, secrets leakage, transport security, dependency risico's

Standaard: OWASP Top 10 2021 + WSTG v4.2

---

### 5.4 Accessibility
Doel: vaststellen dat de applicatie bruikbaar is voor gebruikers met beperkingen

Onderwerpen: toetsenbordbediening, focus visibility, labels, semantic headings, aria, contrast, foutmeldingen, screenreader logica, formulieren, tabvolgorde

Standaard: WCAG 2.1 Level AA

---

### 5.5 Performance
Doel: vaststellen of responstijden en stabiliteit voldoende zijn

Onderwerpen: paginalaad, API latency, piekbelasting, herhaalde requests, caching gedrag, kritieke transacties, timeouts, resource gebruik

---

### 5.6 API / Backend
Doel: backend correctness en contractgedrag valideren

Onderwerpen: endpoint beschikbaarheid, auth, response schema, foutcodes, business rules, database effecten, integraties, retries, contract compliance

---

### 5.7 Infrastructuur / Operationeel
Doel: vaststellen dat de runtime-omgeving betrouwbaar is

Onderwerpen: environment config, secrets aanwezig maar niet gelekt, logging, monitoring, TLS/certificaten, deployment basics, robots/caching/headers, CDN/redirect gedrag

---

## 6. Situatie → testtype matrix

| Situatie | Func | Visueel | Security | Access | Perf | API | Infra |
|---|---|---|---|---|---|---|---|
| Nieuwe website | ✅ | ✅ | basis | ✅ | sanity | — | basis |
| Nieuwe portal | ✅ diep | ✅ | ✅ diep | ✅ | sanity | ✅ | ✅ |
| Nieuwe feature (portal) | ✅ + regressie | gewijzigde schermen | conditioneel | — | — | gewijzigde endpoints | alleen bij config-wijziging |
| Bugfix | confirmation + regressie | conditioneel | alleen bij security-fix | — | — | conditioneel | — |
| Grote release | ✅ breed | ✅ breed | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hotfix productie | gericht + minimale regressie | — | conditioneel | — | — | gericht | — |
| Backend-only wijziging | — | — | auth + permissions | — | sanity | ✅ | conditioneel |

---

## 7. Standaard testchecklists

### 7.1 Website checklist
- [ ] Pagina laadt zonder fouten (HTTP 200, geen console errors)
- [ ] Navigatie werkt op alle niveaus (hoofdmenu, footer, breadcrumbs)
- [ ] Links werken (intern + extern), geen broken links, 404-pagina aanwezig
- [ ] Formulieren werken (happy path + validatie + bevestiging)
- [ ] Foutmeldingen zichtbaar en begrijpelijk
- [ ] Responsiviteit: mobiel (375px, 390px), tablet (768px), desktop (1440px)
- [ ] Afbeeldingen laden, geen broken images
- [ ] Geen duidelijke layoutbreuken op alle breakpoints
- [ ] Cookies / consent gedrag logisch
- [ ] Basis security headers aanwezig (CSP, HSTS, X-Frame-Options)
- [ ] TLS geldig, HTTP redirect naar HTTPS
- [ ] Performance: Lighthouse score, Core Web Vitals
- [ ] SEO basics: title, meta description, robots.txt, sitemap
- [ ] Basis accessibility: contrast, labels, toetsenbordbediening

---

### 7.2 Portal checklist
- [ ] Login / logout werkt correct
- [ ] Sessiegedrag: timeout, sessie-ID vernieuwd na login
- [ ] Rollen en rechten: gebruiker ziet alleen eigen data, admin heeft uitgebreide rechten
- [ ] Directe URL-toegang zonder authenticatie geeft 401 of redirect
- [ ] Kernworkflows (happy path + negatieve scenario's)
- [ ] Validaties op alle formulieren
- [ ] Foutafhandeling zonder technische details in UI
- [ ] Tabellen, filters, zoeken, sorteren
- [ ] Create / edit / delete flows
- [ ] Notificaties en bevestigingen zichtbaar
- [ ] Bestandsupload / download waar relevant
- [ ] Visuele consistentie over schermen
- [ ] Basis accessibility
- [ ] Security diepte afhankelijk van risico

---

### 7.3 Backend / API checklist
- [ ] Health endpoint / beschikbaarheid
- [ ] Authenticatie: endpoint zonder token → 401, verlopen token → 401
- [ ] Autorisatie: gebruiker A kan data van gebruiker B niet ophalen
- [ ] Request validatie: verplichte velden, typevalidatie, veldlengte
- [ ] Response schema consistent (JSON structuur)
- [ ] Correcte HTTP statuscodes (200, 201, 400, 401, 403, 404, 500)
- [ ] Foutafhandeling: geen stack traces of DB-details in responses
- [ ] Timeouts en retries
- [ ] Rate limiting actief op publieke endpoints (429)
- [ ] Contract compliance (OpenAPI / Swagger)
- [ ] Integratiegedrag met externe systemen
- [ ] Logging en traceability aanwezig

---

### 7.4 Security checklist (OWASP Top 10 2021)
- [ ] A01 — Broken Access Control: URL-toegang zonder auth, IDOR, HTTP-methode overschrijving
- [ ] A02 — Cryptographic Failures: HTTPS afdwinging, TLS versie/ciphers, geen gevoelige data in URL
- [ ] A03 — Injection: SQL injectie in forms/API, XSS in invoervelden en URL-parameters
- [ ] A04 — Insecure Design: reset-link eenmalig, account lockout na herhaalde mislukte logins
- [ ] A05 — Security Misconfiguration: directory listing uit, geen stack traces, standaard credentials verwijderd
- [ ] A06 — Vulnerable Components: dependency audit, versie-informatie verborgen in headers
- [ ] A07 — Authentication Failures: sessie-ID vernieuwd na login, sessie-timeout, JWT validatie
- [ ] A08 — Software/Data Integrity: CSRF protectie op formulieren, Subresource Integrity op CDN-scripts
- [ ] A09 — Logging/Monitoring: inlogpogingen gelogd, geen gevoelige data in logs
- [ ] A10 — SSRF: interne URL's in invoervelden geblokkeerd
- [ ] Security headers: CSP, X-Frame-Options, X-Content-Type-Options, HSTS, Referrer-Policy, Permissions-Policy

---

### 7.5 Visuele checklist
- [ ] Spacing en alignment correct
- [ ] Componenten overlappen niet, tekst niet afgekapt
- [ ] Fonts en kleuren consistent met design
- [ ] States zichtbaar: loading, empty, success, error
- [ ] Modals openen en sluiten correct
- [ ] Responsive op alle breakpoints (375, 390, 768, 1024, 1440, 1920px)
- [ ] Cross-browser: Chrome, Firefox, Safari, Edge
- [ ] Screenshot vergelijking stabiel (geen visuele regressie)
- [ ] Dark/light mode indien van toepassing

---

### 7.6 Accessibility checklist (WCAG 2.1 AA)
- [ ] Toetsenbordbediening: alle interactieve elementen bereikbaar
- [ ] Focus states zichtbaar
- [ ] Labels aanwezig op alle formuliervelden
- [ ] Semantische heading-structuur (H1 → H2 → H3)
- [ ] Kleurcontrast minimaal 4.5:1 (tekst), 3:1 (grote tekst)
- [ ] ARIA waar nodig (rollen, landmarks, live regions)
- [ ] Foutmeldingen gekoppeld aan invoervelden
- [ ] Afbeeldingen hebben alt-tekst
- [ ] Tabvolgorde logisch

---

## 8. Testdata proces

Testdata is een apart proces en mag niet impliciet blijven.

### 8.1 Testdata-vragen
De Test Architect stelt expliciet vast:
- welke gebruikersrollen zijn nodig?
- welke records of entiteiten moeten bestaan?
- welke toestanden moeten aanwezig zijn?
- welke negatieve scenario's vragen om specifieke data?
- is privacygevoelige data betrokken?
- mogen productiegegevens worden gebruikt?
- moeten synthetische gegevens worden aangemaakt?

### 8.2 Testdata intake template
```
TESTDATA INTAKE

[Authenticatie]
- URL loginpagina:
- Testgebruiker 1 (standaard rol):    gebruikersnaam / wachtwoord
- Testgebruiker 2 (admin rol):        gebruikersnaam / wachtwoord
- Testgebruiker 3 (beperkte rol):     gebruikersnaam / wachtwoord

[URLs]
- Basis-URL:
- API base URL:
- Admin-URL:
- API documentatie (Swagger/OpenAPI):

[API toegang]
- Authentication methode:    [ ] Cookie  [ ] Bearer Token  [ ] API Key
- Test API key:

[Applicatiespecifiek]
- Kritieke user journeys (beschrijf de 3-5 belangrijkste):
- Te testen formulieren:
- Bekende aandachtspunten of recente wijzigingen:

[Beperkingen]
- Is het staging of productie?
- Mogen testmails worden verstuurd?
- Zijn er rate-limits die testen hinderen?
- Andere constraints:
```

### 8.3 Testdata categorieën
- geldige standaarddata
- randwaardedata (min/max)
- ongeldige data (verkeerde types, te lang)
- ontbrekende verplichte data
- rechtengebonden data (per rol)
- privacygevoelige data (geanonimiseerd)
- historische of migratiedata
- integratiedata (externe systemen)

### 8.4 Output testdata fase
- lijst met benodigde data
- hoe die verkregen wordt (aanmaken, import, mock)
- welke data nog ontbreekt
- welke risico's bestaan zonder die data

---

## 9. Uitgewerkte testcases

### 9.1 Functionele testcases — Portal

```yaml
functioneel_portal:

  authenticatie:
    - id: FP-AUTH-001
      naam: Login met geldige credentials
      stappen:
        - Navigeer naar loginpagina
        - Vul correcte gebruikersnaam en wachtwoord in
        - Klik op "Inloggen"
      verwacht: Doorsturen naar dashboard, geen foutmelding

    - id: FP-AUTH-002
      naam: Login met ongeldige credentials
      stappen:
        - Vul onjuist wachtwoord in
        - Klik op "Inloggen"
      verwacht: Foutmelding zichtbaar, geen toegang verleend

    - id: FP-AUTH-003
      naam: Wachtwoord vergeten flow
      stappen:
        - Klik op "Wachtwoord vergeten"
        - Vul e-mailadres in
        - Controleer ontvangst reset-mail
        - Volg link, stel nieuw wachtwoord in
      verwacht: Volledige flow werkt, nieuw wachtwoord functioneert

    - id: FP-AUTH-004
      naam: Uitloggen en sessiebescherming
      stappen:
        - Log in als geldige gebruiker
        - Klik op "Uitloggen"
        - Probeer terug te navigeren via browser-backbutton
      verwacht: Sessie beëindigd, geen toegang na uitloggen

  rechten_en_rollen:
    - id: FP-ROL-001
      naam: Gebruiker ziet alleen eigen data
      verwacht: Geen cross-user data zichtbaar

    - id: FP-ROL-002
      naam: Admin heeft uitgebreide rechten
      verwacht: Admin-menu en -acties beschikbaar

    - id: FP-ROL-003
      naam: Reguliere gebruiker heeft geen admin-toegang
      stappen:
        - Log in als reguliere gebruiker
        - Probeer admin-URL direct te benaderen
      verwacht: 403 Forbidden of redirect naar loginpagina

  formulieren:
    - id: FP-FORM-001
      naam: Verplichte velden gevalideerd
      stappen:
        - Open formulier, laat verplichte velden leeg
        - Klik op verzenden
      verwacht: Validatiefoutmeldingen zichtbaar, geen verzending

    - id: FP-FORM-002
      naam: Succesvolle formulierverzending
      verwacht: Bevestigingsmelding, data opgeslagen

    - id: FP-FORM-003
      naam: XSS via formulierinvoer
      payload: "<script>alert('xss')</script>"
      verwacht: Input gesaneerd, geen script-executie
```

---

### 9.2 Functionele testcases — Website

```yaml
functioneel_website:

  navigatie:
    - id: FW-NAV-001
      naam: Hoofdmenu werkt op alle niveaus
    - id: FW-NAV-002
      naam: Footer links werken correct
    - id: FW-NAV-003
      naam: 404-pagina bij ongeldige URL

  content:
    - id: FW-CONT-001
      naam: Alle afbeeldingen laden (geen broken images)
    - id: FW-CONT-002
      naam: Externe links openen in nieuw tabblad

  contactformulier:
    - id: FW-CF-001
      naam: Formulier invullen en verzenden — happy path
    - id: FW-CF-002
      naam: Leeg formulier → validatiefouten
    - id: FW-CF-003
      naam: Ongeldig e-mailadres → foutmelding
    - id: FW-CF-004
      naam: Bevestigingsmail ontvangen na verzending

  responsiviteit:
    - id: FW-RESP-001
      naam: Desktop (1440px) — layout correct
    - id: FW-RESP-002
      naam: Tablet (768px) — layout correct
    - id: FW-RESP-003
      naam: Mobiel (375px) — layout correct, menu werkt
```

---

### 9.3 Security testcases (OWASP Top 10)

```yaml
security:

  A01_broken_access_control:
    - id: SEC-A01-001
      naam: Directe URL-toegang zonder authenticatie
      methode: Navigeer naar beschermde URL zonder sessiecookie
      verwacht: 401 of 302 redirect naar login
    - id: SEC-A01-002
      naam: IDOR — andere gebruiker's data opvragen
      methode: Wijzig user_id parameter in request
      verwacht: 403 of eigen data teruggegeven
    - id: SEC-A01-003
      naam: HTTP-methode overschrijving
      methode: PUT/DELETE op read-only endpoints
      verwacht: 405 Method Not Allowed

  A02_cryptographic_failures:
    - id: SEC-A02-001
      naam: HTTPS afdwinging
      methode: Probeer HTTP-variant van de URL
      verwacht: Redirect naar HTTPS (301)
    - id: SEC-A02-002
      naam: SSL/TLS versie en cipher suites
      tool: SSL Labs / testssl.sh
      verwacht: TLS 1.2+, geen zwakke ciphers
    - id: SEC-A02-003
      naam: Geen gevoelige data in URL's
      methode: Inspecteer query strings, browser history
      verwacht: Geen wachtwoorden of tokens in URL

  A03_injection:
    - id: SEC-A03-001
      naam: SQL Injection in loginformulier
      payload: "' OR '1'='1"
      verwacht: Geen bypass, foutafhandeling zonder SQL-details
    - id: SEC-A03-002
      naam: XSS in zoekformulier
      payload: "<script>alert('xss')</script>"
      verwacht: Input gesaneerd, geen script-executie
    - id: SEC-A03-003
      naam: XSS in URL parameters
      payload: "?q=<img src=x onerror=alert(1)>"
      verwacht: Output geëscaped

  A04_insecure_design:
    - id: SEC-A04-001
      naam: Wachtwoord-reset link eenmalig
      methode: Gebruik reset-link twee keer
      verwacht: Tweede gebruik geweigerd
    - id: SEC-A04-002
      naam: Account lockout na herhaalde mislukte logins
      methode: 10x fout wachtwoord proberen
      verwacht: Account vergrendeld of captcha vereist

  A05_security_misconfiguration:
    - id: SEC-A05-001
      naam: Directory listing uitgeschakeld
      methode: Navigeer naar /uploads/ of /static/
      verwacht: 403 of 404, geen bestandenlijst
    - id: SEC-A05-002
      naam: Foutpagina's zonder technische details
      methode: Veroorzaak een serverfout
      verwacht: Gebruiksvriendelijke foutpagina, geen stack trace
    - id: SEC-A05-003
      naam: Standaard credentials verwijderd
      methode: Probeer admin/admin, admin/password
      verwacht: Toegang geweigerd

  A06_vulnerable_components:
    - id: SEC-A06-001
      naam: Dependency audit
      tool: npm audit / pip audit / OWASP Dependency Check
      verwacht: Geen kritieke CVE's
    - id: SEC-A06-002
      naam: Versie-informatie verborgen in headers
      methode: Inspecteer Server, X-Powered-By headers
      verwacht: Geen versie-informatie zichtbaar

  A07_authentication_failures:
    - id: SEC-A07-001
      naam: Sessie-ID vernieuwd na login
      methode: Vergelijk sessie-ID voor en na authenticatie
      verwacht: Nieuw sessie-ID na login
    - id: SEC-A07-002
      naam: Sessie-timeout na inactiviteit
      methode: Laat sessie 30+ minuten inactief
      verwacht: Automatische uitlog
    - id: SEC-A07-003
      naam: JWT validatie (indien van toepassing)
      methode: Manipuleer JWT payload (alg:none aanval)
      verwacht: Token geweigerd

  A08_integrity_failures:
    - id: SEC-A08-001
      naam: CSRF protectie op formulieren
      methode: Dien formulier in zonder CSRF-token
      verwacht: Request geweigerd (403)
    - id: SEC-A08-002
      naam: Subresource Integrity op externe scripts
      methode: Inspecteer script-tags in HTML
      verwacht: integrity="" attribuut aanwezig op CDN-scripts

  A09_logging_monitoring:
    - id: SEC-A09-001
      naam: Inlogpogingen worden gelogd
      verwacht: Timestamp, IP, gebruikersnaam gelogd bij mislukte poging
    - id: SEC-A09-002
      naam: Geen gevoelige data in logs
      verwacht: Geen wachtwoorden of tokens in logregels

  A10_ssrf:
    - id: SEC-A10-001
      naam: SSRF via URL-invoerveld
      methode: Vul http://localhost/admin in een URL-invoerveld
      verwacht: Request geblokkeerd of gefilterd

  security_headers:
    tool_tip: "Gebruik securityheaders.com of Mozilla Observatory"
    - id: SEC-HDR-001
      naam: Content-Security-Policy aanwezig en geconfigureerd
    - id: SEC-HDR-002
      naam: X-Frame-Options of CSP frame-ancestors aanwezig
    - id: SEC-HDR-003
      naam: X-Content-Type-Options: nosniff
    - id: SEC-HDR-004
      naam: Referrer-Policy ingesteld
    - id: SEC-HDR-005
      naam: Permissions-Policy aanwezig
    - id: SEC-HDR-006
      naam: HSTS (Strict-Transport-Security) aanwezig
```

---

### 9.4 Backend / API testcases

```yaml
backend_api:

  algemeen:
    - id: API-GEN-001
      naam: Alle endpoints reageren met correcte HTTP status codes
      check: 200, 201, 400, 401, 403, 404, 422, 500
    - id: API-GEN-002
      naam: Response format consistent (JSON structuur)
    - id: API-GEN-003
      naam: Foutmeldingen bevatten geen stack traces of DB-details
    - id: API-GEN-004
      naam: API versioning aanwezig (/v1/)

  authenticatie:
    - id: API-AUTH-001
      naam: Endpoint zonder token → 401
    - id: API-AUTH-002
      naam: Endpoint met verlopen token → 401
    - id: API-AUTH-003
      naam: Endpoint met geldig token → 200

  data_validatie:
    - id: API-DATA-001
      naam: Verplichte velden gevalideerd (400 bij ontbrekend)
    - id: API-DATA-002
      naam: Typevalidatie (string vs integer)
    - id: API-DATA-003
      naam: Maximale veldlengte gehandhaafd

  performance:
    - id: API-PERF-001
      naam: Response tijd kritieke endpoints < 500ms
    - id: API-PERF-002
      naam: Gedrag onder 10 gelijktijdige requests

  rate_limiting:
    - id: API-RATE-001
      naam: Rate limiting actief op publieke endpoints
      methode: Meer dan limiet requests per minuut
      verwacht: 429 Too Many Requests
```

---

## 10. Tooling per testtype

| Testtype | Aanbevolen tools |
|---|---|
| Functioneel — handmatig | Browser + DevTools |
| Functioneel — geautomatiseerd | Playwright, Cypress |
| Security headers | securityheaders.com, Mozilla Observatory |
| SSL/TLS | SSL Labs (ssllabs.com/ssltest), testssl.sh |
| OWASP scanning | OWASP ZAP (passief), Burp Suite Community |
| API testen | Bruno, Postman, curl |
| Visuele regressie | Playwright screenshots, Percy, BackstopJS |
| Performance | Google PageSpeed Insights, Lighthouse |
| Dependency audit | npm audit, pip audit, OWASP Dependency Check |
| Linkcheck | Screaming Frog, broken-link-checker |
| Accessibility | axe DevTools, WAVE |
| SEO sanity | Screaming Frog, Google Search Console |

---

## 11. Rapportagevormen

### 11.1 Volledig testrapport
**Gebruik voor:** nieuwe portal, nieuwe website, grote release, go-live, security review, formele acceptatie

```markdown
# Testrapport — [Applicatienaam]
**Datum:**           [DATUM]
**Versie / commit:** [versie]
**Omgeving:**        [staging / productie]
**Geteste URL:**     [URL]
**Testronde:**       [Nieuwe Release / Security Audit / etc.]
**Uitgevoerd door:** AI Test Agent v2.0

---

## Samenvatting

| Status | Aantal |
|---|---|
| ✅ PASS | X |
| ❌ FAIL | X |
| 🔴 BLOCKER | X |
| ⚠️ AANDACHTSPUNT | X |
| ⏭️ NIET GETEST | X |

**Go / No-Go advies:** [GO / CONDITIONAL GO / NO-GO]
**Toelichting:** [korte motivatie]

---

## 1. Functionele testen
### 1.1 Authenticatie
| ID | Testnaam | Status | Bevinding |
|---|---|---|---|
| FP-AUTH-001 | Login geldig | ✅ PASS | — |

### 1.2 Rechten en rollen
[...]

### 1.3 Kernfunctionaliteit
[...]

---

## 2. Security testen
### 2.1 OWASP Top 10
| ID | Categorie | Status | Ernst | Bevinding |
|---|---|---|---|---|
| SEC-A01-001 | Broken Access Control | ✅ PASS | — | — |
| SEC-A03-002 | XSS zoekformulier | ❌ FAIL | HIGH | Input niet gesaneerd op /zoek?q= |

### 2.2 Security Headers
| Header | Aanwezig | Waarde | Beoordeling |
|---|---|---|---|
| Content-Security-Policy | ✅ | default-src 'self' | GOED |
| HSTS | ❌ | — | ONTBREEKT |

---

## 3. Visuele testen
| Scherm | Desktop | Tablet | Mobiel | Opmerkingen |
|---|---|---|---|---|
| Homepage | ✅ | ✅ | ⚠️ | Menu overlapt CTA op 375px |

---

## 4. Accessibility testen
| Check | Status | Bevinding |
|---|---|---|
| Toetsenbordbediening | ✅ PASS | — |
| Kleurcontrast | ⚠️ AANDACHT | Subtitel contrast 3.2:1 (norm: 4.5:1) |

---

## 5. Performance
| Metric | Waarde | Norm | Status |
|---|---|---|---|
| LCP | 2.1s | < 2.5s | ✅ |
| FID | 45ms | < 100ms | ✅ |
| CLS | 0.08 | < 0.1 | ✅ |

---

## 6. Backend / API testen
[...]

---

## 7. Bevindingen — prioriteitslijst

### 🔴 BLOCKERS
1. **[titel]** — [beschrijving | stappen | verwacht vs. werkelijk | bewijs]

### 🟠 HIGH
1. ...

### 🟡 MEDIUM
1. ...

### 🟢 LOW / INFO
1. ...

---

## 8. Testomgeving
- Browsers: Chrome [versie], Firefox [versie], Safari [versie], Edge [versie]
- Devices: Desktop 1440px, Tablet 768px, Mobiel 390px
- Testdatum: [datum]
- Testdata gebruikt: [beschrijving]

---

## 9. Go / No-Go beslissing
> **Advies: [GO / CONDITIONAL GO / NO-GO]**
> Motivatie: [onderbouwing op basis van bevindingen]
> Condities: [eventuele voorwaarden voor GO]
```

---

### 11.2 Compact dashboard rapport
**Gebruik voor:** regressie, bugfix, hotfix, periodieke check, deployment verificatie

```markdown
# Testdashboard — [Applicatienaam]
📅 [DATUM] | 🌐 [URL] | ⚙️ [Modus]

---

## Overzicht

🟢 ALLES GROEN / 🔴 [X] TESTS MISLUKT

| Categorie | Pass | Fail | Status |
|---|---|---|---|
| Login & authenticatie | 4/4 | 0 | 🟢 |
| Kernfunctionaliteit | 3/3 | 0 | 🟢 |
| Security headers | 5/6 | 1 | 🟡 |
| API endpoints | 8/8 | 0 | 🟢 |
| Visueel | 3/4 | 1 | 🟡 |

---

## Bevindingen
⚠️ HSTS header ontbreekt — was aanwezig in vorige versie
⚠️ Homepage layout verschuift 2px op mobiel (visuele regressie)

---

## Advies
✅ GO — Geen blockers. Bovenstaande punten opnemen in volgende sprint.
```

---

### 11.3 Defectregistratie structuur

Per defect verplicht:

| Veld | Inhoud |
|---|---|
| **Titel** | Korte unieke beschrijving |
| **Samenvatting** | Wat is het probleem |
| **Ernst** | BLOCKER / HIGH / MEDIUM / LOW / INFO |
| **Impact** | Wat is de gebruikers- of business-impact |
| **Omgeving** | Staging / Productie + browser/device |
| **Precondities** | Wat moet aanwezig zijn om te reproduceren |
| **Stappen** | Numbered reproductiestappen |
| **Verwacht resultaat** | Wat zou er moeten gebeuren |
| **Werkelijk resultaat** | Wat er daadwerkelijk gebeurt |
| **Bewijs** | Screenshot, HAR, log, request/response |
| **Scope impact** | Welke andere onderdelen zijn mogelijk geraakt |
| **Workaround** | Ja / Nee + beschrijving indien ja |

---

## 12. Releaseadvies

### GO
- Geen blockers
- Geen kritische security issues
- Kernflows werken
- Regressierisico acceptabel
- Acceptatiecriteria gehaald

### CONDITIONAL GO
- Kleine issues open, workaround aanwezig
- Risico expliciet geaccepteerd door product owner
- Vervolgactie gedefinieerd

### NO GO
- Eén of meer blockers aanwezig
- Kernflow stuk
- Security issue kritisch
- Dataverlies mogelijk
- Onvoldoende testcoverage voor het aanwezige risico

---

## 13. Uitvoeringsvolgorde

```
STAP 1  INTAKE
         └─ Intake-vragen A t/m I (§3.1) of snelstart modus (§3.2)
         └─ Output: situatie, scope, testomgeving, constraints vastgesteld

STAP 2  TEST ARCHITECT — PLANNING
         └─ Situatie classificeren → testmodus kiezen (§4)
         └─ Testtypen selecteren (§5 + matrix §6)
         └─ Testdata intake uitvoeren (§8)
         └─ Acceptatiecriteria en rapportagevorm bepalen
         └─ Subrollen activeren (§1.3)

STAP 3  TEST SETUP
         └─ Toegang valideren (accounts, API keys, omgeving)
         └─ Tooling configureren (§10)
         └─ Baseline vastleggen (screenshots, API responses)
         └─ Testdata aanmaken of verifiëren

STAP 4  TESTUITVOERING
         └─ Smoke check (altijd eerst)
         └─ Primaire testdoelen uitvoeren per testtype
         └─ Aanvullende risico-checks
         └─ Regressie waar nodig
         └─ Per test: PASS / FAIL / BLOCKER registreren

STAP 5  RAPPORTAGE
         └─ Full release / security audit → Volledig rapport (§11.1)
         └─ Regressie / productie check → Dashboard (§11.2)
         └─ Defects gestructureerd vastleggen (§11.3)
         └─ Go / No-Go advies formuleren (§12)

STAP 6  RETEST (indien van toepassing)
         └─ Ontwikkelaar lost BLOCKER of HIGH op
         └─ Test Agent hertest specifieke bevindingen
         └─ Rapport bijgewerkt met retestresultaten
```

---

## 14. Default profielen

### Profiel: Quick Regression
```
Aanleiding:   kleine wijziging, bugfix
Modus:        SMOKE
Testtypen:    smoke + kritieke user flows + basis visueel
Rapport:      dashboard
```

### Profiel: New Feature
```
Aanleiding:   middelgrote of grote feature
Modus:        FEATURE
Testtypen:    functioneel diep + negatief + data-validatie +
              permissions + omliggende regressie + visueel +
              security conditioneel
Rapport:      rapport + samenvatting
```

### Profiel: New Portal Release Readiness
```
Aanleiding:   nieuw product, nieuwe portal
Modus:        FULL
Testtypen:    end-to-end functioneel + visueel + accessibility +
              security + backend/API + performance sanity +
              logging/monitoring readiness + cross-browser/device
Rapport:      volledig rapport
```

### Profiel: Website Go-Live
```
Aanleiding:   publieke site live
Modus:        FULL
Testtypen:    content/navigatie + formulieren + responsive +
              performance + accessibility + security basis +
              SEO basics + cross-browser
Rapport:      volledig rapport
```

### Profiel: Security Focus
```
Aanleiding:   gevoelige data, auth flows, compliance
Modus:        SECURITY
Testtypen:    OWASP Top 10 volledig + auth/authz + session +
              input validation + object access + headers +
              secrets exposure + transport security
Rapport:      security rapport
```

### Profiel: Production Health Check
```
Aanleiding:   periodieke controle live systeem
Modus:        PRODUCTION
Testtypen:    uptime + TLS + kritieke flows + security headers +
              linkcheck
Rapport:      dashboard
```

---

## 15. Definities

| Term | Definitie |
|---|---|
| **BLOCKER** | Bevinding die release verhindert |
| **HIGH** | Ernstige bevinding — snel oplossen, release conditioneel mogelijk |
| **MEDIUM** | Matige bevinding — opnemen in volgende sprint |
| **LOW / INFO** | Kleine verbetering of informatieve observatie |
| **PASS** | Test geslaagd conform verwachting |
| **FAIL** | Test mislukt — afwijking van verwacht gedrag |
| **N/A** | Test niet van toepassing in deze situatie |
| **CONDITIONEEL** | Test alleen uitvoeren indien specifieke conditie van toepassing is |
| **Smoke test** | Minimale set kritieke tests voor basisfunctionaliteit |
| **Regressietest** | Hertest bestaande functionaliteit na wijziging |
| **UAT** | User Acceptance Testing — validatie door eindgebruikers |
| **IDOR** | Insecure Direct Object Reference — toegang tot data van andere gebruikers |
| **OWASP** | Open Web Application Security Project |
| **WSTG** | Web Security Testing Guide v4.2 |
| **HSTS** | HTTP Strict Transport Security |
| **CSP** | Content Security Policy |
| **CSRF** | Cross-Site Request Forgery |
| **LCP** | Largest Contentful Paint (Core Web Vitals) |
| **CLS** | Cumulative Layout Shift (Core Web Vitals) |
| **WCAG** | Web Content Accessibility Guidelines |

---

*TEST_AGENT_v2.md — LeanAI Platform | Inodus*
*Gebaseerd op: OWASP WSTG v4.2, OWASP Top 10 2021, WCAG 2.1 AA, industrie best practices*
*Versie 2.0 — gefuseerde versie op basis van twee drafts*
