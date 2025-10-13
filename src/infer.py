import os
import json
import time
import cv2
import yaml
import sys
import argparse
from ultralytics import YOLO

# Try to import yt_dlp for resolving YouTube stream URLs. It's optional but
# recommended when the `source` in config is a YouTube link.
try:
    from yt_dlp import YoutubeDL
except Exception:
    YoutubeDL = None


def load_cfg(path: str | None = None):
    # Resolve default config path relative to this file, so running from any CWD works
    if path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(script_dir, os.pardir))
        path = os.path.join(repo_root, "configs", "app.yaml")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def unsharp_mask(img, strength=1.0):
    """Simple unsharp mask sharpening."""
    blur = cv2.GaussianBlur(img, (0, 0), sigmaX=3)
    sharp = cv2.addWeighted(img, 1.0 + strength, blur, -strength, 0)
    return sharp


def apply_clahe(img):
    """Apply CLAHE on the L channel in LAB color space."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    lab2 = cv2.merge((l2, a, b))
    return cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)


def denoise(img):
    """Fast non-local means denoising for color images."""
    return cv2.fastNlMeansDenoisingColored(img, None, h=10, hColor=10, templateWindowSize=7, searchWindowSize=21)


def preprocess_frame(frame, cfg):
    pcfg = cfg.get("preprocess", {}) if cfg else {}
    if pcfg.get("denoise", False):
        frame = denoise(frame)
    if pcfg.get("clahe", False):
        frame = apply_clahe(frame)
    if pcfg.get("sharpen", False):
        frame = unsharp_mask(frame, strength=float(pcfg.get("sharpen_strength", 0.8)))
    # Note: super-resolution (DNN) can be added later if desired
    return frame


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Traffic detection from YouTube link")
    parser.add_argument("--test-stream", action="store_true", help="Resolve and test opening the YouTube stream, then exit")
    parser.add_argument("--config", default=None, help="Path to config YAML")
    args = parser.parse_args()

    cfg = load_cfg(args.config)

    # Resolve repo root relative to this file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, os.pardir))

    # Helper to make absolute path relative to repo root
    def resolve_repo_path(p: str) -> str:
        if p is None:
            return None  # type: ignore
        return p if os.path.isabs(p) else os.path.join(repo_root, p)

    src = cfg["video"]["source"]
    save_output = bool(cfg["video"].get("save_output", True))
    output_path = cfg["video"].get("output", "data/output/result.mp4")

    # Require that the source is a YouTube link. This program is intended to
    # only view video from YouTube links; other input types are rejected.
    src_str = str(src).strip()
    if not (src_str.startswith("http://") or src_str.startswith("https://")):
        print("Error: this program only accepts YouTube HTTP/HTTPS URLs as `video.source` in config.")
        print("Please set `video.source` to a YouTube link (e.g. https://www.youtube.com/watch?v=...) and try again.")
        sys.exit(1)

    if not ("youtube.com" in src_str or "youtu.be" in src_str):
        print("Error: provided URL is not a YouTube link. This program only supports YouTube links.")
        sys.exit(1)

    # Resolve YouTube link to a direct playable stream URL using yt-dlp (must be installed)
    if YoutubeDL is None:
        print("Error: yt-dlp is not installed. Please install yt-dlp (pip install yt-dlp) to resolve YouTube streams.")
        sys.exit(1)

    def resolve_stream_url(url: str) -> str | None:
        """Return a direct stream URL from a YouTube link using yt-dlp.

        Strategy: prefer formats that contain both video and audio and use
        http/https or HLS (m3u8). Prefer mp4/webm containers when possible.
        """
        try:
            ydl_opts = {"quiet": True, "skip_download": True}
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception:
            return None

        formats = info.get("formats") or [info]
        candidates = []
        for f in formats:
            f_url = f.get("url")
            if not f_url:
                continue
            vcodec = f.get("vcodec")
            acodec = f.get("acodec")
            protocol = (f.get("protocol") or "").lower()
            ext = (f.get("ext") or "").lower()
            has_av = (vcodec and vcodec != "none") and (acodec and acodec != "none")
            if not any(p in protocol for p in ("http", "https", "m3u8")):
                continue
            candidates.append((has_av, ext, protocol, f))

        candidates.sort(key=lambda x: (not x[0], 0 if x[1] == "mp4" else 1, 0 if "http" in x[2] else 1))
        if candidates:
            chosen = candidates[0][3]
            return chosen.get("url")
        return info.get("url")

    resolved = resolve_stream_url(src_str)
    if resolved:
        print(f"Resolved YouTube URL to stream: {resolved}")
        src = resolved
    else:
        print("Error: could not resolve YouTube stream via yt-dlp.")
        sys.exit(1)

    # If user only wants to test stream opening, do it now and exit without loading the model
    if args.test_stream:
        print("--test-stream: testing cv2.VideoCapture on resolved URL...")
        cap = None
        try:
            backends = [cv2.CAP_ANY]
            if hasattr(cv2, "CAP_FFMPEG"):
                backends.append(cv2.CAP_FFMPEG)
            if hasattr(cv2, "CAP_GSTREAMER"):
                backends.append(cv2.CAP_GSTREAMER)
            ok_open = False
            for b in backends:
                cap = cv2.VideoCapture(src, b)
                if cap is not None and cap.isOpened():
                    ok_open = True
                    break
            if ok_open:
                print("Stream opened successfully via OpenCV backend.")
                # Try reading one frame
                ret, frame = cap.read()
                if ret:
                    print("Read one frame successfully. Preprocessing test...")
                    frame2 = preprocess_frame(frame, cfg)
                    print("Preprocessing OK. Exiting.")
                else:
                    print("Warning: opened stream but failed to read a frame.")
            else:
                print("Failed to open stream with available OpenCV backends.")
        except Exception as e:
            print("Exception while testing stream:", e)
        finally:
            try:
                if cap is not None:
                    cap.release()
            except Exception:
                pass
        return
    output_path = resolve_repo_path(str(output_path))

    model_path = resolve_repo_path(str(cfg["yolo"]["weights"]))
    conf = float(cfg["yolo"].get("conf", 0.25))
    iou = float(cfg["yolo"].get("iou", 0.5))

    visualize = bool(cfg["runtime"].get("visualize", True))
    resize = cfg["runtime"].get("resize")
    show_counts = bool(cfg["runtime"].get("show_counts", True))
    count_conf = float(cfg["runtime"].get("count_conf", 0.5))

    # ROI cấu hình: dùng hình chữ nhật để tạo vùng đếm
    roi_mode = cfg.get("roi", {}).get("mode", "rect")
    roi_rect_cfg = cfg.get("roi", {}).get("rect", [[200, 300], [900, 700]])  # [[x1,y1],[x2,y2]] or "center"
    roi_rect_ratio = cfg.get("roi", {}).get("rect_ratio", [0.5, 0.4])  # used when rect == "center"

    # Load model
    model = YOLO(model_path)

    # Open video robustly (try default, FFMPEG, then GStreamer)
    cap = None
    if str(src) == "0":
        cap = cv2.VideoCapture(0)
    else:
        backends = [cv2.CAP_ANY]
        # Some systems require explicit backends for WEBM
        if hasattr(cv2, "CAP_FFMPEG"):
            backends.append(cv2.CAP_FFMPEG)
        if hasattr(cv2, "CAP_GSTREAMER"):
            backends.append(cv2.CAP_GSTREAMER)

        for backend in backends:
            cap = cv2.VideoCapture(src, backend)
            if cap.isOpened():
                break

    assert cap is not None and cap.isOpened(), (
        f"Không mở được nguồn video: {src}. Hãy thử đổi sang MP4 hoặc cài FFmpeg/GStreamer."
    )

    writer = None
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps is None or fps <= 1:
        fps = 30.0

    window_name = "Traffic Inference"

    # Đường dẫn ghi thống kê thời gian thực cho backend/frontend
    stats_path = os.path.join(repo_root, "data", "runtime", "stats.json")
    ensure_parent_dir(stats_path)
    t_last = time.time()
    smoothed_fps = fps

    # Trạng thái đếm theo ID: tránh đếm lặp lại cùng 1 đối tượng
    # - id_was_inside: theo dõi ID đang ở trong ROI ở frame trước
    # - counted_ids_per_class: ID nào đã được tính điểm cho mỗi lớp
    id_was_inside = {}
    counted_ids_per_class = {}

    first_frame_done = False
    roi_rect_runtime = None  # sẽ tính khi có frame đầu tiên nếu dùng "center"
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if resize and len(resize) == 2:
            frame = cv2.resize(frame, (int(resize[0]), int(resize[1])))

        # Nếu dùng ROI ở giữa, tính hình chữ nhật theo kích thước khung hình ngay sau frame đầu
        if roi_mode == "rect" and roi_rect_runtime is None:
            h0, w0 = frame.shape[:2]
            if isinstance(roi_rect_cfg, str) and roi_rect_cfg == "center":
                rw = max(1, int(w0 * float(roi_rect_ratio[0])))
                rh = max(1, int(h0 * float(roi_rect_ratio[1])))
                cx, cy = w0 // 2, h0 // 2
                x1 = max(0, cx - rw // 2)
                y1 = max(0, cy - rh // 2)
                x2 = min(w0 - 1, x1 + rw)
                y2 = min(h0 - 1, y1 + rh)
                roi_rect_runtime = [(x1, y1), (x2, y2)]
            elif isinstance(roi_rect_cfg, str) and roi_rect_cfg == "full":
                # Dùng toàn bộ khung hình làm ROI
                roi_rect_runtime = [(0, 0), (w0 - 1, h0 - 1)]
            else:
                # dùng trực tiếp từ cấu hình nếu là 2 điểm
                if isinstance(roi_rect_cfg, list) and len(roi_rect_cfg) == 2:
                    (x1, y1), (x2, y2) = roi_rect_cfg
                    roi_rect_runtime = [(int(x1), int(y1)), (int(x2), int(y2))]

        # Lazy init writer after first valid frame so size is always correct
        if save_output and writer is None:
            h, w = frame.shape[:2]
            ensure_parent_dir(output_path)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

        # Theo dõi (tracking) để có ID ổn định giữa các frame
        # persist=True giúp duy trì ID theo thời gian
        results = model.track(source=frame, conf=conf, iou=iou, verbose=False, persist=True)

        # results is a list with one element (for single frame)
        plotted = frame
        per_class_counts = {}
        if results:
            r = results[0]
            plotted = r.plot()

            # Nếu cấu hình ROI là hình chữ nhật, vẽ nó để minh họa
            if roi_mode == "rect" and roi_rect_runtime and len(roi_rect_runtime) == 2:
                (x1, y1), (x2, y2) = roi_rect_runtime
                cv2.rectangle(plotted, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

            # Đếm khi tâm bbox đi VÀO ROI lần đầu (per-ID, per-class)
            if r.boxes is not None and len(r.boxes) > 0:
                boxes = r.boxes.xyxy.cpu().numpy()
                cls_ids = r.boxes.cls.cpu().numpy().astype(int)
                confs = r.boxes.conf.cpu().numpy()
                ids = r.boxes.id.cpu().numpy().astype(int) if r.boxes.id is not None else None
                names = r.names

                # Hàm kiểm tra tâm nằm trong ROI hình chữ nhật
                def is_inside_rect(cx: float, cy: float) -> bool:
                    if roi_mode != "rect" or not roi_rect_runtime or len(roi_rect_runtime) != 2:
                        return False
                    (rx1, ry1), (rx2, ry2) = roi_rect_runtime
                    x_min, x_max = min(rx1, rx2), max(rx1, rx2)
                    y_min, y_max = min(ry1, ry2), max(ry1, ry2)
                    return x_min <= cx <= x_max and y_min <= cy <= y_max

                for i in range(len(boxes)):
                    # Bỏ qua nếu không có ID theo dõi
                    if ids is None:
                        continue
                    obj_id = int(ids[i])
                    cls_id = int(cls_ids[i])
                    conf_i = float(confs[i])
                    if conf_i < count_conf:
                        continue

                    # Tính tâm bbox
                    x1, y1, x2, y2 = boxes[i]
                    cx = (x1 + x2) / 2.0
                    cy = (y1 + y2) / 2.0

                    inside = is_inside_rect(cx, cy)
                    was_inside = id_was_inside.get(obj_id, False)

                    # Sự kiện ENTER: trước ở ngoài, giờ ở trong => tăng count 1 lần
                    if inside and not was_inside:
                        name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
                        if name not in counted_ids_per_class:
                            counted_ids_per_class[name] = set()
                        if obj_id not in counted_ids_per_class[name]:
                            counted_ids_per_class[name].add(obj_id)
                    # Cập nhật trạng thái inside hiện tại
                    id_was_inside[obj_id] = inside

                # Tổng hợp số đếm hiện tại theo lớp (số ID đã vào ROI ít nhất 1 lần)
                for name, id_set in counted_ids_per_class.items():
                    per_class_counts[name] = len(id_set)

        # Overlay tổng số đã đếm theo từng lớp
        if show_counts and per_class_counts:
            y0 = 30
            dy = 25
            x = 10
            for i, (k, v) in enumerate(sorted(per_class_counts.items())):
                txt = f"{k}: {v}"
                cv2.putText(plotted, txt, (x, y0 + i * dy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Cập nhật và ghi thống kê ra file JSON cho backend/frontend
        now = time.time()
        dt = max(1e-6, now - t_last)
        t_last = now
        smoothed_fps = 0.9 * smoothed_fps + 0.1 * (1.0 / dt)

        stats = {
            "timestamp": now,
            "fps": round(float(smoothed_fps), 1),
            "counts": per_class_counts,
            "total": int(sum(per_class_counts.values()) if per_class_counts else 0),
        }
        try:
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False)
        except Exception:
            pass

        if save_output and writer is not None:
            writer.write(plotted)

        if visualize:
            cv2.imshow(window_name, plotted)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
                break

    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()


