"""Start de scraper: python -m dosi_scraper

Alle instellingen staan in instellingen.toml. Voor een snelle test kun je
de jaren hier overschrijven: python -m dosi_scraper --jaren 2024
"""

import argparse
import sys

from . import analyse, uitvoer, websites
from .instellingen import STANDAARD_PAD, InstellingenFout, jaren_lezen, laden


TOESTEMMING = ".toestemming"  # cookies van toestemming die je zelf gaf, staat in .gitignore


def _methode(fetcher, site, toestemmingsmap):
    """(methode, zoekadres, fout). Bij een cookiemuur mag de gebruiker zelf toestemming geven."""
    for poging in range(2):
        try:
            with uitvoer.console.status(f"{site.naam} controleren (robots.txt, WordPress of zoekbalk)..."):
                return (*websites.methode(fetcher, site), None)
        except websites.Cookiemuur as e:
            if poging or not uitvoer.vraag_toestemming(site.naam, e):
                return None, None, str(e)
            try:
                fetcher.cookies_gebruiken(websites.toestemming_geven(e.adres, toestemmingsmap))
            except websites.WebsiteFout as f:
                return None, None, str(f)
        except websites.WebsiteFout as e:
            return None, None, str(e)


def main(argv=None):
    p = argparse.ArgumentParser(prog="dosi_scraper", description="Scrapet nieuws over materiële schade na oudejaarsavond.")
    p.add_argument("--instellingen", default=STANDAARD_PAD, help="Ander instellingenbestand gebruiken")
    p.add_argument("--jaren", help='Jaren uit instellingen.toml overschrijven, bv. "2024" of "2020-2022"')
    p.add_argument("--test", metavar="ADRES", help="Test één website: wat antwoordt hij en welke methode werkt?")
    args = p.parse_args(argv)

    if args.test:
        fetcher = websites.Fetcher(1.0, STANDAARD_PAD.parent / TOESTEMMING)
        uitvoer.testresultaat(args.test, websites.testen(fetcher, args.test))
        return 0

    try:
        inst = laden(args.instellingen, jaren_lezen(args.jaren) if args.jaren else None)
    except InstellingenFout as e:
        uitvoer.fout(e)
        return 1

    toestemmingsmap = inst.map / TOESTEMMING
    fetcher = websites.Fetcher(inst.wachttijd, toestemmingsmap)
    plan = [(site, *_methode(fetcher, site, toestemmingsmap)) for site in inst.websites]
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
