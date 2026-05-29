"""
Train RandomForest phase detectors for Metal and HH.
No augmentation: noise augmentation was removed because it provided no benefit
and previously caused GroupKFold leakage (noisy copies had distinct group names).
Saves to model/phase_detector_{metal,hh}.pkl
"""
import sys
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import accuracy_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from src.phase_features import compute_peak_features, FEATURE_COLUMNS

GT_PATHS = {
    'metal': 'data/phase-gt-metal.csv',
    'hh': 'data/phase-gt-hh.csv',
}

RF_PARAMS = dict(
    n_estimators=200,
    max_depth=8,
    min_samples_leaf=5,
    class_weight='balanced',
    n_jobs=-1,
    random_state=42,
)


def build_xy(gt_df):
    """
    Compute features per sample (group by Sample Name), stack X, y, groups.
    """
    X_parts, y_parts, g_parts = [], [], []
    for sn, group in gt_df.groupby('Sample Name'):
        group = group.sort_values('peak_idx').reset_index(drop=True)
        renamed = group.rename(columns={
            'Doin': 'Doin (mV)', 'DOmin': 'DOmin (mV)', 'DDO': 'DDO (mV)'
        })
        feats = compute_peak_features(renamed)
        X_parts.append(feats.to_numpy(dtype=float))
        y_parts.append(group['phase_label'].to_numpy(dtype=int))
        g_parts.append(np.full(len(group), sn))
    return np.vstack(X_parts), np.concatenate(y_parts), np.concatenate(g_parts)


def cv_evaluate(X, y, groups, label):
    """5-fold GroupKFold CV. Prints per-peak accuracy."""
    kf = GroupKFold(n_splits=5)
    accs = []
    for fold, (tr, te) in enumerate(kf.split(X, y, groups)):
        model = RandomForestClassifier(**RF_PARAMS)
        model.fit(X[tr], y[tr])
        pred = model.predict(X[te])
        acc = accuracy_score(y[te], pred)
        accs.append(acc)
        print(f'  [{label}] fold {fold+1}: acc={acc:.4f}')
    print(f'  [{label}] CV mean: {np.mean(accs):.4f} +- {np.std(accs):.4f}')


def train_and_save(kind):
    np.random.seed(42)
    path = GT_PATHS[kind]
    if not os.path.exists(path):
        print(f'[SKIP] {path} missing')
        return
    df = pd.read_csv(path)
    df = df.dropna(subset=['DDO']).reset_index(drop=True)
    print(f'[{kind.upper()}] loaded {len(df)} peaks from {df["Sample Name"].nunique()} samples')

    X, y, groups = build_xy(df)
    print(f'  X.shape={X.shape}, classes={np.bincount(y)}')

    print(f'[{kind.upper()}] 5-fold GroupKFold CV:')
    cv_evaluate(X, y, groups, kind)

    print(f'[{kind.upper()}] training final model on all data...')
    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(X, y)
    os.makedirs('model', exist_ok=True)
    out_path = f'model/phase_detector_{kind}.pkl'
    joblib.dump(model, out_path)
    print(f'  saved -> {out_path}')


def main():
    train_and_save('metal')
    train_and_save('hh')


if __name__ == '__main__':
    main()
