"""Rebuild the Windows installer from the publisher's verified Mac release."""
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile
import zipfile
from PIL import Image
import assemble_windows as a

root = a.ROOT
here = Path(__file__).resolve().parent

def run(*args):
    subprocess.run([str(x) for x in args], check=True)

def unpack(archive, destination, *members):
    run(root/'7zip/7zz', 'x', archive, '-y', '-o'+str(destination), *members)

archive=a.get('https://github.com/ip7z/7zip/releases/download/26.06/7z2606-linux-x64.tar.xz',sha256='2b539cf067b2ad48e1baa5093dbaa8818b73542d1222a0ffde9dc5f2922ea62e')
(root/'7zip').mkdir(exist_ok=True)
with tarfile.open(archive) as t:t.extractall(root/'7zip',filter='data')
dmg=a.get('https://download.dub-off.com/editor/beta/dub-off-editor-0.1.0-mac-arm64.dmg',sha256='98f997a7a19332062e78eee8e07d00fa7a0aedda3ded94e9ac42d59692b7825f')
prefix='Dub-Off Editor 0.1.0-arm64/Dub-Off Editor.app/Contents/Resources/'
unpack(dmg,root/'mac',*[prefix+n for n in ['app.asar','python/*','vendor/voice/models/*','vendor/voice/voice-env.json','THIRD_PARTY_NOTICES.md','icon.icns']])
dmg.unlink()
(root/'python-input.json').write_text(json.dumps({'url':'https://github.com/astral-sh/python-build-standalone/releases/download/20261021/cpython-3.12.15%2B20261021-x86_64-pc-windows-msvc-install_only_stripped.tar.gz','sha256':'aac5d331fc3307343f95928fdbea4583f0d53973d08c7e1d081884fbd229a0e1'}))
a.main()

# Recover only the metadata needed by electron-builder; ship app.asar unchanged.
b=(a.MAC/'app.asar').read_bytes()
n=struct.unpack_from('<I',b,12)[0]
h=json.loads(b[16:16+n])
base=8+struct.unpack_from('<I',b,4)[0]
e=h['files']['package.json'];offset=base+int(e['offset'])
(root/'original').mkdir(exist_ok=True)
(root/'original/package.json').write_bytes(b[offset:offset+e['size']])
assert (a.RES/'app.asar').read_bytes()==b

# App-local Microsoft runtime DLLs, copied unmodified from the redistributable.
redist=a.get('https://aka.ms/vs/17/release/vc_redist.x64.exe',sha256='cc0ff0eb1dc3f5188ae6300faef32bf5beeba4bdd6e8e445a9184072096b713b')
data=redist.read_bytes();start=0;cabs=[]
while True:
    offset=data.find(b'MSCF\0\0\0\0',start)
    if offset<0:break
    size=struct.unpack_from('<I',data,offset+8)[0]
    if 0<size<=len(data)-offset:
        dest=root/f'redist-{len(cabs)}.cab';dest.write_bytes(data[offset:offset+size]);cabs.append(dest)
    start=offset+4
unpack(cabs[0],root/'redist-bootstrap')
unpack(cabs[1],root/'redist-payload')
unpack(root/'redist-payload/a12',root/'redist-dlls')
for p in (root/'redist-dlls').glob('*.dll_amd64'):
    shutil.copy2(p,a.PYTHON/p.name.removesuffix('_amd64'))
shutil.copy2(root/'redist-bootstrap/u4',a.PYTHON/'MSVC-LICENSE.rtf')
manifest=json.loads((a.MAC/'vendor/voice/voice-env.json').read_text())
manifest['info'].update(executable='python/python.exe',platform='Windows-AMD64',cuda=False,mps=False)
manifest['msvcRuntime']={'version':'14.44.35211.0','source':'https://aka.ms/vs/17/release/vc_redist.x64.exe'}
for field in ['bytes','trimmed','timings']:manifest.pop(field,None)
assert hashlib.sha256((a.RES/'python/uv.lock').read_bytes()).hexdigest()[:16]==manifest['lockHash']
(a.RES/'vendor/voice/voice-env.json').write_text(json.dumps(manifest,indent=2)+'\n')

