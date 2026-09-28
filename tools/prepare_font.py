import urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
(root/"assets").mkdir(exist_ok=True)
for url,path in (
    ("https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf",root/"assets"/"NotoSansSC.ttf"),
    ("https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/OFL.txt",root/"licenses"/"NotoSansSC-OFL.txt"),
):
    if not path.is_file() or path.stat().st_size==0:
        path.parent.mkdir(parents=True,exist_ok=True)
        urllib.request.urlretrieve(url,path)
