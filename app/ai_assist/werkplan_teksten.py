"""AI-gestuurde tekstgeneratie voor werkplan secties.

Gebruikt Claude API om projectspecifieke teksten te schrijven op basis van
data uit de database. Fallback naar template-tekst als API niet beschikbaar.
"""
import logging

import anthropic

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.order.models import Boring, Order
from app.order.klantcodes import get_klant_naam


def _get_client() -> anthropic.Anthropic | None:
    """Maak Anthropic client aan, of None als geen API key."""
    if not settings.ANTHROPIC_API_KEY:
        return None
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _boring_context(order: Order, boring: Boring) -> str:
    """Bouw context-string op basis van DB-data voor de AI prompt."""
    klant = get_klant_naam(order.klantcode) if order.klantcode else order.opdrachtgever or ""
    locatie = order.locatie or ""

    lines = [
        f"Opdrachtnummer: {order.ordernummer}",
        f"Locatie: {locatie}",
        f"Uitvoerend bedrijf: {klant}",
        f"Opdrachtgever: {order.opdrachtgever or ''}",
    ]

    # Boring details
    lines.append(f"Boring type: {'Gestuurde boring' if boring.type == 'B' else boring.type}")
    if boring.naam:
        lines.append(f"Boring naam: {boring.naam}")
    lines.append(f"Buis: {boring.materiaal} Ø{boring.De_mm:.0f} SDR{boring.SDR}")
    lines.append(f"Medium: {boring.medium}")
    lines.append(f"Boorgat diameter: Ø{boring.Dg_mm:.0f} mm")

    # Vergunning
    verg_map = {"-": "Geen", "P": "Provincie", "W": "Waterschap", "R": "Rijkswaterstaat"}
    lines.append(f"Vergunning: {verg_map.get(order.vergunning, order.vergunning)}")

    # Tracepunten
    if boring.trace_punten:
        lines.append(f"Aantal tracepunten: {len(boring.trace_punten)}")
        for tp in boring.trace_punten:
            lines.append(f"  {tp.label or tp.type}: RD({tp.RD_x:.2f}, {tp.RD_y:.2f})")

    # Doorsneden (bodemopbouw)
    if boring.doorsneden:
        lines.append("Bodemopbouw:")
        for ds in boring.doorsneden:
            gws = f", GWS={ds.GWS_m}m" if ds.GWS_m else ""
            lines.append(f"  {ds.afstand_m}m: {ds.grondtype} op NAP {ds.NAP_m}m{gws}")

    # Maaiveld
    if boring.maaiveld_override:
        mv = boring.maaiveld_override
        lines.append(f"Maaiveld intree: NAP {mv.MVin_NAP_m}m (bron: {mv.MVin_bron})")
        lines.append(f"Maaiveld uittree: NAP {mv.MVuit_NAP_m}m (bron: {mv.MVuit_bron})")

    # Berekening
    if boring.berekening and boring.berekening.Ttot_N:
        ton = boring.berekening.Ttot_N / 9810
        lines.append(f"Berekende intrekkracht: {boring.berekening.Ttot_N:.0f} N ({ton:.2f} ton)")

    # KLIC info
    klic_uploads = getattr(order, 'klic_uploads', [])
    if klic_uploads:
        for ku in klic_uploads:
            if ku.verwerkt and ku.aantal_leidingen:
                lines.append(f"KLIC: {ku.aantal_leidingen} leidingen, {ku.aantal_beheerders} beheerders")

    # Kwel-gerelateerde URLs
    if order.waterkering_url:
        lines.append(f"Waterkering URL beschikbaar: ja")
    if order.oppervlaktewater_url:
        lines.append(f"Oppervlaktewater URL beschikbaar: ja")

    return "\n".join(lines)


def genereer_inleiding(order: Order, boring: Boring,
                       hoofdaannemer: str = "") -> str:
    """Genereer de inleiding-tekst voor het werkplan met Claude."""
    client = _get_client()
    if not client:
        return ""  # Lege string = gebruik template fallback

    context = _boring_context(order, boring)
    klant = get_klant_naam(order.klantcode) if order.klantcode else ""
    ha_tekst = f"Hoofdaannemer: {hoofdaannemer}" if hoofdaannemer else ""

    prompt = f"""Schrijf een inleiding voor een werkplan van een gestuurde boring (HDD - Horizontal Directional Drilling).

Projectgegevens:
{context}
{ha_tekst}

Schrijf in het Nederlands, zakelijk en beknopt (max 3 alinea's). Volg dit format:
1. Eerste alinea: Beschrijf het project en de aanleiding (waarom wordt er geboord, wat wordt er aangelegd)
2. Tweede alinea: Vermeld dat dit werkplan is opgesteld om aan te tonen dat de boring veilig uitgevoerd kan worden
3. Derde alinea: Vermeld wie de boring uitvoert en dat GestuurdeBoringTekening.nl het werkplan heeft opgesteld

Gebruik geen opsommingstekens, geen headers, alleen lopende tekst. Vermijd marketingtaal."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.warning(f"AI tekstgeneratie mislukt: {e}")
        return ""


def genereer_locatie_beschrijving(order: Order, boring: Boring) -> str:
    """Genereer locatiebeschrijving op basis van coordinaten en adres."""
    client = _get_client()
    if not client:
        return ""

    context = _boring_context(order, boring)

    prompt = f"""Schrijf een korte locatiebeschrijving (2-4 zinnen) voor een werkplan van een gestuurde boring.

Projectgegevens:
{context}

Beschrijf de locatie zakelijk: waar het ligt, welke infrastructuur in de buurt is (wegen, spoorlijnen, waterlopen).
Schrijf in het Nederlands, geen opsommingen, alleen lopende tekst."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.warning(f"AI tekstgeneratie mislukt: {e}")
        return ""


def genereer_kwel_beoordeling(order: Order, boring: Boring) -> str:
    """Genereer kwel-beoordeling op basis van projectdata."""
    client = _get_client()
    if not client:
        return ""

    context = _boring_context(order, boring)

    prompt = f"""Schrijf de sectie "Maatregelen op dit project" voor het kwel-hoofdstuk van een werkplan gestuurde boring.

Projectgegevens:
{context}

Beoordeel of er kwelrisico is op basis van:
- Is er een waterkering in de buurt?
- Wordt er oppervlaktewater gekruist?
- Wat is de bodemopbouw (klei/veen = meer risico)?
- Is er een groot waterstandsverschil te verwachten?

Schrijf 2-4 zinnen + een conclusie. Zakelijk Nederlands, geen opsommingen."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.warning(f"AI tekstgeneratie mislukt: {e}")
        return ""
