import struct
import threading
from unittest.mock import MagicMock, patch

import pytest

from Library.Protocol.Transport import TransportAPI

@pytest.fixture
def buffers():
    import mmap
    update = mmap.mmap(-1, TransportAPI._BUF_SIZE_, "test_transport_update")
    action = mmap.mmap(-1, TransportAPI._BUF_SIZE_, "test_transport_action")
    yield update, action
    update.close()
    action.close()

def test_write_read_round_trip(buffers):
    update, _ = buffers
    payload = b"\x01\x02\x03\x04\x05"
    TransportAPI._write_(update, payload)
    result = TransportAPI._read_(update)
    assert result == payload

def test_write_read_empty(buffers):
    update, _ = buffers
    TransportAPI._write_(update, b"")
    result = TransportAPI._read_(update)
    assert result == b""

def test_write_max_capacity(buffers):
    update, _ = buffers
    max_payload = b"\xFF" * (TransportAPI._BUF_SIZE_ - 4)
    TransportAPI._write_(update, max_payload)
    result = TransportAPI._read_(update)
    assert result == max_payload

def test_write_overflow_raises(buffers):
    update, _ = buffers
    oversized = b"\xFF" * (TransportAPI._BUF_SIZE_ - 3)
    with pytest.raises(ValueError, match="Message too large"):
        TransportAPI._write_(update, oversized)

def test_write_uses_little_endian_length(buffers):
    update, _ = buffers
    payload = b"\xAA" * 300
    TransportAPI._write_(update, payload)
    update.seek(0)
    raw_len = update.read(4)
    assert struct.unpack("<I", raw_len)[0] == 300

def test_length_struct_is_little_endian_unsigned():
    assert TransportAPI._LENGTH_.format == b'<I' or TransportAPI._LENGTH_.format == '<I'
    assert TransportAPI._LENGTH_.size == 4

def test_class_constants():
    assert TransportAPI._BUF_SIZE_ == 4096
    assert TransportAPI._POLL_MS_ == 500
    assert TransportAPI._INFINITE_ == 0xFFFFFFFF
    assert TransportAPI._SYNCHRONIZE_ == 0x00100000
    assert TransportAPI._WAIT_TIMEOUT_ == 0x00000102

def test_send_raises_when_closed():
    transport = MagicMock(spec=TransportAPI)
    transport._closed_ = True
    transport.send = TransportAPI.send.__get__(transport, TransportAPI)
    with pytest.raises(SystemExit, match="Transport closed"):
        transport.send(b"\x01")

def test_receive_raises_when_closed():
    transport = MagicMock(spec=TransportAPI)
    transport._closed_ = True
    transport.receive = TransportAPI.receive.__get__(transport, TransportAPI)
    with pytest.raises(SystemExit, match="Transport closed"):
        transport.receive()

def test_wait_raises_on_peer_dead():
    transport = MagicMock(spec=TransportAPI)
    transport._closed_ = False
    transport._peer_dead_ = threading.Event()
    transport._peer_dead_.set()
    transport._wait_ = TransportAPI._wait_.__get__(transport, TransportAPI)
    with pytest.raises(SystemExit, match="Peer process exited"):
        transport._wait_(MagicMock())

def test_close_idempotent():
    transport = MagicMock(spec=TransportAPI)
    transport._closed_ = True
    transport.close = TransportAPI.close.__get__(transport, TransportAPI)
    transport.close()
