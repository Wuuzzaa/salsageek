#!/usr/bin/env python3
"""
Web-App für die Salsa-Lernhilfe auf Basis von Flask.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

import yaml
from flask import Flask, abort, redirect, render_template, request, url_for, session

from src.salsa_notation import (
    Element,
    Figure,
    get_executable_figures,
    load_elements,
    load_figures,
    recommend_elements_to_learn,
)
from src.services.profile_service import ProfileService
from src.services.builder_service import BuilderService

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__)
app.secret_key = "salsa-geek-secret-key" # In Produktion ändern

elements: Dict[str, Element] = load_elements(DATA_DIR / "elements.yaml")
figures: Dict[str, Figure] = load_figures(DATA_DIR / "figures.yaml", elements)

profile_service = ProfileService()
builder_service = BuilderService(elements)

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


def get_active_profile() -> str:
    return session.get("profile_name", "default")

def load_profile() -> Set[str]:
    return profile_service.load_profile(get_active_profile())

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
        "active_profile": get_active_profile(),
        "available_profiles": profile_service.list_profiles(),
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
    active_profile = get_active_profile()
    if request.method == "POST":
        selected = set(request.form.getlist("known_ids"))
        selected = {eid for eid in selected if eid in elements}
        profile_service.save_profile(active_profile, selected)
        return redirect(url_for("repertoire", saved="1"))

    known_ids = profile_service.load_profile(active_profile)

    return render_template(
        "repertoire.html",
        grouped=group_elements_by_level(),
        known_ids=known_ids,
        current_level=current_level_for(known_ids),
        saved=request.args.get("saved") == "1",
        active_profile=active_profile
    )


@app.route("/profile/switch", methods=["POST"])
def switch_profile():
    name = request.form.get("profile_name", "default").strip()
    if not name:
        name = "default"
    
    slug = profile_service.slugify(name)
    session["profile_name"] = slug
    
    # Sicherstellen, dass das Profil existiert (ggf. leer anlegen)
    if slug not in profile_service.list_profiles():
        profile_service.save_profile(slug, set())
        
    return redirect(request.referrer or url_for("index"))


@app.route("/profile/delete/<name>", methods=["POST"])
def delete_profile(name: str):
    if name != "default":
        profile_service.delete_profile(name)
        if session.get("profile_name") == name:
            session["profile_name"] = "default"
    return redirect(url_for("repertoire"))


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
    raw = request.args.get("sequence", "").strip() or request.form.get("sequence", "").strip()
    
    sequence = builder_service.sequence_from_raw(raw)
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "reset":
            sequence = []
        elif action == "add":
            new_id = request.form.get("element_id")
            if new_id:
                sequence = builder_service.add_element(sequence, new_id)
        elif action == "remove":
            index = int(request.form.get("index", -1))
            sequence = builder_service.remove_element(sequence, index)
        elif action == "move":
            index = int(request.form.get("index", -1))
            direction = int(request.form.get("direction", 0))
            sequence = builder_service.move_element(sequence, index, direction)
        
        raw = builder_service.raw_from_sequence(sequence)
        
        # Falls wir nur modifizieren, Redirect um POST-Wiederholung zu vermeiden (optional, aber sauberer)
        if action in ["reset", "add", "remove", "move"]:
             return redirect(url_for("builder", sequence=raw))

    # Validierung durchführen
    validation = builder_service.validate_sequence(sequence)
    if not validation.get("valid"):
        if validation.get("error"):
            error = validation.get("error")
        else:
            result = validation # Enthält "errors" Liste
    else:
        if not validation.get("empty"):
            result = validation

    recommendations = builder_service.get_recommendations(sequence)

    return render_template(
        "builder.html",
        raw=raw,
        sequence=sequence,
        result=result,
        error=error,
        recommendations=recommendations,
        all_elements=sorted(elements.values(), key=lambda e: (e.level, e.name)),
    )


if __name__ == "__main__":
    app.run(debug=True)