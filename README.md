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
"omroep" = "https://www.voorbeeldnieuws.nl"
```

Dit werkt met nieuwssites die op **WordPress** draaien. Is een site geen WordPress, of staat robots.txt scrapen niet toe, dan slaat de scraper die site over en zegt hij waarom.

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
- **Firewalls**: alarmeringen.nl blokkeert scrapers. Die bron is bewust niet opgenomen. Een blokkade omzeilen past niet in ons juridisch kader.

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
| `dosi_scraper/websites.py` | Haalt artikelen op via de WordPress REST API, met robots.txt-controle en wachttijd |
| `dosi_scraper/analyse.py` | Labelt artikelen per deelvraag en telt alles |
| `dosi_scraper/uitvoer.py` | Het scherm tijdens het draaien en de bestanden erna |

Er staat geen deelvraag of website in de code zelf. Alles loopt via de lijst in `instellingen.toml`, zodat elke deelvraag op dezelfde manier wordt verwerkt.

Gebruikte bibliotheken: **requests** (HTTP), **BeautifulSoup** (HTML naar tekst), **rich** (voortgangsbalk en tabellen) en **tomllib** (instellingenbestand, standaard in Python 3.11+).
