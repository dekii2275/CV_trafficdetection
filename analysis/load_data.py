# load_data.py
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from dateutil import tz

DEFAULT_CLASSES = ["car", "motor", "bus", "truck"]

def read_stats_lines(path: str, classes: List[str] = None) -> List[Dict[str, Any]]:
    """
    Đọc file stats.json (mỗi dòng một JSON) -> trả về list dict raw
    """
    classes = classes or DEFAULT_CLASSES
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{path} không tồn tại")
    raws = []
    with p.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
                raws.append(obj)
            except Exception:
                # bỏ qua dòng không parse được nhưng log ra console
                print("Warning: không thể parse line:", ln[:200])
    return raws

def normalize_records(raws: List[Dict[str, Any]], classes: List[str] = None):
    """
    Chuyển raw list -> pandas.DataFrame
    Cột: timestamp(datetime), ts (unix), car,motor,bus,truck,total
    """
    classes = classes or DEFAULT_CLASSES
    rows = []
    for r in raws:
        ts = r.get("timestamp")
        # Nếu timestamp ở dạng string ISO, thử parse
        if isinstance(ts, str):
            try:
                dt = pd.to_datetime(ts)
                ts_val = dt.timestamp()
            except Exception:
                try:
                    ts_val = float(ts)
                except Exception:
                    ts_val = None
        else:
            ts_val = float(ts) if ts is not None else None
        # danh sách counts
        counts = r.get("counts") or {}
        total = r.get("total")
        # nếu total không có, tính tổng từ counts
        if total is None:
            try:
                total = sum([int(counts.get(c, 0)) for c in classes])
            except Exception:
                total = None
        row = {"ts": ts_val, "timestamp": None, "total": total}
        # convert to datetime (local time)
        if ts_val is not None:
            try:
                # assume ts is unix seconds
                dt = datetime.fromtimestamp(ts_val)
                row["timestamp"] = dt
            except Exception:
                row["timestamp"] = None
        # add classes
        for c in classes:
            row[c] = int(counts.get(c, 0))
        rows.append(row)
    df = pd.DataFrame(rows)
    # sort by ts
    if "ts" in df.columns:
        df = df.sort_values(by="ts").reset_index(drop=True)
    # fill missing class columns (if any)
    for c in classes:
        if c not in df.columns:
            df[c] = 0
    return df

def load_and_normalize(path: str, classes: List[str] = None) -> pd.DataFrame:
    raws = read_stats_lines(path, classes=classes)
    df = normalize_records(raws, classes=classes)
    return df

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Load stats.json (line-delimited) -> output sample")
    parser.add_argument("--input", default="data/runtime/stats.json", help="path to stats.json (append mode)")
    parser.add_argument("--n", type=int, default=11, help="show first n rows")
    args = parser.parse_args()
    df = load_and_normalize(args.input)
    print(df.head(args.n))
    # save quick csv for inspection
    out_p = Path("data/processed/quick_stats.csv")
    out_p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_p, index=False)
    print("Saved quick CSV to", out_p)