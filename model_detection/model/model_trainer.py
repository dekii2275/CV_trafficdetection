import yaml
from ultralytics import YOLO
from pathlib import Path
import cv2
import time
def load_training_config(training_config_path):
    with open(training_config_path,"r",encoding="utf-8") as f:
        config=yaml.safe_load(f)
    return config
def train_model(weights,training_config_path):
    model=YOLO(weights)
    config=load_training_config(training_config_path)
    model.train(**config)
    save_dir = getattr(getattr(model, "trainer", None), "save_dir", None) or Path("runs/detect/exp")
    return str(Path(save_dir) / "weights" / "best.pt")
def valid_model(model_path,data_path):
    model=YOLO(model_path)
    results=model.val(data=data_path)
    return results
def benchmark_on_video(model_path: str, video_path: str, save_output: bool = False, output_path: str = "output.mp4"):
    # Load model
    #AICODE
    model = YOLO(model_path)

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Không mở được video {video_path}")

    # Lưu video nếu cần
    writer = None
    if save_output:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = cap.get(cv2.CAP_PROP_FPS)
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    frame_count = 0
    total_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        start = time.time()
        results = model(frame)   # chạy inference trên frame
        end = time.time()

        frame_count += 1
        total_time += (end - start)

        # Vẽ kết quả lên frame
        annotated_frame = results[0].plot()

        if save_output and writer:
            writer.write(annotated_frame)

        # Hiển thị
        cv2.imshow("YOLO Benchmark", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()

    avg_fps = frame_count / total_time if total_time > 0 else 0
    print(f"[INFO] Processed {frame_count} frames in {total_time:.2f}s, ~{avg_fps:.2f} FPS")

    return avg_fps

