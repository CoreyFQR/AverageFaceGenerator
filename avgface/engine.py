"""Local alignment and averaging with user-provided labels."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from .i18n import tr

import cv2
import numpy as np
from PIL import Image, ImageOps

from .common import WIDTH, HEIGHT, GROUP_NAMES, METRICS, Cancelled, resource_dir


@dataclass
class Face:
    id: str
    source: str
    index: int
    image: np.ndarray
    points: np.ndarray
    five: np.ndarray
    group: str
    metrics: dict
    enabled: bool = True
    valid_mask: np.ndarray | None = None
    backend: str = "open"
    label_source: str = tr('人工标签')
    group_photo: bool = False


def read_image(path):
    with Image.open(path) as im:
        if im.width * im.height > 80_000_000:
            raise ValueError(tr('图片超过 8000 万像素，请先缩小'))
        im = ImageOps.exif_transpose(im)
        im.thumbnail((6000, 6000), Image.Resampling.LANCZOS)
        if "A" in im.getbands() or "transparency" in im.info:
            rgba = im.convert("RGBA")
            base = Image.new("RGBA", rgba.size, "white")
            im = Image.alpha_composite(base, rgba)
        return cv2.cvtColor(np.asarray(im.convert("RGB")), cv2.COLOR_RGB2BGR)


def write_image(path, bgr):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg"):
        raise ValueError(tr('导出文件必须是 PNG 或 JPG'))
    ok, buf = cv2.imencode(suffix, bgr)
    if not ok:
        raise OSError(tr('图片编码失败'))
    path.write_bytes(buf.tobytes())


def transform_points(points, matrix):
    return (points @ matrix[:, :2].T + matrix[:, 2]).astype(np.float32)


def similarity(source, target):
    """Least-squares similarity fit, preserving facial proportions."""
    a, b = source.mean(0), target.mean(0)
    x, y = source - a, target - b
    u, s, vt = np.linalg.svd(y.T @ x / len(x))
    d = np.ones(2)
    if np.linalg.det(u @ vt) < 0:
        d[-1] = -1
    rotation = u @ np.diag(d) @ vt
    scale = float(s @ d) / max(float(np.mean(np.sum(x*x, axis=1))), 1e-8)
    return np.column_stack((scale * rotation, b - scale * rotation @ a)).astype(np.float32)


def measure(points, five):
    width, height = np.ptp(points, axis=0)
    if min(width, height) < 1:
        raise ValueError(tr('关键点无效'))
    eye = float(np.linalg.norm(five[0] - five[1]))
    mouth = float(np.linalg.norm(five[3] - five[4]))
    return dict(eye_px=eye, width_px=float(width), height_px=float(height),
                eye_width=eye/width, mouth_width=mouth/width,
                height_width=height/width,
                nose_height=float(five[2, 1] - five[:2, 1].mean())/height)


class Engine:
    def __init__(self, model_dir=None, backend="open"):
        from .models import OpenModels
        cv2.setNumThreads(2)
        root = Path(model_dir or resource_dir() / "models")
        self.backend = backend
        self.open = None
        if backend == "open":
            self.open = OpenModels(root)
            return
        if backend != "insightface":
            raise ValueError(tr('未知人脸处理模型'))
        manifest = json.loads((root / "manifest.json").read_text("utf-8"))
        import onnxruntime as ort
        opts = ort.SessionOptions()
        # SCRFD's output metadata is fixed to 640, but its graph supports dynamic sizes.
        opts.log_severity_level = 3
        opts.intra_op_num_threads = 2
        opts.inter_op_num_threads = 1
        self.sessions = {}
        for key, entry in manifest["models"].items():
            if key not in ("detector", "landmark"):
                continue
            path = root / entry["file"]
            if path.resolve().parent != root.resolve():
                raise ValueError(tr('模型路径必须位于所选模型文件夹内'))
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                raise RuntimeError(tr('模型缺失或损坏：{0}。请重新下载完整程序。').format(path.name))
            self.sessions[key] = ort.InferenceSession(str(path), opts, providers=["CPUExecutionProvider"])
        self.config = manifest["models"]

    def close(self):
        if self.open:
            self.open.close()

    def run(self, key, blob):
        session = self.sessions[key]
        return session.run(None, {session.get_inputs()[0].name: blob})

    def detect(self, image, size=640, threshold=.55):
        if self.open:
            return self.open.detect(image, size, threshold)
        h, w = image.shape[:2]
        scale = size / max(h, w)
        rw, rh = max(1, round(w*scale)), max(1, round(h*scale))
        canvas = np.zeros((size, size, 3), np.uint8)
        canvas[:rh, :rw] = cv2.resize(image, (rw, rh))
        outputs = self.run("detector", cv2.dnn.blobFromImage(canvas, 1/128, (size, size), (127.5,)*3, swapRB=True))
        boxes, scores, points = [], [], []
        for i, stride in enumerate((8, 16, 32)):
            score = outputs[i].reshape(-1)
            ids = np.flatnonzero(score >= threshold)
            yy, xx = np.mgrid[:size//stride, :size//stride]
            anchors = np.repeat(np.column_stack((xx.ravel(), yy.ravel())), 2, axis=0) * stride
            a = anchors[ids]
            delta = outputs[i+3].reshape(-1, 4)[ids] * stride
            boxes.append(np.column_stack((a-delta[:, :2], a+delta[:, 2:])) / scale)
            scores.append(score[ids])
            points.append((outputs[i+6].reshape(-1, 5, 2)[ids]*stride + a[:, None, :])/scale)
        boxes, scores, points = np.concatenate(boxes), np.concatenate(scores), np.concatenate(points)
        xywh = boxes.copy()
        xywh[:, 2:] -= xywh[:, :2]
        keep = np.asarray(cv2.dnn.NMSBoxes(xywh.tolist(), scores.tolist(), threshold, .4)).reshape(-1)
        return [(boxes[i], points[i].astype(np.float32), float(scores[i])) for i in keep]

    def dense_detect(self, image, cancelled=lambda: False):
        """Overlapping tiles preserve small faces in high-resolution group photos."""
        found = self.detect(image, 960)
        h, w = image.shape[:2]
        if max(h, w) > 1400:
            def starts(length):
                return sorted(set(list(range(0, max(1, length-1199), 900)) + [max(0, length-1200)]))
            for y in starts(h):
                for x in starts(w):
                    if cancelled():
                        raise Cancelled()
                    for box, kps, score in self.detect(image[y:y+1200, x:x+1200], 960):
                        # Avoid accepting faces truncated at internal tile edges.
                        th, tw = image[y:y+1200, x:x+1200].shape[:2]
                        if (x > 0 and box[0] < 12) or (y > 0 and box[1] < 12) or (x+tw < w and box[2] > tw-12) or (y+th < h and box[3] > th-12):
                            continue
                        found.append((box + np.array([x,y,x,y]), kps + [x,y], score))
        if not found:
            return []
        xywh = [list(b[:2]) + list(b[2:]-b[:2]) for b, _, _ in found]
        keep = np.asarray(cv2.dnn.NMSBoxes(xywh, [f[2] for f in found], .55, .35)).reshape(-1)
        return sorted([found[i] for i in keep], key=lambda f: (round(f[0][1]/40), f[0][0]))

    def attribute(self, image, bbox, key):
        session = self.sessions[key]
        size = session.get_inputs()[0].shape[-1]
        center = (bbox[:2] + bbox[2:]) / 2
        scale = size / (max(bbox[2:]-bbox[:2])*1.5)
        matrix = np.array([[scale, 0, size/2-center[0]*scale], [0, scale, size/2-center[1]*scale]], np.float32)
        crop = cv2.warpAffine(image, matrix, (size, size))
        cfg = self.config[key]
        blob = cv2.dnn.blobFromImage(crop, 1/cfg["std"], (size, size), (cfg["mean"],)*3, swapRB=True)
        return self.run(key, blob)[0].reshape(-1), matrix, size

    def process(self, path, mode="auto", group_photo=False, cancelled=lambda: False, digest=None):
        image = read_image(path)
        detections = self.dense_detect(image, cancelled) if group_photo else self.detect(image)
        messages = []
        if not detections:
            return [], [tr('未检测到人脸')]
        if not group_photo and len(detections) > 1:
            return [], [tr('检测到 {0} 张脸；请使用「导入合照」以避免误选').format(len(detections))]
        faces = []
        # Portrait framing: leave space above the hair and below the chin for shoulders.
        target = np.array([[.38,.42],[.62,.42],[.5,.515625],[.4175,.60],[.5825,.60]], np.float32)*[WIDTH, HEIGHT]
        digest = digest or hashlib.sha256(Path(path).read_bytes()).hexdigest()
        source_mask = np.ones(image.shape[:2],np.uint8)
        for i, (bbox, five, score) in enumerate(detections):
            if cancelled():
                raise Cancelled()
            if min(bbox[2:]-bbox[:2]) < 24:
                messages.append(tr('人脸 {0} 过小，已跳过').format(i+1))
                continue
            try:
                if self.open:
                    points, metric_points = self.open.landmarks(image,bbox)
                else:
                    pred, matrix, side = self.attribute(image, bbox, "landmark")
                    points = transform_points((pred.reshape(-1, 2)+1)*(side/2), cv2.invertAffineTransform(matrix))
                    metric_points = points
            except ValueError as error:
                messages.append(tr('人脸 {0}：{1}').format(i+1,error))
                continue
            group = mode if mode in ("male", "female") else "review"
            label_source = tr('人工导入标签') if mode in ("male","female") else tr('待人工分组')
            affine = similarity(five, target)
            metric_points = transform_points(metric_points,affine)
            points, aligned_five = transform_points(points, affine), transform_points(five, affine)
            if not np.isfinite(points).all() or np.any(points < 1) or np.any(points > [WIDTH-2, HEIGHT-2]):
                messages.append(tr('人脸 {0} 姿态或关键点异常，已跳过').format(i+1))
                continue
            crop = cv2.warpAffine(image, affine, (WIDTH, HEIGHT), borderMode=cv2.BORDER_CONSTANT, borderValue=(245,245,245))
            valid_mask = cv2.warpAffine(source_mask, affine, (WIDTH, HEIGHT), flags=cv2.INTER_NEAREST)
            faces.append(Face(f"{digest}:{i}", str(path), i+1, crop, points, aligned_five,
                              group, measure(metric_points, aligned_five),
                              valid_mask=valid_mask, backend=self.backend,label_source=label_source,group_photo=group_photo))
        return faces, messages


def statistics(faces):
    return {group: {"count": len(items := [f for f in faces if f.enabled and f.group == group]),
                    "metrics": {key: {"mean": float(np.mean(v)), "std": float(np.std(v, ddof=1)) if len(v)>1 else 0.0}
                                for key in METRICS if (v := [f.metrics[key] for f in items])}}
            for group in ("male", "female")}


def average(faces, normalize=True, cancelled=lambda: False, progress=lambda a,b: None):
    if not faces:
        raise ValueError(tr('当前组没有可用样本'))
    if len({(f.backend, len(f.points)) for f in faces}) != 1:
        raise ValueError(tr('不能混合不同关键点模型的样本，请清空后使用同一模型重新导入'))
    if cancelled():raise Cancelled()
    if len(faces)==1:
        face=faces[0]; result=face.image.copy()
        if face.valid_mask is not None:result[face.valid_mask==0]=245
        progress(1,1)
        return result,face.points.copy()
    border=np.array([[0,0],[WIDTH//2,0],[WIDTH-1,0],[WIDTH-1,HEIGHT//2],
                     [WIDTH-1,HEIGHT-1],[WIDTH//2,HEIGHT-1],[0,HEIGHT-1],[0,HEIGHT//2]],np.float32)
    shapes=[np.vstack((f.points,border)) for f in faces]
    mean=np.mean(shapes,axis=0).astype(np.float32)
    from scipy.spatial import Delaunay
    from scipy.sparse import csr_matrix
    triangles=Delaunay(mean).simplices
    indices=np.zeros((HEIGHT,WIDTH,3),np.int32)
    weights=np.zeros((HEIGHT,WIDTH,3),np.float32)
    # Barycentric weights depend only on the destination mean shape, not the sample.
    # Build them once, then map each entire image with one remap operation.
    for tri in triangles:
        if cancelled():raise Cancelled()
        dst=mean[tri]; x,y,w,h=cv2.boundingRect(dst)
        x,y=max(x,0),max(y,0); w,h=min(w,WIDTH-x),min(h,HEIGHT-y)
        if w<=0 or h<=0:continue
        mask=np.zeros((h,w),np.uint8)
        cv2.fillConvexPoly(mask,np.round(dst-[x,y]).astype(np.int32),1)
        yy,xx=np.nonzero(mask)
        xy=np.column_stack((xx+x,yy+y,np.ones(len(xx),np.float32))).astype(np.float32)
        bary=xy@np.linalg.inv(np.vstack((dst.T,np.ones(3,np.float32)))).T
        indices[y+yy,x+xx]=tri; weights[y+yy,x+xx]=bary
    warp=csr_matrix((weights.reshape(-1),indices.reshape(-1),np.arange(0,HEIGHT*WIDTH*3+1,3)),
                    shape=(HEIGHT*WIDTH,len(mean)))
    total=np.zeros((HEIGHT,WIDTH,3),np.float64)
    sample_weight=np.zeros((HEIGHT,WIDTH),np.float32)
    moments=[]
    if normalize:
        for face in faces:
            if cancelled():raise Cancelled()
            luminance=cv2.cvtColor(face.image,cv2.COLOR_BGR2LAB)[:,:,0].astype(np.float32)
            mask=np.zeros((HEIGHT,WIDTH),np.uint8)
            cv2.fillConvexPoly(mask,cv2.convexHull(face.points.astype(np.int32)),1)
            pixels=luminance[mask>0]; moments.append((pixels.mean(),pixels.std()))
        target_mean=np.mean([m[0] for m in moments]); target_std=np.mean([m[1] for m in moments])
    for n,(face,source) in enumerate(zip(faces,shapes)):
        if cancelled():raise Cancelled()
        img=face.image
        if normalize:
            lab=cv2.cvtColor(img,cv2.COLOR_BGR2LAB).astype(np.float32)
            mu,sd=moments[n]
            lab[:,:,0]=(lab[:,:,0]-mu)*np.clip(target_std/max(sd,1),.7,1.4)+target_mean
            img=cv2.cvtColor(np.clip(lab,0,255).astype(np.uint8),cv2.COLOR_LAB2BGR)
        coords=(warp@source).reshape(HEIGHT,WIDTH,2)
        warped=cv2.remap(img,coords,None,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
        valid=cv2.remap(face.valid_mask,coords,None,cv2.INTER_NEAREST) if face.valid_mask is not None else np.ones((HEIGHT,WIDTH),np.uint8)
        total+=warped*valid[:,:,None]; sample_weight+=valid
        progress(n+1,len(faces))
    result=np.full((HEIGHT,WIDTH,3),245,np.float64)
    np.divide(total,sample_weight[:,:,None],out=result,where=sample_weight[:,:,None]>0)
    return np.clip(result,0,255).astype(np.uint8),mean[:-8]
