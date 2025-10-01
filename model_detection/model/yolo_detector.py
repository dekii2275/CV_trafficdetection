from ultralytics import YOLO
import cv2
class YOLODetector:
    def __init__(self,model_path,device='auto'):
        self.model=YOLO(model_path)
        self.set_device(device)
    def set_device(self,device):
        self.device=device
        if device in ('cuda','cpu','mps'):
            self.model.to(device)
    def detect_frame(self,frame,conf_threshold = 0.25,):
        results=self.model.track(frame,persist=True)[0]
        vehicle_dict=[]
        for box in results.boxes:
            track_id=int(box.id.tolist()[0])
            result=box.xyxy.tolist()[0]
            object_cls_id=box.cls.tolist()[0]
            score = float(box.conf.tolist()[0])
            if (score >=conf_threshold):
                vehicle_dict.append({
                "id": track_id,
                "bbox": result,
                "cls": object_cls_id,
                "score": score
                })
        return vehicle_dict
    def detect_frames(self,frames):
        vehicle_detections=[]
        for frame in frames:
            detections=self.detect_frame(frame)
            vehicle_detections.append(detections)
        return vehicle_detections

    def detect_video(self,video_path,stride=1, conf_threshold = 0.25,max_frames=None,):
        cap=cv2.VideoCapture(video_path)
        output_frames=[]
        all_detections=[]
        frame_idx=0
        processed=0
        while cap.isOpened():
            ret,frame=cap.read()
            if not ret:
                break
            if frame_idx % stride == 0:
                detections=self.detect_frame(frame, conf_threshold=conf_threshold)
                output_frames.append(frame)
                all_detections.append(detections)
                processed+=1
                if max_frames is not None and processed>=max_frames:
                    break
            frame_idx+=1
        cap.release()
        return output_frames,all_detections
    def draw_bboxes(self,video_frames,vehicle_detections):
        output_video_frame=[]
        for frame, vehicle_dict in zip(video_frames,vehicle_detections):
            for item in vehicle_dict:
                x1,y1,x2,y2=item['bbox']
                track_id=item['id']
                cv2.putText(frame,f"Vehicle ID: {track_id}",(int(x1),int(y1-10)),cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
            output_video_frame.append(frame)
        return output_video_frame

