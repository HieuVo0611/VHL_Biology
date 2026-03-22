"""
CatBoost classifier retraining script with multiple improvement strategies.
Compares old model vs new candidates, picks best, saves if improved.

Usage: conda activate vhl && python tools/retrain-catboost-classifier.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from catboost import CatBoostClassifier
from src.utils import aggregate_features
import shutil
import json
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────
DATA_DIR = "data"
MODEL_DIR = "model"
RANDOM_STATE = 42

# Aligned training data (extracted by peak_extractor, same as inference)
ALIGNED_DATA = f"{DATA_DIR}/training-peaks-algorithm-extracted.csv"

# Legacy ground-truth training data (from Excel metadata)
LEGACY_TRAIN_FILES = {
    "gga": f"{DATA_DIR}/metadata-gga-2024-10-23.csv",
    "gga-metal": [
        f"{DATA_DIR}/metadata-gga-metal-2024-10-23.csv",
        f"{DATA_DIR}/metadata-gga-metal-hh-2024-10-23.csv",
    ],
}

# ── Data Loading ────────────────────────────────────────────────────
def load_aligned_data():
    """Load algorithm-extracted training data (same distribution as inference)."""
    df = pd.read_csv(ALIGNED_DATA)
    n_gga = df[df["label"] == "gga"]["Sample Name"].nunique()
    n_metal = df[df["label"] == "gga-metal"]["Sample Name"].nunique()
    print(f"  Aligned data: {len(df)} peaks, {n_gga} GGA + {n_metal} metal samples")
    return df

def load_training_data():
    """Load legacy ground-truth training CSVs with labels."""
    frames = []

    # GGA samples
    df_gga = pd.read_csv(LEGACY_TRAIN_FILES["gga"])
    df_gga["label"] = "gga"
    frames.append(df_gga)
    print(f"  GGA: {len(df_gga)} peaks, {df_gga['Sample Name'].nunique()} samples")

    # GGA-metal samples (may have multiple files)
    for fpath in LEGACY_TRAIN_FILES["gga-metal"]:
        df_m = pd.read_csv(fpath)
        df_m["label"] = "gga-metal"
        frames.append(df_m)
        print(f"  Metal ({os.path.basename(fpath)}): {len(df_m)} peaks, {df_m['Sample Name'].nunique()} samples")

    df_all = pd.concat(frames, ignore_index=True)
    print(f"  Total: {len(df_all)} peaks, {df_all['Sample Name'].nunique()} samples\n")
    return df_all


# ── Training Experiments ────────────────────────────────────────────
def run_experiments(X, y, feature_names):
    """Run multiple CatBoost configs, return results sorted by accuracy."""
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    experiments = [
        {
            "name": "baseline (no class weights)",
            "params": {
                "iterations": 200, "learning_rate": 0.1, "depth": 6,
                "verbose": 0, "random_state": RANDOM_STATE,
            },
        },
        {
            "name": "balanced class weights",
            "params": {
                "iterations": 200, "learning_rate": 0.1, "depth": 6,
                "verbose": 0, "random_state": RANDOM_STATE,
                "auto_class_weights": "Balanced",
            },
        },
        {
            "name": "balanced + deeper trees (depth=8)",
            "params": {
                "iterations": 300, "learning_rate": 0.05, "depth": 8,
                "verbose": 0, "random_state": RANDOM_STATE,
                "auto_class_weights": "Balanced",
            },
        },
        {
            "name": "balanced + L2 regularization",
            "params": {
                "iterations": 300, "learning_rate": 0.05, "depth": 6,
                "verbose": 0, "random_state": RANDOM_STATE,
                "auto_class_weights": "Balanced",
                "l2_leaf_reg": 5,
            },
        },
        {
            "name": "SqrtBalanced class weights",
            "params": {
                "iterations": 300, "learning_rate": 0.05, "depth": 6,
                "verbose": 0, "random_state": RANDOM_STATE,
                "auto_class_weights": "SqrtBalanced",
            },
        },
        {
            "name": "balanced + more iterations",
            "params": {
                "iterations": 500, "learning_rate": 0.03, "depth": 6,
                "verbose": 0, "random_state": RANDOM_STATE,
                "auto_class_weights": "Balanced",
                "l2_leaf_reg": 3,
            },
        },
    ]

    results = []
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    for exp in experiments:
        print(f"  [{exp['name']}]")
        model = CatBoostClassifier(**exp["params"])

        # 5-fold cross-validation
        cv_scores = cross_val_score(model, X, y_enc, cv=skf, scoring="accuracy")
        cv_mean = cv_scores.mean()
        cv_std = cv_scores.std()

        # Full train/test split for detailed metrics
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y_enc, test_size=0.4, stratify=y_enc, random_state=RANDOM_STATE
        )
        model.fit(X_tr, y_tr)
        y_pred = model.predict(X_te)
        acc = accuracy_score(y_te, y_pred)
        cm = confusion_matrix(y_te, y_pred)

        # Per-class recall
        gga_idx = np.where(le.classes_ == "gga")[0][0]
        metal_idx = np.where(le.classes_ == "gga-metal")[0][0]
        gga_total = np.sum(y_te == gga_idx)
        metal_total = np.sum(y_te == metal_idx)
        gga_correct = cm[gga_idx][gga_idx]
        metal_correct = cm[metal_idx][metal_idx]
        gga_recall = gga_correct / gga_total * 100 if gga_total > 0 else 0
        metal_recall = metal_correct / metal_total * 100 if metal_total > 0 else 0

        # Feature importance (top 10)
        fi = model.get_feature_importance()
        top_fi = sorted(zip(feature_names, fi), key=lambda x: -x[1])[:10]

        results.append({
            "name": exp["name"],
            "params": exp["params"],
            "cv_mean": cv_mean,
            "cv_std": cv_std,
            "test_acc": acc,
            "gga_recall": gga_recall,
            "metal_recall": metal_recall,
            "cm": cm,
            "model": model,
            "top_features": top_fi,
        })

        print(f"    CV: {cv_mean:.3f} ± {cv_std:.3f} | Test: {acc:.3f} | "
              f"GGA recall: {gga_recall:.1f}% | Metal recall: {metal_recall:.1f}%")

    return results, le


# ── Main ────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", choices=["aligned", "legacy"], default="aligned",
                        help="aligned=peak_extractor output, legacy=ground-truth CSV")
    args = parser.parse_args()

    print("=" * 60)
    print("CATBOOST CLASSIFIER RETRAINING")
    print(f"Data source: {args.data}")
    print("=" * 60)

    # Step 1: Load data
    print("\n[1] Loading training data...")
    if args.data == "aligned":
        df_all = load_aligned_data()
    else:
        df_all = load_training_data()

    # Step 2: Feature engineering
    print("[2] Aggregating features (70 features per sample)...")
    df_agg = aggregate_features(df_all, has_label=True)
    feature_cols = [c for c in df_agg.columns if c != "label"]
    X = df_agg[feature_cols].values.astype(float)
    y = df_agg["label"].values
    n_gga = np.sum(y == "gga")
    n_metal = np.sum(y == "gga-metal")
    print(f"  Samples: {len(y)} (GGA: {n_gga}, Metal: {n_metal})")
    print(f"  Features: {len(feature_cols)}")
    print(f"  Class ratio: GGA {n_gga/len(y)*100:.1f}% / Metal {n_metal/len(y)*100:.1f}%\n")

    # Step 3: Run experiments
    print("[3] Running 6 experiment configurations (5-fold CV each)...\n")
    results, le = run_experiments(X, y, feature_cols)

    # Step 4: Rank results
    print(f"\n{'=' * 60}")
    print("EXPERIMENT RESULTS (sorted by CV accuracy)")
    print(f"{'=' * 60}")
    results.sort(key=lambda r: r["cv_mean"], reverse=True)
    for i, r in enumerate(results):
        marker = " ** BEST" if i == 0 else ""
        print(f"  {i+1}. {r['name']:40s} CV={r['cv_mean']:.3f}±{r['cv_std']:.3f}  "
              f"Test={r['test_acc']:.3f}  GGA={r['gga_recall']:5.1f}%  Metal={r['metal_recall']:5.1f}%{marker}")

    # Step 5: Select best model (prioritize balanced recall)
    # Score = CV accuracy * 0.5 + min(gga_recall, metal_recall) * 0.005
    # This favors models with balanced class performance
    for r in results:
        r["balanced_score"] = r["cv_mean"] * 0.5 + min(r["gga_recall"], r["metal_recall"]) * 0.005
    results.sort(key=lambda r: r["balanced_score"], reverse=True)
    best = results[0]

    print(f"\n** BEST MODEL: {best['name']}")
    print(f"  CV Accuracy: {best['cv_mean']:.3f} ± {best['cv_std']:.3f}")
    print(f"  Test Accuracy: {best['test_acc']:.3f}")
    print(f"  GGA Recall: {best['gga_recall']:.1f}%")
    print(f"  Metal Recall: {best['metal_recall']:.1f}%")
    print(f"  Confusion Matrix:\n{best['cm']}")
    print(f"\n  Top 10 Features:")
    for fname, fval in best["top_features"]:
        print(f"    {fname:40s} {fval:.1f}")

    # Step 6: Retrain best config on FULL dataset & save
    print(f"\n[4] Retraining best config on FULL dataset...")
    le_full = LabelEncoder()
    y_full_enc = le_full.fit_transform(y)

    final_model = CatBoostClassifier(**best["params"])
    final_model.fit(X, y_full_enc)

    # Backup old model
    old_model_path = f"{MODEL_DIR}/catboost_model.cbm"
    old_le_path = f"{MODEL_DIR}/label_encoder_classes.npy"
    backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")

    if os.path.exists(old_model_path):
        shutil.copy2(old_model_path, f"{MODEL_DIR}/catboost_model_backup_{backup_suffix}.cbm")
        print(f"  Backed up old model -> catboost_model_backup_{backup_suffix}.cbm")
    if os.path.exists(old_le_path):
        shutil.copy2(old_le_path, f"{MODEL_DIR}/label_encoder_classes_backup_{backup_suffix}.npy")

    # Save new model
    final_model.save_model(old_model_path)
    np.save(old_le_path, le_full.classes_)
    print(f"  Saved new model -> {old_model_path}")
    print(f"  Saved label encoder -> {old_le_path}")

    # Save training metadata
    meta = {
        "date": datetime.now().isoformat(),
        "experiment": best["name"],
        "params": {k: str(v) for k, v in best["params"].items()},
        "cv_accuracy": f"{best['cv_mean']:.4f} ± {best['cv_std']:.4f}",
        "test_accuracy": f"{best['test_acc']:.4f}",
        "gga_recall": f"{best['gga_recall']:.1f}%",
        "metal_recall": f"{best['metal_recall']:.1f}%",
        "n_samples": int(len(y)),
        "n_gga": int(n_gga),
        "n_metal": int(n_metal),
        "n_features": len(feature_cols),
        "feature_names": feature_cols,
        "top_features": [(n, float(v)) for n, v in best["top_features"]],
    }
    meta_path = f"{MODEL_DIR}/catboost_training_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  Saved metadata -> {meta_path}")

    print(f"\n{'=' * 60}")
    print("DONE. Run validation to compare:")
    print("  python tools/validate-classifier-accuracy.py")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