Image.open(a.MAC/'icon.icns').save(root/'icon.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
branding=(here/'set-branding.mjs.in').read_text().replace('/workspace/work',str(root))
(here/'set-branding.mjs').write_text(branding)
run('node',here/'set-branding.mjs')

config={
 'appId':'com.dub-off.editor','productName':'Dub-Off Editor',
 'artifactName':'Dub-Off-Editor-0.1.0-Windows-x64-Setup.${ext}',
 'electronVersion':'45.0.0',
 'directories':{'output':str(root/'release'),'buildResources':str(root)},
 'win':{'target':[{'target':'nsis','arch':['x64']}],'icon':str(root/'icon.ico'),'signAndEditExecutable':False},
 'nsis':{'oneClick':True,'perMachine':False,'allowElevation':False,'createDesktopShortcut':False,'createStartMenuShortcut':True,'shortcutName':'Dub-Off Editor','installerIcon':str(root/'icon.ico'),'uninstallerIcon':str(root/'icon.ico'),'packElevateHelper':False,'runAfterFinish':True,'deleteAppDataOnUninstall':False},
 'fileAssociations':[{'ext':'dub','name':'Dub-Off Scene','role':'Editor'}],
 'publish':None
}
(root/'electron-builder.json').write_text(json.dumps(config))
run('node',here/'package.cjs')
installer=root/'release/Dub-Off-Editor-0.1.0-Windows-x64-Setup.exe'
run(root/'7zip/7zz','t',installer)
digest=hashlib.file_digest(installer.open('rb'),'sha256').hexdigest()
portable=root/'release/Dub-Off-Editor-0.1.0-Windows-x64-Portable.zip'
with zipfile.ZipFile(portable,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
    for p in sorted(a.APP.rglob('*')):
        if p.is_file():z.write(p,Path('Dub-Off Editor')/p.relative_to(a.APP))
run(root/'7zip/7zz','t',portable)
portable_digest=hashlib.file_digest(portable.open('rb'),'sha256').hexdigest()
(root/'release/SHA256SUMS.txt').write_text(digest+'  '+installer.name+'\n'+portable_digest+'  '+portable.name+'\n')
readme=here.parent/'README.md'
readme_text=re.sub(r'(Installer SHA-256:\n\n`)[0-9a-f]{64}(`)',lambda m:m.group(1)+digest+m.group(2),readme.read_text())
readme_text=re.sub(r'\(approximately [\d,]+ MB\)',f'(approximately {installer.stat().st_size/1e6:.0f} MB)',readme_text,count=1)
readme.write_text(readme_text)
(root/'release/notes.md').write_text('Unofficial Windows x64 packaging of Dub-Off Editor 0.1.0. Original application code and interface are unchanged; Windows runtimes and offline speech models are included.\n\nDownload the setup EXE under Assets. Requires 64-bit Windows 10 or 11. The installer is unsigned.\n\n**Experimental:** the original local build passed an offline speech smoke test under Wine. Full installation, graphical editing, and export on a real Windows PC remain untested. This is not an official Dub-Off release. See README for verification and update limitations.\n\nThis release was rebuilt on GitHub Actions from the same verified inputs because the connected cloud session could not authenticate to GitHub\'s asset-upload host. Installer packaging bytes and its checksum therefore differ from the earlier local build.\n\nSHA-256: `'+digest+'`\n')
with (root/'release/notes.md').open('a') as f:
    f.write('\nThe Portable ZIP contains the complete unpacked Windows application, including its runtime libraries, Python packages, and offline models. Extract it and open `Dub-Off Editor.exe`. Recovered application code, assets, build scripts, and verification records are also public in the repository.\n')
