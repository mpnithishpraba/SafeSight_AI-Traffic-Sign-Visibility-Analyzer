from ultralytics import YOLO


class SignDetector:
    def __init__(self, model='models/best.pt', conf=0.15):
        self.model = YOLO(model)
        self.conf = conf

    def detect(self, frame, imgsz=1280):
        # Use YOLO tracking out-of-the-box for persistence
        res = self.model.track(frame, persist=True, conf=self.conf, imgsz=imgsz, verbose=False)[0]
        dets = []
        for box in res.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2 - x1) * (y2 - y1)
            
            # Smart filter: ignore very small bounding boxes
            if area < 100:
                continue
                
            c = float(box.conf[0])
            cid = int(box.cls[0])
            
            # Extract track_id if available, fallback to a local counter or -1
            tid = int(box.id[0]) if box.id is not None else -1
            
            lbl = self.model.names[cid]
            # Format camel case labels to be more readable
            lbl = ''.join([' ' + char if char.isupper() else char for char in lbl]).strip()
            
            dets.append({
                'track_id': tid,
                'bbox': (x1, y1, x2, y2),
                'conf': c,
                'label': lbl,
                'cls_id': cid
            })
        return dets
