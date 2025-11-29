"""
analyze.py: Xử lý pipeline dữ liệu thống kê giao thông (real-time)
1. Đọc file stats.json và lọc dữ liệu gần nhất
2. Gom dữ liệu theo khoảng thời gian (resampling)
3. Tính tỷ lệ phần trăm từng loại xe
4. Phát hiện đỉnh lưu lượng (peak detection)
5. Xuất kết quả ra CSV/JSON
"""
import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import timedelta, datetime, timezone
import os
import tempfile
from load_data import DEFAULT_CLASSES, load_and_normalize, load_tail_and_normalize


def load_recent_stats(stats_path, minutes=10, classes=None, tail_lines: int = None):
    classes = classes or DEFAULT_CLASSES
    try:
        if tail_lines is not None:
            df = load_tail_and_normalize(stats_path, n=tail_lines, classes=classes)
        else:
            df = load_and_normalize(stats_path, classes=classes)
    except Exception as e:
        print(f"[Load] error reading stats: {e}")
        return pd.DataFrame()
    if df is None or df.empty:
        print("[Load] No valid records.")
        return pd.DataFrame()
    if 'ts' in df.columns and not df['ts'].isna().all():
        last_ts = float(df['ts'].dropna().iloc[-1])
        limit_ts = last_ts - minutes * 60
        df = df[df['ts'] >= limit_ts].copy()
    elif 'timestamp' in df.columns and not df['timestamp'].isna().all():
        last_ts = df['timestamp'].dropna().iloc[-1].timestamp()
        limit_ts = pd.to_datetime(last_ts - minutes * 60, unit='s', utc=True)
        df = df[df['timestamp'] >= pd.to_datetime(limit_ts, utc=True)].copy()
    if df.empty:
        print(f"[Load] No records found in the last {minutes} minutes.")
        return pd.DataFrame()
    print(f"[Load] {len(df)} records in the last {minutes} minutes.")
    for c in classes:
        if c not in df.columns:
            df[c] = 0
    if 'total' not in df.columns:
        df['total'] = df[classes].sum(axis=1)
    return df.reset_index(drop=True)

def aggregate_timeseries(df: pd.DataFrame, freq: str = "1min", classes: list = None) -> pd.DataFrame:
    classes = classes or DEFAULT_CLASSES
    d = df.copy()
    if 'timestamp' in d.columns and pd.api.types.is_datetime64_any_dtype(d['timestamp']):
        d = d.set_index('timestamp')
    elif 'ts' in d.columns:
        d['timestamp'] = pd.to_datetime(d['ts'], unit='s', utc=True)
        d = d.set_index('timestamp')
    else:
        d['timestamp'] = pd.to_datetime(d.get('timestamp'))
        d = d.set_index('timestamp')
    agg = d[classes].resample(freq).last().fillna(0).astype(int)
    agg["total"] = agg[classes].sum(axis=1)
    return agg

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
        def _to_iso(x):
            try:
                if pd.isna(x):
                    return None
                if isinstance(x, pd.Timestamp):
                    s = x.isoformat()
                    # append Z for naive timestamps to indicate UTC
                    if x.tzinfo is None:
                        s = s + "Z"
                    return s
                if hasattr(x, "strftime"):
                    return x.strftime("%Y-%m-%dT%H:%M:%SZ")
                return str(x)
            except Exception:
                return str(x)
        df["time"] = df["timestamp"].apply(_to_iso)
        df = df.drop(columns=["timestamp"])
    df.to_csv(csv_path, index=False)
    records = df.to_dict(orient="records")
    def _normalize_value(v):
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
        if isinstance(v, (np.bool_,)):
            return bool(v)
        return v
    norm_records = []
    for r in records:
        nr = {k: _normalize_value(v) for k, v in r.items()}
        norm_records.append(nr)
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=str(p))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(norm_records, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(json_path))
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    return str(csv_path), str(json_path)


def to_json_records(df: pd.DataFrame) -> list:
    if df is None or df.empty:
        return []
    out = df.copy().reset_index()
    if "timestamp" in out.columns:
        def _fmt(x):
            if pd.isna(x):
                return None
            if isinstance(x, pd.Timestamp):
                s = x.isoformat()
                if x.tzinfo is None:
                    s = s + "Z"
                return s
            try:
                return pd.to_datetime(x).isoformat() + "Z"
            except Exception:
                return str(x)
        out["time"] = out["timestamp"].apply(_fmt)
        out = out.drop(columns=["timestamp"])
    records = out.to_dict(orient="records")
    norm = []
    for r in records:
        nr = {}
        for k, v in r.items():
            if isinstance(v, (np.integer,)):
                nr[k] = int(v)
            elif isinstance(v, (np.floating,)):
                nr[k] = float(v)
            elif isinstance(v, (np.bool_,)):
                nr[k] = bool(v)
            else:
                nr[k] = v
        norm.append(nr)
    return norm

def analyze_pipeline_for_api(stats_path: str,
                             classes: list = None,
                             agg_freq: str = "1min",
                             peak_window: int = 5,
                             peak_threshold: int = None,
                             minutes_window: int = 10,
                             export: bool = False,
                             out_dir: str = "data/processed") -> tuple:
    classes = classes or DEFAULT_CLASSES
    df = load_recent_stats(stats_path, minutes=minutes_window, classes=classes)
    if df.empty:
        return pd.DataFrame(), []
    agg = aggregate_timeseries(df, freq=agg_freq, classes=classes)
    perc = compute_percentages(agg, classes=classes)
    peak_df = detect_peaks(agg, window=peak_window, threshold=peak_threshold)
    merged = perc.join(peak_df[["is_peak_auto", "is_peak_thr"]], how="left")
    if export:
        export_for_backend(merged, out_dir=out_dir)
    records = to_json_records(merged)
    return merged, records

def analyze_pipeline_realtime(stats_path: str,
                              out_dir: str = "data/processed",
                              classes: list = None,
                              agg_freq: str = "1min",
                              peak_window: int = 5,
                              peak_threshold: int = None,
                              minutes_window: int = 10):
    classes = classes or DEFAULT_CLASSES
    df = load_recent_stats(stats_path, minutes=minutes_window, classes=classes)
    if df.empty:
        return pd.DataFrame()    
    agg = aggregate_timeseries(df, freq=agg_freq, classes=classes)
    perc = compute_percentages(agg, classes=classes)
    peak_df = detect_peaks(agg, window=peak_window, threshold=peak_threshold)
    merged = perc.join(peak_df[["is_peak_auto", "is_peak_thr"]], how="left")
    
    csv_path, json_path = export_for_backend(merged, out_dir=out_dir)
    print("Exported:", csv_path, json_path)
    return merged

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/runtime/stats.json")
    parser.add_argument("--out", default="data/processed")
    parser.add_argument("--freq", default="1min")
    parser.add_argument("--threshold", type=int, default=None)
    args = parser.parse_args()
    df = analyze_pipeline_realtime(args.input, out_dir=args.out, agg_freq=args.freq, 
                                   peak_threshold=args.threshold, minutes_window=10)
    print(df)