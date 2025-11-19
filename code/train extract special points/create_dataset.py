# -*- coding: utf-8 -*-
"""
CREATE DATASET - MATCHING SIÊU CHUẨN + FEATURES NÂNG CAO
Output: X.npy (N, 14), y.npy (N, 2) → start, interval
"""

import pandas as pd
import numpy as np
from scipy.signal import find_peaks, welch
import re
from difflib import SequenceMatcher

# ================== ĐƯỜNG DẪN ==================
TXT_CSV = r"E:\VHL Project\Bio Zone\VHL_Biology\data\metadata-gga-txt.csv"
EXCEL_CSV = r"E:\VHL Project\Bio Zone\VHL_Biology\data\metadata-gga-2024-10-23.csv"

# ================== LOAD DATA ==================
df_txt_all = pd.read_csv(TXT_CSV)
df_excel = pd.read_csv(EXCEL_CSV)
excel_names = df_excel['Sample Name'].unique()

# ================== FALLBACK MATCH: Date + Q ==================
def fallback_match(txt_name, excel_names):
    norm_txt = normalize_name(txt_name)
    txt_parts = extract_parts(norm_txt)
    if not txt_parts['date'] or txt_parts['q'] is None:
        return None

    best_match = None
    best_q_diff = float('inf')
    for exc in excel_names:
        norm_exc = normalize_name(exc)
        exc_parts = extract_parts(norm_exc)
        if not exc_parts['date'] or exc_parts['q'] is None:
            continue
        if txt_parts['date'] == exc_parts['date']:
            q_diff = abs(txt_parts['q'] - exc_parts['q'])
            if q_diff < best_q_diff:
                best_q_diff = q_diff
                best_match = exc
                if q_diff <= 0.05:  # Q gần như bằng nhau
                    return best_match
    return best_match  # Trả về nếu cùng ngày, Q gần nhất

# ================== HÀM CHUẨN HÓA TÊN ==================
def normalize_name(name):
    name = re.sub(r'\.txt$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^[A-Z]\d+-', '', name)
    name = re.sub(r'_ph[uú]t', '/phút', name)
    name = re.sub(r'ph[uú]t', '/phút', name)
    name = re.sub(r'Q\s*=\s*', 'Q=', name, flags=re.IGNORECASE)
    name = re.sub(r'BOD-?(\d+)', r'\1', name, flags=re.IGNORECASE)
    name = re.sub(r'BOD', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r',', '.', name)
    name = re.sub(r'mLmin', 'mL/phút', name)
    name = re.sub(r'mLphut', 'mL/phút', name)
    return name

# ================== TRÍCH XUẤT PARTS ==================
def extract_parts(name):
    parts = {}
    date_match = re.search(r'(\d{8})', name)
    parts['date'] = date_match.group(1) if date_match else None
    bod_match = re.search(r'(\d{1,3}[.,]?\d{0,2}-\d{1,3}[.,]?\d{0,2}(-\d{1,3}[.,]?\d{0,2})?)', name)
    parts['bod'] = bod_match.group(1).replace(',', '.') if bod_match else None
    u_match = re.search(r'U(\d+(-H\d+)?(-VS\d+)?)', name)
    parts['u_id'] = u_match.group(1) if u_match else None
    q_match = re.search(r'Q=([\d.,]+)', name)
    parts['q'] = float(q_match.group(1).replace(',', '.')) if q_match else None
    return parts

# ================== SIÊU MATCH ==================
# THAY TOÀN BỘ HÀM super_match BẰNG:
def super_match(txt_name, excel_names, threshold=0.8):
    # 1. Thử match chính (parts đầy đủ)
    norm_txt = normalize_name(txt_name)
    txt_parts = extract_parts(norm_txt)
    best_match = None
    best_score = 0
    for exc in excel_names:
        norm_exc = normalize_name(exc)
        exc_parts = extract_parts(norm_exc)
        if (txt_parts['date'] == exc_parts['date'] and
            txt_parts['bod'] == exc_parts['bod'] and
            txt_parts['u_id'] == exc_parts['u_id']):
            if txt_parts['q'] is not None and exc_parts['q'] is not None:
                q_diff = abs(txt_parts['q'] - exc_parts['q']) / max(txt_parts['q'], exc_parts['q'])
                if q_diff > 0.1:
                    continue
            score = SequenceMatcher(None, norm_txt, norm_exc).ratio()
            if score > threshold and score > best_score:
                best_score = score
                best_match = exc

    # 2. Nếu không match → FALLBACK: Date + Q
    if not best_match:
        best_match = fallback_match(txt_name, excel_names)

    return best_match

