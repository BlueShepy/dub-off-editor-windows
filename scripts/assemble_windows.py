"""Repackage the official Dub-Off Editor without modifying its app code.

Build inputs are verified against their publishers' checksums or the editor's
original uv.lock. All intermediate files stay in /workspace/work.
"""
import concurrent.futures
import hashlib
import json
import pathlib
import os
import shutil
import tarfile
import tomllib
import urllib.parse
import urllib.request
import zipfile

ROOT = pathlib.Path(os.environ['DUB_PORT_WORK_ROOT'])
MAC = ROOT / 'mac/Dub-Off Editor 0.1.0-arm64/Dub-Off Editor.app/Contents/Resources'
APP = ROOT / 'windows/Dub-Off Editor'
CACHE = ROOT / 'downloads'
RES = APP / 'resources'
PYTHON = RES / 'vendor/voice/python'
RECORDS = []
CACHE.mkdir(parents=True, exist_ok=True)
RES.mkdir(parents=True, exist_ok=True)

def get(url, filename=None, sha256=None):
    name = filename or pathlib.PurePosixPath(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
    dest = CACHE / name
    if not dest.exists():
        print('Downloading', name, flush=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'Dub-Off-Windows-Port/0.1'})
        with urllib.request.urlopen(req, timeout=180) as response, dest.with_suffix(dest.suffix+'.part').open('wb') as out:
            shutil.copyfileobj(response, out)
        dest.with_suffix(dest.suffix+'.part').replace(dest)
    actual = hashlib.file_digest(dest.open('rb'), 'sha256').hexdigest()
    if sha256 and actual.lower() != sha256.lower():
        raise ValueError(f'Checksum mismatch: {name}: {actual} != {sha256}')
    RECORDS.append(dict(url=url, file=name, sha256=actual, publisherChecksumVerified=bool(sha256)))
    return dest

def sums(url):
    data = get(url, hashlib.sha256(url.encode()).hexdigest()[:12]+'.sha256').read_text()
    return {line.split()[-1].lstrip('*'): line.split()[0] for line in data.splitlines() if len(line.split()) >= 2}

def electron():
    base = 'https://github.com/electron/electron/releases/download/v45.0.0/'
    name = 'electron-v45.0.0-win32-x64.zip'
    archive = get(base+name, sha256=sums(base+'SHASUMS256.txt')[name])
    with zipfile.ZipFile(archive) as z:
        z.extractall(APP)
    (APP/'electron.exe').rename(APP/'Dub-Off Editor.exe')
    (RES/'default_app.asar').unlink(missing_ok=True)

def ffmpeg():
    base = 'https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/autobuild-2026-09-30-13-08/'
    name = 'ffmpeg-n9.0.2-17-g2a571b6068-win64-gpl-9.0.zip'
    archive = get(base+name, sha256=sums(base+'checksums.sha256')[name])
    out = RES/'vendor/ffmpeg'
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for member in z.namelist():
            p = pathlib.PurePosixPath(member)
            if p.name in ['ffmpeg.exe', 'ffprobe.exe', 'LICENSE.txt'] or '/doc/' in member and p.suffix == '.txt':
                (out/p.name).write_bytes(z.read(member))
    (out/'VERSION').write_text('9.0.2\n')

def ytdlp():
    base = 'https://github.com/yt-dlp/yt-dlp/releases/download/2026.10.21/'
    name = 'yt-dlp.exe'
    exe = get(base+name, sha256=sums(base+'SHA2-256SUMS')[name])
    out = RES/'vendor/yt-dlp'
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(exe, out/name)
    (out/'VERSION').write_text('2026.10.21\n')

def python_runtime():
    # Supplied via a build input file so the selected upstream release is recorded.
    entry = json.loads((ROOT/'python-input.json').read_text())
    archive = get(entry['url'], sha256=entry['sha256'])
    out = ROOT/'python-unpack'
    out.mkdir(exist_ok=True)
    with tarfile.open(archive) as t:
        t.extractall(out, filter='data')
    shutil.copytree(out/'python', PYTHON, dirs_exist_ok=True)

def wheels():
    lock = tomllib.loads((MAC/'python/uv.lock').read_text())
    packages = []
    for p in lock['package']:
        if 'virtual' in p['source'] or p['name'] == 'torch' and '+cpu' not in p['version']:
            continue
        candidates = [w for w in p.get('wheels',[]) if 'win_amd64.whl' in w['url']]
        if not candidates:
            candidates = [w for w in p.get('wheels',[]) if 'none-any.whl' in w['url']]
        if len(candidates) != 1:
            raise ValueError(f'Expected one Windows wheel for {p["name"]}: {candidates}')
        packages.append((p,candidates[0]))
    def download(item):
        p,w = item
        f=get(w['url'],sha256=w['hash'].removeprefix('sha256:'))
        return p,f
    site=PYTHON/'Lib/site-packages'
    site.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for p,archive in pool.map(download,packages):
            with zipfile.ZipFile(archive) as z:
                for member in z.infolist():
                    path=pathlib.PurePosixPath(member.filename)
                    if member.is_dir(): continue
                    parts=path.parts
                    if any(x == '..' for x in parts): raise ValueError('Unsafe wheel path')
                    if parts[0].endswith('.data'):
                        if parts[1] in ['purelib','platlib']: path=pathlib.PurePosixPath(*parts[2:])
                        else: continue
                    dest=site/path
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_bytes(z.read(member))
            print('Installed',p['name'],p['version'],flush=True)

def main():
    # Runtime extraction precedes wheels because they share site-packages.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(f) for f in [electron,ffmpeg,ytdlp,python_runtime]]
        for job in jobs: job.result()
    wheels()
    shutil.copy2(MAC/'app.asar',RES/'app.asar')
    (RES/'python').mkdir(exist_ok=True)
    for name in ['voice.py','pyproject.toml','uv.lock']:
        shutil.copy2(MAC/'python'/name,RES/'python'/name)
    shutil.copytree(MAC/'vendor/voice/models',RES/'vendor/voice/models',dirs_exist_ok=True)
    # 7-Zip extracts the DMG's extended attributes as colon-suffixed files on
    # Linux. They are Mac metadata, not model data or Windows filenames.
    for metadata in RES.rglob('*:com.apple.provenance'):
        if metadata.is_file(): metadata.unlink()
    shutil.copy2(MAC/'THIRD_PARTY_NOTICES.md',RES/'THIRD_PARTY_NOTICES.md')
    (ROOT/'windows-inputs.json').write_text(json.dumps(RECORDS,indent=2)+'\n')
    print('Windows app assembled:',APP,flush=True)

if __name__=='__main__': main()
