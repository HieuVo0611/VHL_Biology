"""
Benchmark script: runs 518 labeled samples (GGA + GGA-metal) through full pipeline.
Measures per-step timing and collects classification + phase detection results.
Output: plans/reports/benchmark-260622-full-518.xlsx
"""
import sys, os, time
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import extract_peaks_from_txt, catboost_inference_from_csv
from src.phase_detector import update_phase_tags

MODEL_PATH         = "model/catboost_model.cbm"
LABEL_ENCODER_PATH = "model/label_encoder_classes.npy"
GGA_DIR            = "data/GGA/File txt"
METAL_DIR          = "data/GGA-metal/File txt"
OUTPUT_PATH        = "plans/reports/benchmark-260622-full-518.xlsx"


def find_txt_files(base_dir):
    """Recursively find all .txt files under base_dir."""
    results = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith(".txt"):
                results.append(os.path.join(root, f))
    return sorted(results)


def run_benchmark():
    gga_files   = [(f, "gga")       for f in find_txt_files(GGA_DIR)]
    metal_files = [(f, "gga-metal") for f in find_txt_files(METAL_DIR)]
    all_files   = gga_files + metal_files
    print(f"Found {len(gga_files)} GGA + {len(metal_files)} GGA-metal = {len(all_files)} total\n")

    records = []
    for fpath, true_label in tqdm(all_files, desc="Benchmarking"):
        sample_name = os.path.basename(fpath).replace(".txt", "")
        rec = dict(
            sample_name=sample_name, true_label=true_label,
            pred_label="", correct=False, confidence_pct=0.0,
            n_peaks=0, n_phase1=0, n_transition=0, n_phase2=0,
            t_extract=0.0, t_classify=0.0, t_phase=0.0, t_total=0.0,
            error_msg="",
        )
        t_start = time.time()
        try:
            # Step 1: extract peaks
            t0 = time.time()
            peaks_df = extract_peaks_from_txt(fpath)
            rec["t_extract"] = round(time.time() - t0, 3)
            rec["n_peaks"]   = len(peaks_df)

            if len(peaks_df) == 0:
                rec["error_msg"] = "0 peaks extracted"
                rec["t_total"]   = round(time.time() - t_start, 3)
                records.append(rec)
                continue

            # Step 2: classify
            t0 = time.time()
            preds = catboost_inference_from_csv(peaks_df, MODEL_PATH, LABEL_ENCODER_PATH)
            _, pred_label, pred_proba = preds[0]
            pred_label = str(pred_label).strip().lower()
            rec["t_classify"]     = round(time.time() - t0, 3)
            rec["pred_label"]     = pred_label
            rec["correct"]        = (pred_label == true_label)
            rec["confidence_pct"] = round(max(pred_proba) * 100, 1)

            # Step 3: phase detection
            t0 = time.time()
            peaks_df = update_phase_tags(peaks_df, pred_label)
            rec["t_phase"] = round(time.time() - t0, 3)

            tag_counts        = peaks_df["Tag"].str.strip().value_counts()
            rec["n_phase1"]     = int(tag_counts.get("phase1",     0))
            rec["n_transition"] = int(tag_counts.get("transition", 0))
            rec["n_phase2"]     = int(tag_counts.get("phase2",     0))

        except Exception as e:
            rec["error_msg"] = str(e)[:120]

        rec["t_total"] = round(time.time() - t_start, 3)
        records.append(rec)

    return records


if __name__ == "__main__":
    records = run_benchmark()
    print(f"\nCollected {len(records)} records")
    for r in records[:3]:
        print(r)
