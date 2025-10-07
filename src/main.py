import cv2
import yaml
import numpy as np

def load_cfg(path="configs/app.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    cfg = load_cfg()
    src = cfg["video"]["source"]
    cap = cv2.VideoCapture(0 if str(src)=="0" else src)
    assert cap.isOpened(), f"Không mở được nguồn video: {src}"

    while True:
        ok, frame = cap.read()
        if not ok: break

        # resize tạm (nếu config có)
        if "resize" in cfg["runtime"] and cfg["runtime"]["resize"]:
            w, h = cfg["runtime"]["resize"]
            frame = cv2.resize(frame, (w, h))

        # vẽ ROI line tạm để kiểm tra tọa độ
        if cfg["roi"]["mode"] == "line":
            A, B = cfg["roi"]["line"]
            cv2.line(frame, tuple(A), tuple(B), (0, 255, 0), 2)

        cv2.putText(frame, "Smoke test OK (press ESC to quit)",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        cv2.imshow("Smoke Test", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
