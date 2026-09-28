"""Local SFace similarity. Scores are cosine similarities, never probabilities.

The cache lives only in memory and contains no group labels. It is not used to
infer attributes or transfer labels between photos.
"""
from pathlib import Path
import cv2
import numpy as np
from .common import Cancelled, resource_dir
from .models import checked


class Similarity:
    def __init__(self):
        self.model = None
        self.cache = {}

    def feature(self, image, five):
        if self.model is None:
            self.model = cv2.FaceRecognizerSF_create(checked(resource_dir() / 'models', 'sface.onnx'), '')
        h, w = image.shape[:2]
        row = np.r_[0, 0, w, h, np.asarray(five).reshape(-1), 1].astype(np.float32)
        aligned = self.model.alignCrop(image, row)
        value = self.model.feature(aligned).reshape(-1)
        norm = np.linalg.norm(value)
        if not np.isfinite(norm) or norm < 1e-8:
            raise ValueError('Unable to compute a valid face feature')
        return value / norm

    def vectors(self, faces, cancelled, progress):
        result = []
        for i, face in enumerate(faces):
            if cancelled():
                raise Cancelled()
            if face.id not in self.cache:
                self.cache[face.id] = self.feature(face.image, face.five)
            result.append(self.cache[face.id])
            progress(i + 1, len(faces))
        return np.asarray(result)

    def rank(self, faces, averages, cancelled=lambda: False, progress=lambda n,t: None):
        eligible = [f for f in faces if f.enabled and f.group in averages]
        vectors = self.vectors(eligible, cancelled, progress)
        result = {}
        for group, (image, _) in averages.items():
            if cancelled():
                raise Cancelled()
            indices = [i for i,f in enumerate(eligible) if f.group == group]
            if not indices:
                continue
            # All average portraits use the mean geometry of their contributors.
            five = np.mean([eligible[i].five for i in indices], axis=0)
            target = self.feature(image, five)
            scores = np.clip(vectors[indices] @ target, -1, 1)
            near, far = int(np.argmax(scores)), int(np.argmin(scores))
            result[group] = ((eligible[indices[near]], float(scores[near])),
                             (eligible[indices[far]], float(scores[far])))
        return result

    def compare(self, query, faces, cancelled=lambda: False, progress=lambda n,t: None):
        eligible = [f for f in faces if f.enabled]
        if not eligible:
            return []
        vectors = self.vectors(eligible, cancelled, progress)
        if cancelled():
            raise Cancelled()
        target = self.feature(query.image, query.five)
        scores = np.clip(vectors @ target, -1, 1)
        order = np.argsort(-scores, kind='stable')[:10]
        return [(eligible[i], float(scores[i])) for i in order]

    def clear(self):
        self.cache.clear()
