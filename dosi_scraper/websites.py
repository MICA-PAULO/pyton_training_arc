"""Artikelen ophalen van nieuwswebsites, netjes en volgens robots.txt.

Twee methodes, de scraper kiest zelf:

1. WordPress: via de officiële WordPress API (/wp-json). Snel en precies,
   want de API kan op datum filteren.
2. Zoekpagina: voor alle andere sites. De scraper zoekt de zoekbalk op de
   homepage (of gebruikt de zoekpagina uit instellingen.toml), bladert door de
   resultaten en leest elk artikel met trafilatura, een bestaande scraper die
   op vrijwel elke nieuwspagina tekst en datum herkent.

Juridisch kader: robots.txt wordt altijd gecontroleerd (ECLI:NL:RBAMS:2024:6563,
artikel 15o Auteurswet). We stellen ons eerlijk voor met een eigen User-Agent.
Blokkeert een site ons (firewall, cookiemuur), dan stoppen we bij die site.
"""

import json
import re
import time
import urllib.robotparser
from urllib.parse import quote_plus, urlencode, urljoin, urlsplit

import requests
import trafilatura
from bs4 import BeautifulSoup

USER_AGENT = "DOSI-scraper/1.0 (studentenonderzoek OSINT, niet-commercieel)"
TIJDELIJKE_FOUTEN = {429, 500, 502, 503, 504}
ONZIN = "qxzvbnmq"  # zoekterm zonder resultaten, om menu-links te herkennen
ZOEKVELD = re.compile(r"^(q|s|query|search|zoek|zoeken|zoekterm|keyword|keywords|term|text)$", re.I)
VOLGENDE = re.compile(r"^\s*(volgende|next|meer|meer resultaten|oudere berichten|»|›|>|→)\s*", re.I)
GEEN_ARTIKEL = re.compile(r"\.(jpe?g|png|gif|svg|webp|pdf|mp[34]|zip)$|^(mailto|tel|javascript):", re.I)


class WebsiteFout(Exception):
    """De website kan of mag niet gescraped worden. De tekst is voor de gebruiker."""


class GeenWordPress(Exception):
    pass


def _host(url):
    return urlsplit(url).netloc.lower().removeprefix("www.")


class Fetcher:
    """Haalt pagina's op met wachttijd, robots.txt-controle en nieuwe pogingen."""

    def __init__(self, wachttijd):
        self.wachttijd = wachttijd
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._robots = {}
        self._laatste = 0.0

    def _wachten(self):
        wacht = self.wachttijd - (time.monotonic() - self._laatste)
        if wacht > 0:
            time.sleep(wacht)
        self._laatste = time.monotonic()

    def _controleer(self, url):
        basis = "{0.scheme}://{0.netloc}".format(urlsplit(url))
        if basis not in self._robots:
            rp, reden = urllib.robotparser.RobotFileParser(), None
            try:
                self._wachten()
                r = self.session.get(basis + "/robots.txt", timeout=30)
                if _host(r.url) != _host(basis):
                    reden = (f"de website stuurt door naar {urlsplit(r.url).netloc}, waarschijnlijk een cookiemuur. "
                             "Automatisch toestemming geven doen we niet.")
                elif r.status_code == 404:
                    rp.allow_all = True  # geen robots.txt = geen beperkingen
                elif r.ok:
                    rp.parse(r.text.splitlines())
                elif r.status_code in (401, 403, 429):
                    reden = (f"de website blokkeert scrapers (foutcode {r.status_code}, meestal een firewall). "
                             "Dat omzeilen we niet. Vanaf een ander netwerk, zoals thuis, kan het soms wel werken.")
                else:
                    reden = f"robots.txt gaf foutcode {r.status_code}, dus we scrapen voor de zekerheid niet"
            except requests.RequestException as e:
                reden = f"website niet bereikbaar ({e.__class__.__name__})"
            self._robots[basis] = (rp, reden)
        rp, reden = self._robots[basis]
        if reden:
            raise WebsiteFout(reden)
        if not rp.can_fetch(USER_AGENT, url):
            raise WebsiteFout(f"robots.txt staat {urlsplit(url).path or '/'} niet toe")

    def ophalen(self, url, params=None, pogingen=4):
        self._controleer(url)
        for poging in range(pogingen):
            self._wachten()
            try:
                r = self.session.get(url, params=params, timeout=60)
                if _host(r.url) != _host(url):
                    raise WebsiteFout(f"de website stuurt door naar {urlsplit(r.url).netloc}, waarschijnlijk een "
                                      "cookiemuur of inlogpagina. Automatisch toestemming geven doen we niet.")
                if r.status_code not in TIJDELIJKE_FOUTEN:
                    return r
                fout = f"foutcode {r.status_code}"
            except requests.RequestException as e:
                fout = f"geen verbinding: {e.__class__.__name__}"
            if poging < pogingen - 1:
                time.sleep(2 ** (poging + 1))
        raise WebsiteFout(f"geen antwoord na {pogingen} pogingen ({fout})")

    def json(self, url, params=None):
        for poging in range(3):
            r = self.ophalen(url, params)
            if r.status_code == 404:
                raise GeenWordPress()
            if not r.ok:
                raise WebsiteFout(f"de website gaf foutcode {r.status_code}")
            try:
                return r.json(), r.headers
            except ValueError:
                time.sleep(2 ** (poging + 1))  # soms tijdelijk een controlepagina
        raise GeenWordPress()

    def html(self, url):
        r = self.ophalen(url)
        if not r.ok:
            raise WebsiteFout(f"{url} gaf foutcode {r.status_code}")
        return r.text, r.url


