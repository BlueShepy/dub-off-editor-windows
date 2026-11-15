# Dub-Off Editor for Windows

Unofficial Windows x64 packaging of [Dub-Off Editor](https://dub-off.com/editor) 0.1.0. This repository is not affiliated with or endorsed by the original publisher.

## Download

[Download the Windows installer](https://github.com/BlueShepy/dub-off-editor-windows/releases/download/v0.1.0-windows.1/Dub-Off-Editor-0.1.0-Windows-x64-Setup.exe) (approximately 917 MB).

Requires 64-bit Windows 10 or 11. Run the installer; it installs for your Windows user and adds Dub-Off Editor to the Start menu. The installer is unsigned.

The editor application archive, interface, Python voice script, dependency lock, and model data are unchanged from the original Mac release. Windows versions of Electron, Python, FFmpeg, yt-dlp, and the speech dependencies replace the Mac runtimes. The original icon is preserved. Speech tools and models are bundled for offline processing.

## Verification and limits

The source DMG matched the publisher's SHA-256. Platform dependencies matched their published checksums or the original dependency lock. The Windows application's archive is byte-for-byte identical to the original archive. Both the complete payload and the NSIS installer passed integrity checks.

Windows Python, FFmpeg, and the speech libraries ran under Wine 10 on Linux. With network model access disabled, a one-second silent WAV completed Demucs separation and Whisper-small transcription, producing both stems and a transcript with no dialogue words. This verifies model loading and the processing pipeline, not transcription accuracy. The test used Wine-specific compatibility settings that are not shipped in the Windows app.

**Installation, graphical editing, and export have not been tested on a real Windows PC.** Wine graphics limitations prevented interface verification. This is an experimental repack, not a verified official Windows release.

The original update mechanism remains. At build time the publisher's Windows download returned 404 and its release manifest listed only a Mac build. Automatic Windows updates therefore depend on the publisher providing its Windows update feed.

## Integrity

The release includes SHA256SUMS.txt. Verify the downloaded installer in PowerShell:

```powershell
Get-FileHash .\Dub-Off-Editor-0.1.0-Windows-x64-Setup.exe -Algorithm SHA256
```

Installer SHA-256:

`ef1c359b7dd5ca3eaccc7b23c8453c4ad5dcb9b39a3a62bcf8a3e81f91fa39a9`

Original Mac installer SHA-256:

`98f997a7a19332062e78eee8e07d00fa7a0aedda3ded94e9ac42d59692b7825f`

Original application archive SHA-256 (unchanged in this build):

`102459ea85a6fd996a09c2081faed7fe70c560a9b9d308c2da00acbcb803d6b6`

## Credits and licences

Dub-Off Editor belongs to its original publisher. Original software and bundled third-party components retain their original copyrights and licences. Third-party notices are included in the application. No licence or ownership of the original application is asserted by this repository.
