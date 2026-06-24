"""
Per-peak feature engineering for phase boundary detection.
Input columns: ['No.peak', 'Doin (mV)', 'DOmin (mV)', 'DDO (mV)']
Output: DataFrame with 16 numeric features, one row per peak, same order.
"""
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    'DDO', 'Doin', 'DOmin', 'peak_idx', 'position_norm',
    'DDO_delta_prev', 'DDO_delta_next', 'peak_spacing_prev',
    'rolling_mean_DDO', 'rolling_std_DDO', 'local_trend_slope',
    'cum_var_from_start', 'dist_to_global_mean', 'cum_drift',
    'total_peaks', 'signal_DDO_range',
]


def compute_peak_features(peaks_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-peak features for phase classification.
    Robust to short sequences (n<3): zeros where stats undefined.
    """
    n = len(peaks_df)
    if n == 0:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    ddo = peaks_df['DDO (mV)'].to_numpy(dtype=float)
    doin = peaks_df['Doin (mV)'].to_numpy(dtype=float)
    domin = peaks_df['DOmin (mV)'].to_numpy(dtype=float)
    pos = peaks_df['No.peak'].to_numpy(dtype=float)

    idx = np.arange(n)
    position_norm = idx / max(n - 1, 1)  # 0..1
    global_mean = float(np.nanmean(ddo)) if n > 0 else 0.0
    signal_range = float(np.nanmax(ddo) - np.nanmin(ddo)) if n > 0 else 0.0

    delta_prev = np.zeros(n)
    delta_next = np.zeros(n)
    spacing_prev = np.zeros(n)
    if n > 1:
        delta_prev[1:] = ddo[1:] - ddo[:-1]
        delta_next[:-1] = ddo[1:] - ddo[:-1]
        spacing_prev[1:] = pos[1:] - pos[:-1]

    # Rolling stats over window +/-2 (5 points centered)
    rolling_mean = np.zeros(n)
    rolling_std = np.zeros(n)
    local_slope = np.zeros(n)
    for i in range(n):
        lo, hi = max(0, i - 2), min(n, i + 3)
        window = ddo[lo:hi]
        rolling_mean[i] = float(np.mean(window))
        rolling_std[i] = float(np.std(window)) if len(window) > 1 else 0.0
        if len(window) > 1:
            x = np.arange(len(window), dtype=float)
            slope = float(np.polyfit(x, window, 1)[0])
            local_slope[i] = slope

    cum_var = np.zeros(n)
    for i in range(n):
        if i >= 1:
            cum_var[i] = float(np.var(ddo[: i + 1]))

    dist_to_mean = np.abs(ddo - global_mean)
    cum_drift = np.cumsum(np.abs(delta_prev))

    out = pd.DataFrame({
        'DDO': ddo,
        'Doin': doin,
        'DOmin': domin,
        'peak_idx': idx,
        'position_norm': position_norm,
        'DDO_delta_prev': delta_prev,
        'DDO_delta_next': delta_next,
        'peak_spacing_prev': spacing_prev,
        'rolling_mean_DDO': rolling_mean,
        'rolling_std_DDO': rolling_std,
        'local_trend_slope': local_slope,
        'cum_var_from_start': cum_var,
        'dist_to_global_mean': dist_to_mean,
        'cum_drift': cum_drift,
        'total_peaks': np.full(n, n, dtype=float),
        'signal_DDO_range': np.full(n, signal_range, dtype=float),
    })
    return out
