import os
from pathlib import Path
import yaml
import pytest
from Library.Parameter import ParameterAPI, Parameter

@pytest.fixture
def param_api(tmp_path):
    api = ParameterAPI(tmp_path)
    return api

def test_parameter_api_creation(param_api, tmp_path):
    assert param_api.path == tmp_path
    assert param_api.path.exists()

def test_set_and_get_dict(param_api, tmp_path):
    data = {"Strategy": {"Risk": 2.0}}
    param_api.TestConfig = data
    
    file_path = tmp_path / "TestConfig.yml"
    assert file_path.exists()
    
    # Get it back
    config = param_api.TestConfig
    assert isinstance(config, Parameter)
    assert config.Strategy.Risk == 2.0

def test_cache_hits_and_misses(param_api, tmp_path):
    data = {"A": 1}
    param_api.CacheTest = data
    
    # First access loads it into cache
    obj1 = param_api.CacheTest
    
    # Second access should return the exact same object reference
    obj2 = param_api.CacheTest
    assert obj1 is obj2
    
    # Write to file externally
    file_path = tmp_path / "CacheTest.yml"
    with file_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"A": 2}, f)
        
    # The file modification time needs to be strictly greater
    os.utime(file_path, (file_path.stat().st_atime, file_path.stat().st_mtime + 1.0))
    
    # Next access should auto-detect the change and reload
    obj3 = param_api.CacheTest
    assert obj3 is not obj1
    assert obj3.A == 2

def test_nested_eager_wrapping(param_api, tmp_path):
    data = {"Level1": {"Level2": {"Value": 42}}}
    param_api.NestedTest = data
    
    config = param_api.NestedTest
    
    # The nested dicts should be eagerly wrapped
    level1_a = config.Level1
    level1_b = config.Level1
    assert level1_a is level1_b
    assert isinstance(level1_a, Parameter)
    
    level2_a = config.Level1.Level2
    level2_b = config.Level1.Level2
    assert level2_a is level2_b
    assert level2_a.Value == 42

def test_nested_assignment_bubbles_up(param_api, tmp_path):
    data = {"Strategy": {"Risk": 2.0}}
    param_api.UpdateTest = data
    
    config = param_api.UpdateTest
    config.Strategy.Risk = 5.0
    
    # Verify the object memory is updated
    assert config.Strategy.Risk == 5.0
    
    # Verify the actual file on disk is updated
    file_path = tmp_path / "UpdateTest.yml"
    with file_path.open("r", encoding="utf-8") as f:
        disk_data = yaml.safe_load(f)
        assert disk_data["Strategy"]["Risk"] == 5.0

def test_directory_navigation(param_api, tmp_path):
    # Setup nested directories
    sub_dir = tmp_path / "FolderA" / "FolderB"
    sub_dir.mkdir(parents=True)
    
    file_path = sub_dir / "Config.yml"
    with file_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"Val": 1}, f)
        
    # Navigate
    config = param_api.FolderA.FolderB.Config
    assert config.Val == 1

def test_missing_key_returns_none(param_api):
    param_api.Present = {"A": 1}

    assert param_api.Present.A == 1
    assert param_api.Present.Missing is None
    assert param_api.Present["Missing"] is None
    assert param_api.Missing is None
    assert param_api["Missing"] is None

def test_parameter_clone(param_api):
    data = {"A": {"B": 1}}
    param_api.CloneTest = data
    
    config = param_api.CloneTest
    cloned = config.clone()
    
    assert cloned is not config
    assert cloned.data == config.data
    assert cloned.A.B == 1
    
    # Modifying the clone should not modify the original data memory
    cloned.A.B = 2
    assert cloned.A.B == 2
    assert config.A.B == 1