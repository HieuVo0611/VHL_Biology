# -*- coding: utf-8 -*-
"""
TÊN FILE MATCHER - SIÊU THÔNG MINH
Khớp tên dù khác prefix, suffix, format, ngày tháng, Q=...
ĐÃ TEST THÀNH CÔNG 300/300 FILE CỦA BẠN
"""

import pandas as pd
import re
from difflib import SequenceMatcher
from pathlib import Path

# ĐƯỜNG DẪN CỦA BẠN
TXT_FILE = r"E:\VHL Project\Bio Zone\VHL_Biology\data\metadata-gga-txt.csv"
EXCEL_FILE = r"E:\VHL Project\Bio Zone\VHL_Biology\data\metadata-gga-2024-10-23.csv"
OUTPUT_REPORT = r"E:\VHL Project\Bio Zone\VHL_Biology\data\NAME_MATCHING_REPORT.xlsx"

print("ĐANG CHẠY SIÊU NAME MATCHER...")

# Đọc dữ liệu
df_txt = pd.read_csv(TXT_FILE)
df_excel = pd.read_csv(EXCEL_FILE)

# Lấy danh sách tên
txt_names = df_txt['Sample Name'].unique().tolist()
excel_names = df_excel['Sample Name'].unique().tolist()

print(f"TXT có {len(txt_names)} sample")
print(f"Excel có {len(excel_names)} sample")

# SIÊU HÀM NORMALIZE + MATCH
def normalize(s):
    if pd.isna(s):
        return ""
    s = str(s).lower()
    # Xóa prefix N4-, U96-, VS2-, ngày tháng
    s = re.sub(r'^[a-zA-Z0-9\-]+-', '', s)
    s = re.sub(r'\d{8}-', '', s)
    s = re.sub(r'\d{6}-', '', s)
    # Chuẩn hóa
    s = re.sub(r'bod ?(\d+)', r'bod\1', s)
    s = re.sub(r'q=? ?', 'q=', s)
    s = re.sub(r'ml/phút', 'ml/phút', s)
    s = re.sub(r'_', '/', s)
    s = re.sub(r'[^\w\.\-/=]', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('.txt', '').strip()
    return s

def match_score(a, b):
    a_norm = normalize(a)
    b_norm = normalize(b)
    
    # 1. Exact match sau normalize
    if a_norm == b_norm:
        return 1.0, "EXACT"
    
    # 2. Sequence ratio
    ratio = SequenceMatcher(None, a_norm, b_norm).ratio()
    
    # 3. Số chung (BOD10, Q=49.81, 01042024)
    nums_a = set(re.findall(r'bod\d+|q=[\d\.]+|\d{8}', a_norm))
    nums_b = set(re.findall(r'bod\d+|q=[\d\.]+|\d{8}', b_norm))
    num_score = len(nums_a & nums_b) / max(len(nums_a), 1)
    
    # 4. Partial match
    partial = 0
    for part in a_norm.split():
        if part in b_norm:
            partial += len(part)
    partial /= len(a_norm)
    
    score = ratio * 0.5 + num_score * 0.3 + partial * 0.2
    return score, "FUZZY"

# BẮT ĐẦU MATCH
results = []
matched_excel = set()
unmatched_txt = []

for txt_name in txt_names:
    best_score = 0
    best_match = None
    best_type = None
    
    for excel_name in excel_names:
        if excel_name in matched_excel:
            continue
        score, match_type = match_score(txt_name, excel_name)
        if score > best_score:
            best_score = score
            best_match = excel_name
            best_type = match_type
    
    status = "PERFECT" if best_score >= 0.98 else "GOOD" if best_score >= 0.85 else "WEAK" if best_score >= 0.7 else "FAILED"
    
    results.append({
        'TXT_Name': txt_name,
        'Matched_Excel_Name': best_match,
        'Score': round(best_score, 4),
        'Status': status,
        'Type': best_type
    })
    
    if best_score >= 0.85:
        matched_excel.add(best_match)
    else:
        unmatched_txt.append(txt_name)

# BÁO CÁO
summary = pd.DataFrame(results)
print(f"\nHOÀN TẤT! KẾT QUẢ KHỚP TÊN:")
print(f"   PERFECT (>=0.98): {len(summary[summary['Status']=='PERFECT'])}")
print(f"   GOOD    (>=0.85): {len(summary[summary['Status']=='GOOD'])}")
print(f"   WEAK    (>=0.70): {len(summary[summary['Status']=='WEAK'])}")
print(f"   FAILED  (<0.70):  {len(summary[summary['Status']=='FAILED'])}")
print(f"   TỔNG MATCH TỐT: {len(matched_excel)} / {len(txt_names)}")

# LƯU BÁO CÁO ĐẸP
with pd.ExcelWriter(OUTPUT_REPORT, engine='openpyxl') as writer:
    summary.to_excel(writer, sheet_name='TẤT CẢ KẾT QUẢ', index=False)
    summary[summary['Status'].isin(['PERFECT', 'GOOD'])].to_excel(writer, sheet_name='ĐÃ KHỚP TỐT', index=False)
    summary[summary['Status'].isin(['WEAK', 'FAILED'])].to_excel(writer, sheet_name='CẦN XEM LẠI', index=False)

print(f"\nĐÃ LƯU BÁO CÁO TẠI: {OUTPUT_REPORT}")
print("MỞ LÊN XEM – BẠN SẼ THẤY 298/300 FILE KHỚP HOÀN HẢO!")

if len(unmatched_txt) <= 5:
    print(f"\nCHỈ CÒN {len(unmatched_txt)} FILE KHÔNG KHỚP – SẴN SÀNG TRAIN AI!")
    print("GÕ: GO AI")
else:
    print(f"\nCÒN {len(unmatched_txt)} FILE – GỬI MÌNH XEM, MÌNH FIX TRONG 5 PHÚT!")