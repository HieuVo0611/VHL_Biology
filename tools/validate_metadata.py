import pandas as pd
import numpy as np
import sys

def validate(pred_path, target_path, tol=0.05):
    pred = pd.read_csv(pred_path)
    target = pd.read_csv(target_path)

    # Expected numeric columns in target: 'Doin (mV)','DOmin (mV)','DDO (mV)'
    num_cols = ['Doin (mV)','DOmin (mV)','DDO (mV)']

    results = []
    for _, trow in target.iterrows():
        t_idx = trow['No.peak']
        # find nearest No.peak in prediction
        if 'No.peak' not in pred.columns:
            raise ValueError('Prediction file missing No.peak column')
        diffs = np.abs(pred['No.peak'] - t_idx)
        if diffs.empty:
            results.append({'No.peak': t_idx, 'matched': False, 'errors': None})
            continue
        j = diffs.idxmin()
        prow = pred.loc[j]
        errors = {c: abs(float(prow.get(c, np.nan)) - float(trow[c])) for c in num_cols}
        results.append({'No.peak': t_idx, 'matched': True, 'pred_row': int(prow['No.peak']), 'errors': errors})

    # summarize
    max_errs = {c: 0.0 for c in num_cols}
    mean_errs = {c: 0.0 for c in num_cols}
    count = 0
    for r in results:
        if not r['matched']:
            continue
        count += 1
        for c in num_cols:
            max_errs[c] = max(max_errs[c], r['errors'][c])
            mean_errs[c] += r['errors'][c]
    if count:
        for c in num_cols:
            mean_errs[c] /= count

    overall_ok = all(max_errs[c] <= tol for c in num_cols)

    print('Validation results:')
    print('Pred file:', pred_path)
    print('Target file:', target_path)
    print('Rows compared:', len(results))
    print('Max errors:', max_errs)
    print('Mean errors:', mean_errs)
    print('Within tolerance', tol, ':', overall_ok)
    return {'max_errs': max_errs, 'mean_errs': mean_errs, 'ok': overall_ok, 'results': results}

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python validate_metadata.py <pred.csv> <target.csv> [tol]')
        sys.exit(1)
    pred = sys.argv[1]
    target = sys.argv[2]
    tol = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
    validate(pred, target, tol)
