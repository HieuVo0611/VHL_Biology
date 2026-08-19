"""
Final experiment: Combine best approach from experiments A/B/C.
Winner: B7 — CatBoost + noise injection (s=0.15, 5x) + GGA oversample (45%)
         + 81 features (original 68 + 13 robust).

Retrains on FULL augmented dataset, saves model, runs 518-file validation.

Usage: conda activate vhl && python tools/experiment-final-combine.py
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
import shutil, json
from datetime import datetime

DATA_DIR = "data"
MODEL_DIR = "model"
RANDOM_STATE = 42

# Best config from experiments: B7 approach
AUGMENT_SIGMA = 0.15
AUGMENT_COPIES = 5
GGA_TARGET_RATIO = 0.45
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


def augment_noise_on_peaks(df, n_copies=5, sigma=0.15):
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


def main():
    print("=" * 70)
    print("FINAL: COMBINE BEST APPROACHES (B7 winner)")
    print(f"  Noise injection: s={AUGMENT_SIGMA}, {AUGMENT_COPIES}x copies")
    print(f"  GGA oversample target: {GGA_TARGET_RATIO*100:.0f}%")
    print(f"  Model: CatBoost (balanced, depth=8)")
    print(f"  Features: 81 (68 original + 13 robust)")
    print("=" * 70)

    # Step 1: Load and augment
    print("\n[1] Loading and augmenting data...")
    df_raw = load_gt_data()
    print(f"  Raw: {len(df_raw)} peaks")

    df_aug = augment_noise_on_peaks(df_raw, n_copies=AUGMENT_COPIES, sigma=AUGMENT_SIGMA)
    print(f"  After noise augmentation: {len(df_aug)} peaks")

    # Step 2: Feature engineering
    print("\n[2] Aggregating features...")
    df_agg = aggregate_features(df_aug, has_label=True)
    features = [c for c in df_agg.columns if c != "label"]
    X = df_agg[features].values.astype(float)
    y = df_agg["label"].values
    print(f"  Samples: {len(y)} (GGA: {np.sum(y=='gga')}, Metal: {np.sum(y=='gga-metal')})")
    print(f"  Features: {len(features)}")

    # Step 3: GGA oversampling
    print("\n[3] Oversampling GGA class...")
    X_over, y_over = oversample_gga_features(X, y, target_ratio=GGA_TARGET_RATIO)
    n_gga = np.sum(y_over == "gga")
    n_metal = np.sum(y_over == "gga-metal")
    print(f"  After oversample: {len(y_over)} samples (GGA: {n_gga}, Metal: {n_metal})")

    # Step 4: CV evaluation
    print("\n[4] 5-fold CV evaluation...")
    le = LabelEncoder()
    y_enc = le.fit_transform(y_over)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    model = CatBoostClassifier(**CATBOOST_PARAMS)
    cv_scores = cross_val_score(model, X_over, y_enc, cv=skf, scoring="accuracy")
    print(f"  CV: {cv_scores.mean():.3f} +- {cv_scores.std():.3f}")

    # Step 5: Holdout test
    print("\n[5] Holdout test (60/40)...")
    X_tr, X_te, y_tr, y_te = train_test_split(X_over, y_enc, test_size=0.4,
                                                stratify=y_enc, random_state=RANDOM_STATE)
    model.fit(X_tr, y_tr)
    y_pred = model.predict(X_te)
    acc = accuracy_score(y_te, y_pred)
    cm = confusion_matrix(y_te, y_pred)
    gga_idx = np.where(le.classes_ == "gga")[0][0]
    metal_idx = np.where(le.classes_ == "gga-metal")[0][0]
    gga_recall = cm[gga_idx][gga_idx] / np.sum(y_te == gga_idx) * 100
    metal_recall = cm[metal_idx][metal_idx] / np.sum(y_te == metal_idx) * 100
    print(f"  Test Accuracy: {acc:.3f}")
    print(f"  GGA Recall: {gga_recall:.1f}%")
    print(f"  Metal Recall: {metal_recall:.1f}%")
    print(f"  Confusion Matrix:\n{cm}")

    # Step 6: Retrain on FULL data and save
    print("\n[6] Retraining on FULL augmented dataset...")
    final_model = CatBoostClassifier(**CATBOOST_PARAMS)
    le_full = LabelEncoder()
    y_full = le_full.fit_transform(y_over)
    final_model.fit(X_over, y_full)

    # Backup old model
    old_path = f"{MODEL_DIR}/catboost_model.cbm"
    old_le = f"{MODEL_DIR}/label_encoder_classes.npy"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if os.path.exists(old_path):
        shutil.copy2(old_path, f"{MODEL_DIR}/catboost_model_backup_{ts}.cbm")
        print(f"  Backed up old model -> catboost_model_backup_{ts}.cbm")
    if os.path.exists(old_le):
        shutil.copy2(old_le, f"{MODEL_DIR}/label_encoder_classes_backup_{ts}.npy")

    # Save new model
    final_model.save_model(old_path)
    np.save(old_le, le_full.classes_)
    print(f"  Saved new model -> {old_path}")
    print(f"  Saved label encoder -> {old_le}")

    # Save metadata
    meta = {
        "date": datetime.now().isoformat(),
        "experiment": "final-B7-noise-oversample",
        "approach": "noise s=0.15 5x + GGA oversample 45% + CatBoost balanced depth=8",
        "augmentation": {"sigma": AUGMENT_SIGMA, "copies": AUGMENT_COPIES},
        "oversample_ratio": GGA_TARGET_RATIO,
        "params": {k: str(v) for k, v in CATBOOST_PARAMS.items()},
        "cv_accuracy": f"{cv_scores.mean():.4f} +- {cv_scores.std():.4f}",
        "test_accuracy": f"{acc:.4f}",
        "gga_recall": f"{gga_recall:.1f}%",
        "metal_recall": f"{metal_recall:.1f}%",
        "n_train_samples": int(len(y_over)),
        "n_features": len(features),
        "feature_names": features,
    }
    meta_path = f"{MODEL_DIR}/catboost_training_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  Saved metadata -> {meta_path}")

    print(f"\n{'='*70}")
    print("DONE. Now run 518-file validation:")
    print("  python tools/validate-classifier-accuracy.py")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
