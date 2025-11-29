# load_data.py
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
"""load_data: đọc file stats newline-delimited và chuẩn hoá thành DataFrame nhỏ gọn."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

DEFAULT_CLASSES = ["car", "motor", "bus", "truck"]


def _read_lines(path: str) -> List[str]:
    p = Path(path)
    if not p.exists():
        return []
    return [ln.rstrip('\n') for ln in p.read_text(encoding='utf-8', errors='ignore').splitlines() if ln.strip()]


def _read_tail(path: str, n: int = 500) -> List[str]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open('rb') as f:
        f.seek(0, 2)
        size = f.tell()
        block = 4096
        data = b''
        pos = size
        lines = []
        while pos > 0 and len(lines) <= n:
            read = block if pos - block > 0 else pos
            pos -= read
            f.seek(pos)
            data = f.read(read) + data
            lines = data.splitlines()
        return [ln.decode('utf-8', errors='ignore') for ln in lines[-n:]]


def _parse_json_lines(str_lines: List[str]) -> List[Dict[str, Any]]:
    out = []
    for ln in str_lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def normalize_records(raws: List[Dict[str, Any]], classes: List[str] = None) -> pd.DataFrame:
    classes = classes or DEFAULT_CLASSES
    rows = []
    for r in raws:
        ts = r.get('timestamp', r.get('time', r.get('ts')))
        try:
            tsf = float(ts)
        except Exception:
            try:
                tsf = float(pd.to_datetime(ts, utc=True).timestamp())
            except Exception:
                tsf = None
        counts = r.get('counts') or {}
        row = {'ts': tsf}
        for c in classes:
            row[c] = int(counts.get(c, r.get(c, 0)) or 0)
        row['total'] = int(r.get('total', sum(row[c] for c in classes)))
        rows.append(row)
    df = pd.DataFrame(rows)
    if 'ts' in df.columns:
        df = df.sort_values('ts', na_position='last').reset_index(drop=True)
        df['timestamp'] = pd.to_datetime(df['ts'], unit='s', utc=True)
    else:
        df['timestamp'] = pd.NaT
    return df


def load_and_normalize(path: str, classes: List[str] = None) -> pd.DataFrame:
    lines = _read_lines(path)
    raws = _parse_json_lines(lines)
    return normalize_records(raws, classes=classes)


def load_tail_and_normalize(path: str, n: int = 500, classes: List[str] = None) -> pd.DataFrame:
    lines = _read_tail(path, n=n)
    raws = _parse_json_lines(lines)
    return normalize_records(raws, classes=classes)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--input', default='data/runtime/stats.json')
    p.add_argument('--tail', type=int, default=None)
    args = p.parse_args()
    if args.tail:
        print(load_tail_and_normalize(args.input, n=args.tail).head())
    else:
        print(load_and_normalize(args.input).head())