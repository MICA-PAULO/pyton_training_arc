"""Haalt artikelen op via de WordPress REST API (/wp-json/wp/v2/posts).

Dit is een bestaande, officiële interface van WordPress. Daardoor hoeven we
geen HTML-layout te parsen en breekt de scraper niet als het thema van de
site verandert.
"""

from datetime import date

from bs4 import BeautifulSoup

from . import config

VELDEN = "id,date,link,title,content,categories"


def _categorieen(fetcher, basis):
    r = fetcher.get(f"{basis}/wp-json/wp/v2/categories", params={"per_page": 100, "_fields": "id,name"})
    return {c["id"]: BeautifulSoup(c["name"], "html.parser").get_text() for c in r.json()}


def _tekst(html):
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def venster(jaar):
    """Periode rond de jaarwisseling `jaar`/`jaar+1`."""
    m1, d1 = config.VENSTER_START
    m2, d2 = config.VENSTER_EIND
    return date(jaar, m1, d1), date(jaar + 1, m2, d2)


def artikelen(fetcher, bron, basis, jaren, zoektermen=config.ZOEKTERMEN, bezig=None, voortgang=None):
    """Geeft per artikel een dict terug. Dubbele artikelen worden overgeslagen.

    `bezig` wordt voor elk verzoek aangeroepen met (jaar, term, pagina).
    `voortgang` wordt na elke opgehaalde pagina aangeroepen met
    (jaar, term, pagina, totaal_paginas, nieuwe_artikelen).
    """
    cats = _categorieen(fetcher, basis)
    gezien = set()
    for jaar in jaren:
        start, eind = venster(jaar)
        for term in zoektermen:
            pagina = 1
            while True:
                if bezig:
                    bezig(jaar, term, pagina)
                r = fetcher.get(
                    f"{basis}/wp-json/wp/v2/posts",
                    params={
                        "search": term,
                        "after": f"{start.isoformat()}T00:00:00",
                        "before": f"{eind.isoformat()}T00:00:00",
                        "per_page": 100,
                        "page": pagina,
                        "orderby": "date",
                        "order": "asc",
                        "_fields": VELDEN,
                    },
                )
                totaal = max(1, int(r.headers.get("X-WP-TotalPages", 1)))
                nieuw = 0
                for p in r.json():
                    if p["id"] in gezien:
                        continue
                    gezien.add(p["id"])
                    nieuw += 1
                    yield {
                        "bron": bron,
                        "id": p["id"],
                        "jaarwisseling": f"{jaar}/{jaar + 1}",
                        "datum": p["date"],
                        "url": p["link"],
                        "titel": _tekst(p["title"]["rendered"]),
                        "regio": [cats.get(c, str(c)) for c in p.get("categories", [])],
                        "tekst": _tekst(p["content"]["rendered"]),
                    }
                if voortgang:
                    voortgang(jaar, term, pagina, totaal, nieuw)
                if pagina >= totaal:
                    break
                pagina += 1
