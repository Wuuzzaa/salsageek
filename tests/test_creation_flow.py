import pytest
import yaml
from app import app, salsa_service, element_editor_service, builder_service
from pathlib import Path

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_create_new_element_flow(client, tmp_path, monkeypatch):
    """Test creating a brand new element and verify it's saved in the correct place."""
    elem_dir = tmp_path / "elements"
    elem_dir.mkdir()
    monkeypatch.setattr(element_editor_service, "dir", elem_dir)
    
    # Mock schema for validation
    test_schema = {
        "hand_holds": [{"id": "closed"}],
        "positions": [{"id": "closed"}],
        "slots": [{"id": "center"}],
        "connections": [{"id": "neutral"}],
        "weights": [{"id": "L"}, {"id": "R"}],
        "directions": [{"id": "pause"}],
        "turn_types": []
    }
    monkeypatch.setattr(salsa_service, "schema", test_schema)
    monkeypatch.setattr(element_editor_service, "schema", test_schema)

    form_data = {
        "action": "add_element",
        "name": "Test New Element",
        "level": "1",
        "counts": "8",
        "pre_hand": ["closed"],
        "pre_pos": ["closed"],
        "pre_slot": ["center"],
        "pre_conn": ["neutral"],
        "pre_leader_weight": ["R"],
        "pre_follower_weight": ["L"],
        "post_hand": ["closed"],
        "post_pos": ["closed"],
        "post_slot": ["center"],
        "post_conn": ["neutral"],
        "post_leader_weight": ["R"],
        "post_follower_weight": ["L"],
    }
    
    try:
        response = client.post("/element-editor", data=form_data, follow_redirects=True)
        assert response.status_code == 200
        
        # Verify file exists in the new structure
        yaml_files = list(elem_dir.glob("*.yaml"))
        assert len(yaml_files) == 1
        
        with open(yaml_files[0], "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            assert data["elements"][0]["name"] == "Test New Element"
            # Check that it doesn't have "custom" in the ID or path
            assert "custom" not in yaml_files[0].name
    finally:
        # Restore global state properly
        from app import DATA_DIR
        element_editor_service.dir = DATA_DIR / "elements"
        salsa_service.data_dir = DATA_DIR
        salsa_service.reload_elements()

def test_create_new_figure_flow(client, tmp_path, monkeypatch):
    """Test creating a new figure and verify it's saved in the correct place."""
    fig_dir = tmp_path / "figures"
    fig_dir.mkdir()
    
    # Also create schema.yaml because SalsaService._load_schema needs it
    with open(tmp_path / "schema.yaml", "w", encoding="utf-8") as f:
        yaml.dump({}, f)

    monkeypatch.setattr(salsa_service, "data_dir", tmp_path)
    monkeypatch.setattr(builder_service, "data_dir", tmp_path)
    
    # Ensure elements are available for the builder
    from src.salsa_notation import Element, SalsaState
    empty_state = SalsaState(set(), set(), set(), set(), set(), set())
    test_elem = Element(
        id="test_elem", name="Test Elem", level=1, counts=8,
        description="", tags=[], pre=empty_state, post=empty_state,
        leader_actions=[], follower_actions=[], signals=[]
    )
    monkeypatch.setattr(salsa_service, "elements", {"test_elem": test_elem})
    monkeypatch.setattr(builder_service, "elements", salsa_service.elements)

    form_data = {
        "action": "save",
        "figure_name": "Test New Figure",
        "figure_description": "A test figure",
        "sequence": "test_elem"
    }
    
    try:
        # We need to simulate the builder state. The builder expects 'sequence' in form or args.
        # Note: Use follow_redirects=True to see the detail page. 
        # Detail page will call salsa_service.get_all_figures() which loads from data_dir.
        response = client.post("/builder", data=form_data, follow_redirects=True)
        assert response.status_code == 200
        
        # Verify file exists in data/figures/
        yaml_files = list(fig_dir.glob("*.yaml"))
        assert len(yaml_files) == 1
        
        with open(yaml_files[0], "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            assert data["figures"][0]["name"] == "Test New Figure"
            assert data["figures"][0]["sequence"] == ["test_elem"]
    finally:
        # Restore global state properly
        from app import DATA_DIR
        salsa_service.data_dir = DATA_DIR
        builder_service.data_dir = DATA_DIR
        salsa_service.reload_elements()
