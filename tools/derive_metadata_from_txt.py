import pandas as pd
import numpy as np
from scipy.signal import find_peaks

def derive_metadata(txt_csv_path, window=50, smooth_window=5, distance=None):
    df = pd.read_csv(txt_csv_path)
    # ensure Time is integer index
    if 'Time' in df.columns:
        df = df[['Time','DO']]
    else:
        df = df.iloc[:,0:2]
        df.columns = ['Time','DO']

    # smooth DO to reduce noise
    df['DO_smooth'] = df['DO'].rolling(smooth_window, center=True, min_periods=1).median()

    # find local minima on smoothed signal
    inv = -df['DO_smooth'].values
    # use find_peaks on inverted signal to locate minima
    # allow overriding distance between minima (in samples)
    if distance is None:
        distance = round(window*0.6)
    peaks_min, _ = find_peaks(inv, distance=int(distance))

    rows = []
    for i, idx in enumerate(peaks_min):
        # find preceding max between previous min (or start) and this min
        start = peaks_min[i-1] if i>0 else max(0, idx - window*4)
        seg = df['DO_smooth'].iloc[start:idx+1]
        if seg.empty:
            continue
        # preceding max is argmax in segment
        max_pos = seg.idxmax()
        # compute Doin (mean of few points around max_pos)
        max_slice = df['DO'].iloc[max(0, max_pos-2):max_pos+3]
        doin = float(max_slice.mean())
        # DOmin as min around idx
        min_slice = df['DO'].iloc[max(0, idx-1):idx+2]
        domin = float(min_slice.min())
        ddo = round(doin - domin, 5)
        rows.append({'No.peak': int(df['Time'].iloc[idx]), 'Tag': None, 'Doin (mV)': round(doin,5), 'DOmin (mV)': round(domin,5), 'DDO (mV)': ddo})

    # Build DataFrame
    meta = pd.DataFrame(rows)
    # Assign sample name from file name if available
    sample_name = txt_csv_path
    meta['Sample Name'] = sample_name

    # Simple heuristic for Tag: if early peaks -> BOD10 else BOD5 (based on split)
    if len(meta) > 8:
        meta.loc[:7, 'Tag'] = 'BOD10'
        meta.loc[8:, 'Tag'] = 'BOD5'
    else:
        meta['Tag'] = 'BOD10'

    return meta[['No.peak','Tag','Doin (mV)','DOmin (mV)','DDO (mV)','Sample Name']]

if __name__ == '__main__':
    import sys
    inpath = sys.argv[1] if len(sys.argv)>1 else 'data/metadata-gga-txt_1 sample.csv'
    # optional target path for tuning
    target = sys.argv[2] if len(sys.argv)>2 else None
    if target:
        import pandas as pd
        tgt = pd.read_csv(target)
        best = None
        best_cfg = None
        # grid search over distance and smoothing
        for dist in [300, 400, 450, 500, 550]:
            for sw in [5, 11, 21]:
                try:
                    cand = derive_metadata(inpath, window=50, smooth_window=sw, distance=dist)
                except Exception:
                    continue
                # compare to target by nearest No.peak
                cols = ['Doin (mV)','DOmin (mV)','DDO (mV)']
                import numpy as np
                res = []
                for i, trow in tgt.iterrows():
                    t_idx = trow['No.peak']
                    diffs = np.abs(cand['No.peak'] - t_idx)
                    if diffs.empty:
                        res.append(1e9)
                        continue
                    j = diffs.idxmin()
                    drow = cand.loc[j]
                    diffs_vals = [abs(float(drow[c]) - float(trow[c])) for c in cols]
                    res.append(max(diffs_vals))
                maxerr = max(res)
                if best is None or maxerr < best:
                    best = maxerr
                    best_cfg = (dist, sw)
        print(f'Best max error {best} with (distance, smooth)={best_cfg}')
        # produce final with best cfg
        out = derive_metadata(inpath, window=50, smooth_window=best_cfg[1], distance=best_cfg[0])
        out.to_csv('data/derived_metadata.csv', index=False)
        print('Wrote data/derived_metadata.csv')
        print(out)
    else:
        out = derive_metadata(inpath)
        out.to_csv('data/derived_metadata.csv', index=False)
        print('Wrote data/derived_metadata.csv')
