"""A bounded two-worker pipeline; each worker owns and reuses its model objects."""
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .i18n import tr
from .common import Cancelled


class _BatchDigests:
    """Skip successful duplicates, but let another copy retry a failed import."""
    def __init__(self, known):
        self.completed = set(known)
        self.running = set()
        self.condition = threading.Condition()

    def claim(self, digest, cancelled):
        with self.condition:
            while digest in self.running:
                if cancelled():
                    raise Cancelled()
                self.condition.wait(timeout=.05)
            if cancelled():
                raise Cancelled()
            if digest in self.completed:
                return False
            self.running.add(digest)
            return True

    def release(self, digest, succeeded):
        with self.condition:
            self.running.remove(digest)
            if succeeded:
                self.completed.add(digest)
            self.condition.notify_all()


class ImportSession:
    def __init__(self):
        self.pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='face-import')
        self.local=threading.local()
        self.engines=[]
        self.gender=None
        self.gender_lock=threading.Lock()

    def gender_model(self):
        with self.gender_lock:
            if self.gender is None:
                from .models import GenderModel
                from .common import resource_dir
                self.gender=GenderModel(resource_dir() / "models")
            return self.gender

    def process(self,path,mode,group_photo,cancelled,options,known,batch=None):
        if cancelled():raise Cancelled()
        digest=hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if digest in known:return [],[tr('已导入，跳过重复照片')]
        if batch is not None and not batch.claim(digest,cancelled):
            return [],[tr('已导入，跳过重复照片')]
        succeeded=False
        try:
            result=self._process_image(path,mode,group_photo,cancelled,options,digest)
            succeeded=bool(result[0])
            return result
        finally:
            if batch is not None:batch.release(digest,succeeded)

    def _process_image(self,path,mode,group_photo,cancelled,options,digest):
        key=(options.get('backend','open'),str(options.get('model_dir','')))
        cache=getattr(self.local,'cache',None)
        if cache is None:cache=self.local.cache={}
        if key not in cache:
            from .engine import Engine
            engine_options={k:v for k,v in options.items() if k!='auto_gender'}
            cache[key]=Engine(**engine_options); self.engines.append(cache[key])
        faces,messages=cache[key].process(path,mode,group_photo,cancelled,digest=digest)
        # Auto gender classification applies only to the unlabeled path
        # (mixed portraits and group photos). Male/female imports keep the
        # user-provided label and are left untouched.
        if faces and mode=='auto' and options.get('auto_gender'):
            classifier=self.gender_model()
            for face in faces:
                if cancelled():raise Cancelled()
                label,_=classifier.classify(face.image)
                face.group=label; face.label_source=tr('自动性别分类')
        return faces,messages

    def iterate(self,paths,mode,group_photo,cancelled,options,known):
        iterator=iter(paths); pending=[]; active=None
        batch=_BatchDigests(known)
        def submit():
            path=next(iterator,None)
            if path is not None:
                pending.append((path,self.pool.submit(self.process,path,mode,group_photo,cancelled,options,known,batch)))
        submit(); submit()
        try:
            while pending:
                path,future=pending.pop(0); active=future
                if cancelled():raise Cancelled()
                try:result=future.result()
                except Cancelled:raise
                except Exception as error:result=([],[tr('处理失败：{0}').format(error)])
                active=None
                yield path,result
                if cancelled():raise Cancelled()
                submit()
        finally:
            # No model can be reused by a later UI operation while a cancelled job is still running.
            if active is not None:pending.append(('',active))
            for _,future in pending:future.cancel()
            for _,future in pending:
                try:future.result()
                except Exception:pass

    def close(self):
        self.pool.shutdown(wait=True,cancel_futures=True)
        for engine in self.engines:engine.close()
        self.engines.clear()
        if self.gender is not None:
            self.gender.close(); self.gender=None
