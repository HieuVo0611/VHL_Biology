"""
Batch classification validation script.
Runs full pipeline (TXT → peaks → CatBoost) on all files in data/GGA and data/GGA-metal,
compares predictions against ground-truth folder labels.
"""
import sys, os, glob, time, traceback
import pandas as pd
import numpy as np

# Add project root (parent of tools/) to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import extract_peaks_from_txt, catboost_inference_from_csv

# Paths
MODEL_PATH = "model/catboost_model.cbm"
LABEL_ENCODER_PATH = "model/label_encoder_classes.npy"
GGA_DIR = "data/GGA/File txt"
METAL_DIR = "data/GGA-metal/File txt"

def find_txt_files(base_dir):
    """Recursively find all .txt files under base_dir."""
    results = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith(".txt"):
                results.append(os.path.join(root, f))
    return results

def run_validation():
    # Collect files
    gga_files = find_txt_files(GGA_DIR)
    metal_files = find_txt_files(METAL_DIR)
    print(f"Found: {len(gga_files)} GGA files, {len(metal_files)} GGA-metal files")
    print(f"Total: {len(gga_files) + len(metal_files)} files\n")

    results = []
    errors = []
    t0 = time.time()

    all_files = [(f, "gga") for f in gga_files] + [(f, "gga-metal") for f in metal_files]

    for i, (fpath, true_label) in enumerate(all_files):
        fname = os.path.basename(fpath)
        try:
            # Step 1: Extract peaks
            peaks_df = extract_peaks_from_txt(fpath)
            n_peaks = len(peaks_df)

            if n_peaks == 0:
                errors.append({"file": fname, "true": true_label, "error": "0 peaks extracted"})
                continue

            # Step 2: Classify
            preds = catboost_inference_from_csv(peaks_df, MODEL_PATH, LABEL_ENCODER_PATH)
            # preds = [(sample_name, pred_label, pred_proba)]
            _, pred_label, pred_proba = preds[0]
            pred_label = str(pred_label).strip().lower()
            max_prob = max(pred_proba) * 100

            results.append({
                "file": fname,
                "true": true_label,
                "pred": pred_label,
                "correct": pred_label == true_label,
                "prob": round(max_prob, 1),
                "n_peaks": n_peaks
            })

        except Exception as e:
            errors.append({"file": fname, "true": true_label, "error": str(e)[:100]})

        # Progress every 50 files
        if (i + 1) % 50 == 0:
            elapsed = time.time() - t0
            print(f"  [{i+1}/{len(all_files)}] {elapsed:.1f}s elapsed ...")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s ({len(all_files)} files)")

    # --- Analysis ---
    df = pd.DataFrame(results)
    n_total = len(df)
    n_correct = df["correct"].sum()
    n_wrong = n_total - n_correct
    accuracy = n_correct / n_total * 100 if n_total > 0 else 0

    print(f"\n{'='*60}")
    print(f"CLASSIFICATION VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"Total files processed: {n_total}")
    print(f"Errors (skipped):      {len(errors)}")
    print(f"Correct:               {n_correct}")
    print(f"Wrong:                 {n_wrong}")
    print(f"ACCURACY:              {accuracy:.1f}%")

    # Per-class breakdown
    print(f"\n--- Per-class breakdown ---")
    for label in ["gga", "gga-metal"]:
        subset = df[df["true"] == label]
        if len(subset) == 0:
            continue
        corr = subset["correct"].sum()
        tot = len(subset)
        acc = corr / tot * 100
        print(f"  {label:12s}: {corr:3d}/{tot:3d} correct = {acc:.1f}%")

    # Confusion matrix
    print(f"\n--- Confusion Matrix ---")
    print(f"{'':15s} {'Pred GGA':>10s} {'Pred Metal':>12s}")
    for label in ["gga", "gga-metal"]:
        subset = df[df["true"] == label]
        pred_gga = len(subset[subset["pred"] == "gga"])
        pred_metal = len(subset[subset["pred"] == "gga-metal"])
        print(f"  True {label:10s}: {pred_gga:>8d} {pred_metal:>12d}")

    # Wrong predictions detail
    wrong = df[~df["correct"]]
    if len(wrong) > 0:
        print(f"\n--- Misclassified Files ({len(wrong)}) ---")
        for _, row in wrong.iterrows():
            print(f"  {row['file'][:60]:60s} true={row['true']:10s} pred={row['pred']:10s} prob={row['prob']}%  peaks={row['n_peaks']}")

    # Probability distribution
    print(f"\n--- Confidence Distribution ---")
    for bucket in [(0,50), (50,60), (60,70), (70,80), (80,90), (90,100)]:
        cnt = len(df[(df["prob"] >= bucket[0]) & (df["prob"] < bucket[1])])
        if cnt > 0:
            print(f"  {bucket[0]:3d}-{bucket[1]:3d}%: {cnt} files")

    # Error details
    if errors:
        print(f"\n--- Errors ({len(errors)}) ---")
        for e in errors[:20]:
            print(f"  {e['file'][:50]:50s} true={e['true']:10s} err={e['error']}")

    # Save CSV
    df.to_csv("plans/reports/classification-validation-results.csv", index=False)
    print(f"\nResults saved to plans/reports/classification-validation-results.csv")

if __name__ == "__main__":
    run_validation()
