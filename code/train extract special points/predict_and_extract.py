# predict_and_extract.py
import pandas as pd
import numpy as np
import xgboost as xgb
import os

TXT_CSV = r"E:\VHL Project\Bio Zone\VHL_Biology\data\metadata-gga-txt_1 sample.csv"
OUTPUT_EXCEL = r"E:\VHL Project\Bio Zone\VHL_Biology\data\SPECIAL_POINTS_EXTRACTED.xlsx"

# Load 2 model
model_start = xgb.Booster(); model_start.load_model('bod_model_start.json')
model_interval = xgb.Booster(); model_interval.load_model('bod_model_interval.json')

def extract_features(do):
    do = do[:2000]
    return np.array([
        np.mean(do[:1000]), np.std(do[:1000]),
        np.mean(do[1000:]), np.std(do[1000:]),
        *np.percentile(do, [10,50,90])
    ], dtype=float)

df = pd.read_csv(TXT_CSV)
results = []

for name in df['Sample Name'].unique():
    seg = df[df['Sample Name'] == name]
    do = seg['DO'].values
    if len(do) < 1000: continue

    feat = extract_features(do)
    dfeat = xgb.DMatrix(feat.reshape(1, -1))
    start = max(int(model_start.predict(dfeat)[0]), 50)
    interval = max(int(model_interval.predict(dfeat)[0]), 400)

    records = []
    t = start
    count = 0
    while t + 200 < len(do) and count < 25:
        do_in = do[t-1]
        do_min = do[t:t+200].min()
        ddo = do_in - do_min
        # BỎ FILTER ddo < 1.0 → giữ hết
        records.append({
            'No.peak': t, 'Tag': 'BOD10' if count<8 else 'BOD5',
            'Doin (mV)': round(do_in,5), 'DOmin (mV)': round(do_min,5),
            'DDO (mV)': round(ddo,5), 'Sample Name': name.replace('.txt','')
        })
        t += interval
        count += 1
    if len(records) >= 8:  # Chỉ giữ nếu đủ BOD10
        results.append(pd.DataFrame(records))

final = pd.concat(results, ignore_index=True)
final.to_excel(OUTPUT_EXCEL, index=False)
print(f"HOÀN TẤT! XUẤT {len(final)} ĐIỂM")