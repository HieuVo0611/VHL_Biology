"""
Experiment D: Train CatBoost on algorithm-extracted peaks (real distribution).
Re-extract peaks from all 518 TXT files, aggregate features, train CatBoost.
This closes the GT-vs-extractor distribution gap by training on production data.

Usage: conda activate vhl && python tools/experiment-d-aligned-training.py
"""
import sys, os, glob, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score, confusion_matrix
from catboost import CatBoostClassifier
from src.utils import extract_peaks_from_txt, aggregate_features
import json, shutil
from datetime import datetime

DATA_DIR = "data"
MODEL_DIR = "model"
RANDOM_STATE = 42
CATBOOST_PARAMS = {
    "iterations": 300, "learning_rate": 0.05, "depth": 8,
    "verbose": 0, "random_state": RANDOM_STATE,
    "auto_class_weights": "Balanced",
}


def extract_all_peaks(data_dir):
    """Re-extract peaks from all TXT files using production extractor."""
    gga_dir = os.path.join(data_dir, "GGA", "File txt")
    metal_dir = os.path.join(data_dir, "GGA-metal", "File txt")
    all_peaks = []
    errors = 0

    for label, folder in [("gga", gga_dir), ("gga-metal", metal_dir)]:
        # Recursively find all .txt files
        txt_files = []
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(".txt"):
                    txt_files.append(os.path.join(root, f))
        print(f"  {label}: {len(txt_files)} files")
        for i, fpath in enumerate(txt_files):
            try:
                df_peaks = extract_peaks_from_txt(fpath)
                if df_peaks is not None and len(df_peaks) > 0:
                    df_peaks["label"] = label
                    all_peaks.append(df_peaks)
            except Exception as e:
                errors += 1
            if (i + 1) % 50 == 0:
                print(f"    [{i+1}/{len(txt_files)}]...")

    print(f"  Errors: {errors}")
    return pd.concat(all_peaks, ignore_index=True) if all_peaks else pd.DataFrame()


def oversample_gga_features(X, y, target_ratio=0.45):
    """Random oversample GGA class."""
    rng = np.random.RandomState(RANDOM_STATE)
    gga_mask = y == "gga"
    n_gga = gga_mask.sum()
    n_metal = (~gga_mask).sum()
    n_target_gga = int(n_metal * target_ratio / (1 - target_ratio))
    n_extra = n_target_gga - n_gga
    if n_extra <= 0:
        return X, y
    gga_indices = np.where(gga_mask)[0]
    extra_indices = rng.choice(gga_indices, size=n_extra, replace=True)
    new_X = np.vstack([X, X[extra_indices]])
    new_y = np.concatenate([y, y[extra_indices]])
    return new_X, new_y


def evaluate(X, y, experiment_name):
    """Evaluate model via CV + holdout."""
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    model = CatBoostClassifier(**CATBOOST_PARAMS)
    cv_scores = cross_val_score(model, X, y_enc, cv=skf, scoring="accuracy")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y_enc, test_size=0.4,
                                                stratify=y_enc, random_state=RANDOM_STATE)
    model.fit(X_tr, y_tr)
    y_pred = model.predict(X_te)
    acc = accuracy_score(y_te, y_pred)
    cm = confusion_matrix(y_te, y_pred)

    gga_idx = np.where(le.classes_ == "gga")[0][0]
    metal_idx = np.where(le.classes_ == "gga-metal")[0][0]
    gga_recall = cm[gga_idx][gga_idx] / np.sum(y_te == gga_idx) * 100
    metal_recall = cm[metal_idx][metal_idx] / np.sum(y_te == metal_idx) * 100

    print(f"  {experiment_name}")
    print(f"    CV: {cv_scores.mean():.3f}+-{cv_scores.std():.3f}  Test: {acc:.3f}")
    print(f"    GGA: {gga_recall:.1f}%  Metal: {metal_recall:.1f}%")
    return {"name": experiment_name, "cv_mean": cv_scores.mean(), "cv_std": cv_scores.std(),
            "test_acc": acc, "gga_recall": gga_recall, "metal_recall": metal_recall,
            "model": model, "le": le}


