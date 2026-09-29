import sys
import json
import filecmp
import subprocess

import pytest

from datetime import datetime
from types import SimpleNamespace

from Library.Database import PostgresDatabaseAPI
from Library.Database.Dataframe import np
from Library.Market.Tape import TapeAPI
from Library.Portfolio.Sizing import calculate_fixed_fractional_volume
from Library.Strategy.Hybrid.DDPG import DDPGStrategyAPI
from Library.System.Learning import LearningAPI
from Library.System.Main import SystemCommandAPI
from Library.Universe.Contract import CommissionType, SpreadType, SwapType
from Library.Universe.Security import SecurityAPI
from Library.Utility.IO import read_yaml
from Library.Utility.Parameter import Parameter
from Library.Utility.Path import traceback_root
from Library.Utility.Runtime import split_arguments

ROOT = traceback_root()
GOLDENS = sorted([*(ROOT / "Tests" / "Golden" / "Offline").glob("Golden *"), *(ROOT / "Tests" / "Golden" / "Consistency").iterdir()])
EXPORTS = ("trades", "positions", "orders", "deals")
MAJORS = ("EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD")

def _command_(golden) -> list:
    command = json.loads((golden / "Run.json").read_text(encoding="utf-8"))["Command"]
    arguments = split_arguments(command.split(" --run ", 1)[0])
    if "--parameters" not in arguments: arguments += ["--parameters", (golden / "Parameters.yml").relative_to(ROOT).as_posix()]
    if "--contract" not in arguments: arguments += ["--contract", (golden / "Contract.yml").relative_to(ROOT).as_posix()]
    return arguments

def test_every_golden_folder_is_complete():
    assert GOLDENS
    for golden in GOLDENS:
        assert all((golden / name).is_file() for name in ("Run.json", "Parameters.yml", "Contract.yml", *(f"{export}.csv" for export in EXPORTS))), golden

