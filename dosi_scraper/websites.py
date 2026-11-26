"""Artikelen ophalen van nieuwswebsites, netjes en volgens robots.txt.

Drie methodes, de scraper kiest zelf in deze volgorde:

1. WordPress: via de officiële WordPress API (/wp-json). Snel en precies,
   want de API kan op datum filteren.
2. Sitemap: bijna elke nieuwssite heeft een sitemap, een lijst van alle
   artikelen met hun datum. De scraper leest alleen de artikelen binnen de
   gekozen periodes. Werkt ook voor oudere jaren en heeft geen zoekbalk nodig.
3. Zoekpagina: als laatste redmiddel. De scraper zoekt de zoekbalk op de
   homepage (of gebruikt de zoekpagina uit instellingen.toml) en bladert door
   de resultaten.

Bij methode 2 en 3 leest trafilatura elk artikel: een bestaande scraper die op
vrijwel elke nieuwspagina tekst en datum herkent.

Juridisch kader: robots.txt wordt altijd gecontroleerd (ECLI:NL:RBAMS:2024:6563,
artikel 15o Auteurswet). We stellen ons eerlijk voor met een eigen User-Agent.
Blokkeert een site ons (firewall, cookiemuur), dan stoppen we bij die site.
"""

import gzip
import json
import re
import xml.etree.ElementTree as ET
from datetime import date
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
STANDAARD_SITEMAPS = ("/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml")
URL_DATUM = re.compile(r"/(20\d\d)[/-](\d\d)[/-](\d\d)(?:[/-]|$)")
PROVINCIES = {
    "drenthe": "Drenthe", "flevoland": "Flevoland", "friesland": "Friesland", "fryslan": "Friesland",
    "gelderland": "Gelderland", "groningen": "Groningen", "limburg": "Limburg", "noord-brabant": "Noord-Brabant",
    "noord-holland": "Noord-Holland", "overijssel": "Overijssel", "utrecht": "Utrecht", "zeeland": "Zeeland",
    "zuid-holland": "Zuid-Holland",
}
GEEN_ARTIKEL = re.compile(r"\.(jpe?g|png|gif|svg|webp|pdf|mp[34]|zip)$|^(mailto|tel|javascript):", re.I)


class WebsiteFout(Exception):
    """De website kan of mag niet gescraped worden. De tekst is voor de gebruiker."""


class GeenWordPress(Exception):
    pass


class Cookiemuur(WebsiteFout):
    """De website stuurt door naar een toestemmingspagina voor cookies."""

    def __init__(self, adres, doel):
        self.adres = adres
        super().__init__(f"de website vraagt eerst toestemming voor cookies (via {urlsplit(doel).netloc})")


def _host(url):
    return (urlsplit(url).hostname or "").removeprefix("www.")


class Fetcher:
    """Haalt pagina's op met wachttijd, robots.txt-controle en nieuwe pogingen."""

    def __init__(self, wachttijd, toestemmingsmap=None):
        self.wachttijd = wachttijd
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._robots = {}
        self._laatste = 0.0
        self.toestemmingsmap = toestemmingsmap
        if toestemmingsmap and toestemmingsmap.is_dir():
            for bestand in toestemmingsmap.glob("*.json"):
                self.cookies_gebruiken(json.loads(bestand.read_text(encoding="utf-8")))

    def cookies_gebruiken(self, cookies):
        for c in cookies:
            self.session.cookies.set(c["name"], c["value"], domain=c["domain"], path=c.get("path", "/"))

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
                r = self._zelfde_site(basis + "/robots.txt")  # cookiemuur: niet onthouden, na toestemming opnieuw
                if r.status_code == 404:
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

    def _zelfde_site(self, url, params=None):
        """Volgt doorverwijzingen alleen binnen dezelfde website. Een doorverwijzing naar
        een ander domein (meestal een cookiemuur) volgen we niet."""
        r = self.session.get(url, params=params, timeout=60, allow_redirects=False)
        for _ in range(5):
            if not r.is_redirect:
                return r
            doel = urljoin(r.url, r.headers["location"])
            if _host(doel) != _host(url):
                raise Cookiemuur("{0.scheme}://{0.netloc}".format(urlsplit(url)), doel)
            r = self.session.get(doel, timeout=60, allow_redirects=False)
        raise WebsiteFout("te veel doorverwijzingen")

    def ophalen(self, url, params=None, pogingen=4):
        self._controleer(url)
        for poging in range(pogingen):
            self._wachten()
            try:
                r = self._zelfde_site(url, params)
                if r.status_code not in TIJDELIJKE_FOUTEN:
                    return r
                fout = f"foutcode {r.status_code}"
            except requests.RequestException as e:
                fout = f"geen verbinding: {e.__class__.__name__}"
            if poging < pogingen - 1:
                time.sleep(2 ** (poging + 1))
        raise WebsiteFout(f"geen antwoord na {pogingen} pogingen ({fout})")

    def sitemaps(self, url):
        """De sitemaps die robots.txt noemt (kan leeg zijn)."""
        self._controleer(url)
        return self._robots["{0.scheme}://{0.netloc}".format(urlsplit(url))][0].site_maps() or []

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


