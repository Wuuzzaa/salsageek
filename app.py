#!/usr/bin/env python3
"""
salsa_app.py – Interaktive Salsa-Lernhilfe für LA Style On1 (Leader)
"""
import sys
from pathlib import Path
from typing import Set, Dict, List

# Liegt im selben Verzeichnis wie data/ und src/
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SRC_DIR = BASE_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from src.salsa_notation import (
    load_elements, load_figures,
    get_executable_figures, recommend_elements_to_learn,
    Element, Figure,
)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich import box
from rich.columns import Columns
from rich.rule import Rule
from rich.style import Style

console = Console()

PROFILE_FILE = BASE_DIR / "profil.yaml"

# ---------------------------------------------------------------------------
# Profil speichern / laden
# ---------------------------------------------------------------------------

def save_profile(known_ids: Set[str]):
    import yaml
    data = {"bekannte_elemente": sorted(known_ids)}
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    console.print(f"[dim]✓ Profil gespeichert: {PROFILE_FILE.name}[/dim]")


def load_profile() -> Set[str]:
    import yaml
    if not PROFILE_FILE.exists():
        return set()
    with open(PROFILE_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return set(data.get("bekannte_elemente", []))


# ---------------------------------------------------------------------------
# Level-Farben
# ---------------------------------------------------------------------------
LEVEL_COLOR = {
    1: "green",
    2: "cyan",
    3: "yellow",
    4: "red",
    5: "magenta",
}
LEVEL_LABEL = {
    1: "●  Anfänger",
    2: "●● Einsteiger",
    3: "●●● Mittelstufe",
    4: "●●●● Fortgeschritten",
    5: "●●●●● Experte",
}


def level_badge(level: int) -> Text:
    color = LEVEL_COLOR.get(level, "white")
    label = LEVEL_LABEL.get(level, f"Level {level}")
    return Text(f" {label} ", style=f"bold {color}")


# ---------------------------------------------------------------------------
# Intro
# ---------------------------------------------------------------------------
def print_intro():
    console.print()
    console.print(Panel.fit(
        "[bold yellow]🎵 SALSA ON1 – LA STYLE[/bold yellow]\n"
        "[dim]Figuren-Notation & Lernhilfe für Leader[/dim]\n"
        "[dim italic]Version 0.1 · Erweiterbar via YAML[/dim italic]",
        border_style="yellow",
        padding=(1, 4),
    ))
    console.print()


# ---------------------------------------------------------------------------
# Element-Auswahl
# ---------------------------------------------------------------------------
def select_known_elements(elements: Dict, preloaded: Set[str] = None) -> Set[str]:
    """Interaktive Abfrage: Welche Elemente beherrscht der User?
    Bereits bekannte Elemente werden vorausgefüllt (aus Profil).
    """
    console.print(Rule("[bold]Repertoire bearbeiten[/bold]"))
    console.print(
        "\nBestätige mit [bold green]j[/bold green] (ja) oder "
        "[bold red]n[/bold red] (nein).  "
        "[dim]? = Details anzeigen[/dim]\n"
    )
    if preloaded:
        console.print(
            f"[dim]Vorbelegt aus Profil: {len(preloaded)} Element(e). "
            f"Standard-Antwort entsprechend vorgewählt.[/dim]\n"
        )

    known: Set[str] = set()
    current_level = 0
    if preloaded is None:
        preloaded = set()

    by_level: Dict[int, List[Element]] = {}
    for elem in elements.values():
        by_level.setdefault(elem.level, []).append(elem)

    for level in sorted(by_level.keys()):
        color = LEVEL_COLOR.get(level, "white")
        console.print(f"\n[bold {color}]── Level {level}: {LEVEL_LABEL[level]} ──[/bold {color}]")

        for elem in sorted(by_level[level], key=lambda e: e.id):
            already_known = elem.id in preloaded
            default_answer = "j" if already_known else "n"
            marker = " [green]✓[/green]" if already_known else ""

            console.print(f"\n  [bold]{elem.name}[/bold]{marker}")
            console.print(f"  [dim]{elem.description}[/dim]")
            console.print(f"  [dim]Tags: {', '.join(elem.tags)}[/dim]")

            answer = Prompt.ask(
                f"  Beherrschst du [bold cyan]{elem.name}[/bold cyan]?",
                choices=["j", "n", "?"],
                default=default_answer,
            )

            if answer == "?":
                _show_element_detail(elem)
                answer = Prompt.ask(
                    f"  Beherrschst du [bold cyan]{elem.name}[/bold cyan]?",
                    choices=["j", "n"],
                    default=default_answer,
                )

            if answer == "j":
                known.add(elem.id)
                if elem.level > current_level:
                    current_level = elem.level

    return known


def _show_element_detail(elem: Element):
    """Zeigt detaillierte Informationen zu einem Element."""
    console.print()
    table = Table(
        title=f"[bold]{elem.name}[/bold]",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=False,
        padding=(0, 1),
    )
    table.add_column("Feld", style="dim", width=18)
    table.add_column("Wert")

    table.add_row("Level", level_badge(elem.level))
    table.add_row("Takte", str(elem.counts))
    table.add_row("Tags", ", ".join(elem.tags))
    table.add_row("Beschreibung", elem.description[:200])

    if elem.signals:
        sig_text = "\n".join(
            f"Beat {s.beat or '?'}: {s.description}" if s.beat else s.description
            for s in elem.signals
        )
        table.add_row("Führungssignale", sig_text)

    if elem.leader_actions:
        actions = "\n".join(
            f"Beat {a.beat}: {a.description}" for a in elem.leader_actions if a.description
        )
        table.add_row("Leader-Aktionen", actions[:300])

    table.add_row("Vorbedingung", _state_str(elem.pre))
    table.add_row("Ergebnis-Zustand", _state_str(elem.post))

    if elem.notes:
        table.add_row("Hinweise", elem.notes[:200])

    console.print(table)
    console.print()


def _state_str(state) -> str:
    parts = []
    if state.hand_hold:
        parts.append(f"Hand: {', '.join(sorted(state.hand_hold))}")
    if state.position:
        parts.append(f"Pos: {', '.join(sorted(state.position))}")
    if state.slot:
        parts.append(f"Slot: {', '.join(sorted(state.slot))}")
    return " · ".join(parts)


# ---------------------------------------------------------------------------
# Figuren anzeigen
# ---------------------------------------------------------------------------
def show_executable_figures(known_ids: Set[str], figures: Dict, elements: Dict):
    """Zeigt alle ausführbaren Figuren."""
    console.print()
    console.print(Rule("[bold]Schritt 2: Dein aktuelles Figuren-Repertoire[/bold]"))

    executable = get_executable_figures(known_ids, figures)

    if not executable:
        console.print(
            "\n[yellow]Mit deinen aktuellen Elementen kannst du noch keine "
            "vordefinierten Figuren ausführen.[/yellow]\n"
            "Lerne zunächst die Grundelemente (Level 1).\n"
        )
        return

    console.print(
        f"\n[green bold]Du kannst {len(executable)} Figuren ausführen:[/green bold]\n"
    )

    for fig in executable:
        color = LEVEL_COLOR.get(fig.level, "white")

        # Sequenz als lesbare Kette
        sequence_str = " → ".join(
            elements[eid].name if eid in elements else f"[{eid}]"
            for eid in fig.sequence
        )

        panel_content = (
            f"[dim]{fig.description[:120]}[/dim]\n\n"
            f"[bold]Sequenz:[/bold] {sequence_str}\n"
            f"[bold]Takte:[/bold] {fig.total_counts}  |  "
            f"[bold]Tags:[/bold] {', '.join(fig.tags)}"
        )
        if fig.notes:
            panel_content += f"\n[italic dim]{fig.notes[:100]}[/italic dim]"

        console.print(Panel(
            panel_content,
            title=f"[bold {color}]{fig.name}[/bold {color}]  {level_badge(fig.level)}",
            border_style=color,
            padding=(0, 1),
        ))


# ---------------------------------------------------------------------------
# Lernempfehlungen
# ---------------------------------------------------------------------------
def show_recommendations(known_ids: Set[str], figures: Dict, elements: Dict):
    """Zeigt die empfohlenen nächsten Elemente."""
    console.print()
    console.print(Rule("[bold]Schritt 3: Was solltest du als nächstes lernen?[/bold]"))

    # Aktuelles Level bestimmen
    if known_ids:
        current_level = max(elements[eid].level for eid in known_ids if eid in elements)
    else:
        current_level = 0

    console.print(f"\n[dim]Dein aktuelles Level:[/dim] {level_badge(current_level)}\n")

    recs = recommend_elements_to_learn(
        known_ids, figures, elements, current_level, top_n=5
    )

    if not recs:
        console.print("[green]Du kennst bereits alle relevanten Elemente! 🎉[/green]")
        return

    for rank, rec in enumerate(recs, 1):
        elem = rec["element"]
        color = LEVEL_COLOR.get(elem.level, "white")

        new_figs = rec["new_figures"]
        almost = rec["almost_unlocked"]

        content_lines = [
            f"[dim]{elem.description[:100]}[/dim]",
            f"[bold]Schaltet[/bold] [green]{len(new_figs)} neue Figur(en)[/green] frei",
        ]

        if new_figs:
            content_lines.append(
                "[dim]  → " + ", ".join(f.name for f in new_figs[:3]) +
                ("…" if len(new_figs) > 3 else "") + "[/dim]"
            )

        if almost:
            content_lines.append(
                f"[yellow]Fast fertig:[/yellow] {len(almost)} Figur(en) fehlt dann nur noch 1 Element"
            )
            content_lines.append(
                "[dim]  → " + ", ".join(f.name for f in almost[:3]) + "[/dim]"
            )

        content_lines.append(
            f"[dim]Tags: {', '.join(elem.tags)}[/dim]"
        )

        score_bar = "⭐" * min(rec["score"] // 5, 5)

        console.print(Panel(
            "\n".join(content_lines),
            title=(
                f"[bold]#{rank}[/bold]  "
                f"[bold {color}]{elem.name}[/bold {color}]  "
                f"{level_badge(elem.level)}  [yellow]{score_bar}[/yellow]"
            ),
            border_style=color,
            padding=(0, 1),
        ))


# ---------------------------------------------------------------------------
# Figur-Builder: Prüft ob eine eigene Sequenz gültig ist
# ---------------------------------------------------------------------------
def interactive_figure_builder(elements: Dict):
    """Erlaubt manuelle Komposition einer Figur und prüft Kompatibilität."""
    console.print()
    console.print(Rule("[bold]Figuren-Baukasten[/bold]"))
    console.print(
        "\n[dim]Gib Element-IDs ein (kommasepariert), um eine eigene Sequenz zu prüfen.\n"
        "Verfügbare IDs: " + ", ".join(sorted(elements.keys())) + "[/dim]\n"
    )

    raw = Prompt.ask("Element-Sequenz")
    seq = [s.strip() for s in raw.split(",")]

    unknown = [eid for eid in seq if eid not in elements]
    if unknown:
        console.print(f"[red]Unbekannte Elemente: {', '.join(unknown)}[/red]")
        return

    # Kompatibilität prüfen
    errors = []
    elem_list = [elements[eid] for eid in seq]
    for i in range(len(elem_list) - 1):
        a, b = elem_list[i], elem_list[i + 1]
        if not b.can_follow(a):
            errors.append(
                f"[red]✗[/red] [bold]{a.name}[/bold] → [bold]{b.name}[/bold]: "
                f"Zustand inkompatibel\n"
                f"  Post: {_state_str(a.post)}\n"
                f"  Pre:  {_state_str(b.pre)}"
            )

    if errors:
        console.print("\n[red bold]Kompatibilitätsfehler:[/red bold]")
        for e in errors:
            console.print(e)
    else:
        console.print("\n[green bold]✓ Sequenz ist gültig![/green bold]")
        total = sum(e.counts for e in elem_list)
        console.print(
            f"Sequenz: " +
            " → ".join(f"[cyan]{e.name}[/cyan]" for e in elem_list)
        )
        console.print(f"Gesamt: {total} Takte ({total // 8} × 8-Beat-Phrase)")

        # Anfangszustand ausgeben
        console.print(
            f"\nStart-Zustand: {_state_str(elem_list[0].pre)}\n"
            f"End-Zustand:   {_state_str(elem_list[-1].post)}"
        )


# ---------------------------------------------------------------------------
# Element-Explorer
# ---------------------------------------------------------------------------
def explore_elements(elements: Dict):
    """Zeigt alle Elemente mit Filtermöglichkeit."""
    console.print()
    console.print(Rule("[bold]Element-Explorer[/bold]"))

    filter_level = Prompt.ask(
        "Level filtern (1-5) oder [bold]alle[/bold] anzeigen",
        default="alle"
    )

    for eid, elem in sorted(elements.items(), key=lambda x: (x[1].level, x[0])):
        if filter_level != "alle":
            try:
                if elem.level != int(filter_level):
                    continue
            except ValueError:
                pass
        _show_element_detail(elem)
        if not Confirm.ask("Nächstes Element?", default=True):
            break


# ---------------------------------------------------------------------------
# Hauptmenü
# ---------------------------------------------------------------------------
def main():
    elements = load_elements(DATA_DIR / "elements.yaml")
    figures = load_figures(DATA_DIR / "figures.yaml", elements)

    invalid = [(fid, f) for fid, f in figures.items() if not f.valid]
    if invalid:
        console.print(f"\n[yellow]Warnung: {len(invalid)} Figur(en) haben Validierungsfehler:[/yellow]")
        for fid, f in invalid:
            console.print(f"  [red]{fid}[/red]: {', '.join(f.validation_errors)}")

    print_intro()
    console.print(
        f"[dim]Geladen: {len(elements)} Elemente · {len(figures)} Figuren "
        f"({len(figures) - len(invalid)} gültig)[/dim]\n"
    )

    # Profil laden
    known_ids = load_profile()
    # Unbekannte IDs (z.B. nach YAML-Erweiterung) bereinigen
    known_ids = {eid for eid in known_ids if eid in elements}

    if known_ids:
        console.print(
            f"[green]✓ Profil geladen:[/green] {len(known_ids)} Elemente bekannt "
            f"[dim]({PROFILE_FILE.name})[/dim]\n"
        )
    else:
        console.print(
            f"[dim]Kein Profil gefunden – beim ersten Durchlauf Repertoire eingeben.[/dim]\n"
        )

    while True:
        console.print(Rule("[bold]Hauptmenü[/bold]"))
        profile_hint = (
            f"[dim]  Profil: {len(known_ids)} Elemente geladen[/dim]\n"
            if known_ids else
            "[dim]  Kein Profil – Option 1 wählen[/dim]\n"
        )
        console.print(
            f"\n{profile_hint}"
            "  [bold cyan]1[/bold cyan] → Repertoire bearbeiten & speichern\n"
            "  [bold cyan]2[/bold cyan] → Meine Figuren anzeigen\n"
            "  [bold cyan]3[/bold cyan] → Lernempfehlungen\n"
            "  [bold cyan]4[/bold cyan] → Figuren-Baukasten (eigene Sequenz testen)\n"
            "  [bold cyan]5[/bold cyan] → Element-Explorer (Details)\n"
            "  [bold cyan]q[/bold cyan] → Beenden\n"
        )

        choice = Prompt.ask("Auswahl", choices=["1", "2", "3", "4", "5", "q"], default="1")

        if choice == "q":
            console.print("\n[yellow]Hasta la vista – y a bailar! 💃[/yellow]\n")
            break

        elif choice == "1":
            known_ids = select_known_elements(elements, preloaded=known_ids)
            console.print(f"\n[green]✓ Du beherrschst {len(known_ids)} Elemente.[/green]")
            save_profile(known_ids)

        elif choice == "2":
            if not known_ids:
                console.print("[yellow]Noch kein Repertoire – bitte Option 1 wählen.[/yellow]")
            else:
                show_executable_figures(known_ids, figures, elements)

        elif choice == "3":
            if not known_ids:
                console.print("[yellow]Noch kein Repertoire – bitte Option 1 wählen.[/yellow]")
            else:
                show_executable_figures(known_ids, figures, elements)
                show_recommendations(known_ids, figures, elements)

        elif choice == "4":
            interactive_figure_builder(elements)

        elif choice == "5":
            explore_elements(elements)

        console.print()


if __name__ == "__main__":
    main()
