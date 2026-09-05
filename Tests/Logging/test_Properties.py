from Library.Logging import LoggingAPI, LoggerAPI, ConsoleAPI, FileAPI, VerboseLevel

def test_logger_properties_mirror_attributes(recorder):
    assert recorder.Level is recorder._level_
    assert recorder.Default is recorder._default_
    assert recorder.Enabled is recorder._enabled_
    assert recorder.Locked is recorder._locked_
    assert recorder.Opened is recorder._opened_

def test_logger_opened_tracks_lifecycle(recorder):
    assert recorder.Opened is False
    recorder.open()
    assert recorder.Opened is True
    recorder.close()
    assert recorder.Opened is False

def test_console_properties_mirror_attributes():
    console = LoggingAPI.console
    assert console.Palette is console._palette_
    assert console.Color is console._color_
    assert console.Forced is console._forced_

def test_console_forced_tracks_set_color():
    console = LoggingAPI.console
    console.set_color(True)
    assert console.Forced is True
    console.set_color(None)
    assert console.Forced is None

def test_file_properties_mirror_attributes(tmp_path):
    file = LoggingAPI.file
    assert file.Directory == (file._directory_ if file._directory_ is not None else FileAPI._temporary_())
    assert file.Extension == file._extension_
    assert file.Distinct is file._distinct_
    assert file.Rotation == (file._size_, file._count_)
    assert file.Retention == file._days_
    assert file.Size == file._written_

def test_file_rotation_property_tracks_setter(tmp_path):
    LoggingAPI.file.set_rotation(size=4096, count=2)
    assert LoggingAPI.file.Rotation == (4096, 2)

def test_file_retention_property_tracks_setter(tmp_path):
    LoggingAPI.file.set_retention(days=7)
    assert LoggingAPI.file.Retention == 7

def test_file_negative_rotation_is_clamped(tmp_path):
    LoggingAPI.file.set_rotation(size=-1, count=-5)
    assert LoggingAPI.file.Rotation == (0, 0)

def test_file_negative_retention_is_clamped(tmp_path):
    LoggingAPI.file.set_retention(days=-3)
    assert LoggingAPI.file.Retention == 0

def test_file_size_tracks_writes(tmp_path):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=0)
    LoggingAPI("Sizer").info(lambda: "measured")
    assert LoggingAPI.file.Size > 0

def test_facade_shared_tags_property_mirrors_state():
    LoggingAPI.set_shared_tags("EURUSD", "H1")
    assert LoggingAPI("X").SharedTags == LoggingAPI._shared_tags_ == ("EURUSD", "H1")

def test_facade_instance_tags_property_mirrors_state():
    log = LoggingAPI("Engine", "Backtesting")
    assert log.InstanceTags == log._instance_tags_ == ("test_Properties", "Engine", "Backtesting")

def test_facade_depth_property_mirrors_state():
    log = LoggingAPI("Depth")
    assert log.Depth == 0
    with log:
        assert log.Depth == 1
        with LoggingAPI("Inner"):
            assert log.Depth == 2
    assert log.Depth == 0

def test_shared_tags_precede_instance_tags_in_output(recorder):
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI.set_shared_tags("SHARED")
    log = LoggingAPI("Own")
    log.info(lambda: "message")
    line = recorder.written[0]
    assert line.index("SHARED") < line.index("Info") < line.index("Own")

def test_shared_sinks_are_class_attributes():
    assert isinstance(LoggingAPI.console, ConsoleAPI)
    assert isinstance(LoggingAPI.file, FileAPI)
    assert LoggingAPI("A").console is LoggingAPI("B").console
    assert LoggingAPI("A").file is LoggingAPI("B").file

def test_shared_sinks_are_registered_once():
    assert LoggerAPI.Registry.count(LoggingAPI.console) == 1
    assert LoggerAPI.Registry.count(LoggingAPI.file) == 1

def test_bridge_logger_property():
    from Library.Logging import BridgeAPI
    log = LoggingAPI("Bridged")
    assert BridgeAPI(log).Logger is log

def test_sink_names_are_declared():
    assert LoggingAPI.console.Name == "Console"
    assert LoggingAPI.file.Name == "File"