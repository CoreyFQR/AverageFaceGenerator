"""Small UI-safe definitions; loading a window does not load inference libraries."""
import sys
from pathlib import Path

WIDTH, HEIGHT = 600, 800
GROUP_NAMES = {"male": "男性", "female": "女性", "review": "待确认"}
METRICS = {
    "eye_px": "眼距 · px", "width_px": "脸宽 · px",
    "height_px": "眉颏高 · px", "eye_width": "眼距 / 脸宽",
    "mouth_width": "嘴宽 / 脸宽", "height_width": "眉颏高 / 脸宽",
    "nose_height": "眼线至鼻尖 / 眉颏高",
}

class Cancelled(Exception):
    pass

def resource_dir():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))

def photo_paths(entries):
    """Expand files/folders in deterministic order, deduplicating overlapping inputs."""
    seen=set()
    for entry in entries:
        path=Path(entry)
        candidates=sorted(path.rglob('*')) if path.is_dir() else [path]
        for item in candidates:
            if item.is_file() and item.suffix.lower() in ('.png','.jpg','.jpeg'):
                key=str(item.resolve())
                if key not in seen:
                    seen.add(key)
                    yield key
