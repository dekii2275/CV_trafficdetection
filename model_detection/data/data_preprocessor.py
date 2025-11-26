import os, glob, json
from collections import Counter
import cv2
import numpy as np
import yaml
import pathlib
import matplotlib.pyplot as plt
from pathlib import Path
import random
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

def remap_yolo_labels(
    base_dirs,
    id_map={5: 0, 6: 1, 7: 2, 4: 3},
):
    """
    Remap label IDs trong file YOLO:
    - Mapping cũ → mới theo id_map
    - Các ID không nằm trong id_map sẽ bị cảnh báo
    - Ghi đè trực tiếp file gốc
    """

    unknown_ids = set()
    total_files = 0

    for base in base_dirs:
        for file_path in glob.glob(f"{base}/*.txt"):
            new_lines = []

            with open(file_path, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if not parts:
                        continue

                    # Lấy ID cũ
                    try:
                        old_id = int(float(parts[0]))
                    except:
                        print(f"⚠️ Lỗi ID trong file: {file_path} → dòng: {line.strip()}")
                        continue

                    # Áp dụng map
                    if old_id in id_map:
                        new_id = id_map[old_id]
                    else:
                        # Nếu ID không có trong map → cảnh báo
                        unknown_ids.add(old_id)
                        new_id = old_id  # hoặc bỏ qua tùy bạn

                    # Ghi lại dòng
                    parts[0] = str(new_id)
                    new_lines.append(" ".join(parts) + "\n")

            # Ghi đè file
            with open(file_path, "w") as f:
                f.writelines(new_lines)

            total_files += 1

    print(f"✅ Đã cập nhật {total_files} file label.")
    if unknown_ids:
        print(f"⚠️ Các ID không có trong mapping (không được đổi): {unknown_ids}")
def visualize_image_with_bbox(image_path, label_path, bbox_line, class_names):
    
    img = cv2.imread(str(image_path))
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img_rgb.shape[:2]
    
    parts = bbox_line.split()
    cls_id = int(float(parts[0]))
    x_center = float(parts[1])
    y_center = float(parts[2])
    bbox_w = float(parts[3])
    bbox_h = float(parts[4])
    
   
    x = (x_center - bbox_w / 2) * w
    y = (y_center - bbox_h / 2) * h
    width = bbox_w * w
    height = bbox_h * h
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.imshow(img_rgb)
    
    rect = plt.Rectangle((x, y), width, height, 
                        linewidth=3, edgecolor='lime', facecolor='none')
    ax.add_patch(rect)
    
    class_name = class_names[cls_id] if cls_id < len(class_names) else f"Class {cls_id}"
    ax.text(x, y - 10, f"{class_name} (ID: {cls_id})", 
           color='lime', fontsize=12, weight='bold',
           bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
    
    ax.set_title(f"Class: {class_name} - {image_path.name}", fontsize=14, weight='bold')
    ax.axis('off')
    plt.tight_layout()
    plt.show()
def get_one_image_per_class(images_dir, labels_dir, class_names):
   
    images_dir = Path(images_dir)
    labels_dir = Path(labels_dir)
    
    class_samples = {}  
    
    
    for label_file in labels_dir.glob("*.txt"):
        image_file = images_dir / (label_file.stem + ".jpg")
        if not image_file.exists():
            continue
            
        with open(label_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                
                cls_id = int(float(parts[0]))
                
                if cls_id not in class_samples:
                    class_samples[cls_id] = (image_file, label_file, line.strip())
                    
                if len(class_samples) == len(class_names):
                    break
        
        if len(class_samples) == len(class_names):
            break
    
    return class_samples