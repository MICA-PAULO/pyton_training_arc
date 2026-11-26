"""Alles wat de gebruiker ziet: de terminal tijdens het draaien en de bestanden erna."""

import csv
import json
import time
from datetime import datetime

from rich import box
from rich.console import Console, Group
from rich.markup import escape
from rich.panel import Panel
from rich.progress import (BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TaskProgressColumn,
                           TextColumn, TimeElapsedColumn, TimeRemainingColumn)
from rich.table import Table

from .analyse import secties

console = Console()
BESTANDEN = {
    "rapport.md": "tabellen per deelvraag, begin hier",
    "artikelen.csv": "openen in Excel",
    "artikelen.jsonl": "voor analyse in Python",
}


def _duur(sec):
    sec = int(round(sec))
    return f"{sec} sec" if sec < 60 else f"{sec // 60} min {sec % 60:02d} sec"


def _lijst(waarden):
    return ", ".join(str(w) for w in waarden)


# ---------------------------------------------------------------- terminal

def fout(tekst):
    console.print(Panel(escape(str(tekst)), title="[bold red]Er ging iets mis[/]", border_style="red", expand=False))


def kop(inst, stappen):
    schatting = (stappen + 2 * len(inst.websites)) * (inst.wachttijd + 0.4)
    jaren = [f"{j}/{j + 1}" for j in inst.jaren]
    t = Table.grid(padding=(0, 2))
    t.add_column(style="bold cyan", no_wrap=True)
    t.add_column()
    t.add_row("Websites", _lijst(f"{n} [dim]({u})[/]" for n, u in inst.websites.items()))
    t.add_row("Jaarwisselingen", jaren[0] if len(jaren) == 1 else f"{jaren[0]} t/m {jaren[-1]}  [dim]({len(jaren)} stuks)[/]")
    t.add_row("Periode per jaar", "{1:02d}-{0:02d} t/m {3:02d}-{2:02d}".format(*inst.periode_van, *inst.periode_tot))
    t.add_row("Zoektermen", _lijst(f"'{z}'" for z in inst.zoektermen))
    t.add_row("Deelvragen", "\n".join(f"• {escape(v)}" for _, v in secties(inst)))
    t.add_row("Geschatte duur", f"ongeveer {_duur(schatting)}  [dim]({stappen} zoekopdrachten, {inst.wachttijd} sec pauze)[/]")
    t.add_row("Volledige tekst", "ja" if inst.tekst_opslaan else "nee [dim](AVG: alleen korte fragmenten)[/]")
    t.add_row("Resultaten in", str(inst.uitvoermap))
    console.print(Panel(t, title="[bold]DOSI-scraper[/]", subtitle="instellingen.toml", border_style="cyan", expand=False))


class Voortgang:
    """Voortgangsbalk met percentage, resterende tijd en een live lijst van relevante artikelen."""

    def __init__(self, inst, stappen):
        self.inst = inst
        self.start = time.monotonic()
        self.gevonden = self.relevant = 0
        breed = console.width >= 130
        kolommen = [SpinnerColumn(), TextColumn("[bold]{task.description}"),
                    BarColumn(bar_width=None if breed else 20), TaskProgressColumn()]
        if breed:
            kolommen += [MofNCompleteColumn(), TextColumn("[dim]·[/] verstreken"), TimeElapsedColumn()]
        kolommen += [TextColumn("[dim]·[/] nog"), TimeRemainingColumn(compact=True),
                     TextColumn("[dim]·[/] {task.fields[teller]}")]
        self.progress = Progress(*kolommen, console=console, expand=breed)
        self.taak = self.progress.add_task("Starten", total=stappen, teller="")

    def __enter__(self):
        self.progress.__enter__()
        console.print("\n[bold]Relevante artikelen[/] [dim](de andere worden ook opgeslagen)[/]")
        return self

    def __exit__(self, *exc):
        self.progress.__exit__(*exc)

    def _bijwerken(self, **extra):
        teller = f"[cyan]{self.gevonden}[/] gevonden · [green]{self.relevant}[/] relevant"
        self.progress.update(self.taak, teller=teller, **extra)

    def website(self, naam):
        console.print(f"\n[bold cyan]▶ {escape(naam)}[/]")

    def bezig(self, jaar, term, pagina):
        extra = f" p.{pagina}" if pagina > 1 else ""
        self.progress.update(self.taak, description=f"{jaar}/{jaar + 1}  '{term}'{extra}")

    def klaar(self, pagina, totaal):
        if pagina == 1 and totaal > 1:  # meer pagina's dan verwacht
            self.progress.update(self.taak, total=self.progress.tasks[0].total + totaal - 1)
        self._bijwerken(advance=1)

    def artikel(self, a):
        self.gevonden += 1
        if a["relevant"]:
            self.relevant += 1
            eerste = self.inst.deelvragen[0].sleutel if self.inst.deelvragen else "regio"
            rij = Table.grid(padding=(0, 1), expand=True)
            rij.add_column(width=3)
            rij.add_column(width=10, style="dim")
            rij.add_column(width=14, style="yellow", no_wrap=True, overflow="ellipsis")
            rij.add_column(ratio=3, no_wrap=True, overflow="ellipsis")
            rij.add_column(ratio=2, no_wrap=True, overflow="ellipsis", style="dim")
            rij.add_row(" [green]✓[/]", a["datum"], escape(_lijst(a["regio"]) or "-"),
                        escape(a["titel"]), "→ " + escape(_lijst(a[eerste]) or "-"))
            console.print(rij)
        self._bijwerken()

    def waarschuwing(self, tekst):
        console.print(f"  [bold red]✗[/] {escape(tekst)}")

    def duur(self):
        return time.monotonic() - self.start


