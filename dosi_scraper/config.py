"""Instellingen en zoekwoorden voor DOSI-scraper.

Pas deze lijsten aan als de onderzoeksvraag verandert. Alle patronen zijn
reguliere expressies en worden op kleine letters toegepast.
"""

USER_AGENT = "DOSI-scraper/1.0 (studentenonderzoek OSINT, niet-commercieel)"

# Wachttijd tussen verzoeken in seconden. Niet lager zetten: we willen de
# website niet belasten.
DELAY = 1.5

# Bronnen uit de bronnenmatrix. Alleen WordPress-sites met een open REST API.
# alarmeringen.nl staat er niet in: die blokkeert scrapers met een firewall en
# is in de bronnenmatrix als onbetrouwbaar beoordeeld.
BRONNEN = {
    "112vdg": "https://112vdg.nl",
}

# Zoektermen die naar de API gestuurd worden.
ZOEKTERMEN = ["vuurwerk", "jaarwisseling", "oudejaarsnacht", "oud en nieuw", "nieuwjaarsnacht"]

# Periode rond de jaarwisseling: van 27 december tot en met 7 januari.
VENSTER_START = (12, 27)
VENSTER_EIND = (1, 8)  # exclusief

# Een artikel moet minstens een van deze termen bevatten om mee te tellen.
JAARWISSELING = [r"jaarwisseling", r"oudejaars", r"oud en nieuw", r"oud-en-nieuw",
                 r"nieuwjaarsnacht", r"vuurwerk", r"nieuwjaar"]

# Deelvraag: welke objecten in de openbare ruimte raken beschadigd?
OBJECTEN = {
    "bushokje / abri": [r"bushokje", r"\babri", r"wachthuisje"],
    "afvalbak / prullenbak": [r"prullenba", r"afvalba", r"vuilnisba"],
    "container / glasbak": [r"container", r"glasbak", r"kliko"],
    "lantaarnpaal / verlichting": [r"lantaarnpa", r"straatverlichting", r"lichtmast"],
    "verkeersbord / verkeerslicht": [r"verkeersbord", r"verkeerslicht", r"stoplicht", r"verkeerszuil"],
    "auto / voertuig": [r"\bauto'?s?\b", r"autobrand", r"voertuig", r"bestelbus", r"scooter"],
    "woning / gevel": [r"woning", r"gevel", r"voordeur", r"brievenbus", r"\bhuis\b"],
    "ruit / glas": [r"\bruit", r"\bramen\b", r"etalage"],
    "speeltuin / sportveld": [r"speeltoestel", r"speeltuin", r"cruijff court", r"voetbalkooi", r"trapveld"],
    "straatmeubilair": [r"\bbankje", r"zitbank", r"fietsenrek", r"paaltje", r"hekwerk"],
    "wegdek / bestrating": [r"wegdek", r"asfalt", r"bestrating", r"straatstenen"],
    "laadpaal": [r"laadpa"],
    "camera (vernield)": [r"camera(?:paal|mast)", r"camera'?s?\s+(?:\w+\s+)?(?:vernield|beschadigd|kapot)"],
    "gebouw (school, winkel, bedrijf)": [r"school", r"bedrijfspand", r"winkel", r"\bkerk", r"gemeentehuis", r"supermarkt"],
    "groen / natuur": [r"\bboom\b", r"\bbomen\b", r"plantsoen", r"\bberm", r"natuurgebied", r"heide"],
}

# Deelvraag: welk deel is schoonmaak en welk deel reparatie?
KOSTENSOORT = {
    "schoonmaak": [r"schoonma", r"opruim", r"veegwagen", r"veegdienst", r"vuurwerkafval", r"reinig", r"afval op straat"],
    "reparatie / herstel": [r"herstel", r"repar", r"vervang", r"vernield", r"vernieling", r"beschadig", r"opgeblazen", r"schade"],
}

# Deelvraag: welke factoren hebben impact op de schade?
FACTOREN = {
    "illegaal / zwaar vuurwerk": [r"illegaal", r"cobra", r"nitraat", r"mortier", r"strijker", r"explosief"],
    "brand": [r"\bbrand", r"in brand", r"vlammen"],
    "rellen / onrust": [r"rellen", r"\bonrust", r"ongeregeldhe", r"relschop", r"bekogeld"],
    "vuurwerkverbod / vuurwerkvrije zone": [r"vuurwerkverbod", r"vuurwerkvrije zone", r"vuurwerkvrij"],
    "alcohol": [r"alcohol", r"dronken", r"beschonken"],
    "weer": [r"\bstorm", r"harde wind", r"windstoten", r"\bregen\b"],
}

# Deelvraag: welk deel wordt door hulpdiensten of politie voorkomen?
PREVENTIE = {
    "aanhouding": [r"aangehouden", r"aanhouding", r"opgepakt", r"gearresteerd"],
    "inbeslagname vuurwerk": [r"in beslag", r"inbeslagname", r"onderschept"],
    "noodbevel / maatregel": [r"noodbevel", r"noodverordening", r"veiligheidsrisicogebied", r"preventief fouilleren"],
    "ME / extra inzet": [r"\bme\b", r"mobiele eenheid", r"extra inzet", r"extra agenten"],
    "cameratoezicht": [r"cameratoezicht", r"camerabeelden", r"bodycam"],
    "voorkomen / op tijd geblust": [r"voorkomen", r"op tijd geblust", r"snel geblust", r"wist te voorkomen"],
}

# Bedragen in euro, bijvoorbeeld "€ 1,2 miljoen" of "15.000 euro".
BEDRAG_REGEX = (
    r"(?:€\s?(?P<a>\d[\d.,]*)\s*(?P<ma>miljoen|duizend)?)"
    r"|(?:(?P<b>\d[\d.,]*)\s*(?P<mb>miljoen|duizend)?\s*euro)"
)
