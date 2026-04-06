#!/usr/bin/env python3
"""
Flask-based web application for Salsa learning aid.
"""
from __future__ import annotations

from pathlib import Path
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

from flask import Flask, abort, redirect, render_template, request, url_for, session, send_file

from src.salsa_notation import (
    get_executable_figures,
)
from src.services.builder_service import BuilderService
from src.services.element_editor_service import ElementEditorService
from src.services.github_service import GithubService
from src.services.salsa_service import SalsaService
from src.utils import youtube_embed_url

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__)
app.secret_key = "salsa-geek-secret-key" # Change in production

salsa_service = SalsaService(DATA_DIR)
profile_service = salsa_service.profile_service
builder_service = BuilderService(salsa_service.elements)
element_editor_service = ElementEditorService(DATA_DIR / "custom_elements", schema=salsa_service.schema)
github_service = GithubService()

def get_active_profile() -> str:
    return session.get("profile_name", "default")


@app.context_processor
def inject_globals():
    def level_info(level: int | str):
        try:
            level_int = int(level)
        except (ValueError, TypeError):
            level_int = 1
        
        return {
            "label": salsa_service.level_label.get(level_int, f"Level {level_int}"),
            "badge": salsa_service.level_badge.get(level_int, "secondary")
        }

    return {
        "level_info": level_info,
        "level_label": salsa_service.level_label,
        "level_badge": salsa_service.level_badge,
        "elements": salsa_service.elements,
        "active_profile": get_active_profile(),
        "available_profiles": profile_service.list_profiles(),
        "schema": salsa_service.schema,
        "github_configured": github_service.is_configured(),
    }

@app.template_filter("youtube_embed")
def youtube_embed_filter(url: str) -> str:
    """Converts YouTube URLs (watch, short, etc.) to embed format."""
    return youtube_embed_url(url)


@app.route("/")
def index():
    profile_name = get_active_profile()
    known_ids = salsa_service.get_known_elements(profile_name)
    all_figs = salsa_service.get_all_figures_with_custom(profile_name)
    executable = get_executable_figures(known_ids, all_figs)
    almost_executable = salsa_service.get_almost_executable_figures(known_ids, all_figs)
    invalid = [fig for fig in all_figs.values() if not fig.valid]
    current_level = salsa_service.get_current_level(known_ids)
    
    # Next recommendation for summary
    recs = salsa_service.get_recommendations(known_ids, all_figs, current_level)
    top_rec = recs[0] if recs else None

    return render_template(
        "index.html",
        known_ids=known_ids,
        elements=salsa_service.elements,
        figures=all_figs,
        executable=executable,
        almost_executable=almost_executable,
        invalid=invalid,
        current_level=current_level,
        top_rec=top_rec
    )


@app.route("/elemente")
def elemente():
    profile_name = get_active_profile()
    known_ids = salsa_service.get_known_elements(profile_name)
    grouped = salsa_service.group_elements_by_level()

    # Convert elements to dict for easier template access if needed, 
    # but SalsaService.group_elements_by_level returns Element objects.
    # The template uses elem.description, elem.tags etc.
    # To be safe, we can convert the grouped items to dicts
    grouped_dicts = {}
    for level, items in grouped.items():
        grouped_dicts[level] = [element_editor_service.to_dict(item) for item in items]

    return render_template(
        "elemente.html",
        grouped=grouped_dicts,
        known_ids=known_ids,
    )


@app.route("/element/<element_id>")
def element_detail(element_id: str):
    element = salsa_service.get_element(element_id)
    if element is None:
        abort(404)

    profile_name = get_active_profile()
    known_ids = salsa_service.get_known_elements(profile_name)
    all_figs = salsa_service.get_all_figures_with_custom(profile_name)
    used_in_figures = salsa_service.find_figures_using_element(element_id, all_figs)

    # Convert element and states to dict for template consistency
    element_dict = element_editor_service.to_dict(element)

    return render_template(
        "element_detail.html",
        element=element_dict,
        is_known=element_id in known_ids,
        used_in_figures=used_in_figures,
        pre_state=element_dict.get("pre"),
        post_state=element_dict.get("post"),
    )


