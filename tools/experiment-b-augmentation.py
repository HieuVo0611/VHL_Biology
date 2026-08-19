"""
Experiment B: Data augmentation strategies.
Tests: noise injection (σ=0.08, σ=0.15, σ=0.25), GGA oversampling, and combinations.
Uses expert ground-truth training data, evaluates with CV + holdout.

Usage: conda activate vhl && python tools/experiment-b-augmentation.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score, confusion_matrix
from catboost import CatBoostClassifier
from src.utils import aggregate_features

DATA_DIR = "data"
RANDOM_STATE = 42
CATBOOST_PARAMS = {
    "iterations": 300, "learning_rate": 0.05, "depth": 8,
    "verbose": 0, "random_state": RANDOM_STATE,
    "auto_class_weights": "Balanced",
}


def load_gt_data():
    """Load expert ground-truth training data."""
    frames = []
    df_gga = pd.read_csv(f"{DATA_DIR}/metadata-gga-2024-10-23.csv")
    df_gga["label"] = "gga"
    frames.append(df_gga)
    for fpath in [f"{DATA_DIR}/metadata-gga-metal-2024-10-23.csv",
                  f"{DATA_DIR}/metadata-gga-metal-hh-2024-10-23.csv"]:
        df_m = pd.read_csv(fpath)
        df_m["label"] = "gga-metal"
        frames.append(df_m)
    return pd.concat(frames, ignore_index=True)


def augment_noise_on_peaks(df, n_copies=5, sigma=0.08):
    """Add Gaussian noise to Doin/DOmin columns, recalculate DDO."""
    noisy_frames = [df.copy()]  # keep original
    rng = np.random.RandomState(RANDOM_STATE)
    for i in range(n_copies):
        noisy = df.copy()
        for col in ['Doin (mV)', 'DOmin (mV)']:
            noisy[col] = noisy[col] + rng.normal(0, sigma, size=len(noisy))
        noisy['DDO (mV)'] = noisy['Doin (mV)'] - noisy['DOmin (mV)']
        noisy_frames.append(noisy)
    return pd.concat(noisy_frames, ignore_index=True)


def oversample_gga_features(X, y, target_ratio=0.45):
    """Random oversample GGA class at feature level."""
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
    """Train CatBoost with 5-fold CV and holdout test."""
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

    print(f"  {experiment_name:55s} CV={cv_scores.mean():.3f}+-{cv_scores.std():.3f}  "
          f"Test={acc:.3f}  GGA={gga_recall:.1f}%  Metal={metal_recall:.1f}%  "
          f"(n_samples={len(y)})")
    return {
        "name": experiment_name, "cv_mean": cv_scores.mean(), "cv_std": cv_scores.std(),
        "test_acc": acc, "gga_recall": gga_recall, "metal_recall": metal_recall,
    }


def main():
    print("=" * 70)
    print("EXPERIMENT B: DATA AUGMENTATION + NOISE INJECTION")
    print("=" * 70)

    df_raw = load_gt_data()
    n_gga = df_raw[df_raw['label'] == 'gga']['Sample Name'].nunique()
    n_metal = df_raw[df_raw['label'] == 'gga-metal']['Sample Name'].nunique()
    print(f"\nRaw data: {len(df_raw)} peaks, {n_gga} GGA + {n_metal} metal samples")

    results = []

    # B1: Baseline (no augmentation)
    print("\n[B1] Baseline (no augmentation)...")
    df_agg = aggregate_features(df_raw, has_label=True)
    features = [c for c in df_agg.columns if c != "label"]
    X = df_agg[features].values.astype(float)
    y = df_agg["label"].values
    results.append(evaluate(X, y, "B1: Baseline (no augmentation)"))

    # B2: Noise s=0.08, 5x
    print("\n[B2] Noise s=0.08, 5x copies...")
    df_n08 = augment_noise_on_peaks(df_raw, n_copies=5, sigma=0.08)
    df_agg_n08 = aggregate_features(df_n08, has_label=True)
    X_n08 = df_agg_n08[features].values.astype(float)
    y_n08 = df_agg_n08["label"].values
    results.append(evaluate(X_n08, y_n08, "B2: Noise s=0.08, 5x"))

    # B3: Noise s=0.15, 5x
    print("\n[B3] Noise s=0.15, 5x copies...")
    df_n15 = augment_noise_on_peaks(df_raw, n_copies=5, sigma=0.15)
    df_agg_n15 = aggregate_features(df_n15, has_label=True)
    X_n15 = df_agg_n15[features].values.astype(float)
    y_n15 = df_agg_n15["label"].values
    results.append(evaluate(X_n15, y_n15, "B3: Noise s=0.15, 5x"))

    # B4: Noise s=0.25, 5x (aggressive)
    print("\n[B4] Noise s=0.25, 5x copies (aggressive)...")
    df_n25 = augment_noise_on_peaks(df_raw, n_copies=5, sigma=0.25)
    df_agg_n25 = aggregate_features(df_n25, has_label=True)
    X_n25 = df_agg_n25[features].values.astype(float)
    y_n25 = df_agg_n25["label"].values
    results.append(evaluate(X_n25, y_n25, "B4: Noise s=0.25, 5x"))

    # B5: GGA oversampling only (to 45%)
    print("\n[B5] GGA oversampling (target 45%)...")
    X_over, y_over = oversample_gga_features(X, y, target_ratio=0.45)
    results.append(evaluate(X_over, y_over, "B5: GGA oversampling (45%)"))

    # B6: Noise s=0.08 + GGA oversampling
    print("\n[B6] Noise s=0.08 + GGA oversampling (45%)...")
    X_n08_over, y_n08_over = oversample_gga_features(X_n08, y_n08, target_ratio=0.45)
    results.append(evaluate(X_n08_over, y_n08_over, "B6: Noise s=0.08 + oversample (45%)"))

    # B7: Noise s=0.15 + GGA oversampling
    print("\n[B7] Noise s=0.15 + GGA oversampling (45%)...")
    X_n15_over, y_n15_over = oversample_gga_features(X_n15, y_n15, target_ratio=0.45)
    results.append(evaluate(X_n15_over, y_n15_over, "B7: Noise s=0.15 + oversample (45%)"))

    # Summary
    print(f"\n{'='*70}")
    print("EXPERIMENT B SUMMARY (sorted by balanced score)")
    print(f"{'='*70}")
    for r in results:
        r["balanced_score"] = r["cv_mean"] * 0.5 + min(r["gga_recall"], r["metal_recall"]) * 0.005
    results.sort(key=lambda r: r["balanced_score"], reverse=True)
    for i, r in enumerate(results):
        marker = " ** BEST" if i == 0 else ""
        print(f"  {i+1}. {r['name']:55s} CV={r['cv_mean']:.3f}  GGA={r['gga_recall']:.1f}%  "
              f"Metal={r['metal_recall']:.1f}%{marker}")


if __name__ == "__main__":
    main()
