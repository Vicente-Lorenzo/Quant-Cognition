"""
IPC Benchmark: ZMQ TCP vs Named Pipes vs Shared Memory
Simulates cTrader <-> Python round-trip communication lifecycle on Windows.

Each round-trip:
  Producer -> Consumer: update payload (tick or bar sized)
  Consumer -> Producer: action response

Usage: conda run -n Quant python Tests/Benchmark/IPC.py [-n 100000]
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import mmap
import multiprocessing
import struct
import time

# ── Windows Kernel32 ─────────────────────────────────────────────────────────

K32 = ctypes.windll.kernel32
K32.CreateEventW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.BOOL, wt.LPCWSTR]
K32.CreateEventW.restype = wt.HANDLE
K32.SetEvent.argtypes = [wt.HANDLE]
K32.SetEvent.restype = wt.BOOL
K32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
K32.WaitForSingleObject.restype = wt.DWORD
K32.CloseHandle.argtypes = [wt.HANDLE]
K32.CloseHandle.restype = wt.BOOL
INFINITE = 0xFFFFFFFF

# ── Payloads (matching real System.cs SendUpdateTick / SendUpdateBar) ────────

TICK = json.dumps({
    "UpdateID": 10, "Timestamp": 1706745600000,
    "Ask": 1.08432, "Bid": 1.08430,
    "AskBaseConversion": 1.0, "BidBaseConversion": 1.0,
    "AskQuoteConversion": 1.08432, "BidQuoteConversion": 1.08430,
    "Volume": 100
}).encode()

BAR = json.dumps({
    "UpdateID": 11, "Timestamp": 1706745600000,
    "GapAsk": 1.08432, "GapBid": 1.08430,
    "GapTimestamp": 1706745600000, "GapVolume": 50,
    "GapAskBaseConversion": 1.0, "GapBidBaseConversion": 1.0,
    "GapAskQuoteConversion": 1.08432, "GapBidQuoteConversion": 1.08430,
    "OpenAsk": 1.08400, "OpenBid": 1.08398,
    "OpenTimestamp": 1706745600001, "OpenVolume": 120,
    "OpenAskBaseConversion": 1.0, "OpenBidBaseConversion": 1.0,
    "OpenAskQuoteConversion": 1.08400, "OpenBidQuoteConversion": 1.08398,
    "HighAsk": 1.08500, "HighBid": 1.08498,
    "HighTimestamp": 1706745612000, "HighVolume": 200,
    "HighAskBaseConversion": 1.0, "HighBidBaseConversion": 1.0,
    "HighAskQuoteConversion": 1.08500, "HighBidQuoteConversion": 1.08498,
    "LowAsk": 1.08350, "LowBid": 1.08348,
    "LowTimestamp": 1706745624000, "LowVolume": 80,
    "LowAskBaseConversion": 1.0, "LowBidBaseConversion": 1.0,
    "LowAskQuoteConversion": 1.08350, "LowBidQuoteConversion": 1.08348,
    "CloseAsk": 1.08450, "CloseBid": 1.08448,
    "CloseTimestamp": 1706745636000, "CloseVolume": 150,
    "CloseAskBaseConversion": 1.0, "CloseBidBaseConversion": 1.0,
    "CloseAskQuoteConversion": 1.08450, "CloseBidQuoteConversion": 1.08448,
    "Volume": 1000
}).encode()

RESPONSE = json.dumps({"ActionID": 1}).encode()

# ── ZMQ TCP PAIR ─────────────────────────────────────────────────────────────

def _zmq_consumer_(n, port, warmup):
    import zmq
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PAIR)
    sock.bind(f"tcp://127.0.0.1:{port}")
    for _ in range(warmup + n):
        sock.recv()
        sock.send(RESPONSE)
    sock.close()
    ctx.term()

def bench_zmq(n, payload, port=15555, warmup=2000):
    import zmq
    proc = multiprocessing.Process(target=_zmq_consumer_, args=(n, port, warmup))
    proc.start()
    time.sleep(0.5)
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PAIR)
    sock.connect(f"tcp://127.0.0.1:{port}")
    time.sleep(0.2)
    for _ in range(warmup):
        sock.send(payload)
        sock.recv()
    t0 = time.perf_counter()
    for _ in range(n):
        sock.send(payload)
        sock.recv()
    elapsed = time.perf_counter() - t0
    sock.close()
    ctx.term()
    proc.join()
    return elapsed

# ── Named Pipes (Windows native) ────────────────────────────────────────────

def _pipe_consumer_(n, address, warmup):
    from multiprocessing.connection import Listener
    listener = Listener(address)
    conn = listener.accept()
    for _ in range(warmup + n):
        conn.recv_bytes()
        conn.send_bytes(RESPONSE)
    conn.close()
    listener.close()

def bench_pipe(n, payload, warmup=2000):
    address = r"\\.\pipe\ipc_bench_pipe"
    proc = multiprocessing.Process(target=_pipe_consumer_, args=(n, address, warmup))
    proc.start()
    time.sleep(0.5)
    from multiprocessing.connection import Client
    conn = Client(address)
    for _ in range(warmup):
        conn.send_bytes(payload)
        conn.recv_bytes()
    t0 = time.perf_counter()
    for _ in range(n):
        conn.send_bytes(payload)
        conn.recv_bytes()
    elapsed = time.perf_counter() - t0
    conn.close()
    proc.join()
    return elapsed

# ── Shared Memory + Named Events ────────────────────────────────────────────

BUF = 16384

def _shm_write_(shm, data):
    shm.seek(0)
    shm.write(struct.pack("I", len(data)))
    shm.write(data)

def _shm_read_(shm):
    shm.seek(0)
    size = struct.unpack("I", shm.read(4))[0]
    return shm.read(size)

def _shm_consumer_(n, warmup):
    u_shm = mmap.mmap(-1, BUF, "ipc_bench_u")
    a_shm = mmap.mmap(-1, BUF, "ipc_bench_a")
    u_evt = K32.CreateEventW(None, False, False, "ipc_bench_ue")
    a_evt = K32.CreateEventW(None, False, False, "ipc_bench_ae")
    for _ in range(warmup + n):
        K32.WaitForSingleObject(u_evt, INFINITE)
        _shm_read_(u_shm)
        _shm_write_(a_shm, RESPONSE)
        K32.SetEvent(a_evt)
    K32.CloseHandle(u_evt)
    K32.CloseHandle(a_evt)
    u_shm.close()
    a_shm.close()

def bench_shm(n, payload, warmup=2000):
    u_shm = mmap.mmap(-1, BUF, "ipc_bench_u")
    a_shm = mmap.mmap(-1, BUF, "ipc_bench_a")
    u_evt = K32.CreateEventW(None, False, False, "ipc_bench_ue")
    a_evt = K32.CreateEventW(None, False, False, "ipc_bench_ae")
    proc = multiprocessing.Process(target=_shm_consumer_, args=(n, warmup))
    proc.start()
    time.sleep(0.3)
    for _ in range(warmup):
        _shm_write_(u_shm, payload)
        K32.SetEvent(u_evt)
        K32.WaitForSingleObject(a_evt, INFINITE)
        _shm_read_(a_shm)
    t0 = time.perf_counter()
    for _ in range(n):
        _shm_write_(u_shm, payload)
        K32.SetEvent(u_evt)
        K32.WaitForSingleObject(a_evt, INFINITE)
        _shm_read_(a_shm)
    elapsed = time.perf_counter() - t0
    proc.join()
    K32.CloseHandle(u_evt)
    K32.CloseHandle(a_evt)
    u_shm.close()
    a_shm.close()
    return elapsed

# ── Report ───────────────────────────────────────────────────────────────────

TRANSPORTS = [
    ("ZMQ TCP PAIR", bench_zmq),
    ("Named Pipes", bench_pipe),
    ("Shared Memory", bench_shm),
]

def header(n):
    print(f"\n{'=' * 95}")
    print(f"  IPC Benchmark  |  {n:,} round-trips per test  |  2 messages per round-trip")
    print(f"  Payload sizes: Tick = {len(TICK)} B, Bar = {len(BAR)} B, Response = {len(RESPONSE)} B")
    print(f"{'=' * 95}")
    print(f"  {'Transport':<20s} {'Payload':<8s} {'Size':>6s}"
          f"  {'Time':>9s}  {'Round-trips/s':>14s}  {'Messages/s':>14s}  {'Latency':>10s}")
    print(f"  {'-' * 20} {'-' * 8} {'-' * 6}"
          f"  {'-' * 9}  {'-' * 14}  {'-' * 14}  {'-' * 10}")

def row(name, payload_name, n, elapsed, payload_size):
    rps = n / elapsed
    mps = rps * 2
    lat = elapsed / n * 1_000_000
    print(f"  {name:<20s} {payload_name:<8s} {payload_size:>5d} B"
          f"  {elapsed:>8.3f} s  {rps:>13,.0f} /s  {mps:>13,.0f} /s  {lat:>8.2f} us")

def separator():
    print(f"  {'.' * 87}")

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="IPC transport benchmark")
    parser.add_argument("-n", "--iterations", type=int, default=100_000)
    parser.add_argument("--tick-only", action="store_true")
    parser.add_argument("--bar-only", action="store_true")
    args = parser.parse_args()
    n = args.iterations

    payloads = []
    if not args.bar_only:
        payloads.append((TICK, "Tick"))
    if not args.tick_only:
        payloads.append((BAR, "Bar"))

    header(n)
    for payload, pname in payloads:
        for tname, bench_fn in TRANSPORTS:
            try:
                elapsed = bench_fn(n, payload)
                row(tname, pname, n, elapsed, len(payload))
            except Exception as e:
                print(f"  {tname:<20s} {pname:<8s}  FAILED: {e}")
        separator()
    print(f"{'=' * 95}\n")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()