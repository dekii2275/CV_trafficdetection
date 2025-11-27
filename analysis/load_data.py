# load_data.py

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime, timezone

DEFAULT_CLASSES = ["car", "motor", "bus", "truck"]

def read_stats_lines(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{path} không tồn tại")
    raws: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
                raws.append(obj)
            except Exception:
                print("Warning: không thể parse line:", ln[:200])
    return raws


def read_stats_tail(path: str, n: int = 500) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{path} không tồn tại")
    lines: List[bytes] = []
    with p.open("rb") as f:
        f.seek(0, 2)
        file_size = f.tell()
        block_size = 4096
        data = b""
        pos = file_size
        while pos > 0 and len(lines) <= n:
            read_size = block_size if pos - block_size > 0 else pos
            pos -= read_size
            f.seek(pos)
            chunk = f.read(read_size)
            data = chunk + data
            lines = data.splitlines()
            if pos == 0:
                break
    str_lines = [ln.decode("utf-8", errors="ignore") for ln in lines[-n:]]
    objs: List[Dict[str, Any]] = []
    for ln in str_lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            objs.append(json.loads(ln))
        except Exception:
            continue
    return objs


def _parse_timestamp(candidate) -> Optional[float]:
    if candidate is None:
        return None
    if isinstance(candidate, (int, float)):
        try:
            return float(candidate)
        except Exception:
            return None
    if isinstance(candidate, pd.Timestamp):
        try:
            return float(candidate.tz_convert('UTC').timestamp()) if candidate.tzinfo else float(candidate.timestamp())
        except Exception:
            return None
    if isinstance(candidate, str):
        s = candidate.strip()
        try:
            return float(s)
        except Exception:
            try:
                dt = pd.to_datetime(s, utc=True)
                return float(dt.timestamp())
            except Exception:
                return None
    return None


def normalize_records(raws: List[Dict[str, Any]], classes: List[str] = None) -> pd.DataFrame:
    classes = classes or DEFAULT_CLASSES
    rows: List[Dict[str, Any]] = []
    for r in raws:
        candidate = r.get('timestamp', r.get('time', r.get('ts', None)))
        ts_val = _parse_timestamp(candidate)
        counts = r.get('counts') or {}
        total = r.get('total')
        row: Dict[str, Any] = {"ts": ts_val}
        for c in classes:
            try:
                row[c] = int(counts.get(c, 0))
            except Exception:
                try:
                    row[c] = int(r.get(c, 0))
                except Exception:
                    row[c] = 0
        if total is None:
            try:
                row['total'] = sum(int(row[c]) for c in classes)
            except Exception:
                row['total'] = None
        else:
            try:
                row['total'] = int(total)
            except Exception:
                row['total'] = None
        rows.append(row)
    df = pd.DataFrame(rows)
    if 'ts' in df.columns:
        df = df.sort_values(by='ts', na_position='last').reset_index(drop=True)
    for c in classes:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    if 'ts' in df.columns:
        try:
            df['timestamp'] = pd.to_datetime(df['ts'], unit='s', utc=True)
        except Exception:
            df['timestamp'] = pd.NaT
    else:
        df['timestamp'] = pd.NaT
    if 'total' in df.columns:
        df['total'] = pd.to_numeric(df['total'], errors='coerce').fillna(0).astype(int)
    else:
        df['total'] = df[classes].sum(axis=1).astype(int)
    return df

def load_and_normalize(path: str, classes: List[str] = None) -> pd.DataFrame:
    raws = read_stats_lines(path)
    df = normalize_records(raws, classes=classes)
    return df

def load_tail_and_normalize(path: str, n: int = 500, classes: List[str] = None) -> pd.DataFrame:
    raws = read_stats_tail(path, n=n)
    df = normalize_records(raws, classes=classes)
    return df

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Load stats.json (line-delimited) -> sample')
    parser.add_argument('--input', default='data/runtime/stats.json')
    parser.add_argument('--tail', type=int, default=None, help='read only last N lines')
    args = parser.parse_args()
    if args.tail:
        df = load_tail_and_normalize(args.input, n=args.tail)
    else:
        df = load_and_normalize(args.input)
    print(df.head())