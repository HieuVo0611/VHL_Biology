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


import os

@pytest.mark.skipif(
    not os.path.exists('model/phase_detector_metal.pkl'),
    reason='Metal model not trained yet'
)
def test_metal_ml_predict_returns_valid_labels():
    """Metal model returns labels in {0,1,2} with matching length."""
    from src.phase_detector import _ml_predict
    df = _make_df([4.0, 4.1, 3.9, 4.0, 3.8, 4.0, 4.1, 2.5, 2.4, 2.5, 2.4, 2.5, 2.3, 2.4, 2.5])
    preds, confs = _ml_predict(df, 'metal')
    assert len(preds) == len(df)
    assert set(preds.tolist()).issubset({0, 1, 2})
    assert all(0.0 <= c <= 1.0 for c in confs)


def test_update_phase_tags_metal_path():
    """Full update_phase_tags pipeline with Metal classification."""
    from src.phase_detector import update_phase_tags
    df = _make_df([4.0, 4.1, 3.9, 4.0, 3.8, 4.0, 4.1, 2.5, 2.4, 2.5, 2.4, 2.5, 2.3, 2.4, 2.5])
    df['Tag'] = 'unknown'
    out = update_phase_tags(df, 'Metal')
    assert 'phase_confidence' in out.columns
    valid_tags = {'phase1', 'transition', 'phase2'}
    assert set(out['Tag'].unique()).issubset(valid_tags)


def test_update_phase_tags_short_sample_fallback():
    """n<8 peaks → fallback heuristic, no transition rows."""
    from src.phase_detector import update_phase_tags
    df = _make_df([4.0, 4.0, 4.0, 2.5, 2.5, 2.5])
    out = update_phase_tags(df, 'GGA')
    assert (out['Tag'] == 'transition').sum() == 0
    assert (out['Tag'] == 'phase1').sum() == 3
    assert (out['Tag'] == 'phase2').sum() == 3
