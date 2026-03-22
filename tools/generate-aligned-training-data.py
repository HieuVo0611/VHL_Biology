"""
Generate aligned training data by running peak_extractor on all TXT files.
Labels come from folder structure (data/GGA vs data/GGA-metal).
This ensures training data distribution matches inference distribution.

Usage: conda activate vhl && python tools/generate-aligned-training-data.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.utils import extract_peaks_from_txt

# ── Config ──────────────────────────────────────────────────────────
GGA_DIR = "data/GGA/File txt"
METAL_DIR = "data/GGA-metal/File txt"
OUTPUT_PATH = "data/training-peaks-algorithm-extracted.csv"

def find_txt_files(base_dir):
    """Recursively find all .txt files."""
    results = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith(".txt"):
                results.append(os.path.join(root, f))
    return results

def main():
    print("=" * 60)
    print("GENERATING ALIGNED TRAINING DATA")
    print("(Using same peak_extractor as inference)")
    print("=" * 60)

    gga_files = find_txt_files(GGA_DIR)
    metal_files = find_txt_files(METAL_DIR)
    print(f"\nFound: {len(gga_files)} GGA + {len(metal_files)} metal = {len(gga_files) + len(metal_files)} files")

    all_frames = []
    errors = []
    t0 = time.time()

    all_files = [(f, "gga") for f in gga_files] + [(f, "gga-metal") for f in metal_files]

    for i, (fpath, label) in enumerate(all_files):
        try:
            peaks_df = extract_peaks_from_txt(fpath)
            if len(peaks_df) > 0:
                peaks_df["label"] = label
                all_frames.append(peaks_df)
        except Exception as e:
            errors.append({"file": os.path.basename(fpath), "label": label, "error": str(e)[:80]})

        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{len(all_files)}] {time.time()-t0:.1f}s ...")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")

    # Combine all frames
    df_all = pd.concat(all_frames, ignore_index=True)
    n_gga = df_all[df_all["label"] == "gga"]["Sample Name"].nunique()
    n_metal = df_all[df_all["label"] == "gga-metal"]["Sample Name"].nunique()

    print(f"\nResult:")
    print(f"  Total peaks: {len(df_all)}")
    print(f"  GGA samples: {n_gga}")
    print(f"  Metal samples: {n_metal}")
    print(f"  Errors: {len(errors)}")

    # Save
    df_all.to_csv(OUTPUT_PATH, index=False)
    print(f"  Saved to: {OUTPUT_PATH}")

    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors[:10]:
            print(f"    {e['file'][:50]} ({e['label']}): {e['error']}")

if __name__ == "__main__":
    main()
