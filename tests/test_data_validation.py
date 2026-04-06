import pytest
from pathlib import Path
from src.salsa_notation import load_elements, load_figures

def get_data_dir(app):
    return Path(app.root_path) / 'data'

def load_all_elements_for_test(data_dir: Path):
    elements = load_elements(data_dir / 'elements.yaml')
    
    # Legacy custom elements
    custom_legacy = data_dir / 'custom_elements.yaml'
    if custom_legacy.exists():
        elements.update(load_elements(custom_legacy))
        
    # New individual custom elements
    custom_dir = data_dir / 'custom_elements'
    if custom_dir.exists() and custom_dir.is_dir():
        for yaml_file in custom_dir.glob("*.yaml"):
            elements.update(load_elements(yaml_file))
            
    return elements

def test_elements_data_valid(app):
    data_dir = get_data_dir(app)
    elements = load_all_elements_for_test(data_dir)
    
    assert len(elements) > 0, 'Keine Elemente gefunden'
    for eid, elem in elements.items():
        assert elem.id == eid, f"Element ID Mismatch: Key '{eid}' != Element ID '{elem.id}'"
        assert elem.name, f"Element '{eid}' hat keinen Namen"
        assert elem.counts > 0, f"Element '{eid}' hat ungültige Counts"

def test_figures_data_valid(app):
    data_dir = get_data_dir(app)
    elements = load_all_elements_for_test(data_dir)
    
    figures = load_figures(data_dir / 'figures.yaml', elements)
    
    errors = []
    for fid, fig in figures.items():
        if not fig.valid:
            errors.append(f"Figur '{fid}': " + " | ".join(fig.validation_errors))
    
    assert not errors, "\n".join(errors)

def test_all_elements_pages(client, app):
    data_dir = get_data_dir(app)
    elements = load_all_elements_for_test(data_dir)
    for eid in elements.keys():
        response = client.get(f'/element/{eid}')
        assert response.status_code == 200, f"Detailseite für Element '{eid}' konnte nicht geladen werden"

def test_all_figures_pages(client, app):
    data_dir = get_data_dir(app)
    elements = load_all_elements_for_test(data_dir)
    figures = load_figures(data_dir / 'figures.yaml', elements)
    for fid in figures.keys():
        response = client.get(f'/figuren/{fid}')
        assert response.status_code in [200, 302], f"Detailseite für Figur '{fid}' konnte nicht geladen werden"

def test_visualize_sequences(client, app):
    data_dir = get_data_dir(app)
    elements = load_all_elements_for_test(data_dir)
    figures = load_figures(data_dir / 'figures.yaml', elements)
    
    # Test visualization for each figure's sequence
    for fid, fig in figures.items():
        if fig.valid:
            seq_str = ",".join(fig.sequence)
            response = client.get(f'/visualize?sequence={seq_str}&title={fig.name}')
            assert response.status_code == 200, f"Visualisierung für Figur '{fid}' fehlgeschlagen"
            assert b"mermaid" in response.data, f"Mermaid-Diagramm fehlt in Visualisierung für '{fid}'"
