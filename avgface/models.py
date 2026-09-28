"""Offline face detection and landmarks."""
from __future__ import annotations
import hashlib
import os
import tempfile
from pathlib import Path
from .i18n import tr

import cv2
import numpy as np

HASHES = {
    'sface.onnx': '0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79',
    'yunet.onnx': '8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4',
    'face_landmarker.task': '64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff',
    # Both build variants validate, whichever is bundled under this filename:
    # FP32 (models/realistic_gender.onnx) and FP16 (models/realistic_gender_fp16.onnx).
    'realistic_gender.onnx': ('6979b430816434c52db5f94e3bd1042e8219faa2034ebc8b1fda867507b87af1',
                              '5f12876f1f9ce1f83ef51efd25f6c8fbd76983a7d7af9b772cd75ab7e5c1f00f'),
}


def checked(root, name):
    path = Path(root) / name
    if not path.is_file():
        raise RuntimeError(tr('模型缺失或校验失败：{0}').format(name))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = HASHES[name]
    if digest not in (expected if isinstance(expected, tuple) else (expected,)):
        raise RuntimeError(tr('模型缺失或校验失败：{0}').format(name))
    return str(path)


class OpenModels:
    def __init__(self, root):
        self.root = root
        self.detector = cv2.FaceDetectorYN_create(checked(root, 'yunet.onnx'), '', (640, 640), .75, .3, 5000)
        self.landmarker = None

    def detect(self, image, size=640, threshold=.55):
        h, w = image.shape[:2]
        scale = size / max(h, w)
        rw, rh = max(1, round(w*scale)), max(1, round(h*scale))
        canvas = np.zeros((size, size, 3), np.uint8)
        canvas[:rh, :rw] = cv2.resize(image, (rw, rh))
        self.detector.setInputSize((size, size))
        self.detector.setScoreThreshold(max(.75, threshold))
        _, detections = self.detector.detect(canvas)
        if detections is None:
            return []
        return [(np.array([f[0], f[1], f[0]+f[2], f[1]+f[3]]) / scale,
                 f[4:14].reshape(5, 2).copy() / scale, float(f[-1])) for f in detections]

    def landmarks(self, image, bbox):
        if self.landmarker is None:
            os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'avgface-mpl'))
            os.environ.setdefault('MPLBACKEND', 'Agg')
            import mediapipe as mp
            from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarksConnections as C
            self.mp = mp
            options = mp.tasks.vision.FaceLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=checked(self.root, 'face_landmarker.task')),
                running_mode=mp.tasks.vision.RunningMode.IMAGE, num_faces=1,
                min_face_detection_confidence=.5, min_face_presence_confidence=.5,
                output_face_blendshapes=False, output_facial_transformation_matrixes=False)
            self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
            self.indices = sorted({i for c in C.FACE_LANDMARKS_CONTOURS + C.FACE_LANDMARKS_NOSE for i in (c.start,c.end)})
            self.brows = sorted({i for c in C.FACE_LANDMARKS_LEFT_EYEBROW + C.FACE_LANDMARKS_RIGHT_EYEBROW for i in (c.start,c.end)})
        # Keep context around the face but not the entire group photograph.
        side = max(bbox[2:]-bbox[:2])*1.8
        center = (bbox[:2]+bbox[2:])/2
        scale = 384 / side
        matrix = np.array([[scale,0,192-center[0]*scale],[0,scale,192-center[1]*scale]],np.float32)
        crop = cv2.warpAffine(image,matrix,(384,384))
        result = self.landmarker.detect(self.mp.Image(image_format=self.mp.ImageFormat.SRGB,
                                                        data=cv2.cvtColor(crop,cv2.COLOR_BGR2RGB)))
        if not result.face_landmarks:
            raise ValueError(tr('关键点模型未确认人脸'))
        xy = np.array([(p.x*384,p.y*384) for p in result.face_landmarks[0]],np.float32)
        inverse = cv2.invertAffineTransform(matrix)
        xy = xy @ inverse[:,:2].T + inverse[:,2]
        # Metrics exclude the forehead; geometry retains the whole oval.
        selected = xy[self.indices]
        measurement = selected[selected[:,1] >= xy[self.brows,1].min()]
        return selected, measurement

    def close(self):
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None


class GenderModel:
    """Offline SigLIP2 portrait classifier, binarised to male / female.

    The Hugging Face model prithivMLmods/Realistic-Gender-Classification is a
    SigLIP2-base image-classification fine-tune (0: female portrait, 1: male
    portrait). It is converted to one self-contained ONNX file at build time
    (tools/prepare_gender_model.py); the app runs it with onnxruntime only.
    """

    def __init__(self, root):
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        opts.intra_op_num_threads = 2
        opts.inter_op_num_threads = 1
        self.session = ort.InferenceSession(checked(root, 'realistic_gender.onnx'),
                                            opts, providers=["CPUExecutionProvider"])
        self.input = self.session.get_inputs()[0].name

    @staticmethod
    def preprocess(bgr):
        """Match SiglipImageProcessor: resize 224x224 bicubic, /127.5-1."""
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_CUBIC)
        return ((resized.astype(np.float32) / 127.5) - 1.0).transpose(2, 0, 1)[None]

    def classify(self, bgr):
        logits = self.session.run(None, {self.input: self.preprocess(bgr)})[0].reshape(-1)
        return ('male' if int(np.argmax(logits)) == 1 else 'female'), logits

    def close(self):
        self.session = None
