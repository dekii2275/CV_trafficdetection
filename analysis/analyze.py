"""analyze: gọn nhẹ - aggregate, percent, peak detection, export."""

import pandas as pd
import numpy as np
from pathlib import Path
import json, os, tempfile
from load_data import DEFAULT_CLASSES, load_and_normalize, load_tail_and_normalize


def load_recent_stats(path, minutes=10, classes=None, tail_lines=None):
    classes = classes or DEFAULT_CLASSES
    df = load_tail_and_normalize(path, n=tail_lines, classes=classes) if tail_lines else load_and_normalize(path, classes=classes)
    if df is None or df.empty:
        return pd.DataFrame()
    if 'ts' in df.columns and df['ts'].notna().any():
        last = float(df['ts'].dropna().iloc[-1])
        df = df[df['ts'] >= last - minutes * 60]
    elif 'timestamp' in df.columns and df['timestamp'].notna().any():
        last = df['timestamp'].dropna().iloc[-1].timestamp()
        df = df[df['timestamp'] >= pd.to_datetime(last - minutes * 60, unit='s', utc=True)]
    if df.empty:
        return pd.DataFrame()
    for c in classes:
        if c not in df.columns:
            df[c] = 0
    if 'total' not in df.columns:
        df['total'] = df[DEFAULT_CLASSES].sum(axis=1)
    return df.reset_index(drop=True)


def aggregate_timeseries(df, freq='1T', classes=None):
    classes = classes or DEFAULT_CLASSES
    d = df.copy()
    if 'ts' in d.columns:
        d['timestamp'] = pd.to_datetime(d['ts'], unit='s', utc=True)
    if 'timestamp' in d.columns:
        d = d.set_index('timestamp')
    agg = d[classes].resample(freq).last().fillna(0).astype(int)
    agg['total'] = agg[classes].sum(axis=1)
    return agg


def compute_percentages(agg_df, classes=None):
    classes = classes or DEFAULT_CLASSES
    df = agg_df.copy()
    tot = df['total'].replace(0, np.nan)
    for c in classes:
        df[c + '_pct'] = (df[c] / tot * 100).fillna(0).round(2)
    return df


def detect_peaks(agg_df, window=5, threshold=None):
    df = agg_df.copy()
    m = df['total'].shift(1).rolling(window=window, min_periods=1).mean()
    s = df['total'].shift(1).rolling(window=window, min_periods=2).std().fillna(0)
    df['rolling_mean'] = m.fillna(0)
    df['rolling_std'] = s
    df['is_peak_auto'] = df['total'] > (m + 3 * s)
    df['is_peak_thr'] = df['total'] > threshold if threshold is not None else False
    return df


def _isoify(df):
    out = df.copy().reset_index()
    if 'timestamp' in out.columns:
        out['time'] = out['timestamp'].apply(lambda x: x.isoformat() + 'Z' if pd.notna(x) else None)
        out = out.drop(columns=['timestamp'])
    return out


def export_for_backend(agg_df, out_dir='data/processed'):
    p = Path(out_dir); p.mkdir(parents=True, exist_ok=True)
    csv_path = p / 'traffic_data.csv'
    json_path = p / 'traffic_data.json'
    df = _isoify(agg_df)
    df.to_csv(csv_path, index=False)
    records = df.to_dict(orient='records')
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.json', dir=str(p))
    try:
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(json_path))
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    return str(csv_path), str(json_path)


def analyze_pipeline_for_api(path, classes=None, agg_freq='1T', peak_window=5, peak_threshold=None, minutes_window=10, export=False, out_dir='data/processed'):
    classes = classes or DEFAULT_CLASSES
    df = load_recent_stats(path, minutes=minutes_window, classes=classes)
    if df.empty:
        return pd.DataFrame(), []
    agg = aggregate_timeseries(df, freq=agg_freq, classes=classes)
    perc = compute_percentages(agg, classes=classes)
    peaks = detect_peaks(agg, window=peak_window, threshold=peak_threshold)
    merged = perc.join(peaks[['is_peak_auto', 'is_peak_thr']], how='left')
    if export:
        export_for_backend(merged, out_dir=out_dir)
    return merged, _isoify(merged).to_dict(orient='records')


def analyze_pipeline_realtime(path, out_dir='data/processed', classes=None, agg_freq='1T', peak_window=5, peak_threshold=None, minutes_window=10):
    df, _ = analyze_pipeline_for_api(path, classes=classes, agg_freq=agg_freq, peak_window=peak_window, peak_threshold=peak_threshold, minutes_window=minutes_window, export=True, out_dir=out_dir)
    return df


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--input', default='data/runtime/stats.json')
    p.add_argument('--out', default='data/processed')
    p.add_argument('--freq', default='1min')
    p.add_argument('--threshold', type=int, default=None)
    args = p.parse_args()
    print(analyze_pipeline_realtime(args.input, out_dir=args.out, agg_freq=args.freq, peak_threshold=args.threshold))