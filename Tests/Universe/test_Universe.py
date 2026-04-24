from Library.Universe.Universe import UniverseAPI

def test_universe_constants():
    assert UniverseAPI.Database == "Tests"
    assert UniverseAPI.Schema == "Universe"

def test_universe_base_structure():
    structure = UniverseAPI(db=None).Structure
    assert "CreatedAt" in structure
    assert "CreatedBy" in structure
    assert "UpdatedAt" in structure
    assert "UpdatedBy" in structure