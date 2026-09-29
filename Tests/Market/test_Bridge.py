import pytest

from Library.Database.Dataframe import np
from Library.Market.Tape import TapeAPI

def _tape_(stamps, asks, bids):
    return TapeAPI(Security=1, Stamps=np.array(stamps, dtype=np.int64), Asks=np.array(asks), Bids=np.array(bids), Volumes=np.zeros(len(stamps)))

def test_a_bridged_rate_multiplies_its_legs_at_every_stamp_either_leg_moves():
    usdjpy = _tape_([10, 30], [150.02, 151.02], [150.00, 151.00])
    usdchf = _tape_([20, 40], [0.9002, 0.9102], [0.9000, 0.9100])
    bridged = TapeAPI.compose((usdjpy, True), (usdchf, False))
    assert bridged.Stamps.tolist() == [20, 30, 40]
    assert bridged.Asks.tolist() == pytest.approx([0.9002 / 150.00, 0.9002 / 151.00, 0.9102 / 151.00])
    assert bridged.Bids.tolist() == pytest.approx([0.9000 / 150.02, 0.9000 / 151.02, 0.9100 / 151.02])

def test_a_bridged_rate_reads_like_a_direct_pair():
    usdjpy = _tape_([10, 30], [150.02, 151.02], [150.00, 151.00])
    usdchf = _tape_([5, 40], [0.9002, 0.9102], [0.9000, 0.9100])
    asks, bids = TapeAPI.rates(np.array([12, 35, 45], dtype=np.int64), (TapeAPI.compose((usdjpy, True), (usdchf, False)), False))
    assert bids.tolist() == pytest.approx([0.9000 / 150.02, 0.9000 / 151.02, 0.9100 / 151.02])
    assert np.isnan(TapeAPI.rates(np.array([7], dtype=np.int64), (TapeAPI.compose((usdjpy, True), (usdchf, False)), False))[0][0])