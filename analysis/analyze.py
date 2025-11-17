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
from datetime import timedelta
from load_data import load_and_normalize, DEFAULT_CLASSES

def load_recent_stats(stats_path, minutes=10, classes=None):
    """
    Đọc file stats.json (JSON line-delimited) và lọc các bản ghi trong `minutes` phút gần nhất.
    Trích xuất lượng xe cho từng loại từ cột "counts" (dict).
    """
    classes = classes or DEFAULT_CLASSES
    valid = []
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
    df.rename(columns={"timestamp": "time"}, inplace=True)
    df["time"] = df["time"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if hasattr(x, "strftime") else x)
    df.to_csv(csv_path, index=False)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)
    return str(csv_path), str(json_path)

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