"""Gebruik: python -m dosi_scraper [--jaren 2020-2025] [--wp URL] [--uit data] [--met-tekst]"""

import argparse
import os
from urllib.parse import urlsplit

import requests

from . import analyse, config, export, ui, wordpress
from .fetch import Fetcher, RobotsVerbod


def jaren_parsen(s):
    if "-" in s:
        a, b = s.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",")]


def main(argv=None):
    p = argparse.ArgumentParser(prog="dosi_scraper", description="Scrapet nieuws over materiële schade na oudejaarsavond.")
    p.add_argument("--jaren", default="2020-2025", help="Beginjaar van de jaarwisseling, bv. 2020-2025 of 2023,2024")
    p.add_argument("--bron", action="append", choices=sorted(config.BRONNEN), help="Alleen deze bron (standaard: alle)")
    p.add_argument("--wp", action="append", default=[], metavar="URL",
                   help="Extra WordPress-nieuwssite, bv. --wp https://voorbeeld.nl (mag vaker)")
    p.add_argument("--uit", default="data", help="Map voor de resultaten")
    p.add_argument("--met-tekst", action="store_true",
                   help="Volledige artikeltekst opslaan. Standaard uit (AVG: dataminimalisatie)")
    args = p.parse_args(argv)

    jaren = jaren_parsen(args.jaren)
    bronnen = dict(config.BRONNEN)
    if args.bron:
        bronnen = {b: bronnen[b] for b in args.bron}
    for url in args.wp:
        url = url.rstrip("/")
        bronnen[urlsplit(url).netloc] = url
    os.makedirs(args.uit, exist_ok=True)
    stappen = len(bronnen) * len(jaren) * len(config.ZOEKTERMEN)
    ui.kop(bronnen, jaren, args.uit, stappen, args.met_tekst)
    fetcher = Fetcher()

    arts = []
    v = ui.Voortgang(stappen)
    try:
        with v:
            for bron, basis in bronnen.items():
                v.bron(bron)
                try:
                    for a in wordpress.artikelen(fetcher, bron, basis, jaren, bezig=v.bezig, voortgang=v.klaar):
                        analyse.label(a)
                        if not args.met_tekst:
                            del a["tekst"]
                        arts.append(a)
                        v.artikel(a)
                except RobotsVerbod as e:
                    v.waarschuwing(f"{bron} overgeslagen: robots.txt verbiedt {e} of is niet bereikbaar")
                except requests.RequestException as e:
                    v.waarschuwing(f"{bron} overgeslagen: {e}. Is het wel een WordPress-site?")
    except KeyboardInterrupt:
        ui.console.print("\n[yellow]Gestopt met Ctrl+C. Wat al binnen is wordt opgeslagen.[/]")

    arts.sort(key=lambda a: a["datum"])
    s = analyse.samenvatting(arts)
    bestanden = [os.path.join(args.uit, n) for n in ("rapport.md", "artikelen.csv", "artikelen.jsonl")]
    export.rapport_schrijven(s, bronnen, bestanden[0])
    export.csv_schrijven(arts, bestanden[1])
    export.jsonl_schrijven(arts, bestanden[2])
    ui.overzicht(arts, s, bestanden, v.duur())


if __name__ == "__main__":
    main()
