import numpy as np
import pandas as pd
import pytest
from src.phase_features import compute_peak_features

def test_compute_peak_features_shape():
    """Returns DataFrame with one row per peak and expected columns."""
    df = pd.DataFrame({
        'No.peak': [100, 500, 900, 1300, 1700, 2100, 2500, 2900],
        'Doin (mV)': [260.0] * 8,
        'DOmin (mV)': [256.0] * 8,
        'DDO (mV)': [4.0, 4.1, 3.9, 4.0, 3.8, 2.5, 2.4, 2.5],
    })
    feats = compute_peak_features(df)
    assert len(feats) == 8
    expected_cols = {
        'DDO', 'Doin', 'DOmin', 'peak_idx', 'position_norm',
        'DDO_delta_prev', 'DDO_delta_next', 'peak_spacing_prev',
        'rolling_mean_DDO', 'rolling_std_DDO', 'local_trend_slope',
        'cum_var_from_start', 'dist_to_global_mean', 'cum_drift',
        'total_peaks', 'signal_DDO_range',
    }
    assert expected_cols.issubset(set(feats.columns))

def test_position_norm_first_and_last():
    df = pd.DataFrame({
        'No.peak': [100, 500, 900],
        'Doin (mV)': [260.0, 260.0, 260.0],
        'DOmin (mV)': [256.0, 256.0, 256.0],
        'DDO (mV)': [4.0, 4.0, 4.0],
    })
    feats = compute_peak_features(df)
    assert feats['position_norm'].iloc[0] == 0.0
    assert feats['position_norm'].iloc[-1] == 1.0

def test_ddo_delta_prev_first_is_zero():
    df = pd.DataFrame({
        'No.peak': [100, 500, 900],
        'Doin (mV)': [260.0, 260.0, 260.0],
        'DOmin (mV)': [256.0, 256.0, 256.0],
        'DDO (mV)': [4.0, 3.5, 3.0],
    })
    feats = compute_peak_features(df)
    assert feats['DDO_delta_prev'].iloc[0] == 0.0
    assert abs(feats['DDO_delta_prev'].iloc[1] - (-0.5)) < 1e-9
