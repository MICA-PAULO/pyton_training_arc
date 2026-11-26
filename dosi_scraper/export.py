"""Schrijft resultaten weg als CSV, JSON Lines en een leesbaar Markdown-rapport."""

import csv
import json
from datetime import datetime

LIJSTVELDEN = ["regio", "provincie", "objecten", "kostensoort", "factoren", "preventie", "bedragen_eur", "fragmenten"]
KOLOMMEN = ["bron", "id", "jaarwisseling", "datum", "titel", "url", "over_jaarwisseling",
            "materiele_schade"] + LIJSTVELDEN


def csv_schrijven(arts, pad):
    with open(pad, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=KOLOMMEN, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for a in arts:
            rij = dict(a)
            for v in LIJSTVELDEN:
                rij[v] = " | ".join(str(x) for x in a.get(v, []))
            w.writerow(rij)


def jsonl_schrijven(arts, pad):
    with open(pad, "w", encoding="utf-8") as f:
        for a in arts:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")


def _tabel(teller, kop, op_naam=False):
    if not teller:
        return "_Geen treffers._\n"
    rijen = sorted(teller.items()) if op_naam else teller.most_common()
    regels = [f"| {kop} | Aantal artikelen |", "|---|---:|"]
    regels += [f"| {k} | {v} |" for k, v in rijen]
    return "\n".join(regels) + "\n"


def rapport_schrijven(s, bronnen, pad):
    jaren = list(s["objecten_per_jaar"])
    objecten = [k for k, _ in s["objecten"].most_common()]
    per_jaar = ["| Object | " + " | ".join(jaren) + " |", "|---|" + "---:|" * len(jaren)]
    for o in objecten:
        per_jaar.append(f"| {o} | " + " | ".join(str(s["objecten_per_jaar"][j][o]) for j in jaren) + " |")

    bedragen = ["| Jaarwisseling | Bedrag | Artikel |", "|---|---:|---|"]
    for j, b, t, u in sorted(s["bedragen"]):
        bedragen.append(f"| {j} | € {b:,.0f} | [{t}]({u}) |".replace(",", "."))

    tekst = f"""# DOSI-scraper rapport

Gegenereerd op {datetime.now():%d-%m-%Y %H:%M}. Bronnen: {", ".join(bronnen)}.

Artikelen opgehaald: **{s["totaal_artikelen"]}**. Relevant (over de jaarwisseling en over materiële schade): **{s["relevant"]}**.

Let op: de labels komen uit zoekwoorden. Een telling betekent "aantal artikelen waarin het voorkomt", niet "aantal incidenten". Controleer altijd een steekproef handmatig.

## Relevante artikelen per jaarwisseling
{_tabel(s["per_jaarwisseling"], "Jaarwisseling", op_naam=True)}
## Welke objecten in de openbare ruimte raken het vaakst beschadigd?
{_tabel(s["objecten"], "Object")}
## Welk deel van de kosten is schoonmaak en welk deel reparatie?
{_tabel(s["kostensoort"], "Soort")}
### Genoemde bedragen
Bedragen kunnen ook over boetes of buit gaan. Lees het artikel voordat je een bedrag als schade telt.

{chr(10).join(bedragen) if s["bedragen"] else "_Geen bedragen gevonden._"}

## Welke factoren hebben impact op de materiële schade?
{_tabel(s["factoren"], "Factor")}
## In welke gebieden is de meeste schade?
{_tabel(s["provincie"], "Provincie")}
## Welk deel van de schade wordt door hulpdiensten of politie voorkomen?
{_tabel(s["preventie"], "Maatregel")}
## Hoe verschilt de schade over de jaren heen?
{chr(10).join(per_jaar) if objecten else "_Geen treffers._"}
"""
    with open(pad, "w", encoding="utf-8") as f:
        f.write(tekst)
