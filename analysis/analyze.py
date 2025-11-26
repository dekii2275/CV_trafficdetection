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
from load_data import load_and_normalize, DEFAULT_CLASSES


def read_tail_lines(path: str, n: int = 1000):
    """Đọc nhanh N dòng cuối của file (binary-safe). Trả về list các dòng (chuỗi).

    Mục đích: tránh đọc toàn bộ file khi file `stats.json` lớn.
    """
    lines = []
    with open(path, "rb") as f:
        f.seek(0, 2)
        file_size = f.tell()
        block_size = 4096
        data = b""
        pos = file_size
        # đọc lùi tới khi đủ số dòng hoặc tới đầu file
        while pos > 0 and len(lines) <= n:
            read_size = block_size if pos - block_size > 0 else pos
            pos -= read_size
            f.seek(pos)
            chunk = f.read(read_size)
            data = chunk + data
            lines = data.splitlines()
            if pos == 0:
                break
        # chuyển bytes -> str và chỉ lấy N dòng cuối
        result = [ln.decode("utf-8", errors="ignore") for ln in lines[-n:]]
    return result

def load_recent_stats(stats_path, minutes=10, classes=None, tail_lines: int = None):
    """
    Đọc file stats.json (JSON line-delimited) và lọc các bản ghi trong `minutes` phút gần nhất.
    Trích xuất lượng xe cho từng loại từ cột "counts" (dict).
    """
    classes = classes or DEFAULT_CLASSES
    valid = []
    # Nếu tail_lines được cung cấp thì chỉ đọc N dòng cuối (tối ưu cho realtime)
    if tail_lines is not None:
        try:
            lines = read_tail_lines(stats_path, n=tail_lines)
        except Exception:
            lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                ts = float(item.get("timestamp", 0))
                item["timestamp"] = ts
                valid.append(item)
            except Exception:
                continue
    else:
        with open(stats_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    ts = float(item.get("timestamp", 0))
                    item["timestamp"] = ts
                    valid.append(item)
                except Exception:
                    continue
    if not valid:
        print("[Load] No valid records.")
        return pd.DataFrame()

    # Lọc dữ liệu trong `minutes` phút cuối cùng (dựa trên dòng cuối cùng trong file)
    last_ts = valid[-1]["timestamp"]
    limit_ts = last_ts - minutes*60
    filtered = [it for it in valid if it["timestamp"] >= limit_ts]

    if not filtered:
        print(f"[Load] No records found in the last {minutes} minutes.")
        return pd.DataFrame()
    
    print(f"[Load] {len(filtered)} records in the last {minutes} minutes.")
    
    df = pd.DataFrame(filtered)
    
    # Trích xuất từng loại xe từ cột "counts" (dict)
    for c in classes:
        df[c] = df["counts"].apply(lambda x: x.get(c, 0) if isinstance(x, dict) else 0)
    
    # Tính tổng nếu chưa có
    if "total" not in df.columns:
        df["total"] = df[classes].sum(axis=1)
    
    # Bỏ cột counts (đã trích xuất xong)
    df = df.drop(columns=["counts"]) 
    
    return df

def aggregate_timeseries(df: pd.DataFrame, freq: str = "1T", classes: list = None) -> pd.DataFrame:
    """
    Gom dữ liệu theo khoảng thời gian (resampling).
    Dùng giá trị cuối cùng (.last()) trong mỗi khoảng và tính tổng.
    """
    classes = classes or DEFAULT_CLASSES
    d = df.copy()
    d["timestamp"] = pd.to_datetime(d["timestamp"], unit="s", origin="unix")
    d = d.set_index("timestamp")
    
    agg = d[classes].resample(freq).last().fillna(0).astype(int) 
    agg["total"] = agg[classes].sum(axis=1)
    return agg

def compute_percentages(agg_df: pd.DataFrame, classes: list = None):
    """Tính tỷ lệ phần trăm (%) của từng loại xe so với tổng cộng."""
    classes = classes or DEFAULT_CLASSES
    df = agg_df.copy()
    tot = df["total"].replace(0, np.nan)
    for c in classes:
        df[c + "_pct"] = (df[c] / tot * 100).fillna(0).round(2)
    return df


def detect_peaks(agg_df: pd.DataFrame, window: int = 5, threshold: int = None):
    """
    Phát hiện đỉnh lưu lượng (peak) dùng rolling mean + rolling std.
    - is_peak_auto: đỉnh được phát hiện tự động (mean + 3*std)
    - is_peak_thr: đỉnh dựa trên ngưỡng cố định (nếu có)
    """
    df = agg_df.copy()
    
    # Dùng shifted total để tránh nhìn trước (lookahead bias)
    shifted_total = df["total"].shift(1)
    
    # Tính trung bình động và độ lệch chuẩn
    df["rolling_mean"] = shifted_total.rolling(window=window, min_periods=1).mean()
    df["rolling_std"] = shifted_total.rolling(window=window, min_periods=2).std()
    
    # Ngưỡng peak: mean + 3*std (3 sigma rule - chỉ bắt những đỉnh cực lớn)
    threshold_line = df["rolling_mean"] + (3 * df["rolling_std"])
    
    # Tự động bỏ qua các điểm đầu tiên nếu std chưa tính được (NaN)
    df["is_peak_auto"] = df["total"] > threshold_line
    
    # Điền giá trị NaN cho output file (tính toán vẫn dùng NaN để chính xác)
    df["rolling_mean"] = df["rolling_mean"].fillna(0)
    df["rolling_std"] = df["rolling_std"].fillna(0)

    # Peak dựa trên ngưỡng cố định (nếu có)
    if threshold is not None:
        df["is_peak_thr"] = df["total"] > threshold
    else:
        df["is_peak_thr"] = False
    return df

def export_for_backend(agg_df: pd.DataFrame, out_dir: str = "data/processed"):
    """Xuất kết quả phân tích ra file CSV và JSON để backend sử dụng."""
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    csv_path = p / "traffic_data.csv"
    json_path = p / "traffic_data.json"
    df = agg_df.copy().reset_index()
    # convert timestamp -> ISO8601 (UTC) in column 'time' for frontend
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
    # write CSV (overwrite)
    df.to_csv(csv_path, index=False)

    # atomic write JSON: write to temp file then replace
    records = df.to_dict(orient="records")
    # normalize numpy types into native python types
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
    """Chuyển DataFrame phân tích thành list-of-dicts JSON-friendly.

    - Chuyển timestamp sang ISO8601 trong trường `time` nếu có.
    - Convert numpy scalar types sang python native.
    """
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
                             agg_freq: str = "1T",
                             peak_window: int = 5,
                             peak_threshold: int = None,
                             minutes_window: int = 10,
                             export: bool = False,
                             out_dir: str = "data/processed") -> tuple:
    """Phiên bản pipeline trả payload JSON-friendly cho backend/frontend.

    Trả về (merged_df, records_list). Nếu export=True thì cũng ghi CSV/JSON như trước.
    """
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
                              agg_freq: str = "1T",
                              peak_window: int = 5,
                              peak_threshold: int = None,
                              minutes_window: int = 10):
    """
    Pipeline chính: đọc -> gom -> tính % -> phát hiện đỉnh -> xuất kết quả.
    
    Args:
        stats_path: đường dẫn tới stats.json
        out_dir: thư mục xuất kết quả
        classes: danh sách loại xe
        agg_freq: tần suất gom dữ liệu (ví dụ: "1T" = 1 phút)
        peak_window: cửa sổ tính rolling stats
        peak_threshold: ngưỡng peak cố định (nếu có)
        minutes_window: lọc dữ liệu bao nhiêu phút gần nhất
    """
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