# Public project files

- `app/`: the complete application code and renderer assets recovered from the
  publisher's `app.asar`, including the bundled JavaScript, CSS, fonts, and HTML.
  These are the shipped build files; the publisher's original TypeScript/React
  development project was not present in the downloaded release.
- `python/`: the original voice script, Python project definition, and complete
  locked dependency versions.
- `assets/`: the original app icon converted to the Windows ICO format.
- `scripts/`: the Windows assembly, branding, and packaging scripts.
- `.github/workflows/build-windows.yml`: the manually triggered build and release
  workflow. It does not run automatically on commits.
- `build-tools/`: the npm dependency manifest and lock used for the original
  local packaging tools. The workflow installs its explicitly pinned build tools.
- `verification/local-build/`: input download records, dependency audit, original
  speech smoke-test results, and archive integrity reports. These refer to the
  first local build; the current published build is recreated on GitHub Actions
  from the same verified inputs and has a different installer checksum.
- `THIRD_PARTY_NOTICES.md`: the original release's third-party notices.

## Complete Windows package

The [release downloads](https://github.com/BlueShepy/dub-off-editor-windows/releases/tag/v0.1.0-windows.1)
include a **Portable ZIP** containing every file in the unpacked Windows app:
Electron, the original `resources/app.asar`, FFmpeg, yt-dlp, Python, installed
Python libraries, Microsoft runtime DLLs, offline speech models, and notices.
These large third-party binaries and models are distributed as release assets
rather than Git source files. Extract the ZIP and open `Dub-Off Editor.exe`.

The installer packages the same complete app. `SHA256SUMS.txt` on the release
contains checksums for both downloads. Software and models retain their original
copyrights and licences; this repository does not grant new rights in the
publisher's application or claim to contain development sources it did not ship.

## Rebuilding

Use the repository's **Actions → Build and publish Windows installer → Run
workflow** entry. The workflow downloads and verifies the original Mac release
and the matching Windows dependencies, rebuilds both packages, checks archive
integrity, and publishes them to the release. It needs repository contents-write
permission to attach the downloads and update the documented checksum.

The runtime files are assembled from the release inputs; `app/` and `python/`
are public snapshots of the original files and are not automatically compiled
into replacement frontend or speech code. The assembler deliberately preserves
the publisher's application archive unchanged.