def _tekst(html):
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


# ---------------------------------------------------------------- methode kiezen

def methode(fetcher, site):
    """('wordpress', None) of ('zoekpagina', sjabloon). WebsiteFout als het niet lukt."""
    if site.zoekpagina:
        return "zoekpagina", site.zoekpagina
    try:
        fetcher.json(f"{site.adres}/wp-json/wp/v2/posts", {"per_page": 1, "_fields": "id"})
        return "wordpress", None
    except GeenWordPress:
        pass
    html, url = fetcher.html(site.adres + "/")
    sjabloon = _zoekformulier(html, url)
    if not sjabloon:
        raise WebsiteFout("geen WordPress en geen zoekbalk gevonden. Zoek op de website zelf naar 'vuurwerk', "
                          "kopieer het adres uit de adresbalk en zet het in instellingen.toml als zoekpagina, "
                          "met {zoekterm} op de plek van vuurwerk. Zie de README.")
    return "zoekpagina", sjabloon


def _zoekformulier(html, url):
    """Maakt van de zoekbalk op een pagina een zoekadres met {zoekterm}."""
    for form in BeautifulSoup(html, "html.parser").find_all("form"):
        if (form.get("method") or "get").lower() != "get":
            continue
        veld = form.find("input", attrs={"type": "search"}) or form.find("input", attrs={"name": ZOEKVELD})
        if not veld or not veld.get("name"):
            continue
        velden = {i["name"]: i.get("value", "") for i in form.find_all("input", type="hidden") if i.get("name")}
        velden[veld["name"]] = "{zoekterm}"
        actie = urljoin(url, form.get("action") or url)
        return actie + ("&" if "?" in actie else "?") + urlencode(velden, safe="{}")
    return None


# ---------------------------------------------------------------- methode 1: WordPress

def _wordpress(fetcher, site, inst, vp):
    data, _ = fetcher.json(f"{site.adres}/wp-json/wp/v2/categories", {"per_page": 100, "_fields": "id,name"})
    categorieen = {c["id"]: _tekst(c["name"]) for c in data}
    for jaar in inst.jaren:
        start, eind = inst.venster(jaar)
        for term in inst.zoektermen:
            pagina, totaal = 1, 1
            while pagina <= totaal:
                vp.bezig(f"{jaar}/{jaar + 1} '{term}'" + (f" p.{pagina}" if pagina > 1 else ""))
                posts, headers = fetcher.json(f"{site.adres}/wp-json/wp/v2/posts", {
                    "search": term, "after": f"{start}T00:00:00", "before": f"{eind}T00:00:00",
                    "per_page": 100, "page": pagina, "_fields": "id,date,link,title,content,categories",
                })
                totaal = max(1, int(headers.get("X-WP-TotalPages", 1)))
                for p in posts:
                    yield {
                        "jaarwisseling": f"{jaar}/{jaar + 1}",
                        "datum": p["date"][:10],
                        "titel": _tekst(p["title"]["rendered"]),
                        "url": p["link"],
                        "categorieen": [categorieen.get(c, str(c)) for c in p.get("categories", [])],
                        "tekst": _tekst(p["content"]["rendered"]),
                    }
                vp.stap(erbij=totaal - 1 if pagina == 1 else 0)
                pagina += 1


