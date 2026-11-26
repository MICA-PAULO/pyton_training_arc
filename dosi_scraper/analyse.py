"""Labelt artikelen per deelvraag met eenvoudige zoekwoorden.

Dit is een hulpmiddel en geen vervanging voor handmatige beoordeling. Controleer
altijd een steekproef van de artikelen voordat je conclusies trekt.
"""

import re
from collections import Counter

from . import config

GEEN_REGIO = {"Uitgelicht", "Provincies", "Binnenland", "Buitenland", "Overig"}
_ZIN = re.compile(r"(?<=[.!?])\s+")


def _compileer(groepen):
    return {naam: re.compile("|".join(patronen)) for naam, patronen in groepen.items()}


_OBJ = _compileer(config.OBJECTEN)
_KOST = _compileer(config.KOSTENSOORT)
_FACT = _compileer(config.FACTOREN)
_PREV = _compileer(config.PREVENTIE)
_JW = re.compile("|".join(config.JAARWISSELING))
_BEDRAG = re.compile(config.BEDRAG_REGEX)
_SCHADE = re.compile("|".join(config.KOSTENSOORT["reparatie / herstel"] + config.KOSTENSOORT["schoonmaak"]))


def _treffers(groepen, tekst):
    return [naam for naam, rx in groepen.items() if rx.search(tekst)]


def _getal(s, mult):
    s = s.strip(".,")
    # Nederlandse notatie: 1.250.000 of 1,2
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") >= 1 and len(s.split(".")[-1]) == 3:
        s = s.replace(".", "")
    try:
        w = float(s)
    except ValueError:
        return None
    return w * {"miljoen": 1_000_000, "duizend": 1_000}.get(mult or "", 1)


def bedragen(tekst):
    uit = []
    for m in _BEDRAG.finditer(tekst):
        getal = m.group("a") or m.group("b")
        mult = m.group("ma") or m.group("mb")
        w = _getal(getal, mult)
        if w:
            uit.append(w)
    return uit


def label(art, max_fragmenten=3):
    t = f"{art['titel']}. {art['tekst']}".lower()
    zinnen = _ZIN.split(f"{art['titel']}. {art['tekst']}")
    art["over_jaarwisseling"] = bool(_JW.search(t))
    art["provincie"] = [r for r in art["regio"] if r not in GEEN_REGIO]
    art["objecten"] = _treffers(_OBJ, t)
    art["kostensoort"] = _treffers(_KOST, t)
    art["factoren"] = _treffers(_FACT, t)
    art["preventie"] = _treffers(_PREV, t)
    art["bedragen_eur"] = bedragen(t)
    art["materiele_schade"] = bool(_SCHADE.search(t)) or bool(art["objecten"] and "brand" in art["factoren"])
    art["fragmenten"] = [z for z in zinnen if _SCHADE.search(z.lower())][:max_fragmenten]
    return art


def samenvatting(arts):
    rel = [a for a in arts if a["over_jaarwisseling"] and a["materiele_schade"]]
    tel = lambda veld: Counter(x for a in rel for x in a[veld])
    return {
        "totaal_artikelen": len(arts),
        "relevant": len(rel),
        "per_jaarwisseling": Counter(a["jaarwisseling"] for a in rel),
        "objecten": tel("objecten"),
        "kostensoort": tel("kostensoort"),
        "factoren": tel("factoren"),
        "preventie": tel("preventie"),
        "provincie": tel("provincie"),
        "objecten_per_jaar": {
            j: Counter(x for a in rel if a["jaarwisseling"] == j for x in a["objecten"])
            for j in sorted({a["jaarwisseling"] for a in rel})
        },
        "bedragen": [(a["jaarwisseling"], b, a["titel"], a["url"]) for a in rel for b in a["bedragen_eur"]],
    }
