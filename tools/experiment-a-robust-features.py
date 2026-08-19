"""
Experiment A: Retrain CatBoost with robust features added.
Tests: original features only, original+new, drop raw mV extremes, robust only.
Uses expert ground-truth training data.

Usage: conda activate vhl && python tools/experiment-a-robust-features.py
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

# New robust features added in Task 1
ROBUST_FEATURES = [
    'DDO_to_doin_range_ratio', 'DOmin_Doin_std_ratio', 'DDO_coeff_variation',
    'normalized_DDO_mean', 'peak_spacing_regularity', 'DDO_iqr', 'DDO_range_ratio',
    'n_high_DDO_peaks', 'n_low_DDO_peaks', 'BOD_tag_ratio_5', 'BOD_tag_ratio_10',
    'BOD_tag_ratio_15', 'peak_density',
]

# Raw mV features most sensitive to extraction error
RAW_MV_FEATURES = [
    'mean_Doin (mV)', 'std_Doin (mV)', 'max_Doin (mV)', 'min_Doin (mV)',
    'mean_DOmin (mV)', 'std_DOmin (mV)', 'max_DOmin (mV)', 'min_DOmin (mV)',
    'mean_DDO (mV)', 'std_DDO (mV)', 'max_DDO (mV)', 'min_DDO (mV)',
]


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


def evaluate(X, y, feature_names, experiment_name):
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

    # Feature importance (top 10)
    fi = model.get_feature_importance()
    top_fi = sorted(zip(feature_names, fi), key=lambda x: -x[1])[:10]

    print(f"  {experiment_name:50s} CV={cv_scores.mean():.3f}+-{cv_scores.std():.3f}  "
          f"Test={acc:.3f}  GGA={gga_recall:.1f}%  Metal={metal_recall:.1f}%  "
          f"({len(feature_names)} feats)")
    return {
        "name": experiment_name, "cv_mean": cv_scores.mean(), "cv_std": cv_scores.std(),
        "test_acc": acc, "gga_recall": gga_recall, "metal_recall": metal_recall,
        "n_features": len(feature_names), "top_features": top_fi,
    }


def main():
    print("=" * 70)
    print("EXPERIMENT A: ROBUST FEATURE ENGINEERING")
    print("=" * 70)

    df_all = load_gt_data()
    df_agg = aggregate_features(df_all, has_label=True)
    all_features = [c for c in df_agg.columns if c != "label"]
    y = df_agg["label"].values

    # Feature sets to test
    original_only = [f for f in all_features if f not in ROBUST_FEATURES]
    robust_only = [f for f in all_features if f in ROBUST_FEATURES]
    all_with_robust = all_features
    no_raw_extremes = [f for f in all_features if f not in RAW_MV_FEATURES]

    experiments = [
        ("A1: Original 68 features only (baseline)", original_only),
        ("A2: Original + 13 robust features (81)", all_with_robust),
        ("A3: Drop 12 raw mV extremes + keep robust", no_raw_extremes),
    ]
    if len(robust_only) >= 5:
        experiments.append(("A4: Robust 13 features only", robust_only))

    n_gga = np.sum(y == "gga")
    n_metal = np.sum(y == "gga-metal")
    print(f"\nSamples: {len(y)} (GGA: {n_gga}, Metal: {n_metal})")
    print(f"Total features available: {len(all_features)}\n")

    results = []
    for name, feature_set in experiments:
        X = df_agg[feature_set].values.astype(float)
        r = evaluate(X, y, feature_set, name)
        results.append(r)

    # Summary
    print(f"\n{'='*70}")
    print("EXPERIMENT A SUMMARY (sorted by balanced score)")
    print(f"{'='*70}")
    for r in results:
        r["balanced_score"] = r["cv_mean"] * 0.5 + min(r["gga_recall"], r["metal_recall"]) * 0.005
    results.sort(key=lambda r: r["balanced_score"], reverse=True)
    for i, r in enumerate(results):
        marker = " ** BEST" if i == 0 else ""
        print(f"  {i+1}. {r['name']:50s} CV={r['cv_mean']:.3f}  GGA={r['gga_recall']:.1f}%  "
              f"Metal={r['metal_recall']:.1f}%{marker}")

    best = results[0]
    print(f"\n  Top 10 features of best model:")
    for fname, fval in best["top_features"]:
        print(f"    {fname:40s} {fval:.1f}")


if __name__ == "__main__":
    main()
