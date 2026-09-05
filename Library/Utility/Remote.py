import json
import threading
from typing import Callable

from Library.Utility.Service import ServiceAPI
from Library.Utility.Profiler import Timer
from Library.Utility.Typing import MISSING, Missing

class RemoteAPI(ServiceAPI):

    _PING_: int = 5

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
            self._socket_.setsockopt(zmq.RCVTIMEO, self._PING_ * 1000)
            self._socket_.connect(f"tcp://{self._host_}:{self._port_}")
            try:
                self._socket_.send(json.dumps(self._envelope_("ping", (), {})).encode())
                header = json.loads(self._socket_.recv_multipart()[0])
                if header["status"] != "ok": raise RuntimeError(header["error"])
            except zmq.Again:
                self._disconnect_()
                raise ConnectionError(f"Server Unreachable (tcp://{self._host_}:{self._port_})") from None
            except Exception:
                self._disconnect_()
                raise
            self._socket_.setsockopt(zmq.RCVTIMEO, self._timeout_ * 1000 if self._timeout_ is not MISSING else -1)
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

    @staticmethod
    def _reply_(socket, header: dict, payload: bytes = b"") -> None:
        socket.send_multipart([json.dumps(header).encode(), payload])

    @staticmethod
    def _unsubscribed_(publisher) -> bool:
        unsubscribed = False
        while publisher.poll(0):
            if publisher.recv()[:1] == b"\x00": unsubscribed = True
        return unsubscribed

    def _envelope_(self, name: str, args: tuple, kwargs: dict) -> dict:
        return {"call": name, "args": args, "kwargs": kwargs, "token": None if self._token_ is MISSING else self._token_}

    def _dispatch_(self, name: str, args: list, kwargs: dict) -> bytes:
        raise NotImplementedError(f"{self.__class__.__name__}._dispatch_() is not implemented")

    def _publish_(self, name: str, args: list, kwargs: dict):
        raise NotImplementedError(f"{self.__class__.__name__}._publish_() is not implemented")

    def _exchange_(self, envelope: dict) -> tuple[dict, list]:
        import zmq
        request = json.dumps(envelope, default=str).encode()
        try:
            self._socket_.send(request)
            frames = self._socket_.recv_multipart()
        except zmq.Again:
            self.disconnect()
            raise TimeoutError(f"No reply within {self._timeout_} seconds (tcp://{self._host_}:{self._port_})") from None
        except Exception:
            self.disconnect()
            raise
        header = json.loads(frames[0])
        if header["status"] != "ok": raise RuntimeError(header["error"])
        return header, frames

    def _request_(self, name: str, *args, **kwargs) -> bytes:
        _, frames = self._exchange_(self._envelope_(name, args, kwargs))
        return frames[1]

    def _listen_(self, name: str, *args, callback: Callable, limit: int | Missing = MISSING, **kwargs) -> None:
        import zmq
        envelope = self._envelope_(name, args, kwargs)
        envelope["stream"] = None if limit is MISSING else limit
        header, _ = self._exchange_(envelope)
        subscriber = zmq.Context.instance().socket(zmq.SUB)
        subscriber.setsockopt(zmq.LINGER, 0)
        if self._timeout_ is not MISSING: subscriber.setsockopt(zmq.RCVTIMEO, self._timeout_ * 1000)
        subscriber.connect(f"tcp://{self._host_}:{header['port']}")
        subscriber.setsockopt(zmq.SUBSCRIBE, b"")
        try:
            count = 0
            while limit is MISSING or count < limit:
                callback(subscriber.recv())
                count += 1
        except zmq.Again:
            raise TimeoutError(f"No update within {self._timeout_} seconds (tcp://{self._host_}:{header['port']})") from None
        finally:
            subscriber.close()

    def _broadcast_(self, publisher, envelope: dict) -> None:
        source = self._publish_(envelope["call"], envelope["args"], envelope["kwargs"])
        limit = envelope["stream"]
        try:
            if publisher.poll(self._PING_ * 1000) == 0:
                self._log_.warning(lambda: "Stream Operation: Aborted · No Subscriber Arrived")
                return
            publisher.recv()
            count = 0
            for payload in source:
                if self._unsubscribed_(publisher):
                    self._log_.debug(lambda: f"Stream Operation: Unsubscribed ({count} Updates)")
                    return
                publisher.send(payload)
                count += 1
                if limit is not None and count >= limit: break
            self._log_.debug(lambda: f"Stream Operation: Completed ({count} Updates)")
        except Exception as e:
            self._log_.error(lambda: f"Stream Operation: Failed · {e}")
            self._log_.exception(lambda: f"Stream Operation: Failed · {e}")
        finally:
            source.close()
            publisher.close()

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
                    if envelope["call"] == "ping":
                        timer.stop()
                        self._reply_(socket, {"status": "ok"})
                        self._log_.debug(lambda: f"Serve Operation: Answered ping ({timer.result()} · {peer})")
                    elif "stream" in envelope:
                        publisher = zmq.Context.instance().socket(zmq.XPUB)
                        stream = publisher.bind_to_random_port("tcp://*")
                        threading.Thread(target=self._broadcast_, args=(publisher, envelope), daemon=True).start()
                        timer.stop()
                        self._reply_(socket, {"status": "ok", "port": stream})
                        self._log_.debug(lambda: f"Serve Operation: Streaming {envelope['call']} (Port {stream} · {envelope['stream']} Updates · {peer})")
                    else:
                        payload = self._dispatch_(envelope["call"], envelope["args"], envelope["kwargs"])
                        timer.stop()
                        self._reply_(socket, {"status": "ok"}, payload)
                        self._log_.debug(lambda: f"Serve Operation: Answered {envelope['call']} ({len(payload)} Bytes · {timer.result()} · {peer})")
                except PermissionError as e:
                    timer.stop()
                    self._reply_(socket, {"status": "error", "error": f"{e}"})
                    self._log_.warning(lambda: f"Serve Operation: Rejected · {e} ({peer})")
                except Exception as e:
                    timer.stop()
                    self._reply_(socket, {"status": "error", "error": f"{e}"})
                    self._log_.error(lambda: f"Serve Operation: Failed · {e}")
        except KeyboardInterrupt:
            self._log_.info(lambda: "Serve Operation: Interrupted by User")
        finally:
            socket.close()