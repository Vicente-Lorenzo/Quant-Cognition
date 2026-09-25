import pytest

from concurrent.futures import ProcessPoolExecutor

from Library.Utility.Memory import ParcelAPI, memory_to_string

def _received_(handle: tuple) -> int:
    return len(ParcelAPI.attach(handle)["Rows"])

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

def test_a_parcel_hands_the_same_value_back():
    value = {"Name": "EURUSD", "Rows": list(range(1000)), "Empty": None}
    parcel = ParcelAPI(value)
    try: assert ParcelAPI.attach(parcel.handle()) == value
    finally: parcel.close()

def test_a_worker_process_receives_a_parcel_larger_than_the_spawn_pipe():
    parcel = ParcelAPI({"Rows": b"x" * 2_000_000})
    try:
        with ProcessPoolExecutor(max_workers=1) as pool: assert pool.submit(_received_, parcel.handle()).result(timeout=120) == 2_000_000
    finally: parcel.close()

def test_a_closed_parcel_is_gone():
    parcel = ParcelAPI([1, 2, 3])
    handle = parcel.handle()
    parcel.close()
    with pytest.raises(FileNotFoundError): ParcelAPI.attach(handle)