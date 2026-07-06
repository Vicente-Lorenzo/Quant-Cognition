from __future__ import annotations

import json

from Library.Utility.Service import ServiceAPI
from Library.Utility.Statistic import Timer
from Library.Utility.Typing import MISSING, Missing

class RemoteAPI(ServiceAPI):

    def __init__(self,
                 api: ServiceAPI | Missing = MISSING, *,
                 host: str | Missing = MISSING,
                 port: int | Missing = MISSING,
                 token: str | Missing = MISSING,
                 timeout: int | Missing = MISSING,
                 **kwargs) -> None:
        super().__init__(api, **kwargs)
        self._host_: str | Missing = host
        self._port_: int | Missing = port
        self._token_: str | Missing = token
        self._timeout_: int | Missing = timeout
        self._socket_ = None
        self._connected_: bool = False

    def remote(self) -> bool:
        return self._host_ is not MISSING

    def connected(self) -> bool:
        return self._connected_

    def _connect_(self, **kwargs) -> None:
        if self.remote():
            import zmq
            self._socket_ = zmq.Context.instance().socket(zmq.REQ)
            self._socket_.setsockopt(zmq.LINGER, 0)
            if self._timeout_ is not MISSING: self._socket_.setsockopt(zmq.RCVTIMEO, self._timeout_ * 1000)
            self._socket_.connect(f"tcp://{self._host_}:{self._port_}")
            self._log_.info(lambda: f"Remote Operation: Targeting (tcp://{self._host_}:{self._port_})")
        self._connected_ = True

    def disconnected(self) -> bool:
        return not self._connected_

    def _disconnect_(self) -> None:
        if self._socket_ is not None:
            self._socket_.close()
            self._socket_ = None
        self._connected_ = False

    @staticmethod
    def _address_() -> str:
        import socket
        try: return socket.gethostbyname(socket.gethostname())
        except OSError: return "0.0.0.0"

    @staticmethod
    def _peer_(request) -> str | None:
        try: return request.get("Peer-Address")
        except Exception: return None

    @staticmethod
    def _filter_(peer: str | None, whitelist: list[str] | Missing, blacklist: list[str] | Missing) -> None:
        if whitelist is not MISSING and peer not in whitelist: raise PermissionError("Address Not Whitelisted")
        if blacklist is not MISSING and peer in blacklist: raise PermissionError("Address Blacklisted")

    def _dispatch_(self, name: str, args: list, kwargs: dict) -> bytes:
        raise NotImplementedError(f"{self.__class__.__name__}._dispatch_() is not implemented")

    def _request_(self, name: str, *args, **kwargs) -> bytes:
        token = None if self._token_ is MISSING else self._token_
        request = json.dumps({"call": name, "args": args, "kwargs": kwargs, "token": token}, default=str).encode()
        try:
            self._socket_.send(request)
            frames = self._socket_.recv_multipart()
        except Exception:
            self.disconnect()
            raise
        header = json.loads(frames[0])
        if header["status"] != "ok": raise RuntimeError(header["error"])
        return frames[1]

    def serve(self,
              port: int,
              token: str | Missing = MISSING,
              whitelist: list[str] | Missing = MISSING,
              blacklist: list[str] | Missing = MISSING) -> None:
        if self.remote(): raise RuntimeError("Serving requires a local interface")
        import zmq
        self.connect()
        socket = zmq.Context.instance().socket(zmq.REP)
        socket.bind(f"tcp://*:{port}")
        self._log_.info(lambda: f"Serve Operation: Listening (tcp://{self._address_()}:{port})")
        try:
            while True:
                request = socket.recv(copy=False)
                peer = self._peer_(request)
                timer = Timer()
                timer.start()
                try:
                    self._filter_(peer, whitelist, blacklist)
                    envelope = json.loads(bytes(request.buffer))
                    if token is not MISSING and envelope.get("token") != token: raise PermissionError("Invalid Token")
                    payload = self._dispatch_(envelope["call"], envelope["args"], envelope["kwargs"])
                    timer.stop()
                    socket.send_multipart([json.dumps({"status": "ok"}).encode(), payload])
                    self._log_.debug(lambda: f"Serve Operation: Answered {envelope['call']} ({len(payload)} Bytes · {timer.result()} · {peer})")
                except PermissionError as e:
                    timer.stop()
                    socket.send_multipart([json.dumps({"status": "error", "error": f"{e}"}).encode()])
                    self._log_.warning(lambda: f"Serve Operation: Rejected · {e} ({peer})")
                except Exception as e:
                    timer.stop()
                    socket.send_multipart([json.dumps({"status": "error", "error": f"{e}"}).encode()])
                    self._log_.error(lambda: f"Serve Operation: Failed · {e}")
        except KeyboardInterrupt:
            self._log_.info(lambda: "Serve Operation: Interrupted by User")
        finally:
            socket.close()