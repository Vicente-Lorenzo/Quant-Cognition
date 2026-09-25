import socket
import threading
import urllib.request

import pytest

from Script.Setup.Spotware import SignInCommandAPI

def _port_() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]

def test_a_redirect_address_yields_its_code():
    assert SignInCommandAPI._code_("http://127.0.0.1:8765/callback?code=abc&state=x") == "abc"
    with pytest.raises(PermissionError, match="access_denied"):
        SignInCommandAPI._code_("http://127.0.0.1:8765/callback?error=access_denied")
    with pytest.raises(ValueError, match="no code"):
        SignInCommandAPI._code_("http://127.0.0.1:8765/callback")

def test_the_loopback_listener_takes_one_redirect():
    redirect = f"http://127.0.0.1:{_port_()}/callback"
    visit = threading.Timer(0.5, lambda: urllib.request.urlopen(f"{redirect}?code=xyz", timeout=5).read())
    visit.start()
    try: assert SignInCommandAPI._listen_(redirect, 10) == "xyz"
    finally: visit.join()

def test_the_loopback_listener_gives_up_after_its_timeout():
    with pytest.raises(TimeoutError, match="No redirect"):
        SignInCommandAPI._listen_(f"http://127.0.0.1:{_port_()}/callback", 0.5)