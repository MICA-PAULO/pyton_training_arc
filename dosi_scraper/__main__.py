"""Gebruik: python -m dosi_scraper [--jaren 2020-2025] [--wp URL] [--uit data] [--met-tekst]"""

import argparse
import os
import sys
from urllib.parse import urlsplit

import requests

from . import analyse, config, export, wordpress
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
    fetcher = Fetcher()

    arts = []
    for bron, basis in bronnen.items():
        print(f"Bron {bron} ({basis})")
        try:
            for a in wordpress.artikelen(fetcher, bron, basis, jaren):
                analyse.label(a)
                if not args.met_tekst:
                    del a["tekst"]
                arts.append(a)
        except RobotsVerbod as e:
            print(f"  Overgeslagen: robots.txt verbiedt {e} of is niet bereikbaar", file=sys.stderr)
        except requests.RequestException as e:
            print(f"  Overgeslagen: {bron} gaf een fout ({e}). Is het wel een WordPress-site?", file=sys.stderr)

    arts.sort(key=lambda a: a["datum"])
    s = analyse.samenvatting(arts)
    export.csv_schrijven(arts, os.path.join(args.uit, "artikelen.csv"))
    export.jsonl_schrijven(arts, os.path.join(args.uit, "artikelen.jsonl"))
    export.rapport_schrijven(s, bronnen, os.path.join(args.uit, "rapport.md"))
    print(f"\nKlaar: {len(arts)} artikelen, {s['relevant']} relevant. Zie {args.uit}/rapport.md")


if __name__ == "__main__":
    main()
