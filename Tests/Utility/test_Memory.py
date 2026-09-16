from Library.Utility.Memory import memory_to_string

def test_memory_to_string_keeps_bytes_whole():
    assert memory_to_string(0) == "0 B"
    assert memory_to_string(512) == "512 B"
    assert memory_to_string(1023) == "1023 B"

def test_memory_to_string_scales_by_1024_with_one_decimal():
    assert memory_to_string(1024) == "1.0 kB"
    assert memory_to_string(1536) == "1.5 kB"
    assert memory_to_string(1572864) == "1.5 MB"
    assert memory_to_string(3 * 1024 ** 3) == "3.0 GB"

def test_memory_to_string_treats_missing_as_zero():
    assert memory_to_string(None) == "0 B"

def test_memory_to_string_caps_at_the_largest_unit():
    assert memory_to_string(4096 * 1024 ** 5) == "4096.0 PB"