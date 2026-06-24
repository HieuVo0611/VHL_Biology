"""
Adaptive Peak Extractor — production module for DO signal peak extraction.

Extracts DOin, DOmin, DDO from raw dissolved oxygen time-series signals.
Uses two-pass HH detection + bias correction (+0.05mV non-HH, +0.04mV HH).

Tuned over 485+ configurations. See MEMORY.md for accuracy benchmarks.

Input:  Raw DO array + Time array (from UTF-16 TXT files)
Output: DataFrame [No.peak, Tag, Doin (mV), DOmin (mV), DDO (mV), Sample Name]
"""

import numpy as np
import pandas as pd
from scipy import signal
from scipy.ndimage import uniform_filter1d


# ── Cycle Length Detection ───────────────────────────────────────────────────

def detect_cycle_length(DO, min_samples=100, max_samples=1000):
    """Auto-detect cycle length via autocorrelation, FFT fallback."""
    n = min(len(DO), 10000)
    y = DO[:n]
    y = (y - np.mean(y)) / (np.std(y) + 1e-8)

    autocorr = np.correlate(y, y, mode='full')
    autocorr = autocorr[len(autocorr) // 2:]
    autocorr = autocorr / autocorr[0]

    search_start = min_samples
    search_end = min(max_samples, len(autocorr) - 1)

    if search_end <= search_start:
        return 476

    search_region = autocorr[search_start:search_end]
    peaks, _ = signal.find_peaks(search_region, height=0.1, distance=50)

    if len(peaks) == 0:
        return _detect_cycle_fft(DO, min_samples, max_samples)

    return int(peaks[0] + search_start)


def _detect_cycle_fft(DO, min_samples=100, max_samples=1000):
    """Detect cycle length using FFT (fallback)."""
    n = min(len(DO), 10000)
    y_detrend = signal.detrend(DO[:n])

    fft_vals = np.abs(np.fft.rfft(y_detrend))
    freqs = np.fft.rfftfreq(len(y_detrend))

    min_freq = 1 / max_samples
    max_freq = 1 / min_samples
    valid_mask = (freqs >= min_freq) & (freqs <= max_freq)

    if not valid_mask.any():
        return 476

    fft_copy = fft_vals.copy()
    fft_copy[~valid_mask] = 0

    dominant_idx = np.argmax(fft_copy)
    if freqs[dominant_idx] > 0:
        return int(1 / freqs[dominant_idx])
    return 476


# ── Signal Classification ────────────────────────────────────────────────────

def classify_signal_type(DO):
    """Classify signal variance level for parameter selection."""
    std = np.std(DO)
    range_val = np.percentile(DO, 99) - np.percentile(DO, 1)

    if std < 5 and range_val < 20:
        return 'low_variance'
    elif std > 10 or range_val > 50:
        return 'high_variance'
    else:
        return 'medium_variance'


def detect_hh_type_from_ddo(ddo_values, signal_range):
    """
    Robust HH-type detection using DDO statistics.
    Returns (confidence, is_hh_type).
    HH signals have DDO P90 > 12mV and max > 20mV.
    """
    if len(ddo_values) < 5:
        return 0.0, False

    ddo_p50 = np.median(ddo_values)
    ddo_p90 = np.percentile(ddo_values, 90)
    ddo_p95 = np.percentile(ddo_values, 95)
    ddo_max = np.max(ddo_values)

    if ddo_p90 < 12.0 or ddo_max < 20.0:
        return 0.0, False

    p90_score = min(1.0, max(0.0, (ddo_p90 - 12) / 20))
    max_score = min(1.0, max(0.0, (ddo_max - 20) / 30))
    spread_score = 0.0
    if ddo_p95 > 15:
        spread_ratio = ddo_p95 / (ddo_p50 + 0.1)
        spread_score = min(1.0, max(0.0, (spread_ratio - 3) / 5))
    sr_score = min(1.0, max(0.0, (signal_range - 20) / 30))

    confidence = p90_score * 0.40 + max_score * 0.30 + spread_score * 0.15 + sr_score * 0.15
    return confidence, confidence > 0.35


# ── Normalization ────────────────────────────────────────────────────────────

def normalize_signal(DO):
    """Normalize signal to 0-100 range (robust to outliers)."""
    min_val = np.percentile(DO, 1)
    max_val = np.percentile(DO, 99)
    range_val = max_val - min_val
    if range_val < 1e-6:
        range_val = 1.0
    normalized = (DO - min_val) / range_val * 100
    return normalized, {'min': min_val, 'max': max_val, 'range': range_val}


# ── Minima Detection ────────────────────────────────────────────────────────

def find_minima_adaptive(DO, cycle_length=None, min_height_pct=2.0,
                         signal_range=None, is_hh_type=None):
    """
    Find cycle minima using local prominence filtering.
    For HH signals: pre-filters to bottom 25% of robust range.
    """
    if cycle_length is None:
        cycle_length = 300

    DO_smooth = uniform_filter1d(DO, size=7)

    if is_hh_type is None:
        is_hh_type = signal_range is not None and signal_range > 40

    # Find all potential minima
    minima, _ = signal.find_peaks(-DO_smooth, distance=50)
    if len(minima) == 0:
        return []

    # HH pre-filter: keep only minima in bottom portion
    if is_hh_type:
        q5 = np.percentile(DO, 5)
        q95 = np.percentile(DO, 95)
        robust_range = q95 - q5
        minima_threshold = q5 + robust_range * 0.25
        minima = [m for m in minima if DO[m] < minima_threshold]
        if len(minima) == 0:
            return []

    # Filter using local prominence
    filtered_minima = []
    for min_pos in minima:
        start = max(0, min_pos - 500)
        end = min(len(DO), min_pos + 500)
        local_range = DO_smooth[start:end].max() - DO_smooth[start:end].min()

        if local_range < 0.5:
            continue

        pre_max = DO_smooth[max(0, min_pos - 200):min_pos].max() if min_pos > 0 else DO_smooth[min_pos]
        post_max = DO_smooth[min_pos:min(len(DO), min_pos + 200)].max()
        drop = max(pre_max, post_max) - DO_smooth[min_pos]

        if is_hh_type:
            min_drop = max(local_range * (min_height_pct / 100), robust_range * 0.3)
        else:
            min_drop = max(local_range * (min_height_pct / 100), 1.0)

        if drop >= min_drop:
            # Refine position in raw signal
            s = max(0, min_pos - 10)
            e = min(len(DO), min_pos + 11)
            filtered_minima.append(s + np.argmin(DO[s:e]))

    # Merge nearby minima (within 30 samples)
    merged = []
    i = 0
    while i < len(filtered_minima):
        group = [filtered_minima[i]]
        while i + 1 < len(filtered_minima) and filtered_minima[i + 1] - filtered_minima[i] < 30:
            i += 1
            group.append(filtered_minima[i])
        merged.append(min(group, key=lambda x: DO[x]))
        i += 1

    return merged


# ── Plateau (DOin) Detection ────────────────────────────────────────────────

def find_plateau_adaptive(DO, min_pos, prev_min, cycle_length, norm_params,
                          signal_range=None, is_hh_type=None):
    """
    Find plateau (Doin) value — the stable high region before the drop.
    Applies bias correction: +0.04 HH, +0.05 non-HH.
    """
    if is_hh_type is None:
        is_hh_type = signal_range is not None and signal_range > 40

    # Constrain search region
    if prev_min > 0:
        lookback_ratio = 0.50 if is_hh_type else 0.75
        max_lookback = int((min_pos - prev_min) * lookback_ratio)
        search_start = max(prev_min + 20, min_pos - max_lookback)
    else:
        search_start = max(30, min_pos - 150)

    search_end = min_pos - 5
    if search_end <= search_start + 10:
        return np.nan

    # Gradient for drop detection
    smooth_size = 7 if is_hh_type else 11
    DO_smooth = uniform_filter1d(DO, size=smooth_size)
    d1 = np.gradient(DO_smooth)

    # Separate smoothing for Doin value estimation
    doin_smooth_size = 21 if is_hh_type else 19
    DO_doin_smooth = uniform_filter1d(DO, size=doin_smooth_size)

    search_vals = DO[search_start:search_end]
    if len(search_vals) == 0:
        return np.nan

    val_range = np.percentile(search_vals, 95) - np.percentile(search_vals, 5)
    if val_range < 0.1:
        return np.mean(search_vals)

    # Find drop start point
    gradient_threshold = val_range * (0.010 if is_hh_type else 0.012)
    drop_start = search_end
    for j in range(search_end - 3, search_start, -1):
        if j >= len(d1):
            continue
        if d1[j] > -gradient_threshold:
            drop_start = j
            break

    # Safety margin
    drop_start = max(search_start + 5, drop_start - 5)

    # Plateau window
    plateau_window = 90 if is_hh_type else 60
    plateau_search_end = min(drop_start - 3, search_end - 5)
    plateau_search_start = max(search_start, plateau_search_end - plateau_window)

    if plateau_search_end <= plateau_search_start + 5:
        plateau_search_start = max(search_start, search_end - 40)
        plateau_search_end = search_end - 3

    # Collect stable values
    stability_threshold = val_range * 0.012
    stable_vals = []
    for j in range(plateau_search_end, plateau_search_start, -1):
        if j >= len(d1):
            continue
        if abs(d1[j]) < stability_threshold:
            stable_vals.append(DO_doin_smooth[j])
            if len(stable_vals) >= 40:
                break

    # IQR filtering
    if len(stable_vals) >= 10:
        sv_arr = np.array(stable_vals)
        q1, q3 = np.percentile(sv_arr, 25), np.percentile(sv_arr, 75)
        iqr = q3 - q1
        mask = (sv_arr >= q1 - 1.5 * iqr) & (sv_arr <= q3 + 1.5 * iqr)
        if np.sum(mask) >= 5:
            stable_vals = sv_arr[mask].tolist()

    if len(stable_vals) >= 5:
        if is_hh_type and len(stable_vals) >= 10:
            # Weighted average with upward bias for HH
            weights = np.linspace(1.5, 0.5, len(stable_vals))
            return np.average(stable_vals, weights=weights) + 0.04
        else:
            # DDO-adaptive percentile + 0.05 bias correction
            non_hh_bias = 0.05
            if val_range > 20:
                return np.percentile(stable_vals, 65) + non_hh_bias
            elif val_range > 10:
                return np.percentile(stable_vals, 60) + non_hh_bias
            elif val_range > 5:
                return np.percentile(stable_vals, 55) + non_hh_bias
            else:
                return np.median(stable_vals) + non_hh_bias

    # Fallback paths
    fallback_bias = 0.0 if is_hh_type else 0.05
    plateau_vals = DO[plateau_search_start:plateau_search_end]
    if len(plateau_vals) > 0:
        max_idx = np.argmax(plateau_vals)
        window_half = 15 if is_hh_type else 10
        ws = max(0, max_idx - window_half)
        we = min(len(plateau_vals), max_idx + window_half + 1)
        window = plateau_vals[ws:we]
        if len(window) >= 3:
            return np.median(window) + fallback_bias
        return np.percentile(plateau_vals, 70) + fallback_bias

    return np.percentile(search_vals, 65) + fallback_bias


# ── Main Extraction Orchestrator ─────────────────────────────────────────────

def extract_peaks_adaptive(DO_raw, Time=None, sample_name=""):
    """
    Extract peaks from a single DO signal using two-pass HH detection.

    Pass 1: Extract with non-HH params → compute DDO stats
    Pass 2: If HH detected, re-extract with HH params

    Args:
        DO_raw: Raw DO signal array
        Time: Time array (optional, for position indexing)
        sample_name: Sample identifier string

    Returns:
        DataFrame [No.peak, Tag, Doin (mV), DOmin (mV), DDO (mV), Sample Name]
    """
    DO = np.array(DO_raw, dtype=float)

    if len(DO) < 500:
        return pd.DataFrame(columns=['No.peak', 'Tag', 'Doin (mV)', 'DOmin (mV)',
                                     'DDO (mV)', 'Sample Name'])

    # Remove outliers (sensor errors)
    q1, q3 = np.percentile(DO, [5, 95])
    iqr = q3 - q1
    outlier_mask = (DO < q1 - 3 * iqr) | (DO > q3 + 3 * iqr)
    if outlier_mask.any():
        valid_idx = np.where(~outlier_mask)[0]
        outlier_idx = np.where(outlier_mask)[0]
        if len(valid_idx) > 0:
            DO[outlier_idx] = np.interp(outlier_idx, valid_idx, DO[valid_idx])

    # Signal classification and parameters
    signal_type = classify_signal_type(DO)
    signal_range = np.percentile(DO, 95) - np.percentile(DO, 5)

    if signal_type == 'low_variance':
        min_height_pct = 2.0
        use_normalization = False
    elif signal_type == 'high_variance':
        expected_ddo = 5.0
        min_height_pct = max(0.5, min((expected_ddo / signal_range) * 100 * 0.5, 4.0))
        use_normalization = True
    else:
        min_height_pct = 2.0
        use_normalization = True

    cycle_length = detect_cycle_length(DO)

    # Normalize if needed
    if use_normalization:
        DO_work, norm_params = normalize_signal(DO)
    else:
        norm_params = {'min': DO.min(), 'max': DO.max(), 'range': DO.max() - DO.min()}
        if norm_params['range'] > 0:
            DO_work = (DO - norm_params['min']) / norm_params['range'] * 100
        else:
            DO_work = DO

    def _extract_with_hh_flag(is_hh_type):
        """Extract peaks with given HH type flag."""
        minima = find_minima_adaptive(DO_work, cycle_length, min_height_pct,
                                      signal_range, is_hh_type)
        if len(minima) < 2:
            minima = find_minima_adaptive(DO_work, cycle_length, min_height_pct * 0.5,
                                          signal_range, is_hh_type)
        if len(minima) < 2:
            return pd.DataFrame()

        results = []
        prev_min = 0
        for i, min_pos in enumerate(minima):
            domin = DO[min_pos]
            doin = find_plateau_adaptive(DO, min_pos, prev_min, cycle_length,
                                         norm_params, signal_range, is_hh_type)
            ddo = doin - domin if not np.isnan(doin) else np.nan
            tag = 'unknown'  # Tag set downstream by phase_detector.update_phase_tags()
            pos = int(Time[min_pos]) if Time is not None and len(Time) > min_pos else min_pos

            results.append({
                'No.peak': pos,
                'Tag': tag,
                'Doin (mV)': round(doin, 4) if not np.isnan(doin) else np.nan,
                'DOmin (mV)': round(domin, 2),
                'DDO (mV)': round(ddo, 5) if not np.isnan(ddo) else np.nan,
                'Sample Name': sample_name,
            })
            prev_min = min_pos

        return pd.DataFrame(results)

    # Pass 1: non-HH
    df = _extract_with_hh_flag(is_hh_type=False)
    if len(df) == 0:
        return df

    # Pass 2: check if HH, re-extract if so
    ddo_values = df['DDO (mV)'].dropna().values
    if len(ddo_values) >= 5:
        _, is_hh_detected = detect_hh_type_from_ddo(ddo_values, signal_range)
        if is_hh_detected:
            df = _extract_with_hh_flag(is_hh_type=True)

    # Filter noise peaks with adaptive DDO threshold
    if len(df) > 0 and 'DDO (mV)' in df.columns:
        ddo_values = df['DDO (mV)'].dropna().values
        if len(ddo_values) > 5:
            ddo_median = np.median(ddo_values)
            ddo_p25 = np.percentile(ddo_values, 25)
            ddo_p90 = np.percentile(ddo_values, 90)
            ddo_p95 = np.percentile(ddo_values, 95)
            ddo_max = np.max(ddo_values)

            has_high_ddo = ddo_p90 > 11.5 or ddo_p95 > 18
            clear_separation = ddo_p95 > ddo_median * 8
            is_hh_by_sr = signal_range > 25
            is_hh_by_ddo = has_high_ddo and ddo_p90 > ddo_median * 5
            is_bimodal = (is_hh_by_sr or is_hh_by_ddo) and clear_separation and has_high_ddo

            if is_bimodal:
                sorted_ddo = np.sort(ddo_values)
                gaps = np.diff(sorted_ddo)
                gap_threshold = ddo_max * 0.15
                significant_gaps = np.where(gaps > gap_threshold)[0]

                if len(significant_gaps) > 0:
                    first_gap_idx = significant_gaps[0]
                    ddo_threshold = max(sorted_ddo[first_gap_idx + 1] * 0.9, ddo_max * 0.2)
                else:
                    ddo_threshold = ddo_max * 0.3
            else:
                ddo_threshold = max(2.0, ddo_p25)

            df = df[df['DDO (mV)'] >= ddo_threshold]

    return df.reset_index(drop=True)
