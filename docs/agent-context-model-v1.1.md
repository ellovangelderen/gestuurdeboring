# LeanAI Software Factory — Agent Context Model
# Version 1.2 · Naamconventie builder-{project}.md vastgelegd · March 2026

---

## 1. Agent pipeline

Model Agent → PM Agent → Architect Agent → Builder Agent → Release Agent

Model Agent     Analyseert probleem, stelt oplossingsrichting voor
PM Agent        Vertaalt richting naar backlog, scope en prioriteiten
Architect Agent Ontwerpt architectuur, modules, schrijft bouwopdrachten
Builder Agent   Implementeert modules, schrijft tests, levert code
Release Agent   Valideert code, controleert tests, verifieert output

---

## 2. Drie niveaus van context voor de Builder Agent

### builder-base.md — universele agentregels
- Rol, kwaliteitsregels, testdiscipline, security, outputformat
- Verandert nooit per project
- Max 40 regels

### builder-{project}.md — projectspecifieke bouwregels
- Naamconventie: builder-{projectnaam}.md (bijv. builder-hdd.md)
- Stack, architectuurstijl, projectstructuur, codeconventies
- Security-keuzes, testregels, domeinregels, verboden technologieën
- Geen backlog, geen taken, geen klantcontext
- Max 60 regels

### architect task — concrete bouwopdracht
- Module of feature die gebouwd wordt
- Scope, acceptatiecriteria, verwijzingen naar testdata
- Geleverd door de Architect Agent per taak

Builder Agent runtime = builder-base.md + builder-{project}.md + architect task

---

## 3. Rol van CLAUDE.md

CLAUDE.md is de volledige projectbron voor de Architect Agent.

Bevat: architectuur · backlog · domeinkennis · testdata ·
deployment · projectstructuur · technische keuzes

Wordt NIET rechtstreeks aan de Builder Agent gegeven.

---

## 4. Afleiding: CLAUDE.md → builder-{project}.md

Wel overnemen in builder-{project}.md
  technologie stack · projectstructuur · codeconventies
  security regels · testregels · domeinregels die code beïnvloeden
  technische beperkingen · expliciet verboden technologieën

Niet overnemen in builder-{project}.md
  backlog · roadmap · projectprioriteiten · klantcontext
  deploymentprocedures · uitgebreide documentatie · architectrollen

---

## 5. Ontwerpprincipes

Lean context          Agents krijgen alleen wat zij nodig hebben
Rolvastheid           Elke agent heeft één duidelijke verantwoordelijkheid
Deterministische code Kritische berekeningen in code — nooit via AI-prompting
Kleine stack          Bewust beperkte technologiekeuzes
Test first            Elke module bevat tests, geïsoleerd valideerbaar

---

## 6. Samenvatting

CLAUDE.md              → volledige projectbron (Architect Agent)
builder-{project}.md   → builder-specifieke bouwregels (afgeleid uit CLAUDE.md)
builder-base.md        → universele agentregels (alle projecten)
architect task         → concrete bouwopdracht (per taak)

Builder Agent werkt altijd met: builder-base.md + builder-{project}.md + architect task

---

## 7. Bestandsnamen per project (voorbeelden)

builder-base.md        → fabriek-standaard, geldt voor alle projecten
builder-hdd.md         → HDD Ontwerp Platform (golden project — fabriek referentie)