def toestemming_geven(adres, toestemmingsmap):
    """Opent een browservenster waarin de gebruiker zelf op 'akkoord' klikt.

    De cookies van die toestemming worden lokaal bewaard, zodat het maar één keer hoeft.
    We klikken nooit zelf op akkoord: dat doet de onderzoeker.
    """
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError:
        raise WebsiteFout("hiervoor is Playwright nodig. Installeer het met: py -m pip install playwright") from None
    with sync_playwright() as p:
        browser = None
        for kanaal in ("msedge", "chrome", "chromium"):  # Edge staat op elke Windows-computer
            try:
                browser = p.chromium.launch(channel=kanaal, headless=False)
                break
            except Error:
                continue
        if not browser:
            raise WebsiteFout("geen browser gevonden. Installeer er een met: py -m playwright install chromium")
        pagina = browser.new_page()
        pagina.goto(adres + "/")
        try:
            # Klaar zodra de gebruiker terug is op de website zelf (of het venster sluit).
            pagina.wait_for_url(lambda u: _host(u) == _host(adres), timeout=5 * 60 * 1000)
            pagina.wait_for_load_state()
        except Error:
            pass
        cookies = pagina.context.cookies()
        browser.close()
    host = _host(adres)
    if not any(host.endswith(c["domain"].lstrip(".").removeprefix("www.")) for c in cookies):
        raise WebsiteFout("geen toestemming ontvangen. Klik in het venster op akkoord en wacht tot de website zelf laadt.")
    toestemmingsmap.mkdir(parents=True, exist_ok=True)
    (toestemmingsmap / f"{host}.json").write_text(json.dumps(cookies, indent=1), encoding="utf-8")
    return cookies


def _tekst(html):
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


# ---------------------------------------------------------------- methode kiezen

