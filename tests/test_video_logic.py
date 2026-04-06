import pytest
from app import app, youtube_embed_filter
from src.services.element_editor_service import ElementEditorService
from pathlib import Path
import os
import yaml

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_youtube_embed_filter():
    # Test regular watch link
    assert youtube_embed_filter("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "https://www.youtube.com/embed/dQw4w9WgXcQ"
    # Test short link
    assert youtube_embed_filter("https://youtu.be/dQw4w9WgXcQ") == "https://www.youtube.com/embed/dQw4w9WgXcQ"
    # Test link with additional params
    assert youtube_embed_filter("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s") == "https://www.youtube.com/embed/dQw4w9WgXcQ"
    # Test already embedded link
    assert youtube_embed_filter("https://www.youtube.com/embed/dQw4w9WgXcQ") == "https://www.youtube.com/embed/dQw4w9WgXcQ"
    # Test empty or None
    assert youtube_embed_filter("") == ""
    assert youtube_embed_filter(None) == ""
    # Test invalid link (should return as is if no ID found)
    assert youtube_embed_filter("https://example.com") == "https://example.com"

def test_element_editor_service_video_storage(tmp_path):
    # tmp_path as a directory for individual YAML files
    service = ElementEditorService(tmp_path)
    
    # Mock schema for validation (minimal)
    service.schema = {
        "hand_holds": [{"id": "open"}],
        "positions": [{"id": "open"}],
        "slots": [{"id": "center"}],
        "weights": [{"id": "L"}, {"id": "R"}],
        "directions": [],
        "turn_types": []
    }
    
    videos = [
        {"url": "https://youtu.be/test1", "title": "Test Video 1", "type": "Full"},
        {"url": "https://www.youtube.com/watch?v=test2", "title": "Test Video 2", "type": "Slow"}
    ]
    
    pre = {"hand_hold": ["open"], "position": ["open"], "slot": ["center"], "leader_weight": ["R"], "follower_weight": ["L"]}
    post = {"hand_hold": ["open"], "position": ["open"], "slot": ["center"], "leader_weight": ["L"], "follower_weight": ["R"]}
    
    elem_id, errors, data = service.add_custom_element(
        name="Video Test Element",
        level=1,
        counts=8,
        pre=pre,
        post=post,
        videos=videos
    )
    
    assert not errors
    assert elem_id.startswith("custom_video_test_element")
    
    # Verify content in the individual YAML file
    custom_file = tmp_path / f"{elem_id}.yaml"
    assert custom_file.exists()
    with open(custom_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        element = data["elements"][0]
        assert element["videos"] == videos
        assert element["videos"][0]["url"] == "https://youtu.be/test1"

def test_element_editor_post_with_videos(client, tmp_path, monkeypatch):
    # Setup a temporary directory for individual YAML files
    custom_dir = tmp_path
    
    # Point both the service AND the salsa_service to temporary locations
    from app import element_editor_service, salsa_service
    monkeypatch.setattr(element_editor_service, "dir", custom_dir)
    
    # We also need to ensure validation passes.
    # The app's service uses salsa_service.schema which might be empty in tests.
    salsa_service.schema = {
        "hand_holds": [{"id": "open"}],
        "positions": [{"id": "open"}],
        "slots": [{"id": "center"}],
        "connections": [{"id": "neutral"}],
        "weights": [{"id": "L"}, {"id": "R"}],
        "directions": [],
        "turn_types": []
    }
    element_editor_service.schema = salsa_service.schema

    form_data = {
        "action": "add_element",
        "name": "Web Video Element",
        "level": "2",
        "counts": "8",
        "description": "A test element with videos",
        "pre_hand": ["open"],
        "pre_pos": ["open"],
        "pre_slot": ["center"],
        "pre_conn": ["neutral"],
        "pre_leader_weight": ["R"],
        "pre_follower_weight": ["L"],
        "post_hand": ["open"],
        "post_pos": ["open"],
        "post_slot": ["center"],
        "post_conn": ["neutral"],
        "post_leader_weight": ["L"],
        "post_follower_weight": ["R"],
        "video_urls": ["https://youtu.be/web1", "https://youtu.be/web2"],
        "video_titles": ["Web 1", "Web 2"],
        "video_types": ["Full", "Leader"]
    }
    
    response = client.post("/element-editor", data=form_data, follow_redirects=True)
    
    # Debug print if failed
    if response.status_code != 200:
        print(f"Response: {response.status_code}")
        if b"Validierungsfehler" in response.data:
            print("Validation error detected in response!")
            idx = response.data.find(b"Validierungsfehler")
            print(f"Error context: {response.data[idx:idx+200].decode()}")

    assert response.status_code == 200
    
    # Check if file was created and contains videos
    created_files = list(custom_dir.glob("*.yaml"))
    assert len(created_files) > 0
    
    with open(created_files[0], "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        element = next(e for e in data["elements"] if e["name"] == "Web Video Element")
        assert len(element["videos"]) == 2
        assert element["videos"][0]["url"] == "https://youtu.be/web1"
        assert element["videos"][0]["title"] == "Web 1"
        assert element["videos"][1]["type"] == "Leader"
