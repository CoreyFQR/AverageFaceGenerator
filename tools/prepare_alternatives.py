"""Download upstream models for the permissive backend; development time only."""
import hashlib,json,urllib.request,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from avgface.models import HASHES
files={
 "sface.onnx":"https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
 "yunet.onnx":"https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
 "face_landmarker.task":"https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
 "realistic_gender.onnx":"https://huggingface.co/prithivMLmods/Realistic-Gender-Classification",
}
manifest={}
(ROOT/'models').mkdir(exist_ok=True)
for name,url in files.items():
    path=ROOT/"models"/name
    if not path.exists():
        if name == 'realistic_gender.onnx':
            raise RuntimeError('models/realistic_gender.onnx 不存在：请先按 README 运行 tools/prepare_gender_model.py 转换性别模型 (build machine)')
        print("Downloading",name,flush=True)
        urllib.request.urlretrieve(url,path)
    manifest[name]={"source":url,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    accepted=HASHES[name]
    expected=accepted if isinstance(accepted,tuple) else (accepted,)
    if manifest[name]['sha256'] not in expected:
        raise RuntimeError(f'Model checksum mismatch: {name}')
    print(name,path.stat().st_size,manifest[name]["sha256"],flush=True)
(ROOT/"models"/"alternatives.json").write_text(json.dumps(manifest,indent=2))
licenses=ROOT/'licenses'/'models'; licenses.mkdir(parents=True,exist_ok=True)
notices={
 'SFace-Apache-2.0.txt':'https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/LICENSE',
 'YuNet-MIT.txt':'https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/LICENSE',
 'MediaPipe-Apache-2.0.txt':'https://raw.githubusercontent.com/google-ai-edge/mediapipe/master/LICENSE',
 'MediaPipe-FaceMesh-model-card.pdf':'https://storage.googleapis.com/mediapipe-assets/Model%20Card%20MediaPipe%20Face%20Mesh%20V2.pdf',
 'MediaPipe-BlazeFace-model-card.pdf':'https://storage.googleapis.com/mediapipe-assets/MediaPipe%20BlazeFace%20Model%20Card%20(Short%20Range).pdf',
 'MediaPipe-Blendshape-model-card.pdf':'https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Blendshape%20V2.pdf',
 'Realistic-Gender-Apache-2.0.txt':'https://www.apache.org/licenses/LICENSE-2.0.txt',
}
for name,url in notices.items():
    if not (licenses/name).exists():urllib.request.urlretrieve(url,licenses/name)