def methode(fetcher, site):
    """('wordpress', None), ('sitemap', [sitemaps]) of ('zoekpagina', sjabloon). WebsiteFout als niets lukt."""
    if site.zoekpagina:
        return "zoekpagina", site.zoekpagina
    cookiemuur = None
    try:
        fetcher.json(f"{site.adres}/wp-json/wp/v2/posts", {"per_page": 1, "_fields": "id"})
        return "wordpress", None
    except GeenWordPress:
        pass
    except Cookiemuur as e:
        cookiemuur = e  # misschien is de sitemap wel vrij toegankelijk
    kaarten = _sitemaps_vinden(fetcher, site.adres)
    if kaarten:
        return "sitemap", kaarten
    if cookiemuur:
        raise cookiemuur
    html, url = fetcher.html(site.adres + "/")
    sjabloon = _zoekformulier(html, url)
    if not sjabloon:
        raise WebsiteFout("geen WordPress, geen sitemap en geen zoekbalk gevonden. Zoek op de website zelf naar 'vuurwerk', "
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


def testen(fetcher, adres):
    """Controleert stap voor stap wat een website ons antwoordt. Geeft (stap, gelukt, uitleg)."""
    adres = adres.rstrip("/")
    try:
        fetcher.ophalen(adres + "/robots.txt")
        yield "robots.txt en bereikbaarheid", True, "de website antwoordt en robots.txt is gelezen"
    except WebsiteFout as e:
        yield "robots.txt en bereikbaarheid", False, str(e)
        return
    try:
        fetcher.json(f"{adres}/wp-json/wp/v2/posts", {"per_page": 1, "_fields": "id"})
        yield "WordPress", True, "ja, de snelle methode wordt gebruikt"
        return
    except (GeenWordPress, WebsiteFout):
        yield "WordPress", False, "nee"
    try:
        kaarten = _sitemaps_vinden(fetcher, adres)
    except WebsiteFout as e:
        kaarten, reden = [], str(e)
    else:
        reden = "geen bruikbare sitemap gevonden"
    yield "sitemap", bool(kaarten), (", ".join(kaarten) + " (deze methode wordt gebruikt)") if kaarten else reden
    if kaarten:
        return
    html, url = fetcher.html(adres + "/")
    soup = BeautifulSoup(html, "html.parser")
    feeds = [urljoin(url, l["href"]) for l in soup.find_all("link", type=re.compile("rss|atom"), href=True)]
    yield "RSS-feeds", bool(feeds), ", ".join(feeds) or "geen gevonden"
    sjabloon = _zoekformulier(html, url)
    yield "zoekbalk", bool(sjabloon), sjabloon or "niet gevonden in de HTML (misschien werkt hij met JavaScript)"
    if not sjabloon:
        return
    html, url = fetcher.html(sjabloon.replace("{zoekterm}", "vuurwerk"))
    links, soup = _links(html, url, _host(adres))
    yield "zoeken op 'vuurwerk'", bool(links), f"{len(links)} links op de resultatenpagina"
    yield "volgende pagina", bool(_volgende(soup, url)), _volgende(soup, url) or "geen knop gevonden"
    for link in links[-5:]:
        try:
            d = _lees(*fetcher.html(link))
        except WebsiteFout as e:
            yield "artikel lezen", False, f"{link}: {e}"
            continue
        if d:
            yield "artikel lezen", bool(d.get("date")), f"{d.get('date') or 'geen datum'} · {d.get('title')} ({link})"
            return
    yield "artikel lezen", False, "geen artikel kunnen lezen"


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


def _artikel(d, jaarwisseling, url):
    """Eén artikel zoals trafilatura het las, in het vaste formaat van de scraper."""
    categorieen = [c.strip() for c in (d.get("categories") or "").split(";") if c.strip()]
    provincie = [PROVINCIES[deel] for deel in urlsplit(url).path.lower().split("/") if deel in PROVINCIES]
    return {
        "jaarwisseling": jaarwisseling,
        "datum": d["date"][:10],
        "titel": d.get("title") or "",
        "url": url,
        "categorieen": categorieen + provincie[:1],
        "tekst": d.get("text") or "",
    }


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
            yield _artikel(d, jaarwisseling, echt)


# ---------------------------------------------------------------- methode 3 hulp: sitemap

def _datum(tekst):
    try:
        return date.fromisoformat((tekst or "")[:10])
    except ValueError:
        return None


def _sitemap_lezen(fetcher, url):
    """('index', [(adres, datum)]) of ('urls', [(adres, datum)]). None als het geen sitemap is."""
    r = fetcher.ophalen(url)
    if not r.ok:
        return None
    inhoud = gzip.decompress(r.content) if r.content[:2] == b"\x1f\x8b" else r.content
    try:
        root = ET.fromstring(inhoud)
    except ET.ParseError:
        return None
    soort = {"sitemapindex": "index", "urlset": "urls"}.get(root.tag.rsplit("}", 1)[-1])
    items = []
    for el in root:
        velden = {k.tag.rsplit("}", 1)[-1]: (k.text or "").strip() for k in el.iter()}
        if velden.get("loc"):
            # Publicatiedatum gaat voor: die van Google News, dan een datum in het adres, dan 'laatst gewijzigd'.
            m = URL_DATUM.search(velden["loc"])
            d = (_datum(velden.get("publication_date")) or (_datum("-".join(m.groups())) if m else None)
                 or _datum(velden.get("lastmod")))
            items.append((velden["loc"], d))
    return (soort, items) if soort else None


def _sitemaps_vinden(fetcher, adres):
    """Bruikbare sitemaps van een website. Test ook één pagina, zodat een cookiemuur nu al opvalt."""
    gevonden = []
    for url in fetcher.sitemaps(adres) or [adres + p for p in STANDAARD_SITEMAPS]:
        try:
            gelezen = _sitemap_lezen(fetcher, url)
            while gelezen and gelezen[0] == "index" and gelezen[1]:  # afdalen tot een lijst met pagina's
                gelezen = _sitemap_lezen(fetcher, gelezen[1][0][0])
        except Cookiemuur:
            raise
        except WebsiteFout:
            continue
        if not gelezen or not gelezen[1]:
            continue
        try:
            fetcher.html(gelezen[1][0][0])
        except Cookiemuur:
            raise
        except WebsiteFout:
            pass  # die ene pagina mag niet of bestaat niet meer, de rest misschien wel
        gevonden.append(url)
        if fetcher.sitemaps(adres):
            continue  # robots.txt noemt ze allemaal: alle gebruiken
        break
    return gevonden


def _sitemap(fetcher, site, kaarten, inst, vp):
    eerste_dag = min(inst.venster(j)[0] for j in inst.jaren)
    per_jaar, wachtrij, gezien = {}, list(kaarten), set()
    vp.stap(erbij=len(wachtrij) - 1, klaar=0)
    while wachtrij:
        url = wachtrij.pop(0)
        vp.bezig(f"sitemap lezen: {urlsplit(url).path[-40:]}{'?' + urlsplit(url).query if urlsplit(url).query else ''}")
        gelezen = None
        if url not in gezien:
            gezien.add(url)
            try:
                gelezen = _sitemap_lezen(fetcher, url)
            except Cookiemuur:
                raise
            except WebsiteFout:
                pass
        vp.stap()
        if not gelezen:
            continue
        soort, items = gelezen
        if soort == "index":
            # Sitemaps die voor de eerste periode voor het laatst gewijzigd zijn, kunnen niets bevatten.
            nieuw = [loc for loc, d in items if not (d and d < eerste_dag)]
            wachtrij += nieuw
            vp.stap(erbij=len(nieuw), klaar=0)
        else:
            for loc, d in items:
                jaarwisseling = d and inst.jaarwisseling(d.isoformat())
                if jaarwisseling:
                    per_jaar.setdefault(jaarwisseling, {})[loc] = d

    lijst = [(loc, jw) for jw in sorted(per_jaar)
             for loc, _ in sorted(per_jaar[jw].items(), key=lambda kv: kv[1])[: inst.max_artikelen]]
    if not lijst:
        raise WebsiteFout("de sitemap bevat geen pagina's binnen de gekozen periodes")
    vp.melding(f"{len(lijst)} pagina's binnen de periodes, die worden nu gelezen "
               f"(max {inst.max_artikelen} per jaarwisseling)")
    vp.stap(erbij=len(lijst), klaar=0)
    termen = [z.lower() for z in inst.zoektermen]
    for loc, jaarwisseling in lijst:
        vp.bezig(f"{jaarwisseling}  {urlsplit(loc).path[-45:]}")
        try:
            html, echt = fetcher.html(loc)
        except Cookiemuur:
            raise
        except WebsiteFout:
            vp.stap()
            continue
        d = _lees(html, echt)
        vp.stap()
        if d and any(t in f"{d.get('title')} {d.get('text')}".lower() for t in termen):
            d["date"] = d.get("date") or per_jaar[jaarwisseling][loc].isoformat()
            yield _artikel(d, jaarwisseling, echt)


# ---------------------------------------------------------------- samen

def stappen(soort, inst):
    """Eerste schatting van het aantal verzoeken, voor de voortgangsbalk."""
    return {"wordpress": len(inst.jaren) * len(inst.zoektermen), "sitemap": 1}.get(soort, len(inst.zoektermen) + 1)


def artikelen(fetcher, site, soort, sjabloon, inst, vp):
    """Geeft per artikel een dict. Dubbele artikelen worden overgeslagen."""
    bron = {"wordpress": lambda: _wordpress(fetcher, site, inst, vp),
            "sitemap": lambda: _sitemap(fetcher, site, sjabloon, inst, vp),
            "zoekpagina": lambda: _zoekpagina(fetcher, site, sjabloon, inst, vp)}[soort]()
    gezien = set()
    for a in bron:
        if a["url"] not in gezien:
            gezien.add(a["url"])
            yield {"website": site.naam, **a}