@app.route("/repertoire", methods=["GET", "POST"])
def repertoire():
    active_profile = get_active_profile()
    if request.method == "POST":
        selected = set(request.form.getlist("known_ids"))
        selected = {eid for eid in selected if eid in salsa_service.elements}
        profile_service.save_profile(active_profile, selected)
        return redirect(url_for("repertoire", saved="1"))

    known_ids = salsa_service.get_known_elements(active_profile)
    grouped = salsa_service.group_elements_by_level()
    
    # Convert elements to dict for easier template access
    grouped_dicts = {}
    for level, items in grouped.items():
        grouped_dicts[level] = [element_editor_service.to_dict(item) for item in items]

    return render_template(
        "repertoire.html",
        grouped=grouped_dicts,
        known_ids=known_ids,
        current_level=salsa_service.get_current_level(known_ids),
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
    
    # Ensure profile exists (create empty if necessary)
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
    profile_name = get_active_profile()
    known_ids = salsa_service.get_known_elements(profile_name)
    all_figs = salsa_service.get_all_figures_with_custom(profile_name)
    executable = get_executable_figures(known_ids, all_figs)
    almost_executable = salsa_service.get_almost_executable_figures(known_ids, all_figs)

    return render_template(
        "figuren.html",
        known_ids=known_ids,
        executable=executable,
        almost_executable=almost_executable,
    )


@app.route("/figuren/<figure_id>")
def figure_detail(figure_id: str):
    pr_url = request.args.get("pr_url")
    profile_name = get_active_profile()
    all_figs = salsa_service.get_all_figures_with_custom(profile_name)
    if figure_id not in all_figs:
        abort(404)

    fig = all_figs[figure_id]
    known_ids = salsa_service.get_known_elements(profile_name)

    # Check if executable
    is_executable = fig.is_executable_with(known_ids)
    
    return render_template(
        "figure_detail.html",
        figure=fig,
        is_executable=is_executable,
        known_ids=known_ids,
        pr_url=pr_url
    )


@app.route("/empfehlungen")
def empfehlungen():
    profile_name = get_active_profile()
    known_ids = salsa_service.get_known_elements(profile_name)
    all_figs = salsa_service.get_all_figures_with_custom(profile_name)
    current_level = salsa_service.get_current_level(known_ids)

    recs = salsa_service.get_recommendations(
        known_ids=known_ids,
        all_figures=all_figs,
        current_level=current_level
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
    
    # Preserve metadata during the build process
    figure_name = request.args.get("figure_name", "").strip() or request.form.get("figure_name", "").strip()
    figure_description = request.args.get("figure_description", "").strip() or request.form.get("figure_description", "").strip()
    
    sequence = builder_service.sequence_from_raw(raw)
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "reset":
            sequence = []
            figure_name = ""
            figure_description = ""
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
        
        # Redirect after modification to avoid POST repetition
        if action in ["reset", "add", "remove", "move"]:
             return redirect(url_for("builder", sequence=raw, figure_name=figure_name, figure_description=figure_description))

    # Perform validation
    validation = builder_service.validate_sequence(sequence)
    custom_figure = None
    if not validation.get("valid"):
        if validation.get("error"):
            error = validation.get("error")
        else:
            result = validation # Contains "errors" list
    else:
        if not validation.get("empty"):
            result = validation
            custom_figure = builder_service.create_custom_figure(validation)

    # Save logic
    if request.method == "POST" and request.form.get("action") == "save" and custom_figure:
        name = request.form.get("figure_name", "Custom Figure").strip() or "Custom Figure"
        description = request.form.get("figure_description", "").strip()
        
        active_profile = get_active_profile()
        profile_data = profile_service.load_profile(active_profile)
        custom_figs = profile_data.get("custom_figures", [])
        
        # Generate new ID
        import time
        fig_id = f"custom_{int(time.time())}"
        
        new_fig_raw = {
            "id": fig_id,
            "name": name,
            "description": description,
            "level": custom_figure.level,
            "sequence": custom_figure.sequence,
            "total_counts": custom_figure.total_counts,
            "tags": ["Builder", "Custom"],
            "notes": ""
        }
        
        custom_figs.append(new_fig_raw)
        profile_service.save_profile(active_profile, set(profile_data.get("known_elements", [])), custom_figs)
        
        # Reload salsa service to include the new figure globally if needed
        salsa_service.reload_figures()
        
        # Automatischer Pull Request
        pr_url = None
        if github_service.is_configured():
            pr_url = github_service.create_pull_request_for_figure(fig_id, new_fig_raw)
            return redirect(url_for("figure_detail", figure_id=fig_id, pr_url=pr_url))
        
        return redirect(url_for("figure_detail", figure_id=fig_id, saved=True))

    recommendations = builder_service.get_recommendations(sequence)

    return render_template(
        "builder.html",
        raw=raw,
        sequence=sequence,
        result=result,
        error=error,
        recommendations=recommendations,
        all_elements=sorted(salsa_service.elements.values(), key=lambda e: (e.level, e.name)),
        figure=custom_figure,
        known_ids=salsa_service.get_known_elements(get_active_profile()),
        figure_name=figure_name,
        figure_description=figure_description
    )


@app.route("/element-editor", methods=["GET", "POST"])
@app.route("/element-editor/<element_id>", methods=["GET", "POST"])
def element_editor(element_id: str = None):
    # Last 10 created custom_elements for quick access & template selection
    all_elements_sorted = sorted(
        salsa_service.elements.values(),
        key=lambda e: (e.level, e.name)
    )
    
    recent_custom = sorted(
        [e for e in salsa_service.elements.values() if "Custom" in e.tags],
        key=lambda e: e.id,
        reverse=True
    )[:5]
    
    # Check if we should copy from an existing element
    copy_from_id = request.args.get("copy_from")
    
    element_to_edit = None
    if element_id:
        element_to_edit = salsa_service.get_element(element_id)
        if not element_to_edit:
            abort(404)
        # Convert to dict for consistent template access
        element_to_edit = element_editor_service.to_dict(element_to_edit)
    elif copy_from_id:
        source_element = salsa_service.get_element(copy_from_id)
        if source_element:
            element_to_edit = element_editor_service.to_dict(source_element)
            element_to_edit["id"] = None  # Remove ID so it saves as new
            element_to_edit["name"] = f"{element_to_edit['name']} (Copy)"

    # Ensure actions are pre-filled if element exists
    if element_to_edit:
        element_to_edit["leader_actions"] = element_editor_service.fill_missing_steps(
            element_to_edit.get("leader_actions", []), 
            element_to_edit.get("counts", 8)
        )
        element_to_edit["follower_actions"] = element_editor_service.fill_missing_steps(
            element_to_edit.get("follower_actions", []), 
            element_to_edit.get("counts", 8)
        )

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_element":
            name = request.form.get("name", "").strip()
            level = int(request.form.get("level", 3))
            counts = int(request.form.get("counts", 8))
            desc = request.form.get("description", "").strip()
            
            # New attributes from extended form
            pre = {
                "hand_hold": request.form.getlist("pre_hand"),
                "position": request.form.getlist("pre_pos"),
                "slot": request.form.getlist("pre_slot"),
                "connection": request.form.getlist("pre_conn"),
                "leader_weight": request.form.getlist("pre_leader_weight"),
                "follower_weight": request.form.getlist("pre_follower_weight")
            }
            post = {
                "hand_hold": request.form.getlist("post_hand"),
                "position": request.form.getlist("post_pos"),
                "slot": request.form.getlist("post_slot"),
                "connection": request.form.getlist("post_conn"),
                "leader_weight": request.form.getlist("post_leader_weight"),
                "follower_weight": request.form.getlist("post_follower_weight")
            }
            
            # Process tags
            raw_tags = request.form.get("tags", "")
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
            if "Custom" not in tags: tags.append("Custom")
            
            # Signals (simple implementation)
            signal_type = request.form.get("signal_type", "none")
            signal_desc = request.form.get("signal_description", "").strip()
            signals = [{"type": signal_type, "description": signal_desc}] if signal_type != "none" else []
            
            # Notes
            notes = request.form.get("notes", "").strip()

            # Videos
            video_urls = request.form.getlist("video_urls")
            video_titles = request.form.getlist("video_titles")
            video_types = request.form.getlist("video_types")
            videos = []
            for i in range(len(video_urls)):
                if video_urls[i].strip():
                    videos.append({
                        "url": video_urls[i].strip(),
                        "title": video_titles[i].strip() if i < len(video_titles) else "",
                        "type": video_types[i].strip() if i < len(video_types) else "Full"
                    })

            # Parse actions using the service
            leader_actions = element_editor_service.parse_actions_raw(request.form.get("leader_actions_raw", ""))
            follower_actions = element_editor_service.parse_actions_raw(request.form.get("follower_actions_raw", ""))
            
            if name:
                new_id, errors, element_data = element_editor_service.add_custom_element(
                    name=name, level=level, counts=counts, 
                    pre=pre, post=post, description=desc, 
                    tags=tags, signals=signals, videos=videos, notes=notes,
                    leader_actions=leader_actions,
                    follower_actions=follower_actions,
                    custom_id=element_id
                )
                
                if new_id:
                    # Global service neu laden
                    salsa_service.reload_elements()
                    builder_service.elements = salsa_service.elements
                    
                    # Automatischer Pull Request
                    pr_url = None
                    if github_service.is_configured():
                        pr_url = github_service.create_pull_request_for_element(new_id, element_data)
                    
                    return redirect(url_for("element_editor", last_added=new_id, pr_url=pr_url))
                else:
                    return render_template(
                        "element_editor.html",
                        recent_custom=recent_custom,
                        all_elements=all_elements_sorted,
                        copy_from_id=copy_from_id,
                        error=f"Validierungsfehler: {', '.join(errors)}",
                        element=element_to_edit
                    )
    
    return render_template(
        "element_editor.html",
        recent_custom=recent_custom,
        all_elements=all_elements_sorted,
        last_added_id=request.args.get("last_added"),
        pr_url=request.args.get("pr_url"),
        copy_from_id=copy_from_id,
        element=element_to_edit
    )

@app.route("/visualize")
def visualize():
    raw_sequence = request.args.get("sequence", "")
    sequence = builder_service.sequence_from_raw(raw_sequence)
    
    if not sequence:
        return redirect(url_for("builder"))
        
    validation = builder_service.validate_sequence(sequence)
    
    # Get active profile and known elements for context
    active_profile = get_active_profile()
    known_ids = salsa_service.get_known_elements(active_profile)
    
    # Optional: Get figure or name for context
    title = request.args.get("title", "Flow Visualization")
    back_url = request.args.get("back", url_for("builder", sequence=raw_sequence))
    
    return render_template(
        "visualize.html",
        sequence=sequence,
        raw=raw_sequence,
        result=validation,
        elements=salsa_service.elements,
        known_ids=known_ids,
        title=title,
        back_url=back_url
    )


@app.route("/export/elements")
def export_elements():
    """
    Exports all custom elements into a single YAML file.
    This makes it easy to download and check into Git.
    """
    custom_dir = DATA_DIR / "custom_elements"
    combined_data = {"elements": []}
    
    # 1. Load legacy custom_elements.yaml if it exists
    legacy_path = DATA_DIR / "custom_elements.yaml"
    if legacy_path.exists():
        with open(legacy_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data and "elements" in data:
                combined_data["elements"].extend(data["elements"])
    
    # 2. Load all individual YAML files
    if custom_dir.exists() and custom_dir.is_dir():
        for yaml_file in custom_dir.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and "elements" in data:
                    combined_data["elements"].extend(data["elements"])
    
    if not combined_data["elements"]:
        abort(404)
        
    # Create a temporary combined file
    import tempfile
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w", encoding="utf-8")
    yaml.dump(combined_data, temp_file, allow_unicode=True, sort_keys=False)
    temp_file.close()
    
    return send_file(temp_file.name, as_attachment=True, download_name="custom_elements.yaml")


@app.route("/export/profile/<name>")
def export_profile(name):
    # Security: check if profile exists and path is inside profiles dir
    path = (BASE_DIR / "profiles" / f"{name}.yaml").resolve()
    if path.exists() and str(path).startswith(str(BASE_DIR / "profiles")):
        return send_file(path, as_attachment=True)
    abort(404)


if __name__ == "__main__":
    app.run(debug=True)