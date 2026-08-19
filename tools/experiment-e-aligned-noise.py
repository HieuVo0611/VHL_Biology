"""
Experiment E: Combine aligned training (Exp D) with noise injection (Exp B).
Train on algo-extracted peaks + noise augmentation + GGA oversampling.

Usage: conda activate vhl && python tools/experiment-e-aligned-noise.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score, confusion_matrix
from catboost import CatBoostClassifier
from src.utils import aggregate_features
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


def augment_noise_on_peaks(df, n_copies=3, sigma=0.10):
    """Add Gaussian noise to peak mV values, recalculate DDO."""
    noisy_frames = [df.copy()]
    rng = np.random.RandomState(RANDOM_STATE)
    for i in range(n_copies):
        noisy = df.copy()
        for col in ['Doin (mV)', 'DOmin (mV)']:
            noisy[col] = noisy[col] + rng.normal(0, sigma, size=len(noisy))
        noisy['DDO (mV)'] = noisy['Doin (mV)'] - noisy['DOmin (mV)']
        noisy_frames.append(noisy)
    return pd.concat(noisy_frames, ignore_index=True)


def oversample_gga_features(X, y, target_ratio=0.45):
    rng = np.random.RandomState(RANDOM_STATE)
    gga_mask = y == "gga"
    n_gga = gga_mask.sum()
    n_metal = (~gga_mask).sum()
    n_target = int(n_metal * target_ratio / (1 - target_ratio))
    n_extra = n_target - n_gga
    if n_extra <= 0:
        return X, y
    gga_idx = np.where(gga_mask)[0]
    extra = rng.choice(gga_idx, size=n_extra, replace=True)
    return np.vstack([X, X[extra]]), np.concatenate([y, y[extra]])


def evaluate(X, y, name):
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    model = CatBoostClassifier(**CATBOOST_PARAMS)
    cv = cross_val_score(model, X, y_enc, cv=skf, scoring="accuracy")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y_enc, test_size=0.4,
                                                stratify=y_enc, random_state=RANDOM_STATE)
    model.fit(X_tr, y_tr)
    y_pred = model.predict(X_te)
    acc = accuracy_score(y_te, y_pred)
    cm = confusion_matrix(y_te, y_pred)
    gga_idx = np.where(le.classes_ == "gga")[0][0]
    metal_idx = np.where(le.classes_ == "gga-metal")[0][0]
    gga_r = cm[gga_idx][gga_idx] / max(np.sum(y_te == gga_idx), 1) * 100
    metal_r = cm[metal_idx][metal_idx] / max(np.sum(y_te == metal_idx), 1) * 100

    print(f"  {name}")
    print(f"    CV: {cv.mean():.3f}+-{cv.std():.3f}  Test: {acc:.3f}  GGA: {gga_r:.1f}%  Metal: {metal_r:.1f}%")
    return {"name": name, "cv_mean": cv.mean(), "cv_std": cv.std(),
            "test_acc": acc, "gga_recall": gga_r, "metal_recall": metal_r}


def main():
    print("=" * 70)
    print("EXPERIMENT E: ALIGNED TRAINING + NOISE INJECTION")
    print("=" * 70)

    # Load cached algo-extracted peaks
    cache_path = f"{DATA_DIR}/ext_all_518_peaks.csv"
    if not os.path.exists(cache_path):
        print(f"ERROR: {cache_path} not found. Run experiment-d first.")
        return
    df_peaks = pd.read_csv(cache_path)
    print(f"\nLoaded {len(df_peaks)} peaks from {cache_path}")

    results = []

    configs = [
        ("E1: Algo + noise s=0.08 3x + oversample(45%)", 0.08, 3, 0.45),
        ("E2: Algo + noise s=0.10 3x + oversample(45%)", 0.10, 3, 0.45),
        ("E3: Algo + noise s=0.15 3x + oversample(45%)", 0.15, 3, 0.45),
        ("E4: Algo + noise s=0.10 5x + oversample(45%)", 0.10, 5, 0.45),
        ("E5: Algo + noise s=0.10 3x + oversample(40%)", 0.10, 3, 0.40),
    ]

    for name, sigma, copies, ratio in configs:
        print(f"\n{name}...")
        df_aug = augment_noise_on_peaks(df_peaks, n_copies=copies, sigma=sigma)
        df_agg = aggregate_features(df_aug, has_label=True)
        features = [c for c in df_agg.columns if c != "label"]
        X = df_agg[features].values.astype(float)
        y = df_agg["label"].values
        X_over, y_over = oversample_gga_features(X, y, target_ratio=ratio)
        r = evaluate(X_over, y_over, name)
        results.append(r)

    # Also test D2 baseline (no noise) for comparison
    print(f"\nD2 baseline (no noise, oversample 45%)...")
    df_agg_base = aggregate_features(df_peaks, has_label=True)
    features = [c for c in df_agg_base.columns if c != "label"]
    X_base = df_agg_base[features].values.astype(float)
    y_base = df_agg_base["label"].values
    X_b_over, y_b_over = oversample_gga_features(X_base, y_base, target_ratio=0.45)
    r_base = evaluate(X_b_over, y_b_over, "D2 baseline: Algo + oversample(45%)")
    results.append(r_base)

    # Summary
    print(f"\n{'='*70}")
    print("EXPERIMENT E SUMMARY")
    print(f"{'='*70}")
    for r in results:
        r["balanced"] = r["cv_mean"] * 0.5 + min(r["gga_recall"], r["metal_recall"]) * 0.005
    results.sort(key=lambda r: r["balanced"], reverse=True)
    for i, r in enumerate(results):
        marker = " ** BEST" if i == 0 else ""
        print(f"  {i+1}. {r['name']:55s} CV={r['cv_mean']:.3f}  GGA={r['gga_recall']:.1f}%  Metal={r['metal_recall']:.1f}%{marker}")

    # Save best as model
    best = results[0]
    print(f"\n  Best: {best['name']}")
    print(f"  CV={best['cv_mean']:.3f}  GGA={best['gga_recall']:.1f}%  Metal={best['metal_recall']:.1f}%")

    # Find best config and retrain on full data
    best_cfg = None
    for name, sigma, copies, ratio in configs:
        if name == best["name"]:
            best_cfg = (sigma, copies, ratio)
            break
    if best_cfg is None:
        print("  Best is D2 baseline, keeping D2 model.")
        return

    sigma, copies, ratio = best_cfg
    print(f"\n  Retraining final model with sigma={sigma}, copies={copies}, ratio={ratio}...")
    df_aug_final = augment_noise_on_peaks(df_peaks, n_copies=copies, sigma=sigma)
    df_agg_final = aggregate_features(df_aug_final, has_label=True)
    X_final = df_agg_final[features].values.astype(float)
    y_final = df_agg_final["label"].values
    X_f_over, y_f_over = oversample_gga_features(X_final, y_final, target_ratio=ratio)

    le_full = LabelEncoder()
    y_f_enc = le_full.fit_transform(y_f_over)
    final_model = CatBoostClassifier(**CATBOOST_PARAMS)
    final_model.fit(X_f_over, y_f_enc)

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
    print(f"  Saved: {old_path}")

    meta = {
        "date": datetime.now().isoformat(),
        "experiment": best["name"],
        "sigma": sigma, "copies": copies, "ratio": ratio,
        "cv_accuracy": f"{best['cv_mean']:.4f}+-{best['cv_std']:.4f}",
        "gga_recall": f"{best['gga_recall']:.1f}%",
        "metal_recall": f"{best['metal_recall']:.1f}%",
        "training_data": "algo-extracted 518 files + noise + oversample",
    }
    with open(f"{MODEL_DIR}/catboost_training_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  Now validate: python tools/validate-classifier-accuracy.py")


if __name__ == "__main__":
    main()