# ================== FEATURES NÂNG CAO ==================
def extract_advanced_features(do_series):
    # Normalize DO về [0,1]
    do_min, do_max = do_series.min(), do_series.max()
    do_norm = (do_series - do_min) / (do_max - do_min + 1e-6)

    # FFT trên đoạn đầu
    freqs, psd = welch(do_norm[:1024], fs=1.0, nperseg=512)
    peak_freq = freqs[np.argmax(psd[1:]) + 1] if len(psd) > 1 else 0.002
    period = 1 / peak_freq if peak_freq > 0 else 473

    # Số lần giảm >0.1 (tương đương 2–3mV)
    drops = sum(1 for i in range(0, len(do_series)-100, 100) if do_series[i] - do_series[i+100] > 2.0)

    # Features cơ bản trên đoạn đầu
    base = [
        np.mean(do_series[:1000]), np.std(do_series[:1000]),
        np.mean(do_series[1000:2000]), np.std(do_series[1000:2000]),
        *np.percentile(do_series[:2000], [10, 50, 90]),
        drops, period
    ]
    return np.array(base, dtype=float)

# ================== XÂY DỰNG DATASET ==================
X = []
y = []
skipped = []
matched_log = []
skipped_log = []

print("BẮT ĐẦU XỬ LÝ...")

for sample_name in df_txt_all['Sample Name'].unique():
    # --- MATCHING ---
    matched_excel = super_match(sample_name, excel_names)
    if not matched_excel:
        norm_txt = normalize_name(sample_name)
        closest = max(excel_names, key=lambda e: SequenceMatcher(None, norm_txt, normalize_name(e)).ratio())
        score = SequenceMatcher(None, norm_txt, normalize_name(closest)).ratio()
        skipped_log.append(f"{sample_name} closest to {closest} (score: {score:.2f})")
        skipped.append(sample_name)
        continue

    matched_log.append(f"{sample_name} → {matched_excel}")

    # --- LẤY TRUTH ---
    truth_rows = df_excel[df_excel['Sample Name'] == matched_excel]
    if len(truth_rows) < 7:
        skipped.append(sample_name)
        skipped_log.append(f"{sample_name} matched but len(truth)<7: {len(truth_rows)}")
        continue

    peaks = truth_rows['No.peak'].tolist()
    start = peaks[0]
    interval = np.mean(np.diff(peaks)) if len(peaks) > 1 else 473.0

    # --- FEATURES ---
    segment = df_txt_all[df_txt_all['Sample Name'] == sample_name]
    do_series = segment['DO'].values[:2000]  # CHỈ 2000 ĐIỂM
    if len(do_series) < 1000:
        continue

    features = extract_advanced_features(do_series)
    X.append(features)
    # Trong create_dataset.py
    y.append([start, interval])  # TRẢ LẠI 2 TARGET  # CHỈ start

# ================== LƯU KẾT QUẢ ==================
X = np.array(X)
y = np.array(y)

np.save('X.npy', X)
np.save('y.npy', y)

print(f"HOÀN TẤT! TẠO DATASET TỪ {len(X)} SAMPLE")
print(f"X shape: {X.shape} | y shape: {y.shape}")
print(f"Skipped: {len(skipped)} | Matched: {len(matched_log)}")

with open('matching_log.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(matched_log))
print("LOG MATCHING: matching_log.txt")

with open('skipped_log.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(skipped_log))
print("LOG SKIPPED: skipped_log.txt")