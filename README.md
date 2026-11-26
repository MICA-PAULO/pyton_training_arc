# DOSI-scraper

Web scraper voor het DOSI-project van groep 6 (2026-2027). De scraper verzamelt nieuwsartikelen over materiële schade rond oudejaarsavond en ordent ze per deelvraag uit het onderzoeksplan.

**Onderzoeksvraag:** Waar bestaat de materiële schade uit bij herstelwerkzaamheden na oudejaarsavond?

Je hoeft niet te kunnen programmeren. Alles wat je wilt aanpassen staat in **één bestand: `instellingen.toml`**.

---

## 1. Starten

**Windows:** dubbelklik op **`start.bat`**. De eerste keer installeert hij zelf wat nodig is.

Werkt dat niet? Dan staat Python nog niet op je computer. Installeer het via https://www.python.org/downloads/ en vink tijdens de installatie **"Add python.exe to PATH"** aan.

**Via de terminal** (PowerShell, PyCharm of VS Code), vanuit deze map:

```bash
py -m pip install -r requirements.txt
```
```bash
py -m dosi_scraper
```

Op Mac of Linux gebruik je `python3` in plaats van `py`.

Snel testen met één jaar, zonder het instellingenbestand aan te passen:

```bash
py -m dosi_scraper --jaren 2024
```

Stoppen kan altijd met **Ctrl+C**. Wat al binnen is wordt dan nog opgeslagen.

---

## 2. Aanpassen in `instellingen.toml`

Open `instellingen.toml` met Kladblok, VS Code of PyCharm. Regels met een `#` ervoor zijn uitleg.

### Zoekwoorden schrijven

| Je schrijft | Hij vindt |
|---|---|
| `"brand"` | alleen het losse woord *brand* (niet *brandweer*) |
| `"prullenba*"` | alles dat begint met *prullenba*: prullenbak, prullenbakken |
| `"*camera"` | alles dat eindigt op *camera*: deurbelcamera |
| `"*vuurwerk*"` | *vuurwerk* overal in een woord: vuurwerkbom, nitraatvuurwerk |
| `"in brand"` | precies deze woorden achter elkaar |

Hoofdletters maken niet uit.

### Een deelvraag toevoegen

Kopieer dit blok onderaan in het bestand en pas het aan:

```toml
[deelvragen.herstelwerk]
vraag = "Welke herstelwerkzaamheden zijn er nodig na oudejaarsavond?"
"schoonmaken straat" = ["veegwagen*", "*vuurwerkafval*", "opruim*"]
"glas vervangen" = ["ruit", "ruiten", "glaszetter*"]
"brand blussen" = ["geblust", "blussen", "brandweer"]
```

- `herstelwerk` is een korte naam zonder spaties. Dat wordt de kolomnaam in Excel.
- `vraag` is de deelvraag zoals die in het rapport komt.
- Elke regel daaronder is een categorie met de zoekwoorden die erbij horen.

Meer hoef je niet te doen. De nieuwe deelvraag verschijnt vanzelf in het startscherm, in Excel, in het rapport en in het eindoverzicht.

### Een website toevoegen

Zet een regel bij `[websites]`:

```toml
[websites]
"112vdg" = "https://112vdg.nl"
"alarmeringen.nl" = "https://alarmeringen.nl"
"omroep" = "https://www.voorbeeldnieuws.nl"
```

Dat werkt met elke nieuwssite. De scraper kiest zelf hoe:

| Soort website | Hoe hij werkt |
|---|---|
| 1. WordPress | Via de WordPress API. Snel, en zoekt precies binnen de periode. |
| 2. Site met sitemap | Bijna elke nieuwssite heeft een sitemap: een lijst van alle artikelen met hun datum. Hij leest alleen de artikelen binnen de periodes, met **trafilatura**. Werkt ook voor oudere jaren. Zo werkt alarmeringen.nl. |
| 3. Geen sitemap | Hij zoekt de zoekbalk op de homepage, zoekt op elke zoekterm, bladert door de resultaten en leest elk artikel met **trafilatura**. |

Bij het starten zie je per website welke methode hij gebruikt, of waarom hij een site overslaat.

**De sitemap-methode is trager**, omdat hij elk artikel in de periode moet openen. Voor alarmeringen.nl zijn dat er ongeveer 100 per jaarwisseling, dus reken op een paar minuten per jaar. `max_artikelen_per_website` begrenst dit per jaarwisseling.

**Vindt hij geen sitemap en geen zoekbalk?** Zoek dan op de website zelf naar *vuurwerk*. Kopieer het adres uit de adresbalk en zet `{zoekterm}` op de plek van *vuurwerk*:

```toml
"omroep" = { adres = "https://www.voorbeeldnieuws.nl", zoekpagina = "https://www.voorbeeldnieuws.nl/zoeken?q={zoekterm}" }
```

**Oudere jaren missen bij de zoekpagina-methode?** Zoekresultaten staan vaak nieuwste eerst. Zet dan `max_zoekpaginas` bij `[algemeen]` hoger.

**Website overgeslagen?** De scraper zegt altijd waarom:
- *robots.txt staat het niet toe*: de website wil niet gescraped worden. Dat respecteren we.
- *blokkeert scrapers (foutcode 403)*: een firewall houdt de scraper tegen. Dat omzeilen we niet. Vanaf een ander netwerk, zoals thuis, kan het soms wel werken.
- *vraagt eerst toestemming voor cookies*: zie hieronder.

### Websites met een cookiemuur

