"""Bundle an onedir runtime into one EXE with an integrity-checked runtime cache."""
import argparse,hashlib,subprocess,zipfile,runpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
release=runpy.run_path(str(root/'avgface'/'__init__.py'))
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path)
parser.add_argument('--lite',action='store_true',help='Name the FP16 edition lite')
args=parser.parse_args()
name=f'AverageFaceGenerator_{release["DISPLAY_VERSION"]}'+('_lite' if args.lite else '')+'.exe'
output=(args.output or root/'dist'/name).resolve()
runtime=root/'dist'/'AvgFaceRuntime'
build=root/'build'/'launcher'; build.mkdir(parents=True,exist_ok=True)
files=sorted(p for p in runtime.rglob('*') if p.is_file())
assert (runtime/'AvgFaceApp.exe').is_file()
manifest=''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}\t{p.stat().st_size}\t{p.relative_to(runtime).as_posix()}\n' for p in files)
(build/'runtime.manifest').write_text(manifest,encoding='utf-8')
identity=hashlib.sha256(manifest.encode()).hexdigest()[:24]
product='AverageFaceGenerator'+(' lite' if args.lite else '')
(build/'BuildInfo.cs').write_text(
    f'[assembly: System.Reflection.AssemblyVersion("{release["__version__"]}.0")]\n'
    f'[assembly: System.Reflection.AssemblyFileVersion("{release["__version__"]}.0")]\n'
    f'[assembly: System.Reflection.AssemblyInformationalVersion("{release["DISPLAY_VERSION"]}")]\n'
    f'[assembly: System.Reflection.AssemblyProduct("{product}")]\n'
    f'[assembly: System.Reflection.AssemblyTitle("{product}")]\n'
    f'static class BuildInfo {{ public const string Id="{identity}"; public const string Version="{release["DISPLAY_VERSION"]}"; }}',encoding='utf-8')
with zipfile.ZipFile(build/'runtime.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for path in files:archive.write(path,path.relative_to(runtime).as_posix())
csc=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
subprocess.run([str(csc),'/nologo','/target:winexe','/platform:x64','/optimize+',
    '/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll',
    '/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll',
    f'/win32icon:{root / "assets" / "AvgFace.ico"}',
    f'/resource:{build / "runtime.zip"},runtime.zip',f'/resource:{build / "runtime.manifest"},runtime.manifest',
    f'/out:{output}',str(root/'launcher'/'Launcher.cs'),str(build/'BuildInfo.cs')],check=True)
with output.open('rb') as executable:
    digest=hashlib.file_digest(executable,'sha256').hexdigest()
output.with_suffix(output.suffix+'.sha256').write_text(f'{digest}  {output.name}\n',encoding='utf-8')
print('Single EXE:',output.stat().st_size,'runtime version:',identity)
print('SHA-256:',digest)
