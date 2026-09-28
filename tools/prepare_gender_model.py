"""Build-time only: convert the Hugging Face SigLIP2 gender classifier to ONNX.

The packaged app never downloads anything and never imports PyTorch / Transformers.
Run after installing the dev extras (torch CPU, transformers==4.50):

    .\\.venv\\Scripts\\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    .\\.venv\\Scripts\\python.exe -m pip install "transformers==4.50.3" safetensors huggingface_hub
    .\\.venv\\Scripts\\python.exe tools/prepare_gender_model.py

Output: models/realistic_gender.onnx       (FP32, input pixel_values 1x3x224x224)
        models/realistic_gender_fp16.onnx  (FP16 weights/activations, same 1x3x224x224 IO)
The fixed SHA-256 values in avgface/models.py must match the produced files.
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "prithivMLmods/Realistic-Gender-Classification"
BASE = f"https://huggingface.co/{REPO}/resolve/main"
CACHE = ROOT / "research-models" / "realistic-gender"
FILES = ("config.json", "preprocessor_config.json", "model.safetensors")
OUT = ROOT / "models" / "realistic_gender.onnx"
OUT_FP16 = ROOT / "models" / "realistic_gender_fp16.onnx"


def download():
    CACHE.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        out = CACHE / name
        if out.exists() and out.stat().st_size > 0:
            continue
        url = f"{BASE}/{name}?download=true"
        print(f"Downloading {name} …", flush=True)
        tmp = out.with_suffix(out.suffix + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": "avgface-build"})
        with urllib.request.urlopen(req, timeout=120) as response, open(tmp, "wb") as file:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                file.write(chunk)
        tmp.replace(out)
        print("  ", name, out.stat().st_size, "bytes", flush=True)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    download()
    sys.path.insert(0, str(ROOT))
    import json

    import numpy as np
    import torch
    from transformers import SiglipForImageClassification

    config = json.loads((CACHE / "config.json").read_text("utf-8"))
    pre = json.loads((CACHE / "preprocessor_config.json").read_text("utf-8"))
    size = pre["size"]
    print("Preprocess:", pre["resample"], size, pre["image_mean"], pre["image_std"], flush=True)

    model = SiglipForImageClassification.from_pretrained(CACHE)
    model.eval()
    ids = config.get("id2label", {})
    print("Labels:", ids, flush=True)

    # Reference forward pass on CPU (no gradients).
    rng = np.random.RandomState(0)
    probe = rng.rand(1, 3, size["height"], size["width"]).astype(np.float32)
    with torch.no_grad():
        torch_ref = model(torch.from_numpy(probe), return_dict=False)[0].detach().numpy()

    with torch.no_grad():
        torch.onnx.export(
            model,
            (torch.from_numpy(probe),),
            str(OUT),
            input_names=["pixel_values"],
            output_names=["logits"],
            opset_version=18,
            do_constant_folding=True,
        )
    # The dynamo exporter writes large weights to an external ".data" file by
    # default. The packaged app expects one self-contained ONNX file, so embed
    # the weights back into the single file.
    import onnx

    external = OUT.parent / (OUT.name + ".data")
    if external.exists():
        graph = onnx.load(str(OUT), load_external_data=True)
        onnx.save_model(graph, str(OUT), save_as_external_data=False)
        external.unlink()
    print("Exported:", OUT.stat().st_size, "bytes", flush=True)

    import onnxruntime as ort

    session = ort.InferenceSession(str(OUT), providers=["CPUExecutionProvider"])
    (onnx_out,) = session.run(None, {"pixel_values": probe})
    max_diff = float(np.max(np.abs(onnx_out - torch_ref)))
    print(f"ONNX vs PyTorch max abs diff: {max_diff:.6g}", flush=True)
    if max_diff > 1e-3:
        raise RuntimeError("Conversion mismatch is too large")
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print("SHA-256 (FP32):", digest, flush=True)

    # FP16 variant: half the size with no label changes (SigLIP2 fine tune keeps
    # 100% agreement with FP32 in classification), used by the smaller EXE.
    import onnx
    from onnxruntime.transformers.float16 import convert_float_to_float16

    onnx.save_model(convert_float_to_float16(onnx.load(str(OUT)), keep_io_types=True), str(OUT_FP16))
    session16 = ort.InferenceSession(str(OUT_FP16), providers=["CPUExecutionProvider"])
    (fp16_out,) = session16.run(None, {"pixel_values": probe})
    print(f"FP16 vs FP32 max abs diff: {float(np.max(np.abs(fp16_out - onnx_out))):.5g}", flush=True)
    print("FP16:", OUT_FP16.stat().st_size, "bytes", flush=True)
    digest16 = hashlib.sha256(OUT_FP16.read_bytes()).hexdigest()
    print("SHA-256 (FP16):", digest16, flush=True)


if __name__ == "__main__":
    main()
