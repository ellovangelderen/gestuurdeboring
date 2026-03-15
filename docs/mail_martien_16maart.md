# Concept antwoordmail — Martien Luijben
**Verzenden:** 16 maart 2026
**Aan:** Martien Luijben
**Van:** Architect, Inodus LeanAI Platform
**Onderwerp:** Re: Aanvullingen backlog HDD Ontwerp Platform

---

Hallo Martien,

Bedankt voor de aanvullingen — veel nuttige context die we direct in de architectuurdocumentatie hebben verwerkt.

**Backlogvolgorde**

We nemen jouw volgorde over. Één aanpassing die we zelf toevoegen: EV-zone (backlog 1b) bouwen we direct na de KLIC-parser, vóór GWSW. Reden: het is wettelijk kritisch en bouwt voort op de EV-detectie die al in de KLIC-parser zit. Het risico op boetes van Agentschap Telecom rechtvaardigt die prioriteit, ongeacht klantvolgorde.

De volledige herziene volgorde is: KLIC parser → EV-zone → GWSW riool → Sleufloze detectie → Conflictcheck → Boorprofiel geometrie → AHN5 maaiveld → Tracévarianten → Dinoloket → GEF/CPT → Topotijdreis → Vergunningscheck → Berekeningen → Werkplan generator.

**Werkplan generator**

In onze eerdere gesprekken noemde je de werkplan generator als je hoogste persoonlijke tijdsbesparing — het staat nu als laatste op de lijst. We zien twee mogelijke redenen, en willen graag weten welke klopt:

a) Je wilt de andere functies eerst werkend zien voordat je de complexere generator beoordeelt, of
b) Je inschatting van de waarde of urgentie is veranderd.

Wat bedoel je?

**Vergunningscheck (backlog 11)**

We zien hier goede waarde. We gaan onderzoeken of omgevingswet.overheid.nl een publieke API heeft waarmee we op basis van tracé-coördinaten automatisch kunnen bepalen welke overheden van toepassing zijn — Rijkswaterstaat, provincie, waterschap of gemeente. Als die API beschikbaar en toegankelijk is, kan het platform dit straks automatisch weergeven bij het openen van een project. We houden je op de hoogte van wat we vinden.

**Topotijdreis (backlog 10)**

Je drie cases zijn overtuigend — met name het voorbeeld van de boring die stopte op 9 en 12 meter zonder dat de oorzaak vooraf bekend was. We gaan onderzoeken of topotijdreis.nl een REST API of WMS/WCS service aanbiedt voor automatische integratie. Als dat lukt, kan het platform historische kaartlagen tonen voor het tracégebied zonder dat je handmatig naar de website hoeft.

Vraag: hoe ver terug in de tijd wil je kunnen kijken? Ons voorstel is 1900 tot heden, per stap van circa tien jaar. Is dat werkbaar voor jou, of heb je een andere voorkeur?

Als er geen bruikbare API blijkt te zijn, bouwen we als fallback een directe link-out naar topotijdreis.nl met de tracécoördinaten vooringevuld.

**Sigma-bestand**

Als je het Sigma-bestand kunt aanleveren, nemen we dat graag mee als testdata en referentie voor de berekeningen. Je opmerking over validatie hebben we genoteerd: als we bij backlog 12 zelf berekeningen gaan uitvoeren, is de vraag of transparante weergave van alle berekeningsstappen — vergelijkbaar met de Sigma-uitdraai — als acceptabel alternatief wordt beschouwd. Dat onderzoeken we expliciet bij de start van dat item. We noteren ook de tip over Deltares als mogelijk alternatief voor Sigma.

Bijgevoegd vind je het bijgewerkte procesoverzicht v6 met alle aanpassingen verwerkt.

Met vriendelijke groet,

Architect
Inodus LeanAI Platform
