# Third-party notices

Dub-Off Editor ships these programs, libraries, models and fonts beside its
own code. Each keeps its own licence. The versions are the ones the scripts
in `scripts/` pin; the source links are where each one's source code is
published, as the GPL and LGPL require.

## Programs run by the editor

### FFmpeg 9.0.2 (ffmpeg and ffprobe)

GPL version 3 or later. These are static builds configured with
`--enable-gpl`, so they include GPL components, notably x264 (GPL-2.0-or-later)
for the H.264 encodes. Because of that, the two programs as shipped are
distributed under the GPL.

- FFmpeg source: https://ffmpeg.org/download.html (release 9.0.2,
  https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz) and
  https://git.ffmpeg.org/ffmpeg.git
- x264 source: https://code.videolan.org/videolan/x264
- Windows x64 and Linux x64 builds: BtbN/FFmpeg-Builds, autobuild
  2026-09-30-13-08 (`ffmpeg-n9.0.2-17-g2a571b6068-*-gpl-9.0`). Build scripts
  and the exact configuration: https://github.com/BtbN/FFmpeg-Builds
- macOS arm64 build: Martin Riedl, https://ffmpeg.martin-riedl.de (release
  9.0.2). Build scripts: https://git.martin-riedl.de/ffmpeg/build-script
- Licence texts: https://www.gnu.org/licenses/gpl-3.0.html and
  https://www.gnu.org/licenses/old-licenses/gpl-2.0.html

The editor runs these as separate programs; it does not link to them.

### yt-dlp 2026.10.21

The Unlicense (public domain). https://github.com/yt-dlp/yt-dlp

The release builds the editor ships (`yt-dlp_macos.zip`, `yt-dlp.exe`,
`yt-dlp_linux`) are PyInstaller bundles that also contain a Python runtime
and Python packages under their own licences (Python Software Foundation
License, and others listed in the bundle). Release page:
https://github.com/yt-dlp/yt-dlp/releases/tag/2026.10.21. "Check for yt-dlp
update" downloads a newer official release from the same place.

### uv 0.13.1 (build time only)

Apache-2.0 or MIT. https://github.com/astral-sh/uv

uv builds the voice tools when the installer is made. It is not shipped.

## The voice tools

A Python environment built at package time (`scripts/build-voice-env.mjs`)
and shipped read-only inside the app.

### CPython 3.12

Python Software Foundation License Version 2.
https://www.python.org/ and https://github.com/python/cpython. The
interpreter is a python-build-standalone build
(https://github.com/astral-sh/python-build-standalone, BSD-3-Clause build
scripts), which bundles OpenSSL (Apache-2.0), SQLite (public domain),
zlib, libffi, XZ and others under their own licences; see the
build's `PYTHON.json` and licence files.

### Microsoft Visual C++ Runtime (Windows only)

On Windows the voice tools carry the Visual C++ 2015-2022 runtime DLLs that
torch, CTranslate2 and onnxruntime import: `msvcp140.dll`,
`msvcp140_1.dll`, `msvcp140_atomic_wait.dll`, `vcruntime140.dll`,
`vcruntime140_1.dll` and `vcruntime140_threads.dll`, or whichever of them the
build's import check finds (`src/main/msvcRuntime.ts`). They are copied
unmodified from the build machine's Visual Studio or Build Tools install
(`VC\Redist\MSVC\<version>\x64\Microsoft.VC143.CRT`).

Copyright Microsoft Corporation. They are Distributable Code under the
Microsoft Software License Terms of the Visual Studio edition they come
from, which let an application ship the files on Microsoft's REDIST list,
in object code form, unmodified, alongside the application. The terms also
ask that:

- the files ship only as part of a program that adds significant function
  to them;
- whoever receives them agrees to terms that protect them at least as much
  as Microsoft's do;
- Microsoft's names, logos and trademarks aren't used to market the
  program.

The REDIST list and the redistribution guidance:
https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files and
https://learn.microsoft.com/visualstudio/releases/2022/redistribution. They
are not covered by this app's own licence.

### PyTorch 2.14.1 (CPU build)

BSD-3-Clause. https://github.com/pytorch/pytorch. Third-party code inside
PyTorch is listed in its `NOTICE` and
https://github.com/pytorch/pytorch/blob/main/NOTICE.

### Demucs 4.1.0 and the htdemucs model

MIT. https://github.com/adefossez/demucs (originally
https://github.com/facebookresearch/demucs). The htdemucs weights are
published with Demucs under the same licence.

### faster-whisper 1.2.1, CTranslate2 4.8.3 and the Whisper small model

MIT. https://github.com/SYSTRAN/faster-whisper and
https://github.com/OpenNMT/CTranslate2. The model is Systran/faster-whisper-small
(https://huggingface.co/Systran/faster-whisper-small), a conversion of
OpenAI's Whisper small (MIT, https://github.com/openai/whisper).

### Other Python packages

Installed exactly as `python/uv.lock` pins them, each under its own licence,
which ships in its `*.dist-info` folder: among them NumPy (BSD-3-Clause),
PyAV 18.1.0 (BSD-3-Clause, bundling FFmpeg libraries under the LGPL; source
https://github.com/PyAV-Org/PyAV), Hugging Face Hub and tokenizers
(Apache-2.0), ONNX Runtime (MIT), julius, einops and lameenc (MIT; lameenc
bundles LAME, LGPL-2.0, https://lame.sourceforge.io).

## The app itself

- Electron 45 (MIT), which includes Chromium and Node.js under their own
  licences, listed in `LICENSES.chromium.html` next to the app.
  https://github.com/electron/electron
- React and React DOM (MIT). https://github.com/facebook/react
- Tailwind CSS (MIT). https://github.com/tailwindlabs/tailwindcss

## Fonts

SIL Open Font License 1.1, latin subsets: Bebas Neue
(https://github.com/dharmatype/Bebas-Neue), Barlow Condensed
(https://github.com/jpt/barlow) and Inter (https://github.com/rsms/inter).
