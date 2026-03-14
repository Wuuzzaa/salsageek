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


def get_active_profile() -> str:
    return session.get("profile_name", "default")

def get_all_figures(profile_name: str = None) -> Dict[str, Figure]:
    """Kombiniert globale Figuren mit benutzerdefinierten Figuren aus dem Profil."""
    if profile_name is None:
        profile_name = get_active_profile()
    
    all_figs = figures.copy()
    profile_data = profile_service.load_profile(profile_name)
    custom_figs_raw = profile_data.get("custom_figures", [])
    
    for raw in custom_figs_raw:
        fig = Figure(
            id=raw["id"],
            name=raw["name"],
            description=raw.get("description", "").strip(),
            level=int(raw.get("level", 1)),
            sequence=raw.get("sequence", []),
            total_counts=int(raw.get("total_counts", 0)),
            tags=raw.get("tags", []),
            notes=raw.get("notes", "").strip(),
        )
        
        # Elemente auflösen
        elem_list = []
        for eid in fig.sequence:
            if eid in elements:
                elem_list.append(elements[eid])
        
        fig.elements = elem_list
        # Da sie im Builder validiert wurden, setzen wir sie als valide (oder re-validieren hier)
        if fig.total_counts == 0 and elem_list:
            fig.total_counts = sum(e.counts for e in elem_list)
        
        all_figs[fig.id] = fig
        
    return all_figs


def load_profile() -> Set[str]:
    profile_data = profile_service.load_profile(get_active_profile())
    return set(profile_data.get("known_elements", []))

def current_level_for(known_ids: Set[str]) -> int:
    if not known_ids:
        return 0
    levels = [elements[eid].level for eid in known_ids if eid in elements]
    return max(levels) if levels else 0


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
    all_figs = get_all_figures()
    executable = get_executable_figures(known_ids, all_figs)
    almost_executable = get_almost_executable_figures(known_ids, all_figs)
    invalid = [fig for fig in all_figs.values() if not fig.valid]
    current_level = current_level_for(known_ids)
    
    # Nächste Empfehlung für Zusammenfassung
    recs = recommend_elements_to_learn(known_ids, all_figs, elements, current_level, top_n=1)
    top_rec = recs[0] if recs else None

    return render_template(
        "index.html",
        known_ids=known_ids,
        elements=elements,
        figures=all_figs,
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


def group_elements_by_level() -> Dict[int, List[Element]]:
    grouped: Dict[int, List[Element]] = {}
    for elem in elements.values():
        grouped.setdefault(elem.level, []).append(elem)

    for level in grouped:
        grouped[level] = sorted(grouped[level], key=lambda e: e.id)

    return dict(sorted(grouped.items()))


def find_figures_using_element(element_id: str, figs: Dict[str, Figure] = None) -> List[Figure]:
    if figs is None:
        figs = get_all_figures()
    used_in = [
        fig for fig in figs.values()
        if fig.valid and element_id in fig.sequence
    ]
    return sorted(used_in, key=lambda fig: (fig.level, fig.name))


def get_almost_executable_figures(known_ids: Set[str], figs: Dict[str, Figure] = None) -> List[Figure]:
    """Figuren, bei denen genau ein Element fehlt."""
    if figs is None:
        figs = get_all_figures()
    result = [
        fig for fig in figs.values()
        if fig.valid and fig.is_almost_executable(known_ids)
    ]
    return sorted(result, key=lambda f: (f.level, f.name))


@app.route("/repertoire", methods=["GET", "POST"])
def repertoire():
    active_profile = get_active_profile()
    if request.method == "POST":
        selected = set(request.form.getlist("known_ids"))
        selected = {eid for eid in selected if eid in elements}
        profile_service.save_profile(active_profile, selected)
        return redirect(url_for("repertoire", saved="1"))

    known_ids_raw = profile_service.load_profile(active_profile)
    known_ids = set(known_ids_raw.get("known_elements", []))

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
    all_figs = get_all_figures()
    executable = get_executable_figures(known_ids, all_figs)
    almost_executable = get_almost_executable_figures(known_ids, all_figs)

    return render_template(
        "figuren.html",
        known_ids=known_ids,
        executable=executable,
        almost_executable=almost_executable,
    )


@app.route("/figuren/<figure_id>")
def figure_detail(figure_id: str):
    all_figs = get_all_figures()
    if figure_id not in all_figs:
        abort(404)

    fig = all_figs[figure_id]
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
    all_figs = get_all_figures()
    current_level = current_level_for(known_ids)

    recs = recommend_elements_to_learn(
        known_ids=known_ids,
        figures=all_figs,
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
    custom_figure = None
    if not validation.get("valid"):
        if validation.get("error"):
            error = validation.get("error")
        else:
            result = validation # Enthält "errors" Liste
    else:
        if not validation.get("empty"):
            result = validation
            custom_figure = builder_service.create_custom_figure(validation)

    # Speichern-Logik
    if request.method == "POST" and request.form.get("action") == "save" and custom_figure:
        name = request.form.get("figure_name", "Eigene Figur").strip() or "Eigene Figur"
        description = request.form.get("figure_description", "").strip()
        
        profile_data = profile_service.load_profile(get_active_profile())
        custom_figs = profile_data.get("custom_figures", [])
        
        # Neue ID generieren
        import time
        fig_id = f"custom_{int(time.time())}"
        
        new_fig_raw = {
            "id": fig_id,
            "name": name,
            "description": description,
            "level": custom_figure.level,
            "sequence": custom_figure.sequence,
            "total_counts": custom_figure.total_counts,
            "tags": ["Baukasten", "Custom"],
            "notes": ""
        }
        
        custom_figs.append(new_fig_raw)
        profile_service.save_profile(get_active_profile(), set(profile_data.get("known_elements", [])), custom_figs)
        
        return redirect(url_for("figure_detail", figure_id=fig_id))

    recommendations = builder_service.get_recommendations(sequence)

    return render_template(
        "builder.html",
        raw=raw,
        sequence=sequence,
        result=result,
        error=error,
        recommendations=recommendations,
        all_elements=sorted(elements.values(), key=lambda e: (e.level, e.name)),
        figure=custom_figure,
        known_ids=load_profile()
    )


if __name__ == "__main__":
    app.run(debug=True)