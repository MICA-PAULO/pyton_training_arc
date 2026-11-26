# DOSI-scraper

Web scraper voor het DOSI-project van groep 6 (2026-2027). De scraper verzamelt nieuwsartikelen over materiële schade rond oudejaarsavond en ordent ze per deelvraag uit het onderzoeksplan.

**Onderzoeksvraag:** Waar bestaat de materiële schade uit bij herstelwerkzaamheden na oudejaarsavond?

## Hoe het werkt

De scraper bouwt op bestaande onderdelen in plaats van alles zelf te maken:

- **WordPress REST API** (`/wp-json/wp/v2/posts`). Veel Nederlandse nieuwssites draaien op WordPress. Deze officiële API geeft artikelen als nette JSON terug, met datum, titel, tekst en categorie (bij 112vdg.nl is dat de provincie). We hoeven dus geen HTML-layout te ontleden.
- **requests** voor de HTTP-verzoeken en **BeautifulSoup** om de HTML in de artikeltekst om te zetten naar platte tekst. Dit zijn de modules uit ons verkennend onderzoek naar scrapers.
- **urllib.robotparser** uit de standaardbibliotheek om robots.txt te controleren.
- **rich** voor een overzichtelijke terminal: voortgangsbalk met percentage en resterende tijd, een live lijst van gevonden artikelen en een eindoverzicht.

Stappen:

1. Per jaarwisseling (27 december tot en met 7 januari) zoekt de scraper op `vuurwerk`, `jaarwisseling`, `oudejaarsnacht`, `oud en nieuw` en `nieuwjaarsnacht`.
2. Elk artikel krijgt labels op basis van zoekwoorden: beschadigde objecten, schoonmaak of reparatie, factoren, preventie door hulpdiensten, provincie en genoemde bedragen.
3. De resultaten komen in de map `data/`.

## Installeren

```bash
pip install -r requirements.txt
```

Op Windows werkt `pip` vaak niet in PowerShell. Gebruik dan `py -m pip install -r requirements.txt` en start de scraper met `py -m dosi_scraper`.

## Gebruiken

Alle jaarwisselingen van 2020/2021 tot en met 2025/2026:

```bash
python -m dosi_scraper
```

Alleen bepaalde jaren (het jaartal is het jaar van oudejaarsavond):

```bash
python -m dosi_scraper --jaren 2023,2024
```

Een extra WordPress-nieuwssite toevoegen:

```bash
python -m dosi_scraper --wp https://www.voorbeeldnieuws.nl
```

Volledige artikeltekst ook opslaan (standaard uit):

```bash
python -m dosi_scraper --met-tekst
```

## Wat je ziet tijdens het draaien

1. **Startscherm** met bronnen, jaren, zoektermen, aantal zoekopdrachten, geschatte duur en de map waar de resultaten komen.
2. **Live lijst** van relevante artikelen: datum, provincie, titel en de beschadigde objecten.
3. **Voortgangsbalk** met percentage, resterende tijd en hoeveel artikelen gevonden en relevant zijn.
4. **Eindoverzicht** met een tabel per jaarwisseling, de meest genoemde objecten, factoren en provincies, en de volledige paden naar de bestanden.

Stoppen kan met Ctrl+C. Wat al binnen is wordt dan nog opgeslagen.

## Uitvoer

| Bestand | Inhoud |
|---|---|
| `data/rapport.md` | Tabellen per deelvraag. Begin hier. |
| `data/artikelen.csv` | Eén rij per artikel met alle labels. Opent in Excel (puntkomma als scheidingsteken). |
| `data/artikelen.jsonl` | Dezelfde gegevens als JSON, handig voor verdere analyse in Python of pandas. |

Kolommen `over_jaarwisseling` en `materiele_schade` geven aan of een artikel meetelt in het rapport. De kolom `fragmenten` bevat de zinnen waarin schade genoemd wordt, zodat je snel kunt controleren of het label klopt.

## Zoekwoorden aanpassen

Alle zoekwoorden staan in `dosi_scraper/config.py`. Wil je een object toevoegen, zoals "fietsenstalling", zet het dan in `OBJECTEN`. Het zijn reguliere expressies op kleine letters.

## Juridisch kader

- **robots.txt**: elke URL wordt eerst gecontroleerd. Verbiedt robots.txt de URL, of is robots.txt niet bereikbaar, dan slaat de scraper de bron over (zie ECLI:NL:RBAMS:2024:6563 en artikel 15o Auteurswet).
- **Belasting van de site**: minimaal 1,5 seconde tussen verzoeken en een herkenbare User-Agent.
- **AVG**: standaard wordt de volledige tekst niet opgeslagen, alleen titel, link, labels en korte fragmenten. Nieuwsartikelen noemen soms namen. Gebruik die niet in het verslag en deel de map `data/` niet buiten de groep. Daarom staat `data/` in `.gitignore`.
- **Firewalls**: alarmeringen.nl blokkeert scrapers met een firewall. Die bron is bewust niet opgenomen. Een blokkade omzeilen past niet binnen ons juridisch kader, en de bron is in de bronnenmatrix al als onbetrouwbaar beoordeeld.

## Beperkingen

- De labels komen uit zoekwoorden. Een telling in het rapport betekent "aantal artikelen waarin het genoemd wordt", niet "aantal incidenten".
- 112vdg.nl schrijft vooral over letsel en incidenten, minder over herstelkosten. Voor de deelvragen over kosten zijn gemeentelijke bronnen en verzekeraars (bijvoorbeeld het Verbond van Verzekeraars) waarschijnlijk beter.
- Een bedrag in een artikel kan ook een boete of buit zijn. Controleer dit altijd in het artikel.