@pytest.mark.parametrize("golden", GOLDENS, ids=lambda golden: f"{golden.parent.name}/{golden.name}")
def test_a_golden_replays_byte_identically(golden, tmp_path):
    process = subprocess.run([sys.executable, "-m", "Library.System.Main", *_command_(golden), "--run", str(tmp_path)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert process.returncode == 0, process.stderr[-2000:]
    for export in EXPORTS:
        produced = tmp_path / "Output" / "Export" / f"{export}.csv"
        assert produced.is_file() and filecmp.cmp(produced, golden / f"{export}.csv", shallow=False), f"{golden.name} {export}.csv drifted"

def test_backtests_in_one_process_equal_their_standalone_runs(tmp_path):
    offline = [golden for golden in GOLDENS if golden.parent.name == "Offline"][:3]
    for golden in offline:
        assert subprocess.run([sys.executable, "-m", "Library.System.Main", *_command_(golden), "--run", str(tmp_path / "Alone" / golden.name)], cwd=ROOT, capture_output=True).returncode == 0
    for golden in reversed(offline): assert SystemCommandAPI().main([*_command_(golden), "--run", str(tmp_path / "Together" / golden.name)]) == 0
    for golden in offline:
        for export in (*EXPORTS, "net"):
            assert filecmp.cmp(tmp_path / "Alone" / golden.name / "Output" / "Export" / f"{export}.csv", tmp_path / "Together" / golden.name / "Output" / "Export" / f"{export}.csv", shallow=False), f"{golden.name} {export}.csv"

def test_an_optimization_delivers_what_a_backtest_of_its_parameters_produces(tmp_path):
    search = ["Optimization", "--strategy", "Trend", "--ticker", "EURUSD", "--timeframe", "Daily", "--start", "2023-01-01", "--stop", "2024-01-01", "--validation", "3", "--testing", "3", "--workers", "4", "--console", "Warning", "--file", "Warning", "--export", "--run", str(tmp_path / "Search")]
    assert subprocess.run([sys.executable, "-m", "Library.System.Main", *search], cwd=ROOT, capture_output=True).returncode == 0
    replay = ["Backtesting", "--strategy", "Trend", "--ticker", "EURUSD", "--timeframe", "Daily", "--start", "2023-01-01", "--stop", "2024-01-01", "--console", "Warning", "--file", "Warning", "--export", "--parameters", str(tmp_path / "Search" / "Output" / "Parameters.yml"), "--contract", str(tmp_path / "Search" / "Input" / "Contract.yml"), "--run", str(tmp_path / "Replay")]
    assert subprocess.run([sys.executable, "-m", "Library.System.Main", *replay], cwd=ROOT, capture_output=True).returncode == 0
    for export in (*EXPORTS, "net"):
        assert filecmp.cmp(tmp_path / "Search" / "Output" / "Export" / f"{export}.csv", tmp_path / "Replay" / "Output" / "Export" / f"{export}.csv", shallow=False), export

def test_a_learning_pass_on_cached_indicators_equals_a_fresh_one():
    golden = ROOT / "Tests" / "Golden" / "Consistency" / "DDPG"
    data = read_yaml(golden / "Parameters.yml")
    data["SignalManagement"]["Weights"] = [str(golden / "Weights")]
    security, timeframe = LearningAPI._resolve_({"provider": "Spotware(cTrader)", "ticker": "EURUSD", "timeframe": "H1"})
    learner = LearningAPI(strategy=DDPGStrategyAPI, security=security, timeframe=timeframe, parameters=Parameter(data, "."), start="2023-01-01", stop="2024-01-01", account=("EUR", 10000.0, 30.0, None), spread=(SpreadType.Accurate, None), commission=(CommissionType.Points, 3.5), swap=(SwapType.Points, 0.0, 0.0), reward="LogReturn", episodes=1, report=False, export=False)
    fresh = (learner._pass_(learner._range_start_, learner._range_stop_, False), learner._trades_())
    assert learner._dataset_.IndicatorResults is None
    cached = (learner._pass_(learner._range_start_, learner._range_stop_, False), learner._trades_())
    assert learner._dataset_.IndicatorResults is not None and fresh[1] > 0 and cached == fresh

def test_every_account_currency_converts_and_sizes_every_pair_through_its_direct_pairs():
    start, stop = datetime(2024, 3, 5, 12), datetime(2024, 3, 5, 13)
    with PostgresDatabaseAPI(database="Quant") as db:
        pairs = {base + quote: SecurityAPI(Provider="Spotware(cTrader)", Ticker=base + quote, db=db, autoload=True) for base in MAJORS for quote in MAJORS if base != quote and db.first(schema="Universe", table="Ticker", condition='"UID" = :uid:', parameters={"uid": base + quote})}
        tapes = {ticker: TapeAPI.read(db, security.UID, start, stop) for ticker, security in pairs.items()}
        def dollars(asset, stamp):
            if asset == "USD": return 1.0
            tape, inverse = (tapes[asset + "USD"], False) if asset + "USD" in tapes else (tapes["USD" + asset], True)
            index = int(np.searchsorted(tape.Stamps, stamp, "right")) - 1
            middle = (tape.Asks[index] + tape.Bids[index]) / 2.0
            return 1.0 / middle if inverse else middle
        assert len(pairs) == 28
        for ticker, security in pairs.items():
            tape, contract, stamp = tapes[ticker], security.Contract, tapes[ticker].Stamps[-1:]
            for account in MAJORS:
                quote = float(TapeAPI.rates(stamp, TapeAPI.source(db, security, security.Ticker.QuoteAsset, account, tape))[1][0])
                assert abs(quote / (dollars(security.Ticker.QuoteAsset, stamp[0]) / dollars(account, stamp[0])) - 1.0) < 5e-4, (ticker, account)
                funds = 10000.0 * dollars("EUR", stamp[0]) / dollars(account, stamp[0])
                volume = calculate_fixed_fractional_volume(1.0, 50.0, SimpleNamespace(Balance=funds), contract, quote)
                risk = volume * 50.0 * contract.PipSize * quote / funds * 100.0
                assert 1.0 - contract.VolumeStep / volume - 1e-9 <= risk <= 1.0 + 1e-9, (ticker, account, risk)