import os
import time

from Library.Utility.File import PruneAPI

def _aged_(path, days):
    path.write_text("x")
    stamp = time.time() - days * 86400
    os.utime(path, (stamp, stamp))
    return path

def test_sweep_removes_only_stale_candidates(tmp_path):
    stale, fresh = _aged_(tmp_path / "Stale.txt", 40), _aged_(tmp_path / "Fresh.txt", 1)
    assert PruneAPI.sweep((stale, fresh), PruneAPI.horizon())[0] == 1
    assert not stale.exists() and fresh.exists()

def test_sweep_spares_what_the_predicate_protects(tmp_path):
    kept, dropped = _aged_(tmp_path / "Kept.txt", 40), _aged_(tmp_path / "Dropped.txt", 40)
    assert PruneAPI.sweep((kept, dropped), PruneAPI.horizon(), spare=lambda candidate: candidate.name == "Kept.txt")[0] == 1
    assert kept.exists() and not dropped.exists()

def test_prune_forwards_the_spare_predicate(tmp_path):
    kept, dropped = _aged_(tmp_path / "Kept.txt", 40), _aged_(tmp_path / "Dropped.txt", 40)
    assert PruneAPI.prune((tmp_path,), spare=lambda candidate: candidate == kept)[0] == 1
    assert kept.exists() and not dropped.exists()