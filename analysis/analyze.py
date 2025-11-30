import pandas as pd
import numpy as np
from pathlib import Path
import json
import os
import tempfile
from load_data import DEFAULT_CLASSES, load_and_normalize, load_tail_and_normalize

def load_recent_stats(stats_path, minutes=60, classes=None, tail_lines: int = None):
    classes = classes or DEFAULT_CLASSES
    buffer_minutes = minutes + 5 
    try:
        if tail_lines is not None:
            df = load_tail_and_normalize(stats_path, n=tail_lines, classes=classes)
        else:
            df = load_and_normalize(stats_path, classes=classes)
    except Exception as e:
        print(f"[Load] error reading stats: {e}")
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    if 'timestamp' in df.columns and not df['timestamp'].isna().all():
        last_ts = df['timestamp'].dropna().iloc[-1]
        limit_ts = last_ts - pd.Timedelta(minutes=buffer_minutes)
        df = df[df['timestamp'] >= limit_ts].copy()
    if df.empty:
        return pd.DataFrame()
    for c in classes:
        if c not in df.columns:
            df[c] = 0
    df = df.sort_values('timestamp')
    return df.reset_index(drop=True)


def aggregate_timeseries(df: pd.DataFrame, freq: str = "5min", classes: list = None) -> pd.DataFrame:
    classes = classes or DEFAULT_CLASSES
    d = df.copy()
    if 'timestamp' in d.columns:
        d = d.set_index('timestamp')
    resampler = d[classes].resample(freq)
    agg_max = resampler.max().ffill()
    agg_min = resampler.min().ffill()
    agg_flow = agg_max.diff()
    if not agg_max.empty:
        raw_first_flow = agg_max.iloc[0] - agg_min.iloc[0]
        scaled_first_flow = raw_first_flow * 1.25
        scaled_first_flow = scaled_first_flow.round().astype(int)
        agg_flow.iloc[0] = agg_flow.iloc[0].fillna(scaled_first_flow)
    agg_flow = agg_flow.clip(lower=0)
    agg_flow["total"] = agg_flow[classes].sum(axis=1)
    return agg_flow.astype(int)

def compute_percentages(agg_df: pd.DataFrame, classes: list = None):
    classes = classes or DEFAULT_CLASSES
    df = agg_df.copy()
    tot = df["total"].replace(0, np.nan)
    for c in classes:
        df[c + "_pct"] = (df[c] / tot * 100).fillna(0).round(2)
    return df

def detect_peaks(agg_df: pd.DataFrame, window: int = 5, threshold: int = None):
    df = agg_df.copy()
    shifted_total = df["total"].shift(1)
    df["rolling_mean"] = shifted_total.rolling(window=window, min_periods=1).mean()
    df["rolling_std"] = shifted_total.rolling(window=window, min_periods=2).std()
    threshold_line = df["rolling_mean"] + (3 * df["rolling_std"])
    df["is_peak_auto"] = df["total"] > threshold_line
    df["rolling_mean"] = df["rolling_mean"].fillna(0)
    df["rolling_std"] = df["rolling_std"].fillna(0)
    if threshold is not None:
        df["is_peak_thr"] = df["total"] > threshold
    else:
        df["is_peak_thr"] = False
    return df

def export_for_backend(agg_df: pd.DataFrame, out_dir: str = "data/processed"):
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    csv_path = p / "traffic_data.csv"
    json_path = p / "traffic_data.json"
    
    df = agg_df.copy().reset_index()
    if "timestamp" in df.columns:
        df["time"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        df = df.drop(columns=["timestamp"])
    df.to_csv(csv_path, index=False)
    records = df.to_dict(orient="records")
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=str(p))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(json_path))
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return str(csv_path), str(json_path)

def to_json_records(df: pd.DataFrame) -> list:
    if df is None or df.empty:
        return []
    out = df.copy().reset_index()
    if "timestamp" in out.columns:
        out["time"] = out["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        out = out.drop(columns=["timestamp"])
    return out.to_dict(orient="records")

def analyze_pipeline_realtime(stats_path: str,
                              out_dir: str = "data/processed",
                              classes: list = None,
                              agg_freq: str = "5min",
                              peak_window: int = 5,
                              peak_threshold: int = None,
                              minutes_window: int = 60):
    classes = classes or DEFAULT_CLASSES
    
    df = load_recent_stats(stats_path, minutes=minutes_window, classes=classes)
    if df.empty:
        return pd.DataFrame()
    agg = aggregate_timeseries(df, freq=agg_freq, classes=classes)
    if not agg.empty:
        cutoff_time = agg.index[-1] - pd.Timedelta(minutes=minutes_window)
        agg = agg[agg.index >= cutoff_time]
    perc = compute_percentages(agg, classes=classes)
    peak_df = detect_peaks(agg, window=peak_window, threshold=peak_threshold)
    merged = perc.join(peak_df[["is_peak_auto", "is_peak_thr"]], how="left")
    export_for_backend(merged, out_dir=out_dir)
    return merged

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/runtime/stats.json")
    parser.add_argument("--out", default="data/processed")
    parser.add_argument("--freq", default="5min")
    parser.add_argument("--threshold", type=int, default=None)
    args = parser.parse_args()
    df = analyze_pipeline_realtime(args.input, out_dir=args.out, agg_freq=args.freq, 
                                   peak_threshold=args.threshold, minutes_window=60)
    print(df)