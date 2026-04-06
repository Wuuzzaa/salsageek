import pytest
import yaml
from app import app, element_editor_service, salsa_service

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_edit_overwrites_existing_standard_element(client, tmp_path, monkeypatch):
    """Test that editing a standard element saves it to custom_elements/ with same ID."""
    custom_dir = tmp_path / "custom_elements_edit"
    monkeypatch.setattr(element_editor_service, "dir", custom_dir)
    
    # Mock schema
    salsa_service.schema = {
        "hand_holds": [{"id": "closed"}],
        "positions": [{"id": "closed"}],
        "slots": [{"id": "center"}],
        "connections": [{"id": "neutral"}],
        "weights": [{"id": "L"}, {"id": "R"}],
        "directions": [{"id": "pause"}],
        "turn_types": []
    }
    element_editor_service.schema = salsa_service.schema
    
    # We use 'basic_closed' which is a standard element
    form_data = {
        "action": "add_element",
        "name": "Modified Basic Closed",
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
    
    # Post to the edit route for 'basic_closed'
    response = client.post("/element-editor/basic_closed", data=form_data, follow_redirects=True)
    assert response.status_code == 200
    
    elem_file = custom_dir / "basic_closed.yaml"
    assert elem_file.exists()
    with open(elem_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert len(data["elements"]) == 1
        assert data["elements"][0]["id"] == "basic_closed"
        assert data["elements"][0]["name"] == "Modified Basic Closed"

def test_update_custom_element_no_duplicates(client, tmp_path, monkeypatch):
    """Test that updating an existing custom element doesn't create a duplicate."""
    custom_dir = tmp_path / "custom_elements_dup"
    monkeypatch.setattr(element_editor_service, "dir", custom_dir)
    
    # Mock schema
    salsa_service.schema = {
        "hand_holds": [{"id": "open"}],
        "positions": [{"id": "open"}],
        "slots": [{"id": "center"}],
        "connections": [{"id": "neutral"}],
        "weights": [{"id": "L"}, {"id": "R"}],
        "directions": [{"id": "pause"}],
        "turn_types": []
    }
    element_editor_service.schema = salsa_service.schema
    
    # 1. Create a custom element
    form_data = {
        "action": "add_element",
        "name": "My Custom",
        "level": "1",
        "counts": "8",
        "pre_hand": ["open"], "pre_pos": ["open"], "pre_slot": ["center"], "pre_conn": ["neutral"], "pre_leader_weight": ["R"], "pre_follower_weight": ["L"],
        "post_hand": ["open"], "post_pos": ["open"], "post_slot": ["center"], "post_conn": ["neutral"], "post_leader_weight": ["L"], "post_follower_weight": ["R"],
    }
    
    response = client.post("/element-editor", data=form_data, follow_redirects=True)
    assert response.status_code == 200
    
    # Find the created file
    yaml_files = list(custom_dir.glob("*.yaml"))
    assert len(yaml_files) == 1
    yaml_file = yaml_files[0]
    
    with open(yaml_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        elem = data["elements"][0]
        elem_id = elem["id"]
        assert len(data["elements"]) == 1

    # MANUALLY add the element to salsa_service.elements so the route find it
    from src.salsa_notation import Element, SalsaState
    empty_state = SalsaState(set(), set(), set(), set(), set(), set())
    salsa_service.elements[elem_id] = Element(
        id=elem_id, name=elem["name"], level=elem["level"], counts=elem["counts"],
        description="", tags=[], pre=empty_state, post=empty_state,
        leader_actions=[], follower_actions=[], signals=[]
    )
    
    # 2. Update it
    form_data["name"] = "My Custom Updated"
    response = client.post(f"/element-editor/{elem_id}", data=form_data, follow_redirects=True)
    assert response.status_code == 200
    
    # Still only one file (it should overwrite the same file because it has the same ID)
    yaml_files = list(custom_dir.glob("*.yaml"))
    assert len(yaml_files) == 1
    
    with open(yaml_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        assert len(data["elements"]) == 1
        assert data["elements"][0]["id"] == elem_id
        assert data["elements"][0]["name"] == "My Custom Updated"
