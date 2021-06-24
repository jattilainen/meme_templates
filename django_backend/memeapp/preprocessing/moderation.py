from nudenet import NudeDetector
from typing import List
import numpy as np

FORBIDDEN_CLASSES = [
    'EXPOSED_ANUS',
    'EXPOSED_BREAST_F',
    'EXPOSED_GENITALIA_F',
    'EXPOSED_GENITALIA_M'
]


def predict(image_paths: List[str]):
    detector = NudeDetector()
    answers = []
    for img in image_paths:
        marked = False
        pred = detector.detect(img)
        for box in pred:
            if box['label'] in FORBIDDEN_CLASSES and box['score'] > 0.5 and not marked:
                answers.append(1)
                marked = True
                break
        if not marked:
            answers.append(0)
    return np.array(answers)
