"""
Experiment C: Multi-model ensemble strategies.
Tests: CatBoost, XGBoost, RF individually + soft voting + stacking.
Uses expert ground-truth training data.

Usage: conda activate vhl && python tools/experiment-c-ensemble.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.ensemble import RandomForestClassifier, VotingClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from catboost import CatBoostClassifier
from src.utils import aggregate_features

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("WARNING: XGBoost not available, skipping XGB experiments")

DATA_DIR = "data"
RANDOM_STATE = 42


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


def evaluate_model(model, X, y_enc, le, experiment_name):
    """Evaluate a single sklearn-compatible model."""
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
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
          f"Test={acc:.3f}  GGA={gga_recall:.1f}%  Metal={metal_recall:.1f}%")
    return {
        "name": experiment_name, "cv_mean": cv_scores.mean(), "cv_std": cv_scores.std(),
        "test_acc": acc, "gga_recall": gga_recall, "metal_recall": metal_recall,
    }


def main():
    print("=" * 70)
    print("EXPERIMENT C: MULTI-MODEL ENSEMBLE")
    print("=" * 70)

    df_raw = load_gt_data()
    df_agg = aggregate_features(df_raw, has_label=True)
    features = [c for c in df_agg.columns if c != "label"]
    X = df_agg[features].values.astype(float)
    y = df_agg["label"].values

    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    n_gga = np.sum(y == "gga")
    n_metal = np.sum(y == "gga-metal")
    print(f"\nSamples: {len(y)} (GGA: {n_gga}, Metal: {n_metal})")
    print(f"Features: {len(features)}\n")

    results = []

    # C1: CatBoost alone (baseline)
    print("[C1] CatBoost (balanced, depth=8)...")
    cb = CatBoostClassifier(iterations=300, learning_rate=0.05, depth=8,
                            verbose=0, random_state=RANDOM_STATE,
                            auto_class_weights="Balanced")
    results.append(evaluate_model(cb, X, y_enc, le, "C1: CatBoost (balanced, depth=8)"))

    # C2: Random Forest
    print("\n[C2] Random Forest (300 trees, balanced)...")
    rf = RandomForestClassifier(n_estimators=300, max_depth=12,
                                class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1)
    results.append(evaluate_model(rf, X, y_enc, le, "C2: Random Forest (300 trees, balanced)"))

    # C3: XGBoost
    if HAS_XGB:
        print("\n[C3] XGBoost (depth=8, balanced)...")
        scale_pw = n_metal / n_gga
        xgb = XGBClassifier(n_estimators=300, max_depth=8, learning_rate=0.05,
                            scale_pos_weight=scale_pw, random_state=RANDOM_STATE,
                            eval_metric='logloss', use_label_encoder=False)
        results.append(evaluate_model(xgb, X, y_enc, le, "C3: XGBoost (depth=8, balanced)"))

    # C4: Soft Voting (CB + RF + XGB)
    print("\n[C4] Soft Voting Ensemble...")
    estimators = [
        ('cb', CatBoostClassifier(iterations=300, learning_rate=0.05, depth=8,
                                   verbose=0, random_state=RANDOM_STATE,
                                   auto_class_weights="Balanced")),
        ('rf', RandomForestClassifier(n_estimators=300, max_depth=12,
                                      class_weight="balanced", random_state=RANDOM_STATE)),
    ]
    if HAS_XGB:
        estimators.append(('xgb', XGBClassifier(n_estimators=300, max_depth=8,
                                                 learning_rate=0.05,
                                                 scale_pos_weight=n_metal/n_gga,
                                                 random_state=RANDOM_STATE,
                                                 eval_metric='logloss',
                                                 use_label_encoder=False)))
    voting = VotingClassifier(estimators=estimators, voting='soft')
    results.append(evaluate_model(voting, X, y_enc, le, "C4: Soft Voting (CB+RF+XGB)"))

    # C5: Stacking with LR meta-learner
    print("\n[C5] Stacking (LR meta-learner)...")
    stacking = StackingClassifier(
        estimators=estimators,
        final_estimator=LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        cv=5, passthrough=False
    )
    results.append(evaluate_model(stacking, X, y_enc, le, "C5: Stacking (LR meta-learner)"))

    # Summary
    print(f"\n{'='*70}")
    print("EXPERIMENT C SUMMARY (sorted by balanced score)")
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
