# Build with: python -m PyInstaller --clean --noconfirm AvgFace.spec
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files
import os,tempfile
from pathlib import Path
import runpy
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
release=runpy.run_path('avgface/__init__.py')
version_tuple=tuple(int(part) for part in release['__version__'].split('.'))+(0,)
version_info=VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_tuple,prodvers=version_tuple,mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),
    kids=[StringFileInfo([StringTable('040904B0',[
        StringStruct('FileDescription','AverageFaceGenerator'),
        StringStruct('FileVersion',release['__version__']+'.0'),
        StringStruct('ProductName','AverageFaceGenerator'),
        StringStruct('ProductVersion',release['DISPLAY_VERSION']),
        StringStruct('OriginalFilename','AvgFaceApp.exe')])]),
        VarFileInfo([VarStruct('Translation',[1033,1200])])])
os.environ.setdefault('MPLCONFIGDIR',os.path.join(tempfile.gettempdir(),'avgface-mpl'))
os.environ.setdefault('MPLBACKEND','Agg')

datas = [('assets', 'assets'), ('LICENSE', '.'), ('MODEL_LICENSES.md', '.')]
# Excluded converters need no runtime license tree. Their deeply nested notices
# also exceed .NET Framework's path limit when extracting a long cache path.
for entry in Path('licenses').iterdir():
    if entry.name.lower() not in {'torch','transformers'}:
        datas.append((str(entry),'licenses/'+entry.name if entry.is_dir() else 'licenses'))
for model in ['yunet.onnx', 'face_landmarker.task', 'sface.onnx', 'realistic_gender.onnx']:
    datas.append(('models/' + model, 'models'))
datas += collect_data_files('onnxruntime')
datas += collect_data_files('mediapipe')
a = Analysis(['main.py'], pathex=[], binaries=collect_dynamic_libs('onnxruntime')+collect_dynamic_libs('mediapipe'), datas=datas,
             hiddenimports=['scipy.special._ufuncs', 'scipy.spatial._qhull'],
             # PyTorch/Transformers are build-time converters. Runtime inference
             # uses ONNX Runtime; optional SciPy hooks must not bundle converters.
             excludes=['onnx', 'torch', 'transformers', 'pytest', 'tkinter', 'PIL.AvifImagePlugin'],
             hooksconfig={'matplotlib': {'backends': ['Agg']}}, noarchive=False)
# The application processes still images with raster Qt widgets. Video codecs,
# PDF/QML rendering and software OpenGL are not used by any application path.
unused_names={'opengl32sw.dll','Qt6Pdf.dll','qpdf.dll','Qt6Quick.dll','Qt6Qml.dll',
              'Qt6QmlModels.dll','Qt6QmlWorkerScript.dll','Qt6OpenGL.dll'}
a.binaries=[entry for entry in a.binaries if os.path.basename(entry[0].replace('\\','/')) not in unused_names
            and 'opencv_videoio_ffmpeg' not in entry[0]]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='AvgFaceApp',
          icon='assets/AvgFace.ico',
          version=version_info,
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
collection = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='AvgFaceRuntime')
