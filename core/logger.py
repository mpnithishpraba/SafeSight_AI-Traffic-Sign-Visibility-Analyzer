import csv
import os
import time
from datetime import datetime


class CSVLogger:
    HEADERS = ['Label', 'Score', 'Latitude', 'Longitude', 'Timestamp', 'LatLong']

    def __init__(self, path):
        self.path = path
        self._last = {}
        self._cooldown = 3
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(self.path, 'w', newline='') as f:
            csv.writer(f).writerow(self.HEADERS)

    def log(self, label, score, lat, lon):
        now = time.time()
        if label in self._last and (now - self._last[label]) < self._cooldown:
            return False
        self._last[label] = now
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ll = f"{lat},{lon}"
        with open(self.path, 'a', newline='') as f:
            csv.writer(f).writerow([label, score, lat, lon, ts, ll])
        return True
