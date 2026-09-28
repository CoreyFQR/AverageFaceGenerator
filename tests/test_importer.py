import threading
import numpy as np
import pytest
from avgface.common import photo_paths,Cancelled
from avgface.importer import ImportSession

def test_folder_expansion_handles_unicode_subfolders_and_overlapping_inputs(tmp_path):
    (tmp_path/'子目录').mkdir()
    a=tmp_path/'人像.JPG'; b=tmp_path/'子目录'/'b.png'; c=tmp_path/'ignored.txt'
    for p in (a,b,c):p.write_bytes(b'test')
    paths=list(photo_paths([tmp_path,a]))
    assert set(paths)=={str(a.resolve()),str(b.resolve())} and len(paths)==2

def test_import_pool_reuses_models_and_skips_known_content_before_inference(tmp_path,monkeypatch):
    import avgface.engine as engine
    calls=[]; created=[]
    class FakeEngine:
        def __init__(self,**kwargs):created.append(self)
        def process(self,*args,**kwargs):calls.append(args[0]); return [],[]
        def close(self):pass
    monkeypatch.setattr(engine,'Engine',FakeEngine)
    paths=[]
    for i in range(5):
        p=tmp_path/f'{i}.jpg'; p.write_bytes(str(i).encode()); paths.append(str(p))
    session=ImportSession()
    try:
        assert len(list(session.iterate(paths,'male',False,lambda:False,{},set())))==5
        assert 1<=len(created)<=2
        count=len(created)
        import hashlib
        known={hashlib.sha256(b'0').hexdigest()}
        list(session.iterate([paths[0]],'male',False,lambda:False,{},known))
        assert len(calls)==5 and len(created)==count
        with pytest.raises(Cancelled):list(session.iterate(paths,'male',False,lambda:True,{},set()))
    finally:session.close()


def test_same_batch_duplicates_run_inference_once_and_next_batch_can_reimport(tmp_path,monkeypatch):
    import time
    from types import SimpleNamespace
    import avgface.engine as engine
    calls=[]
    class FakeEngine:
        def __init__(self,**kwargs):pass
        def process(self,path,*args,digest=None,**kwargs):
            calls.append(path)
            time.sleep(.05)
            return [SimpleNamespace(id=f'{digest}:0')],[]
        def close(self):pass
    monkeypatch.setattr(engine,'Engine',FakeEngine)
    paths=[]
    for i in range(4):
        path=tmp_path/f'copy{i}.jpg'; path.write_bytes(b'same photo'); paths.append(str(path))
    session=ImportSession()
    try:
        rows=list(session.iterate(paths,'male',False,lambda:False,{},set()))
        assert len(calls)==1
        assert sum(len(faces) for _,(faces,notes) in rows)==1
        assert sum(bool(notes) for _,(faces,notes) in rows)==3
        # Clearing the UI starts a fresh batch, without a session-wide skip cache.
        rows=list(session.iterate(paths,'male',False,lambda:False,{},set()))
        assert len(calls)==2
        assert sum(len(faces) for _,(faces,notes) in rows)==1
    finally:session.close()


@pytest.mark.parametrize('failure', ['exception','empty'])
def test_duplicate_retries_after_failed_inference(tmp_path,monkeypatch,failure):
    import time
    from types import SimpleNamespace
    import avgface.engine as engine
    calls=[]
    class FakeEngine:
        def __init__(self,**kwargs):pass
        def process(self,path,*args,digest=None,**kwargs):
            calls.append(path)
            if len(calls)==1:
                time.sleep(.05)
                if failure=='exception':raise OSError('temporary read failure')
                return [],['no usable face']
            return [SimpleNamespace(id=f'{digest}:0')],[]
        def close(self):pass
    monkeypatch.setattr(engine,'Engine',FakeEngine)
    paths=[]
    for i in range(3):
        path=tmp_path/f'copy{i}.jpg'; path.write_bytes(b'same photo'); paths.append(str(path))
    session=ImportSession()
    try:
        rows=list(session.iterate(paths,'male',False,lambda:False,{},set()))
        assert len(calls)==2
        assert sum(len(faces) for _,(faces,_) in rows)==1
    finally:session.close()


def test_different_photos_still_process_concurrently(tmp_path,monkeypatch):
    import avgface.engine as engine
    barrier=threading.Barrier(2)
    class FakeEngine:
        def __init__(self,**kwargs):pass
        def process(self,*args,**kwargs):
            barrier.wait(timeout=5)
            return [],[]
        def close(self):pass
    monkeypatch.setattr(engine,'Engine',FakeEngine)
    paths=[]
    for i in range(2):
        path=tmp_path/f'{i}.jpg'; path.write_bytes(str(i).encode()); paths.append(str(path))
    session=ImportSession()
    try:
        rows=list(session.iterate(paths,'male',False,lambda:False,{},set()))
        assert all(not notes for _,(_,notes) in rows)
        assert not barrier.broken
    finally:session.close()


def test_cancel_with_duplicate_waiter_drains_workers_and_allows_retry(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    import avgface.engine as engine
    entered=threading.Event(); cancel=threading.Event()
    calls=[]
    class FakeEngine:
        def __init__(self,**kwargs):pass
        def process(self,path,*args,digest=None,**kwargs):
            calls.append(path)
            if len(calls)==1:
                entered.set()
                assert cancel.wait(timeout=5)
                raise Cancelled()
            return [SimpleNamespace(id=f'{digest}:0')],[]
        def close(self):pass
    monkeypatch.setattr(engine,'Engine',FakeEngine)
    paths=[]
    for i in range(2):
        path=tmp_path/f'copy{i}.jpg'; path.write_bytes(b'same photo'); paths.append(str(path))
    session=ImportSession()
    try:
        with ThreadPoolExecutor(max_workers=1) as consumer:
            future=consumer.submit(lambda:list(session.iterate(paths,'male',False,cancel.is_set,{},set())))
            assert entered.wait(timeout=5)
            cancel.set()
            with pytest.raises(Cancelled):future.result(timeout=5)
        cancel.clear()
        rows=list(session.iterate(paths,'male',False,cancel.is_set,{},set()))
        assert len(calls)==2
        assert sum(len(faces) for _,(faces,_) in rows)==1
    finally:
        cancel.set()
        session.close()
