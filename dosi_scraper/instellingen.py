"""Leest instellingen.toml en controleert het met duidelijke foutmeldingen."""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 en ouder
    import tomli as tomllib

STANDAARD_PAD = Path(__file__).resolve().parent.parent / "instellingen.toml"


class InstellingenFout(Exception):
    """Iets in instellingen.toml klopt niet. De tekst is bedoeld voor de gebruiker."""


def patroon(woorden):
    """Zet zoekwoorden om naar één zoekpatroon.

    "brand" is een los woord, "prullenba*" begint met, "*camera" eindigt op.
    """
    delen = []
    for woord in woorden:
        w = woord.strip().lower()
        kern = r"\s+".join(re.escape(d) for d in w.strip("*").split())
        if not kern:
            continue
        begin = r"\w*" if w.startswith("*") else r"(?<!\w)"
        eind = r"\w*" if w.endswith("*") else r"(?!\w)"
        delen.append(begin + kern + eind)
    return re.compile("|".join(delen))


@dataclass
class Deelvraag:
    sleutel: str
    vraag: str
    categorieen: dict  # naam -> gecompileerd patroon


@dataclass
class Instellingen:
    map: Path
    jaren: list
    periode_van: tuple
    periode_tot: tuple
    wachttijd: float
    tekst_opslaan: bool
    uitvoermap: Path
    websites: dict
    zoektermen: list
    onderwerp: re.Pattern
    schade: re.Pattern
    geen_regio: set
    deelvragen: list

    def venster(self, jaar):
        """Begin- en einddatum (exclusief) rond de jaarwisseling jaar/jaar+1."""
        start = date(jaar, *self.periode_van)
        eind_jaar = jaar + 1 if self.periode_tot <= self.periode_van else jaar
        eind = date(eind_jaar, *self.periode_tot) + timedelta(days=1)
        return start, eind


def _sectie(data, naam):
    if not isinstance(data.get(naam), dict):
        raise InstellingenFout(f"Het blok [{naam}] ontbreekt.")
    return data[naam]


def _woorden(sectie, sleutel, waar):
    waarde = sectie.get(sleutel)
    if not isinstance(waarde, list) or not waarde or not all(isinstance(w, str) and w.strip() for w in waarde):
        raise InstellingenFout(f'{waar}: "{sleutel}" moet een lijst met woorden zijn, bv. ["woord", "woord*"].')
    return waarde


def jaren_lezen(tekst):
    try:
        tekst = str(tekst).replace(" ", "")
        if "-" in tekst:
            a, b = tekst.split("-")
            jaren = list(range(int(a), int(b) + 1))
        else:
            jaren = [int(j) for j in tekst.split(",")]
    except ValueError:
        jaren = []
    if not jaren:
        raise InstellingenFout(f'[algemeen] jaren = "{tekst}" begrijp ik niet. Gebruik bv. "2020-2025" of "2023, 2024".')
    return jaren


def _dag(tekst, sleutel):
    try:
        d, m = (int(x) for x in str(tekst).split("-"))
        date(2000, m, d)
        return m, d
    except ValueError:
        raise InstellingenFout(f'[algemeen] {sleutel} = "{tekst}" moet dag-maand zijn, bv. "27-12".') from None


def laden(pad=STANDAARD_PAD, jaren=None):
    pad = Path(pad).resolve()
    try:
        with open(pad, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        raise InstellingenFout(f"Kan het instellingenbestand niet vinden: {pad}") from None
    except tomllib.TOMLDecodeError as e:
        raise InstellingenFout(f"Typfout in {pad.name}: {e}\n"
                               "Tip: kijk op die regel naar aanhalingstekens, komma's en [ ] haken.") from None

    alg = _sectie(data, "algemeen")
    zoek = _sectie(data, "zoeken")

    websites = _sectie(data, "websites")
    for naam, url in websites.items():
        if not isinstance(url, str) or urlsplit(url).scheme not in ("http", "https"):
            raise InstellingenFout(f'[websites] "{naam}" moet een adres zijn dat begint met https://')
    if not websites:
        raise InstellingenFout("[websites] is leeg. Zet er minstens één website in.")

    deelvragen = []
    for sleutel, blok in _sectie(data, "deelvragen").items():
        waar = f"[deelvragen.{sleutel}]"
        if not re.fullmatch(r"\w+", sleutel):
            raise InstellingenFout(f"{waar}: de korte naam mag geen spaties of leestekens bevatten.")
        if not isinstance(blok.get("vraag"), str):
            raise InstellingenFout(f'{waar}: de regel vraag = "..." ontbreekt.')
        cats = {naam: patroon(_woorden(blok, naam, waar)) for naam in blok if naam != "vraag"}
        if not cats:
            raise InstellingenFout(f"{waar}: voeg minstens één categorie met zoekwoorden toe.")
        deelvragen.append(Deelvraag(sleutel, blok["vraag"], cats))

    return Instellingen(
        map=pad.parent,
        jaren=jaren or jaren_lezen(alg.get("jaren", "2020-2025")),
        periode_van=_dag(alg.get("periode_van", "27-12"), "periode_van"),
        periode_tot=_dag(alg.get("periode_tot", "07-01"), "periode_tot"),
        wachttijd=max(1.0, float(alg.get("wachttijd", 1.5))),
        tekst_opslaan=bool(alg.get("volledige_tekst_opslaan", False)),
        uitvoermap=pad.parent / alg.get("uitvoermap", "data"),
        websites={n: u.rstrip("/") for n, u in websites.items()},
        zoektermen=_woorden(zoek, "zoektermen", "[zoeken]"),
        onderwerp=patroon(_woorden(zoek, "onderwerp", "[zoeken]")),
        schade=patroon(_woorden(zoek, "schade", "[zoeken]")),
        geen_regio=set(zoek.get("geen_regio", [])),
        deelvragen=deelvragen,
    )
