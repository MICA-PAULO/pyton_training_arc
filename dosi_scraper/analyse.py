"""Labelt artikelen en telt per deelvraag. Alle deelvragen komen uit instellingen.toml.

De labels komen uit zoekwoorden. Een telling betekent "in hoeveel artikelen wordt
het genoemd", niet "hoeveel incidenten waren er". Controleer altijd een steekproef.
"""

import re
from collections import Counter, defaultdict

REGIO = ("regio", "In welke gebieden is de meeste schade? (categorie op de website)")
_ZIN = re.compile(r"(?<=[.!?])\s+")
_BEDRAG = re.compile(r"(?:€\s?(?P<a>\d[\d.,]*)\s*(?P<ma>miljoen|duizend)?)"
                     r"|(?:(?P<b>\d[\d.,]*)\s*(?P<mb>miljoen|duizend)?\s*euro)")


def secties(inst):
    """(kolomnaam, vraag) voor elke deelvraag plus de regio. Eén lijst voor rapport, CSV en scherm."""
    return [(d.sleutel, d.vraag) for d in inst.deelvragen] + [REGIO]


def _bedrag(getal, factor):
    getal = getal.strip(".,")
    if "," in getal:  # 1.250,50 of 1,2 miljoen
        getal = getal.replace(".", "").replace(",", ".")
    elif "." in getal and len(getal.split(".")[-1]) == 3:  # 15.000
        getal = getal.replace(".", "")
    try:
        return float(getal) * {"miljoen": 1_000_000, "duizend": 1_000}.get(factor, 1)
    except ValueError:
        return None


def bedragen(tekst):
    gevonden = (_bedrag(m["a"] or m["b"], m["ma"] or m["mb"]) for m in _BEDRAG.finditer(tekst))
    return [b for b in gevonden if b]


def label(art, inst):
    """Voegt per deelvraag de gevonden categorieën toe aan het artikel."""
    tekst = f"{art['titel']}. {art['tekst']}"
    laag = tekst.lower()
    art["relevant"] = bool(inst.onderwerp.search(laag) and inst.schade.search(laag))
    for d in inst.deelvragen:
        art[d.sleutel] = [naam for naam, rx in d.categorieen.items() if rx.search(laag)]
    art["regio"] = [c for c in art["categorieen"] if c not in inst.geen_regio]
    art["bedragen_eur"] = bedragen(laag)
    art["fragmenten"] = [z for z in _ZIN.split(tekst) if inst.schade.search(z.lower())][:3]
    if not inst.tekst_opslaan:
        del art["tekst"]
    return art


def tellen(arts, inst):
    """Alle tellingen die het rapport en het eindscherm nodig hebben."""
    relevant = [a for a in arts if a["relevant"]]
    per_sectie = {}
    for sleutel, _ in secties(inst):
        t = defaultdict(Counter)
        for a in relevant:
            for cat in a[sleutel]:
                t[cat][a["jaarwisseling"]] += 1
        per_sectie[sleutel] = sorted(t.items(), key=lambda kv: -sum(kv[1].values()))
    return {
        "jaren": sorted({a["jaarwisseling"] for a in arts}),
        "gevonden": Counter(a["jaarwisseling"] for a in arts),
        "relevant": Counter(a["jaarwisseling"] for a in relevant),
        "per_sectie": per_sectie,
        "bedragen": sorted((a["jaarwisseling"], b, a["titel"], a["url"]) for a in relevant for b in a["bedragen_eur"]),
    }