# ---------------------------------------------------------------- methode 2: zoekpagina

def _links(html, url, host):
    """Links naar pagina's op dezelfde website, in volgorde, plus de geparste pagina."""
    soup = BeautifulSoup(html, "html.parser")
    links = {}
    for a in soup.find_all("a", href=True):
        link = urljoin(url, a["href"]).split("#")[0]
        if _host(link) == host and not GEEN_ARTIKEL.search(a["href"]) and urlsplit(link).path.strip("/"):
            links[link] = None
    return list(links), soup


def _volgende(soup, url):
    a = (soup.find(["a", "link"], rel="next")
         or soup.find("a", attrs={"aria-label": re.compile(r"volgende|next", re.I)})
         or soup.find("a", string=VOLGENDE))
    return urljoin(url, a["href"]) if a and a.get("href") else None


def _lees(html, url):
    """Titel, datum en tekst van een artikel, met trafilatura."""
    uit = trafilatura.extract(html, url=url, output_format="json", with_metadata=True, favor_recall=True)
    return json.loads(uit) if uit else None


def _zoekpagina(fetcher, site, sjabloon, inst, vp):
    host = _host(site.adres)
    vul = lambda term: sjabloon.replace("{zoekterm}", quote_plus(term))

    # Links die ook bij een zoekopdracht zonder resultaten staan, zijn menu's en voetteksten.
    vp.bezig("menu-links herkennen")
    try:
        ruis = set(_links(*fetcher.html(vul(ONZIN)), host)[0])
    except WebsiteFout:
        ruis = set()
    vp.stap()

    kandidaten = {}
    for term in inst.zoektermen:
        url = vul(term)
        for pagina in range(1, inst.max_paginas + 1):
            vp.bezig(f"zoeken '{term}' p.{pagina}")
            html, echt = fetcher.html(url)
            links, soup = _links(html, echt, host)
            nieuw = [l for l in links if l not in ruis and l not in kandidaten]
            kandidaten.update({l: term for l in nieuw})
            url = _volgende(soup, echt)
            doorgaan = bool(url and nieuw and pagina < inst.max_paginas)
            vp.stap(erbij=int(doorgaan))
            if not doorgaan:
                break

    lijst = list(kandidaten.items())[: inst.max_artikelen]
    vp.stap(erbij=len(lijst), klaar=0)
    for link, term in lijst:
        vp.bezig(f"artikel lezen: {urlsplit(link).path[-40:]}")
        try:
            html, echt = fetcher.html(link)
        except WebsiteFout:
            vp.stap()
            continue
        d = _lees(html, echt)
        vp.stap()
        if not d or term.lower() not in (d.get("text") or "").lower():
            continue
        jaarwisseling = inst.jaarwisseling(d.get("date"))
        if jaarwisseling:
            yield {
                "jaarwisseling": jaarwisseling,
                "datum": d["date"][:10],
                "titel": d.get("title") or "",
                "url": echt,
                "categorieen": [c.strip() for c in (d.get("categories") or "").split(";") if c.strip()],
                "tekst": d.get("text") or "",
            }


# ---------------------------------------------------------------- samen

def stappen(soort, inst):
    """Eerste schatting van het aantal verzoeken, voor de voortgangsbalk."""
    return len(inst.jaren) * len(inst.zoektermen) if soort == "wordpress" else len(inst.zoektermen) + 1


def artikelen(fetcher, site, soort, sjabloon, inst, vp):
    """Geeft per artikel een dict. Dubbele artikelen worden overgeslagen."""
    bron = _wordpress(fetcher, site, inst, vp) if soort == "wordpress" else _zoekpagina(fetcher, site, sjabloon, inst, vp)
    gezien = set()
    for a in bron:
        if a["url"] not in gezien:
            gezien.add(a["url"])
            yield {"website": site.naam, **a}
