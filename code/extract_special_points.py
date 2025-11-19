# extract_special_points.py - PHIÊN BẢN CHUẨN 100%
import pandas as pd
import numpy as np
import os

TXT_CSV = r"E:\VHL Project\Bio Zone\VHL_Biology\data\metadata-gga-txt_1 sample.csv"
OUTPUT_EXCEL = r"E:\VHL Project\Bio Zone\VHL_Biology\data\SPECIAL_POINTS_EXTRACTED.xlsx"

if not os.path.exists(TXT_CSV):
    raise FileNotFoundError(f"KHÔNG TÌM THẤY FILE: {TXT_CSV}")

df = pd.read_csv(TXT_CSV)
print(f"ĐÃ LOAD {len(df['Sample Name'].unique())} SAMPLE")

results = []

for name in df['Sample Name'].unique():
    seg = df[df['Sample Name'] == name]
    do = seg['DO'].values
    if len(do) < 2000:
        print(f"SKIP {name}: quá ngắn")
        continue

    # 1. TÌM START: ĐIỂM DO CAO NHẤT TRONG [100:400]
    start_win = do[100:400]
    start_offset = np.argmax(start_win)
    start = 100 + start_offset  # 301

    # 2. INTERVAL CỐ ĐỊNH = 476
    interval = 476

    # 3. TRÍCH ĐIỂM
    records = []
    t = start
    count = 0
    while t + 150 < len(do) and count < 25:
        do_in = do[t]  # ĐÚNG: do[t]
        seg_win = do[t+1:t+151]  # ĐÚNG: 150 điểm sau
        do_min = seg_win.min()
        ddo = do_in - do_min
        records.append({
            'No.peak': t,
            'Tag': 'BOD10' if count < 8 else 'BOD5',
            'Doin (mV)': round(do_in, 5),
            'DOmin (mV)': round(do_min, 5),
            'DDO (mV)': round(ddo, 5),
            'Sample Name': name.replace('.txt', '')
        })
        t += interval
        count += 1

    if records:
        results.append(pd.DataFrame(records))
        print(f"EXTRACTED {len(records)} points từ {name}")

if not results:
    print("KHÔNG TRÍCH XUẤT ĐƯỢC ĐIỂM NÀO! KIỂM TRA DỮ LIỆU.")
else:
    final = pd.concat(results, ignore_index=True)
    final.to_excel(OUTPUT_EXCEL, index=False)
    print(f"HOÀN TẤT! XUẤT {len(final)} ĐIỂM → {OUTPUT_EXCEL}")