Sommige sites, zoals die van DPG Media, vragen op de voorpagina eerst toestemming voor cookies. Vaak is dat geen probleem: de sitemap en de artikelen zelf zijn dan wel gewoon bereikbaar. Bij alarmeringen.nl is dat zo.

Zit de cookiemuur ook op de artikelen, dan vraagt de scraper:

```
Browservenster openen? [j/n] (j):
```

Typ `j`. Er opent een venster van Edge of Chrome. **Klik daar zelf op akkoord** en wacht tot de website laadt. Het venster sluit dan vanzelf en de scraper gaat verder.

- De scraper klikt nooit zelf op akkoord. Die keuze maak jij.
- Je toestemming wordt bewaard in de map `.toestemming`, zodat het maar één keer hoeft. Die map gaat niet naar GitHub.
- Ook na de toestemming wordt robots.txt gewoon gecontroleerd.
- Wil je de toestemming intrekken? Verwijder de map `.toestemming`.

### Een website testen

Werkt een site niet zoals je verwacht? Test hem los:

```bash
py -m dosi_scraper --test https://alarmeringen.nl
```

Je ziet dan stap voor stap wat de site antwoordt: robots.txt, WordPress of niet, de sitemap, de zoekbalk, de volgende-knop en of er een artikel met datum gelezen kan worden.

### Iets anders aanpassen

Jaren, periode, wachttijd en de map voor de resultaten staan bovenaan bij `[algemeen]`. Welke woorden een artikel "relevant" maken staat bij `[zoeken]`.

**Typfout gemaakt?** De scraper zegt op welke regel het misgaat. Meestal is het een vergeten aanhalingsteken `"` of komma.

---

## 3. Resultaten

Na afloop staan in de map `data/`:

| Bestand | Inhoud |
|---|---|
| `rapport.md` | Per deelvraag een tabel met tellingen per jaarwisseling. **Begin hier.** |
| `artikelen.csv` | Eén rij per artikel met alle labels. Opent in Excel. |
| `artikelen.jsonl` | Dezelfde gegevens, voor verdere analyse in Python. |

In de kolom `fragmenten` staan de zinnen waarop de labels gebaseerd zijn. Zo kun je snel nakijken of een label klopt.

Een artikel is **relevant** als het een woord uit `onderwerp` bevat (vuurwerk, jaarwisseling) **en** een woord uit `schade` (vernield, beschadigd, schoonmaak).

---

## 4. Juridisch kader

- **robots.txt** wordt voor elke website gecontroleerd. Verbiedt robots.txt het, of is robots.txt niet bereikbaar, dan slaat de scraper de site over (ECLI:NL:RBAMS:2024:6563, artikel 15o Auteurswet).
- **Belasting van de site**: minimaal 1 seconde tussen verzoeken en een herkenbare User-Agent.
- **AVG**: standaard wordt de volledige tekst niet opgeslagen, alleen titel, link, labels en korte fragmenten. Nieuwsartikelen noemen soms namen. Gebruik die niet in het verslag en deel de map `data/` niet buiten de groep. Daarom staat `data/` in `.gitignore`.
- **Geen omzeiling**: de scraper stelt zich eerlijk voor met een eigen User-Agent. Firewalls en inlogpagina's omzeilen we niet. Dat past niet in ons juridisch kader. Een site die zo blokkeert wordt overgeslagen, met de reden erbij.
- **Cookietoestemming** geeft de onderzoeker zelf, in een gewoon browservenster. Lees daarbij de gebruiksvoorwaarden van de website. Sommige uitgevers verbieden scrapen in hun voorwaarden, ook als robots.txt het toestaat.

## 5. Beperkingen

- De labels komen uit zoekwoorden. Een telling betekent "in hoeveel artikelen wordt het genoemd", niet "hoeveel incidenten waren er".
- 112vdg.nl schrijft vooral over letsel en incidenten, minder over herstelkosten. Voor de vragen over kosten zijn gemeenten en het Verbond van Verzekeraars waarschijnlijk betere bronnen.
- Een bedrag in een artikel kan ook een boete of buit zijn. Controleer dit in het artikel.

---

## Voor wie de code wil lezen

| Bestand | Wat het doet |
|---|---|
| `instellingen.toml` | Alle instellingen, websites, deelvragen en zoekwoorden |
| `start.bat` | Startknop voor Windows |
| `dosi_scraper/__main__.py` | Startpunt: zet de stappen hieronder achter elkaar |
| `dosi_scraper/instellingen.py` | Leest en controleert `instellingen.toml`, zet zoekwoorden om naar zoekpatronen |
| `dosi_scraper/websites.py` | Haalt artikelen op via de WordPress API, de sitemap of de zoekpagina, leest ze met trafilatura, met robots.txt-controle, wachttijd en cookietoestemming |
| `dosi_scraper/analyse.py` | Labelt artikelen per deelvraag en telt alles |
| `dosi_scraper/uitvoer.py` | Het scherm tijdens het draaien en de bestanden erna |

Er staat geen deelvraag of website in de code zelf. Alles loopt via de lijst in `instellingen.toml`, zodat elke deelvraag op dezelfde manier wordt verwerkt.

Gebruikte bibliotheken: **requests** (HTTP), **BeautifulSoup** (HTML lezen), **trafilatura** (bestaande scraper die tekst en datum uit nieuwsartikelen haalt), **Playwright** (browservenster voor cookietoestemming), **rich** (voortgangsbalk en tabellen) en **tomllib** (instellingenbestand, standaard in Python 3.11+).
