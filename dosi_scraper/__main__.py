"""Start de scraper: python -m dosi_scraper

Alle instellingen staan in instellingen.toml. Voor een snelle test kun je
de jaren hier overschrijven: python -m dosi_scraper --jaren 2024
"""

import argparse
import sys

from . import analyse, uitvoer, websites
from .instellingen import STANDAARD_PAD, InstellingenFout, jaren_lezen, laden


def main(argv=None):
    p = argparse.ArgumentParser(prog="dosi_scraper", description="Scrapet nieuws over materiële schade na oudejaarsavond.")
    p.add_argument("--instellingen", default=STANDAARD_PAD, help="Ander instellingenbestand gebruiken")
    p.add_argument("--jaren", help='Jaren uit instellingen.toml overschrijven, bv. "2024" of "2020-2022"')
    args = p.parse_args(argv)

    try:
        inst = laden(args.instellingen, jaren_lezen(args.jaren) if args.jaren else None)
    except InstellingenFout as e:
        uitvoer.fout(e)
        return 1

    fetcher = websites.Fetcher(inst.wachttijd)
    plan = []
    with uitvoer.console.status("Websites controleren (robots.txt, WordPress of zoekbalk)..."):
        for site in inst.websites:
            try:
                plan.append((site, *websites.methode(fetcher, site), None))
            except websites.WebsiteFout as e:
                plan.append((site, None, None, str(e)))
    stappen = sum(websites.stappen(m, inst) for _, m, _, fout in plan if not fout)
    uitvoer.kop(inst, plan, stappen)

    arts = []
    voortgang = uitvoer.Voortgang(inst, stappen)
    try:
        with voortgang:
            for site, methode, zoekadres, fout in plan:
                if fout:
                    continue
                voortgang.website(site.naam)
                try:
                    for a in websites.artikelen(fetcher, site, methode, zoekadres, inst, voortgang):
                        arts.append(analyse.label(a, inst))
                        voortgang.artikel(a)
                except websites.WebsiteFout as e:
                    voortgang.waarschuwing(f"{site.naam} gestopt: {e}")
    except KeyboardInterrupt:
        uitvoer.console.print("\n[yellow]Gestopt met Ctrl+C. Wat al binnen is wordt opgeslagen.[/]")

    arts.sort(key=lambda a: a["datum"])
    tellingen = analyse.tellen(arts, inst)
    uitvoer.opslaan(arts, inst, tellingen)
    uitvoer.overzicht(inst, tellingen, voortgang.duur())
    return 0


if __name__ == "__main__":
    sys.exit(main())
