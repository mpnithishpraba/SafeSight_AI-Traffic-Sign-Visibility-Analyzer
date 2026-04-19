import os
from datetime import datetime


class FileManager:
    @staticmethod
    def ensure(path):
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def csv_path(base):
        FileManager.ensure(base)
        d = datetime.now().strftime("%d-%m-%Y")
        i = 1
        while True:
            p = os.path.join(base, f"{d}({i}).csv")
            if not os.path.exists(p):
                return p
            i += 1

    @staticmethod
    def img_path(label, lat, lon, save_dir):
        FileManager.ensure(save_dir)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_label = label.replace(" ", "_")
        return os.path.join(save_dir, f"{safe_label}_{lat}_{lon}_{ts}.jpg")
