import os, glob, json
from typing import Dict, List, Tuple
from collections import Counter
import cv2
import numpy as np
import yaml
import pathlib
def load_data_set(data_path):
    with open (data_path,"r") as f:
        cfg = yaml.safe_load(f)
        paths = {
            "train_images": cfg["train"],
            "val_images": cfg["val"],
            "test_images": cfg.get("test"),
            "names": cfg["names"],
            "nc": cfg["nc"],
        }
    paths["train_labels"] = infer_labels_dir(paths["train_images"])
    paths["val_labels"] = infer_labels_dir(paths["val_images"])
    paths["test_labels"] = infer_labels_dir(paths["test_images"])
    return paths
def infer_labels_dir(images_dir):
    if images_dir is None: return None
    return images_dir.replace("/images", "/labels")
def verify_image_label_pairs(images_dir, labels_dir) :
    errors = []
    img_paths = sorted(glob.glob(os.path.join(images_dir, "**", "*.*"), recursive=True))
    for p  in (img_paths):
        _, ext = os.path.splitext(p)
        if ext.lower() not in (".jpg", ".jpeg", ".png", ".bmp"):
            continue
        lbl = os.path.join(labels_dir, pathlib.Path(p).stem + ".txt")
        if not os.path.isfile(lbl):
            errors.append(f"Missing label: {lbl}")
    return errors
def compute_dataset_stats(images_dir, labels_dir, small_thr_px = 32) :
    img_paths=sorted(glob.glob(os.path.join(images_dir,"**","*.*"),recursive=True))
    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    img_paths=[p for p in img_paths if os.path.splitext(p)[1].lower() in exts]
    stats = {
        "num_images": 0,
        "num_labels": 0,
        "classes": set(),
        "labels_per_class": Counter(),
        "small_boxes": 0,
        "small_box_ratio": 0.0
    }
    stats['num_images']=len(img_paths)
    for img_path in img_paths:
        img=cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        base=os.path.splitext(os.path.basename(img_path))[0]
        label_path = os.path.join(labels_dir, base + ".txt")
        if not os.path.exists(label_path):
            continue
        with open(label_path,"r") as f:
            lines = f.readlines()
        for line in lines:
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            cls_id, x_center, y_center, bw, bh = map(float, parts)
            cls_id = int(cls_id)
            stats['num_labels']+=1
            stats['classes'].add(cls_id)
            stats['labels_per_class'][cls_id]+=1
            box_w, box_h = bw * w, bh * h
            if box_w < small_thr_px or box_h < small_thr_px:
                stats["small_boxes"] += 1
    if stats['num_labels']>0:
        if stats["num_labels"] > 0:
            stats["small_box_ratio"] = stats["small_boxes"] / stats["num_labels"]
    stats["classes"] = sorted(list(stats["classes"]))
    stats["labels_per_class"] = dict(stats["labels_per_class"])

    return stats



def clip_and_fix_boxes(labels_dir: str, min_box_wh: float = 1e-4) -> int:
    #AI Code
    """
    Clamp các bbox YOLO-normalized về [0,1] và loại bỏ bbox invalid/quá nhỏ.
    Trả về tổng số dòng nhãn bị sửa hoặc xóa.
    """
    def _clip01(x: float) -> float:
        return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

    changed = 0
    label_files = glob.glob(os.path.join(labels_dir, "**", "*.txt"), recursive=True)

    for lf in label_files:
        try:
            with open(lf, "r") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
        except Exception:
            continue

        new_lines = []
        for ln in lines:
            parts = ln.split()
            if len(parts) < 5:
                changed += 1
                continue
            try:
                cls = int(float(parts[0]))
                x = _clip01(float(parts[1]))
                y = _clip01(float(parts[2]))
                w = _clip01(float(parts[3]))
                h = _clip01(float(parts[4]))
            except Exception:
                changed += 1
                continue

            if w < min_box_wh or h < min_box_wh:
                changed += 1
                continue

            fixed = f"{cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}"
            if fixed != ln:
                changed += 1
            new_lines.append(fixed)

        with open(lf, "w") as f:
            f.write("\n".join(new_lines) + ("\n" if new_lines else ""))

    return changed

