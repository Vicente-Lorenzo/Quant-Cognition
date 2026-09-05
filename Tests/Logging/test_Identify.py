import types
from pathlib import Path

import pytest

from Library.Logging import LoggingAPI, VerboseLevel
from Library.Utility.Runtime import find_caller_class, find_caller_module, find_caller_package, find_frame_class, find_frame_module, find_frame_package

class OwnerAPI:

    def __init__(self):
        self.log = LoggingAPI()

    def rebuild(self):
        return LoggingAPI()

class FactoryAPI:

    @classmethod
    def build(cls):
        return LoggingAPI()

    @staticmethod
    def detached():
        return LoggingAPI()

def _function_():
    return LoggingAPI()

def _nested_():
    def inner(): return LoggingAPI()
    return inner()

_MODULE_ = None

def test_class_comes_from_the_owning_instance():
    assert OwnerAPI().log.InstanceTags[0] == "OwnerAPI"

def test_class_is_derived_in_any_method_not_just_init():
    assert OwnerAPI().rebuild().InstanceTags[0] == "OwnerAPI"

def test_class_comes_from_the_owning_class_in_a_classmethod():
    assert FactoryAPI.build().InstanceTags[0] == "FactoryAPI"

def test_class_comes_from_the_qualname_in_a_staticmethod():
    assert FactoryAPI.detached().InstanceTags[0] == "FactoryAPI"

def test_class_falls_back_to_the_module_in_a_function():
    assert _function_().InstanceTags[0] == "test_Identify"

def test_class_falls_back_to_the_module_in_a_nested_function():
    assert _nested_().InstanceTags[0] == "test_Identify"

def test_class_falls_back_to_the_module_at_module_level():
    assert LoggingAPI().InstanceTags[0] == "test_Identify"

def test_subclass_comes_from_the_subsystem():
    assert OwnerAPI().log.InstanceTags[1] == "Tests"

def test_identity_matches_writing_it_by_hand():
    class HandWrittenAPI:

        def __init__(self):
            self.automatic = LoggingAPI()
            self.manual = LoggingAPI(type(self).__name__)
    subject = HandWrittenAPI()
    assert subject.automatic.InstanceTags[0] == subject.manual.InstanceTags[0] == "HandWrittenAPI"

def test_given_tags_follow_the_derived_owner():
    assert LoggingAPI("Explicit").InstanceTags == ("test_Identify", "Explicit")

def test_given_tags_replace_the_derived_subsystem():
    assert LoggingAPI().InstanceTags[1] == "Tests"
    assert LoggingAPI("Explicit").InstanceTags[1] == "Explicit"

def test_identify_false_leaves_both_absent():
    assert LoggingAPI(identify=False).InstanceTags == ()

def test_identify_false_keeps_explicit_tags():
    assert LoggingAPI("A", "B", identify=False).InstanceTags == ("A", "B")

def test_identify_false_keeps_positional_tags():
    assert LoggingAPI("Extra", identify=False).InstanceTags == ("Extra",)

def test_derivation_never_sees_the_logging_package():
    for tag in LoggingAPI().InstanceTags:
        assert tag not in ("Logging", "LoggingAPI", "LoggerAPI")

def test_name_is_the_derived_class():
    assert OwnerAPI().log.name == "OwnerAPI"

def test_logger_records_carry_the_derived_identity(recorder):
    recorder.set_level(VerboseLevel.Debug)
    OwnerAPI().log.info(lambda: "message")
    assert " - Info - OwnerAPI - Tests - message" in recorder.written[0]

@pytest.mark.parametrize("module,expected", [
    ("Library.System.Realtime", "System"),
    ("Library.Scheduler.Executor", "Scheduler"),
    ("Library.App.V2.Page", "App"),
    ("Setup.Universe", "Setup"),
    ("Tests.Logging.test_Identify", "Tests"),
    ("__main__", None),
    ("", None)])
def test_frame_package_resolution(module, expected):
    assert find_frame_package(types.SimpleNamespace(f_globals={"__name__": module})) == expected

@pytest.mark.parametrize("module,expected", [
    ("Library.System.Realtime", "Realtime"),
    ("Setup.Universe", "Universe"),
    ("Solo", "Solo")])
def test_frame_module_resolution(module, expected):
    assert find_frame_module(types.SimpleNamespace(f_globals={"__name__": module})) == expected

def test_frame_module_falls_back_to_the_file_stem():
    frame = types.SimpleNamespace(f_globals={"__name__": "__main__", "__file__": "/some/dir/Runner.py"})
    assert find_frame_module(frame) == "Runner"

def test_frame_helpers_tolerate_a_missing_frame():
    assert find_frame_class(None) is None
    assert find_frame_module(None) is None
    assert find_frame_package(None) is None

def test_frame_package_falls_back_to_the_parent_folder_when_main():
    frame = types.SimpleNamespace(f_globals={"__name__": "__main__", "__file__": str(Path("Setup") / "Retention.py")})
    assert find_frame_package(frame) == "Setup"

def test_frame_package_fallback_covers_direct_script_execution():
    frame = types.SimpleNamespace(f_globals={"__name__": "__main__", "__file__": str(Path("Library") / "System" / "Realtime.py")})
    assert find_frame_package(frame) == "System"

def test_frame_package_without_a_file_is_none():
    assert find_frame_package(types.SimpleNamespace(f_globals={"__name__": "__main__"})) is None

def test_frame_package_honors_a_custom_root():
    frame = types.SimpleNamespace(f_globals={"__name__": "Vendor.Module.Thing"})
    assert find_frame_package(frame, package="Vendor") == "Module"

def test_caller_helpers_describe_their_direct_caller():
    class ProbeAPI:

        def look(self): return find_caller_class(), find_caller_module(), find_caller_package()
    klass, module, package = ProbeAPI().look()
    assert klass == "ProbeAPI"
    assert module == "test_Identify"
    assert package == "Tests"

def test_caller_helpers_respect_depth():
    def outer(): return inner()
    def inner(): return find_caller_module(depth=1)
    assert outer() == "test_Identify"

def test_caller_skip_walks_past_a_package():
    assert find_caller_package(skip="Tests.Logging") != "Tests"