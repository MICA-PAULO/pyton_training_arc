"""Alles wat de gebruiker in de terminal ziet: kop, voortgangsbalk en eindoverzicht."""

import os
import time
from collections import Counter

from rich import box
from rich.console import Console, Group
from rich.markup import escape
from rich.panel import Panel
from rich.progress import (BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TaskProgressColumn,
                           TextColumn, TimeElapsedColumn, TimeRemainingColumn)
from rich.table import Table

from . import config

console = Console()


def _duur(sec):
    sec = int(round(sec))
    if sec < 60:
        return f"{sec} sec"
    return f"{sec // 60} min {sec % 60:02d} sec"


def kop(bronnen, jaren, uitmap, stappen, met_tekst):
    schatting = (stappen + 2 * len(bronnen)) * (config.DELAY + 0.4)
    t = Table.grid(padding=(0, 2))
    t.add_column(style="bold cyan", no_wrap=True)
    t.add_column()
    t.add_row("Bronnen", ", ".join(f"{b} [dim]({u})[/]" for b, u in bronnen.items()))
    t.add_row("Jaarwisselingen", f"{jaren[0]}/{jaren[0] + 1} t/m {jaren[-1]}/{jaren[-1] + 1}  [dim]({len(jaren)} stuks)[/]"
              if len(jaren) > 1 else f"{jaren[0]}/{jaren[0] + 1}")
    t.add_row("Periode per jaar", "27 december t/m 7 januari")
    t.add_row("Zoektermen", ", ".join(f"'{z}'" for z in config.ZOEKTERMEN))
    t.add_row("Zoekopdrachten", f"{stappen}  [dim](1,5 sec pauze tussen elk verzoek)[/]")
    t.add_row("Geschatte duur", f"ongeveer {_duur(schatting)}")
    t.add_row("Volledige tekst", "ja" if met_tekst else "nee [dim](AVG: alleen fragmenten)[/]")
    t.add_row("Resultaten in", os.path.abspath(uitmap))
    console.print(Panel(t, title="[bold]DOSI-scraper[/]", subtitle="materiële schade na oudejaarsavond",
                        border_style="cyan", expand=False))


class Voortgang:
    """Voortgangsbalk met percentage, resterende tijd en een live teller."""

    def __init__(self, stappen):
        self.start = time.monotonic()
        self.gevonden = 0
        self.relevant = 0
        breed = console.width >= 130
        kolommen = [
            SpinnerColumn(),
            TextColumn("[bold]{task.description}"),
            BarColumn(bar_width=None if breed else 20),
            TaskProgressColumn(),
        ]
        if breed:
            kolommen += [MofNCompleteColumn(), TextColumn("[dim]·[/] verstreken"), TimeElapsedColumn()]
        kolommen += [TextColumn("[dim]·[/] nog"), TimeRemainingColumn(compact=True),
                     TextColumn("[dim]·[/] {task.fields[teller]}")]
        self.progress = Progress(*kolommen, console=console, expand=breed)
        self.taak = self.progress.add_task("Starten", total=stappen, teller="")

    def __enter__(self):
        self.progress.__enter__()
        console.print("\n[bold]Gevonden artikelen over materiële schade[/] [dim](de rest wordt wel opgeslagen)[/]")
        return self

    def __exit__(self, *exc):
        self.progress.__exit__(*exc)

    def _teller(self):
        return f"[cyan]{self.gevonden}[/] gevonden · [green]{self.relevant}[/] relevant"

    def bron(self, naam):
        console.print(f"\n[bold cyan]▶ Bron {escape(naam)}[/]")

    def bezig(self, jaar, term, pagina):
        extra = f" p.{pagina}" if pagina > 1 else ""
        self.progress.update(self.taak, description=f"{jaar}/{jaar + 1}  '{term}'{extra}")

    def klaar(self, jaar, term, pagina, totaal, nieuw):
        if pagina == 1 and totaal > 1:
            # Meer pagina's dan verwacht: de balk iets langer maken.
            t = self.progress.tasks[0].total
            self.progress.update(self.taak, total=t + totaal - 1)
        self.progress.update(self.taak, advance=1, teller=self._teller())

    def artikel(self, a):
        self.gevonden += 1
        if a["over_jaarwisseling"] and a["materiele_schade"]:
            self.relevant += 1
            regio = ", ".join(a["provincie"]) or ("landelijk" if "Binnenland" in a["regio"] else "onbekend")
            obj = ", ".join(a["objecten"][:3]) or "-"
            rij = Table.grid(padding=(0, 1), expand=True)
            rij.add_column(width=3)
            rij.add_column(width=10, style="dim")
            rij.add_column(width=14, style="yellow", no_wrap=True, overflow="ellipsis")
            rij.add_column(ratio=3, no_wrap=True, overflow="ellipsis")
            rij.add_column(ratio=2, no_wrap=True, overflow="ellipsis", style="dim")
            rij.add_row(" [green]✓[/]", a["datum"][:10], escape(regio), escape(a["titel"]), "→ " + escape(obj))
            console.print(rij)
        self.progress.update(self.taak, teller=self._teller())

    def waarschuwing(self, tekst):
        console.print(f"  [bold red]✗[/] {escape(tekst)}")

    def duur(self):
        return time.monotonic() - self.start


def _top(teller, n=5):
    if not teller:
        return "[dim]geen[/]"
    return "\n".join(f"{v:>3}  {escape(k)}" for k, v in teller.most_common(n))


def overzicht(arts, s, bestanden, duur):
    per_jaar = Table(title="Per jaarwisseling", box=box.SIMPLE_HEAVY, title_style="bold")
    per_jaar.add_column("Jaarwisseling")
    per_jaar.add_column("Gevonden", justify="right")
    per_jaar.add_column("Relevant", justify="right", style="green")
    per_jaar.add_column("% relevant", justify="right")
    gevonden = Counter(a["jaarwisseling"] for a in arts)
    for j in sorted(gevonden):
        r = s["per_jaarwisseling"].get(j, 0)
        per_jaar.add_row(j, str(gevonden[j]), str(r), f"{r / gevonden[j]:.0%}")
    per_jaar.add_row("[bold]Totaal", f"[bold]{len(arts)}", f"[bold]{s['relevant']}",
                     f"[bold]{s['relevant'] / len(arts):.0%}" if arts else "-", end_section=True)

    top = Table(box=box.SIMPLE_HEAVY, title="Meest genoemd in relevante artikelen", title_style="bold")
    top.add_column("Objecten")
    top.add_column("Factoren")
    top.add_column("Provincies")
    top.add_row(_top(s["objecten"]), _top(s["factoren"]), _top(s["provincie"]))

    files = Table.grid(padding=(0, 2))
    files.add_column(style="bold")
    files.add_column()
    uitleg = {"rapport.md": "tabellen per deelvraag, begin hier",
              "artikelen.csv": "openen in Excel",
              "artikelen.jsonl": "voor analyse in Python"}
    for pad in bestanden:
        naam = os.path.basename(pad)
        files.add_row(naam, f"{os.path.abspath(pad)}  [dim]({uitleg.get(naam, '')})[/]")

    console.print()
    console.print(Panel(Group(per_jaar, top, "[bold]Bestanden[/]", files),
                        title=f"[bold green]Klaar in {_duur(duur)}[/]", border_style="green", expand=False))
    console.print("[dim]Tellingen = aantal artikelen waarin iets genoemd wordt, niet het aantal incidenten. "
                  "Controleer een steekproef met de kolom 'fragmenten' in de CSV.[/]")
