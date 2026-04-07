import pytest
import yaml
from pathlib import Path
from src.services.salsa_service import SalsaService

@pytest.fixture
def temp_data_dir(tmp_path):
    # Setup a minimal data directory
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Create empty folders
    (data_dir / "elements").mkdir(exist_ok=True)
    (data_dir / "figures").mkdir(exist_ok=True)
    
    return data_dir

def test_load_figures_from_data_dir(temp_data_dir):
    # 1. Create a figure file
    fig_dir = temp_data_dir / "figures"
    # fig_dir already created in fixture
    
    fig_data = {
        "figures": [
            {
                "id": "test_fig_1",
                "name": "Test Figure 1",
                "level": 2,
                "sequence": [],
                "total_counts": 8,
                "tags": ["Test"]
            }
        ]
    }
    
    with open(fig_dir / "test_fig_1.yaml", "w", encoding="utf-8") as f:
        yaml.dump(fig_data, f)
        
    # 2. Initialize SalsaService
    service = SalsaService(temp_data_dir)
    
    # 3. Verify it loaded the figure
    assert "test_fig_1" in service.figures
    assert service.figures["test_fig_1"].name == "Test Figure 1"
    assert service.figures["test_fig_1"].level == 2

def test_reload_figures(temp_data_dir):
    service = SalsaService(temp_data_dir)
    assert "new_fig" not in service.figures
    
    # Create new figure file
    fig_dir = temp_data_dir / "figures"
    fig_dir.mkdir(exist_ok=True)
    
    fig_data = {"figures": [{"id": "new_fig", "name": "New Figure", "level": 1, "sequence": []}]}
    with open(fig_dir / "new_fig.yaml", "w", encoding="utf-8") as f:
        yaml.dump(fig_data, f)
        
    # Reload
    service.reload_figures()
    assert "new_fig" in service.figures
    assert service.figures["new_fig"].name == "New Figure"
