import numpy as np
import pandas as pd
import pytest
from src.phase_detector import _gga_algorithm, _fallback_heuristic


def _make_df(ddo_values):
    n = len(ddo_values)
    return pd.DataFrame({
        'No.peak': [100 + 470 * i for i in range(n)],
        'Tag': ['unknown'] * n,
        'Doin (mV)': [260.0] * n,
        'DOmin (mV)': [256.0] * n,
        'DDO (mV)': ddo_values,
        'Sample Name': ['test'] * n,
    })


def test_gga_algorithm_clear_two_phase():
    """7 high-DDO peaks then 8 low-DDO peaks: boundary at index 6."""
    ddo = [4.0, 4.1, 3.9, 4.0, 3.8, 4.0, 4.1, 2.5, 2.4, 2.5, 2.4, 2.5, 2.3, 2.4, 2.5]
    df = _make_df(ddo)
    preds, confs = _gga_algorithm(df)
    assert preds[6] == 0
    assert preds[7] == 1
    assert preds[8] == 2
    assert all(c > 0 for c in confs)


def test_gga_algorithm_constrained_range():
    """Boundary in [5, 8]."""
    ddo = [4.0, 4.1, 3.9, 4.0, 4.1, 2.5, 2.4, 2.5, 2.4, 2.5, 2.3, 2.4]
    df = _make_df(ddo)
    preds, confs = _gga_algorithm(df)
    phase1_count = int((preds == 0).sum())
    assert 5 <= phase1_count <= 8


def test_fallback_heuristic_short_sample():
    """For n<8, fallback splits in half, no transition."""
    df = _make_df([4.0, 4.0, 4.0, 2.5, 2.5, 2.5])
    preds, confs = _fallback_heuristic(df)
    assert len(preds) == 6
    assert (preds == 1).sum() == 0
    assert (preds == 0).sum() == 3
    assert (preds == 2).sum() == 3