def main():
    print("=" * 70)
    print("EXPERIMENT D: ALIGNED TRAINING (algorithm-extracted peaks)")
    print("=" * 70)

    # Step 1: Extract peaks
    cache_path = f"{DATA_DIR}/ext_all_518_peaks.csv"
    if os.path.exists(cache_path):
        print(f"\n[1] Loading cached peaks from {cache_path}...")
        df_peaks = pd.read_csv(cache_path)
    else:
        print("\n[1] Extracting peaks from all 518 TXT files...")
        t0 = time.time()
        df_peaks = extract_all_peaks(DATA_DIR)
        print(f"  Extracted {len(df_peaks)} peaks in {time.time()-t0:.1f}s")
        df_peaks.to_csv(cache_path, index=False)
        print(f"  Cached to {cache_path}")

    print(f"  Total peaks: {len(df_peaks)}")
    print(f"  GGA peaks: {len(df_peaks[df_peaks['label']=='gga'])}")
    print(f"  Metal peaks: {len(df_peaks[df_peaks['label']=='gga-metal'])}")

    # Step 2: Aggregate features
    print("\n[2] Aggregating features...")
    df_agg = aggregate_features(df_peaks, has_label=True)
    features = [c for c in df_agg.columns if c != "label"]
    X = df_agg[features].values.astype(float)
    y = df_agg["label"].values
    n_gga = np.sum(y == "gga")
    n_metal = np.sum(y == "gga-metal")
    print(f"  Samples: {len(y)} (GGA: {n_gga}, Metal: {n_metal})")
    print(f"  Features: {len(features)}")

    results = []

    # D1: Algorithm-extracted, no augmentation
    print("\n[D1] Algorithm-extracted, no augmentation...")
    r1 = evaluate(X, y, "D1: Algo-extracted, raw")
    results.append(r1)

    # D2: Algorithm-extracted + GGA oversample
    print("\n[D2] Algorithm-extracted + GGA oversample (45%)...")
    X_over, y_over = oversample_gga_features(X, y, target_ratio=0.45)
    r2 = evaluate(X_over, y_over, "D2: Algo-extracted + oversample (45%)")
    results.append(r2)

    # D3: Algorithm-extracted + GGA oversample (40%)
    print("\n[D3] Algorithm-extracted + GGA oversample (40%)...")
    X_over40, y_over40 = oversample_gga_features(X, y, target_ratio=0.40)
    r3 = evaluate(X_over40, y_over40, "D3: Algo-extracted + oversample (40%)")
    results.append(r3)

    # Summary
    print(f"\n{'='*70}")
    print("EXPERIMENT D SUMMARY")
    print(f"{'='*70}")
    for r in results:
        r["balanced_score"] = r["cv_mean"] * 0.5 + min(r["gga_recall"], r["metal_recall"]) * 0.005
    results.sort(key=lambda r: r["balanced_score"], reverse=True)
    for i, r in enumerate(results):
        marker = " ** BEST" if i == 0 else ""
        print(f"  {i+1}. {r['name']:50s} CV={r['cv_mean']:.3f}  GGA={r['gga_recall']:.1f}%  "
              f"Metal={r['metal_recall']:.1f}%{marker}")

    # Save best model
    best = results[0]
    print(f"\n  Saving best model ({best['name']})...")

    # Retrain on full data
    final_model = CatBoostClassifier(**CATBOOST_PARAMS)
    le_full = LabelEncoder()
    if "oversample" in best["name"]:
        ratio = 0.45 if "45" in best["name"] else 0.40
        X_full, y_full = oversample_gga_features(X, y, target_ratio=ratio)
    else:
        X_full, y_full = X, y
    y_full_enc = le_full.fit_transform(y_full)
    final_model.fit(X_full, y_full_enc)

    # Backup & save
    old_path = f"{MODEL_DIR}/catboost_model.cbm"
    old_le = f"{MODEL_DIR}/label_encoder_classes.npy"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if os.path.exists(old_path):
        shutil.copy2(old_path, f"{MODEL_DIR}/catboost_model_backup_{ts}.cbm")
    if os.path.exists(old_le):
        shutil.copy2(old_le, f"{MODEL_DIR}/label_encoder_classes_backup_{ts}.npy")

    final_model.save_model(old_path)
    np.save(old_le, le_full.classes_)

    meta = {
        "date": datetime.now().isoformat(),
        "experiment": best["name"],
        "cv_accuracy": f"{best['cv_mean']:.4f}+-{best['cv_std']:.4f}",
        "test_accuracy": f"{best['test_acc']:.4f}",
        "gga_recall": f"{best['gga_recall']:.1f}%",
        "metal_recall": f"{best['metal_recall']:.1f}%",
        "n_train_samples": int(len(y_full)),
        "n_features": len(features),
        "training_data": "algorithm-extracted peaks from 518 TXT files",
        "params": {k: str(v) for k, v in CATBOOST_PARAMS.items()},
    }
    with open(f"{MODEL_DIR}/catboost_training_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"  Saved: {old_path}")
    print(f"\n  Now validate with: python tools/validate-classifier-accuracy.py")


if __name__ == "__main__":
    main()