def overzicht(inst, t, duur):
    per_jaar = Table(box=box.SIMPLE_HEAVY, title="Per jaarwisseling", title_style="bold")
    per_jaar.add_column("Jaarwisseling")
    per_jaar.add_column("Gevonden", justify="right")
    per_jaar.add_column("Relevant", justify="right", style="green")
    per_jaar.add_column("% relevant", justify="right")
    for j in t["jaren"] + ["Totaal"]:
        g = sum(t["gevonden"].values()) if j == "Totaal" else t["gevonden"][j]
        r = sum(t["relevant"].values()) if j == "Totaal" else t["relevant"][j]
        per_jaar.add_row(j, str(g), str(r), f"{r / g:.0%}" if g else "-", style="bold" if j == "Totaal" else None)

    top = Table(box=box.SIMPLE_HEAVY, title="Meest genoemd in relevante artikelen", title_style="bold", show_header=False)
    top.add_column(style="bold cyan", no_wrap=True)
    top.add_column()
    for sleutel, _ in secties(inst):
        rijen = t["per_sectie"][sleutel][:4]
        top.add_row(sleutel, _lijst(f"{escape(c)} ({sum(n.values())})" for c, n in rijen) or "[dim]geen[/]")

    bestanden = Table.grid(padding=(0, 2))
    bestanden.add_column(style="bold")
    bestanden.add_column()
    for naam, uitleg in BESTANDEN.items():
        bestanden.add_row(naam, f"{inst.uitvoermap / naam}  [dim]({uitleg})[/]")

    console.print()
    console.print(Panel(Group(per_jaar, top, "[bold]Bestanden[/]", bestanden),
                        title=f"[bold green]Klaar in {_duur(duur)}[/]", border_style="green", expand=False))
    console.print("[dim]Tellingen = aantal artikelen waarin iets genoemd wordt, niet het aantal incidenten. "
                  "Controleer een steekproef met de kolom 'fragmenten' in de CSV.[/]")


# ---------------------------------------------------------------- bestanden

def _md_tabel(koppen, rijen):
    regels = ["| " + " | ".join(koppen) + " |", "|---" + "|---:" * (len(koppen) - 1) + "|"]
    regels += ["| " + " | ".join(str(c) for c in rij) + " |" for rij in rijen]
    return "\n".join(regels) if rijen else "_Geen treffers._"


def opslaan(arts, inst, t):
    inst.uitvoermap.mkdir(parents=True, exist_ok=True)
    kolommen = (["website", "jaarwisseling", "datum", "titel", "url", "relevant"]
                + [s for s, _ in secties(inst)] + ["bedragen_eur", "fragmenten"]
                + (["tekst"] if inst.tekst_opslaan else []))

    with open(inst.uitvoermap / "artikelen.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=kolommen, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for a in arts:
            w.writerow({k: " | ".join(map(str, v)) if isinstance(v, list) else v for k, v in a.items()})

    with open(inst.uitvoermap / "artikelen.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(a, ensure_ascii=False) + "\n" for a in arts)

    jaren = t["jaren"]
    delen = [
        "# DOSI-scraper rapport",
        f"Gegenereerd op {datetime.now():%d-%m-%Y %H:%M}. Websites: {_lijst(inst.websites)}.",
        "Een telling betekent \"in hoeveel relevante artikelen wordt het genoemd\", niet \"hoeveel incidenten\". "
        "Controleer altijd een steekproef handmatig.",
        "## Artikelen per jaarwisseling",
        _md_tabel(["Jaarwisseling", "Gevonden", "Relevant"],
                  [(j, t["gevonden"][j], t["relevant"][j]) for j in jaren]),
    ]
    for sleutel, vraag in secties(inst):
        rijen = [(c, sum(n.values()), *(n[j] for j in jaren)) for c, n in t["per_sectie"][sleutel]]
        delen += [f"## {vraag}", _md_tabel(["Categorie", "Totaal", *jaren], rijen)]
    delen += [
        "## Genoemde bedragen",
        "Bedragen kunnen ook over boetes of buit gaan. Lees het artikel voordat je een bedrag als schade telt.",
        _md_tabel(["Jaarwisseling", "Bedrag", "Artikel"],
                  [(j, f"€ {b:,.0f}".replace(",", "."), f"[{ti}]({u})") for j, b, ti, u in t["bedragen"]]),
    ]
    (inst.uitvoermap / "rapport.md").write_text("\n\n".join(delen) + "\n", encoding="utf-8")
