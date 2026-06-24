"""
Validate phase detector on all GT sheets.
Reports per-peak 3-class accuracy and per-sample boundary ±N accuracy.

CAVEAT: This validates on training data (no holdout). Use CV from
tools/train-phase-detector.py as the true generalization metric.
This script is for regression detection and integration sanity.
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from src.phase_detector import update_phase_tags

CONFIG = {
    'gga':   {'gt': 'data/phase-gt-gga.csv',   'cls_label': 'GGA'},
    'metal': {'gt': 'data/phase-gt-metal.csv', 'cls_label': 'Metal'},
    'hh':    {'gt': 'data/phase-gt-hh.csv',    'cls_label': 'Metal'},  # HH detected by DDO P90 inside detector
}


def find_phase1_end(labels):
    """Last index labeled 0 (or -1 if none)."""
    arr = np.array(labels)
    zeros = np.where(arr == 0)[0]
    return int(zeros[-1]) if len(zeros) > 0 else -1


def validate(kind):
    cfg = CONFIG[kind]
    if not os.path.exists(cfg['gt']):
        print(f'[SKIP] {cfg["gt"]} not found')
        return
    df = pd.read_csv(cfg['gt']).dropna(subset=['DDO'])
    samples = df['Sample Name'].unique()
    print(f'[{kind.upper()}] {len(samples)} samples, {len(df)} peaks')

    all_true, all_pred = [], []
    diffs = []
    for sn in samples:
        g = df[df['Sample Name'] == sn].sort_values('peak_idx').reset_index(drop=True)
        renamed = g.rename(columns={'Doin': 'Doin (mV)', 'DOmin': 'DOmin (mV)', 'DDO': 'DDO (mV)'})
        renamed['Tag'] = 'unknown'
        renamed['Sample Name'] = sn
        out = update_phase_tags(renamed, cfg['cls_label'])
        tag_to_int = {'phase1': 0, 'transition': 1, 'phase2': 2}
        pred_int = np.array([tag_to_int.get(t, -1) for t in out['Tag']])
        true_int = g['phase_label'].to_numpy(dtype=int)
        all_true.extend(true_int.tolist())
        all_pred.extend(pred_int.tolist())
        diffs.append(abs(find_phase1_end(pred_int) - find_phase1_end(true_int)))

    all_true = np.array(all_true)
    all_pred = np.array(all_pred)
    diffs = np.array(diffs)

    peak_acc = float(np.mean(all_true == all_pred))
    exact = float(np.mean(diffs == 0))
    within1 = float(np.mean(diffs <= 1))
    within2 = float(np.mean(diffs <= 2))
    print(f'  Per-peak 3-class acc: {peak_acc:.4f}')
    print(f'  Per-sample boundary exact: {exact:.4f}')
    print(f'  Per-sample boundary +/-1 : {within1:.4f}')
    print(f'  Per-sample boundary +/-2 : {within2:.4f}')


def main():
    print('=' * 60)
    print('CAVEAT: Validates on TRAINING data (no holdout).')
    print('True generalization comes from CV in train-phase-detector.py:')
    print('  Metal: 93.2% peak-CV, HH: 94.1% peak-CV')
    print('=' * 60)
    for kind in ('gga', 'metal', 'hh'):
        validate(kind)


if __name__ == '__main__':
    main()
