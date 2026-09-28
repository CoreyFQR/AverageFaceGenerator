import numpy as np
import pytest
from avgface.importer import ImportSession
from test_engine import fixture_face


def test_preprocess_matches_siglip_spec():
    from avgface.models import GenderModel
    gray = np.full((300, 200, 3), 127, np.uint8)
    blob = GenderModel.preprocess(gray)
    assert blob.shape == (1, 3, 224, 224)
    assert blob.dtype == np.float32
    # (127/127.5 - 1) applied to every channel/pixel.
    expected = np.full_like(blob, 127 / 127.5 - 1.0)
    np.testing.assert_allclose(blob, expected, atol=1e-6)


class FakeGender:
    def __init__(self):
        self.calls = []

    def classify(self, image):
        self.calls.append(image.copy())
        return ('male' if len(self.calls) % 2 else 'female'), np.array([-1.0, 1.0])

    def close(self):
        pass


class FakeEngine:
    def __init__(self, **kwargs):
        pass

    def process(self, path, mode, group_photo, cancelled, digest=None):
        return [fixture_face(group='review'), fixture_face(group='review'), fixture_face(group='review')], []

    def close(self):
        pass


def _session(monkeypatch):
    import avgface.engine as engine_module
    import avgface.models as models_module
    fake = FakeGender()
    monkeypatch.setattr(engine_module, 'Engine', FakeEngine)
    monkeypatch.setattr(models_module, 'GenderModel', lambda root: fake)
    return ImportSession(), fake


def test_auto_gender_labels_auto_mode_faces(monkeypatch, tmp_path):
    session, fake = _session(monkeypatch)
    path = tmp_path / 'group.jpg'
    path.write_bytes(b'image')
    try:
        faces, _ = session.process(str(path), 'auto', True, lambda: False,
                                   {'auto_gender': True}, set())
    finally:
        session.close()
    assert faces and len(fake.calls) == len(faces)
    assert all(f.group in ('male', 'female') for f in faces)
    assert all(f.label_source == '自动性别分类' for f in faces)


def test_auto_gender_skips_explicit_male_and_off(monkeypatch, tmp_path):
    session, fake = _session(monkeypatch)
    path = tmp_path / 'portrait.jpg'
    path.write_bytes(b'image')
    try:
        faces, _ = session.process(str(path), 'male', False, lambda: False,
                                   {'auto_gender': True}, set())
        assert faces and fake.calls == []
        assert all(f.group == 'review' for f in faces)
        faces, _ = session.process(str(path), 'auto', False, lambda: False,
                                   {'auto_gender': False}, set())
        assert faces and fake.calls == []
    finally:
        session.close()


def test_cancel_inside_gender_loop_raises(monkeypatch, tmp_path):
    session, fake = _session(monkeypatch)
    from avgface.common import Cancelled
    path = tmp_path / 'group.jpg'
    path.write_bytes(b'image')
    try:
        with pytest.raises(Cancelled):
            session.process(str(path), 'auto', True, lambda: len(fake.calls) >= 1,
                            {'auto_gender': True}, set())
    finally:
        session.close()


def test_concurrent_gender_initialization_loads_and_closes_one_model(monkeypatch):
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor
    import avgface.models as models_module
    start=threading.Barrier(2)
    created=[]; closed=[]
    class SlowGender:
        def __init__(self,root):
            created.append(self)
            time.sleep(.1)  # Model loading releases the GIL in real imports.
        def close(self):closed.append(self)
    monkeypatch.setattr(models_module,'GenderModel',SlowGender)
    session=ImportSession()
    def load():
        start.wait(timeout=5)
        return session.gender_model()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(load) for _ in range(2)]
            models=[future.result(timeout=5) for future in futures]
        assert len(created)==1
        assert models[0] is models[1]
    finally:
        session.close()
    assert closed==created


def test_gender_initialization_failure_can_be_retried(monkeypatch):
    import avgface.models as models_module
    attempts=[]
    fake=FakeGender()
    def load(root):
        attempts.append(root)
        if len(attempts)==1:raise RuntimeError('temporary model failure')
        return fake
    monkeypatch.setattr(models_module,'GenderModel',load)
    session=ImportSession()
    try:
        with pytest.raises(RuntimeError):session.gender_model()
        assert session.gender_model() is fake
        assert len(attempts)==2
    finally:
        session.close()
