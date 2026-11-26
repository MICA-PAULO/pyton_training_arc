"""Artikelen ophalen via de WordPress REST API, netjes en volgens robots.txt.

De WordPress API (/wp-json/wp/v2/posts) is een bestaande, officiële interface.
We hoeven dus geen HTML-layout te ontleden en de scraper blijft werken als het
uiterlijk van de site verandert.

Juridisch kader: robots.txt wordt altijd gecontroleerd (ECLI:NL:RBAMS:2024:6563,
artikel 15o Auteurswet). Is robots.txt niet bereikbaar, dan slaan we de site over.
"""

import time
import urllib.robotparser
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

USER_AGENT = "DOSI-scraper/1.0 (studentenonderzoek OSINT, niet-commercieel)"
TIJDELIJKE_FOUTEN = {429, 500, 502, 503, 504}


class WebsiteFout(Exception):
    """De website kan of mag niet gescraped worden. De tekst is voor de gebruiker."""


class Fetcher:
    def __init__(self, wachttijd):
        self.wachttijd = wachttijd
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._robots = {}
        self._laatste = 0.0

    def _mag(self, url):
        basis = "{0.scheme}://{0.netloc}".format(urlsplit(url))
        if basis not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.session.get(basis + "/robots.txt", timeout=30)
                if r.status_code == 404:
                    rp.allow_all = True  # geen robots.txt = geen beperkingen
                elif r.ok:
                    rp.parse(r.text.splitlines())
                else:
                    rp.disallow_all = True
            except requests.RequestException:
                rp.disallow_all = True
            self._robots[basis] = rp
        return self._robots[basis].can_fetch(USER_AGENT, url)

    def get(self, url, params=None, pogingen=4):
        if not self._mag(url):
            raise WebsiteFout("robots.txt staat scrapen niet toe, of robots.txt is niet bereikbaar")
        for poging in range(pogingen):
            wacht = self.wachttijd - (time.monotonic() - self._laatste)
            if wacht > 0:
                time.sleep(wacht)
            self._laatste = time.monotonic()
            try:
                r = self.session.get(url, params=params, timeout=60)
                if r.status_code == 404:
                    raise WebsiteFout("dit lijkt geen WordPress-site (geen /wp-json gevonden)")
                if r.ok:
                    return r.json(), r.headers
                if r.status_code not in TIJDELIJKE_FOUTEN:
                    raise WebsiteFout(f"de website gaf foutcode {r.status_code}")
                fout = f"foutcode {r.status_code}"
            except ValueError:
                fout = "antwoord is geen JSON, is het wel een WordPress-site?"
            except requests.RequestException as e:
                fout = f"geen verbinding: {e.__class__.__name__}"
            if poging < pogingen - 1:
                time.sleep(2 ** (poging + 1))
        raise WebsiteFout(f"geen bruikbaar antwoord na {pogingen} pogingen ({fout})")


def _tekst(html):
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def artikelen(fetcher, naam, basis, inst, bezig=None, klaar=None):
    """Geeft per artikel een dict. Dubbele artikelen worden overgeslagen.

    `bezig(jaar, term, pagina)` wordt voor elk verzoek aangeroepen,
    `klaar(pagina, totaal_paginas)` erna. Zo kan de voortgangsbalk meelopen.
    """
    data, _ = fetcher.get(f"{basis}/wp-json/wp/v2/categories", {"per_page": 100, "_fields": "id,name"})
    categorieen = {c["id"]: _tekst(c["name"]) for c in data}
    gezien = set()

    for jaar in inst.jaren:
        start, eind = inst.venster(jaar)
        for term in inst.zoektermen:
            pagina, totaal = 1, 1
            while pagina <= totaal:
                if bezig:
                    bezig(jaar, term, pagina)
                posts, headers = fetcher.get(f"{basis}/wp-json/wp/v2/posts", {
                    "search": term,
                    "after": f"{start}T00:00:00",
                    "before": f"{eind}T00:00:00",
                    "per_page": 100,
                    "page": pagina,
                    "_fields": "id,date,link,title,content,categories",
                })
                totaal = max(1, int(headers.get("X-WP-TotalPages", 1)))
                for p in posts:
                    if p["id"] in gezien:
                        continue
                    gezien.add(p["id"])
                    yield {
                        "website": naam,
                        "jaarwisseling": f"{jaar}/{jaar + 1}",
                        "datum": p["date"][:10],
                        "titel": _tekst(p["title"]["rendered"]),
                        "url": p["link"],
                        "categorieen": [categorieen.get(c, str(c)) for c in p.get("categories", [])],
                        "tekst": _tekst(p["content"]["rendered"]),
                    }
                if klaar:
                    klaar(pagina, totaal)
                pagina += 1
