import cv2
import numpy as np


class ReflectivityAnalyzer:
    COLORS = {
        'Poor': (0, 0, 255),
        'Moderate': (0, 255, 255),
        'Good': (0, 255, 0)
    }

    @staticmethod
    def score(roi):
        g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Sort pixels to find the brightest reflective parts (text/borders)
        pixels = np.sort(g.flatten())
        # Use the top 15% of the pixels avoiding dark background colors like red/blue
        n = max(1, int(len(pixels) * 0.15))
        top_pixels = pixels[-n:]
        return round(float(np.mean(top_pixels)) / 255.0, 3)

    @staticmethod
    def classify(s):
        # Adjusted thresholds: peak reflective brightness should be high
        if s < 0.45:
            return 'Poor'
        if s < 0.65:
            return 'Moderate'
        return 'Good'

    @staticmethod
    def color(cls):
        return ReflectivityAnalyzer.COLORS.get(cls, (255, 255, 255))
