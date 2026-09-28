import importlib.metadata
import shutil
import urllib.request
from pathlib import Path

root=Path(__file__).resolve().parents[1]/"licenses"
for dist in importlib.metadata.distributions():
    name=dist.metadata["Name"]
    for file in dist.files or []:
        if any(k in Path(str(file)).name.lower() for k in ("license","copying","notice")) and str(file).lower().endswith((".txt",".md",".rst","license","copying")):
            source=Path(dist.locate_file(file))
            if source.is_file():
                target=root/name/str(file).replace("../", "")
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source,target)
notice=root/"InsightFace-MIT.txt"
if not notice.is_file() or notice.stat().st_size==0:
    urllib.request.urlretrieve("https://raw.githubusercontent.com/deepinsight/insightface/v0.7/LICENSE",notice)
