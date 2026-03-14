#!/usr/bin/env python3
"""
Web-App für die Salsa-Lernhilfe auf Basis von Flask.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

import yaml
from flask import Flask, abort, redirect, render_template, request, url_for

from src.salsa_notation import (
    Element,
    Figure,
    get_executable_figures,
    load_elements,
    load_figures,
    recommend_elements_to_learn,
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PROFILE_FILE = BASE_DIR / "profil.yaml"

app = Flask(__name__)

LEVEL_LABEL = {
    0: "Noch offen",
    1: "Anfänger",
    2: "Einsteiger",
    3: "Mittelstufe",
    4: "Fortgeschritten",
    5: "Experte",
}
LEVEL_BADGE = {
    1: "success",
    2: "info",
    3: "warning",
    4: "danger",
    5: "dark",
}

elements: Dict[str, Element] = load_elements(DATA_DIR / "elements.yaml")
figures: Dict[str, Figure] = load_figures(DATA_DIR / "figures.yaml", elements)


def load_profile() -> Set[str]:
    if not PROFILE_FILE.exists():
        return set()

    with open(PROFILE_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    known_ids = set(data.get("bekannte_elemente", []))
    return {eid for eid in known_ids if eid in elements}


def save_profile(known_ids: Set[str]) -> None:
    data = {"bekannte_elemente": sorted(known_ids)}
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def current_level_for(known_ids: Set[str]) -> int:
    if not known_ids:
        return 0
    return max(elements[eid].level for eid in known_ids if eid in elements)


def state_str(state) -> str:
    parts: List[str] = []

    if state.hand_hold:
        parts.append(f"Handverbindung: {', '.join(sorted(state.hand_hold))}")
    if state.position:
        parts.append(f"Position: {', '.join(sorted(state.position))}")
    if state.slot:
        parts.append(f"Slot: {', '.join(sorted(state.slot))}")
    if state.leader_weight:
        parts.append(f"Leader-Gewicht: {', '.join(sorted(state.leader_weight))}")
    if state.follower_weight:
        parts.append(f"Follower-Gewicht: {', '.join(sorted(state.follower_weight))}")

    return " · ".join(parts)


def group_elements_by_level() -> Dict[int, List[Element]]:
    grouped: Dict[int, List[Element]] = {}
    for elem in elements.values():
        grouped.setdefault(elem.level, []).append(elem)

    for level in grouped:
        grouped[level] = sorted(grouped[level], key=lambda e: e.id)

    return dict(sorted(grouped.items()))


def find_figures_using_element(element_id: str) -> List[Figure]:
    used_in = [
        fig for fig in figures.values()
        if fig.valid and element_id in fig.sequence
    ]
    return sorted(used_in, key=lambda fig: (fig.level, fig.name))


def get_almost_executable_figures(known_ids: Set[str]) -> List[Figure]:
    """Figuren, bei denen genau ein Element fehlt."""
    result = [
        fig for fig in figures.values()
        if fig.valid and fig.is_almost_executable(known_ids)
    ]
    return sorted(result, key=lambda f: (f.level, f.name))


def explain_compatibility_error(first: Element, second: Element) -> str:
    """Erklärt benutzerfreundlich, warum Element B nicht auf Element A folgen kann."""
    post = first.post
    pre = second.pre
    
    reasons = []
    if not (post.hand_hold & pre.hand_hold):
        reasons.append(f"die Handverbindung nicht passt (Ende: {', '.join(sorted(post.hand_hold))} vs. Start: {', '.join(sorted(pre.hand_hold))})")
    if not (post.position & pre.position):
        reasons.append(f"die Position im Raum unterschiedlich ist")
    if not (post.slot & pre.slot):
        reasons.append(f"die Ausrichtung im Slot nicht übereinstimmt")
    if not (post.leader_weight & pre.leader_weight):
        reasons.append(f"das Gewicht des Leaders auf dem falschen Fuß ist")
    if not (post.follower_weight & pre.follower_weight):
        reasons.append(f"das Gewicht des Followers auf dem falschen Fuß ist")
    
    if not reasons:
        return "ein unbekannter technischer Fehler vorliegt."
    
    return "weil " + " und ".join(reasons) + "."


@app.context_processor
def inject_globals():
    return {
        "level_label": LEVEL_LABEL,
        "level_badge": LEVEL_BADGE,
        "elements": elements,
    }


@app.route("/")
def index():
    known_ids = load_profile()
    executable = get_executable_figures(known_ids, figures)
    almost_executable = get_almost_executable_figures(known_ids)
    invalid = [fig for fig in figures.values() if not fig.valid]
    current_level = current_level_for(known_ids)
    
    # Nächste Empfehlung für Zusammenfassung
    recs = recommend_elements_to_learn(known_ids, figures, elements, current_level, top_n=1)
    top_rec = recs[0] if recs else None

    return render_template(
        "index.html",
        known_ids=known_ids,
        elements=elements,
        figures=figures,
        executable=executable,
        almost_executable=almost_executable,
        invalid=invalid,
        current_level=current_level,
        top_rec=top_rec
    )


@app.route("/elemente")
def elemente():
    known_ids = load_profile()
    grouped = group_elements_by_level()

    return render_template(
        "elemente.html",
        grouped=grouped,
        known_ids=known_ids,
    )


@app.route("/element/<element_id>")
def element_detail(element_id: str):
    element = elements.get(element_id)
    if element is None:
        abort(404)

    known_ids = load_profile()
    used_in_figures = find_figures_using_element(element_id)

    return render_template(
        "element_detail.html",
        element=element,
        is_known=element_id in known_ids,
        used_in_figures=used_in_figures,
        pre_state=element.pre,
        post_state=element.post,
    )


@app.route("/repertoire", methods=["GET", "POST"])
def repertoire():
    if request.method == "POST":
        selected = set(request.form.getlist("known_ids"))
        selected = {eid for eid in selected if eid in elements}
        save_profile(selected)
        return redirect(url_for("repertoire", saved="1"))

    known_ids = load_profile()

    return render_template(
        "repertoire.html",
        grouped=group_elements_by_level(),
        known_ids=known_ids,
        current_level=current_level_for(known_ids),
        saved=request.args.get("saved") == "1",
    )


@app.route("/figuren")
def figuren_view():
    known_ids = load_profile()
    executable = get_executable_figures(known_ids, figures)
    almost_executable = get_almost_executable_figures(known_ids)

    return render_template(
        "figuren.html",
        known_ids=known_ids,
        executable=executable,
        almost_executable=almost_executable,
    )


@app.route("/figuren/<figure_id>")
def figure_detail(figure_id: str):
    if figure_id not in figures:
        abort(404)

    fig = figures[figure_id]
    known_ids = load_profile()

    # Prüfung ob ausführbar
    is_executable = fig.is_executable_with(known_ids)

    # Details für die Sequenz-Elemente
    # fig.elements ist bereits beim Laden befüllt worden
    
    return render_template(
        "figure_detail.html",
        figure=fig,
        is_executable=is_executable,
        known_ids=known_ids,
    )


@app.route("/empfehlungen")
def empfehlungen():
    known_ids = load_profile()
    current_level = current_level_for(known_ids)

    recs = recommend_elements_to_learn(
        known_ids=known_ids,
        figures=figures,
        elements=elements,
        current_level=current_level,
        top_n=5,
    )

    return render_template(
        "empfehlungen.html",
        known_ids=known_ids,
        recs=recs,
        current_level=current_level,
    )


@app.route("/builder", methods=["GET", "POST"])
def builder():
    result = None
    error = None
    raw = ""

    if request.method == "POST":
        action = request.form.get("action")
        raw = request.form.get("sequence", "").strip()
        
        if action == "reset":
            raw = ""
        elif action == "add":
            new_id = request.form.get("element_id")
            if new_id:
                if raw:
                    raw += "," + new_id
                else:
                    raw = new_id

        seq = [item.strip() for item in raw.split(",") if item.strip()]

        if not seq:
            if action != "reset":
                error = "Deine Sequenz ist noch leer. Wähle Elemente aus der Liste aus."
        else:
            unknown = [eid for eid in seq if eid not in elements]
            if unknown:
                error = f"Unbekannte Elemente: {', '.join(unknown)}"
            else:
                elem_list = [elements[eid] for eid in seq]
                errors = []

                for i in range(len(elem_list) - 1):
                    first = elem_list[i]
                    second = elem_list[i + 1]
                    if not second.can_follow(first):
                        errors.append(
                            {
                                "from_name": first.name,
                                "to_name": second.name,
                                "explanation": explain_compatibility_error(first, second),
                                "post_state": state_str(first.post),
                                "pre_state": state_str(second.pre),
                            }
                        )

                if errors:
                    result = {
                        "valid": False,
                        "errors": errors,
                    }
                else:
                    total_counts = sum(elem.counts for elem in elem_list)
                    result = {
                        "valid": True,
                        "sequence_names": [elem.name for elem in elem_list],
                        "total_counts": total_counts,
                        "phrase_count": total_counts / 8,
                        "start_state": state_str(elem_list[0].pre),
                        "end_state": state_str(elem_list[-1].post),
                    }

    return render_template(
        "builder.html",
        raw=raw,
        result=result,
        error=error,
        all_elements=sorted(elements.values(), key=lambda e: (e.level, e.name)),
    )


if __name__ == "__main__":
    app.run(debug=True)