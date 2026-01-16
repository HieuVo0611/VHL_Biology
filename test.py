import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from itertools import groupby
from operator import itemgetter

# Bước 1: Load file .txt (space-separated, no header)
file_path = r'E:\VHL Project\Bio Zone\VHL_Biology\data\GGA\File txt\N4-VS1-25-03-2024\5-0\N4-5-0-29032024-Q=50.19mL_phút-1.txt'  # Thay bằng tên file thật của bạn
df = pd.read_csv(file_path, sep='\t', header=None, names=['time', 'DO'], encoding='utf-16')

do_smooth = savgol_filter(df['DO'].values, window_length=21, polyorder=3)
diff = np.diff(do_smooth)

def detect_drops(threshold, min_group_len=3, start_idx=0):
    fall_indices = np.where(diff[start_idx:] < threshold)[0] + start_idx + 1
    groups = []
    for k, g in groupby(enumerate(fall_indices), lambda x: x[0] - x[1]):
        group = list(map(itemgetter(1), g))
        if len(group) >= min_group_len:
            mean_pos = int(np.mean(group))
            window = do_smooth[max(0, mean_pos-30):mean_pos+30]
            exact_min_idx = np.argmin(window) + max(0, mean_pos-30)
            groups.append(exact_min_idx)
    return np.array(groups)

# Detect BOD5 và BOD0 (giữ nguyên phần đã ổn)
bod5_points = detect_drops(-0.3, min_group_len=4)
valid_points = []
for i, p in enumerate(bod5_points):
    do_min = do_smooth[p]
    prev_p = 0 if i == 0 else valid_points[-1] if valid_points else bod5_points[i-1]
    segment = do_smooth[prev_p:p]
    do_in_temp = np.max(segment)
    ddo_temp = do_in_temp - do_min
    if ddo_temp <= 6 and do_min >= 272:
        valid_points.append(p)
bod5_points = np.array(valid_points)

if len(bod5_points) > 0:
    start_after_bod5 = bod5_points[-1]
    bod0_points = detect_drops(-0.2, min_group_len=3, start_idx=start_after_bod5)
else:
    bod0_points = np.array([])

all_points = np.concatenate([bod5_points, bod0_points]) if len(bod0_points) > 0 else bod5_points

print("Final detected DOmin positions:", df['time'].iloc[all_points].values)

# === PHẦN MỚI: Tính Doin bằng mean của plateau ổn định ===
data = []
sample_name = "29032024-BOD-5-0-Q=50.19mL/phút-1"

prev_p = 0
for i, curr_p in enumerate(all_points):
    do_min = do_smooth[curr_p]
    no_peak = df['time'].iloc[curr_p]
    tag = "BOD5" if i < 7 else "BOD0"
    
    # Đoạn plateau đầu cycle: 120 điểm đầu sau DOmin (đủ để ổn định)
    plateau_start = curr_p
    plateau_end = min(curr_p + 120, len(do_smooth))
    plateau_segment = do_smooth[plateau_start:plateau_end]
    
    if len(plateau_segment) < 30:
        # Cycle cuối hoặc ngắn: dùng mean toàn bộ
        do_in = np.mean(plateau_segment)
    else:
        # Tìm cửa sổ 30 điểm có std nhỏ nhất (ổn định nhất)
        stds = []
        for j in range(len(plateau_segment) - 30 + 1):
            window = plateau_segment[j:j+30]
            stds.append(np.std(window))
        best_idx = np.argmin(stds)
        stable_window = plateau_segment[best_idx:best_idx+30]
        do_in = np.mean(stable_window)
    
    ddo = do_in - do_min
    
    data.append([no_peak, tag, round(do_in, 5), round(do_min, 5), round(ddo, 5), sample_name])
    
    prev_p = curr_p

# Output
output_df = pd.DataFrame(data, columns=["No.peak", "Tag", "Doin (mV)", "DOmin (mV)", "DDO (mV)", "Sample Name"])
print(output_df.to_string(index=False))
output_df.to_csv('special_points_plateau_mean.csv', index=False)