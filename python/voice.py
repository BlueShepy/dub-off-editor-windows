"""The editor's voice tools: Demucs vocal separation and faster-whisper
transcription, run by the Electron main process as a child.

    python voice.py info
    python voice.py prefetch --whisper small
    python voice.py separate --input clip.m4a --out DIR
    python voice.py run --input clip.m4a --out DIR --whisper small [--device cpu] [--no-separate]

Protocol: every line on stdout is one JSON object with an "event" key
(log, stage, progress, result, error). Libraries print to stdout too, so
sys.stdout is pointed at stderr and protocol lines go to the saved original.
"""

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

PROTOCOL_OUT = sys.stdout
sys.stdout = sys.stderr

DEMUCS_MODEL = "htdemucs"


def emit(event, **fields):
    PROTOCOL_OUT.write(json.dumps({"event": event, **fields}) + "\n")
    PROTOCOL_OUT.flush()


def peak_rss_mb():
    if sys.platform == "win32":
        return windows_peak_working_set_mb()
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # ru_maxrss is bytes on macOS and kilobytes on Linux.
    return round(peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024)


def windows_peak_working_set_mb():
    import ctypes
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD]
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    if not kernel32.K32GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return None
    return round(counters.PeakWorkingSetSize / (1024 * 1024))


def exit_when_parent_goes():
    # When the app exits or is killed, this process follows instead of
    # running on orphaned.
    if sys.platform == "win32":
        # Not a stdin read on Windows: while a thread blocks reading a pipe,
        # anything else touching that pipe waits too, and DLLs numpy loads
        # query stdin as they start, so `import torch` hung (the spike
        # measured `info` hanging past 180 s, against 2.5 s this way). Wait
        # on the parent process's handle instead.
        import ctypes

        SYNCHRONIZE = 0x00100000
        INFINITE = 0xFFFFFFFF
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        parent = kernel32.OpenProcess(SYNCHRONIZE, False, os.getppid())
        if not parent:
            os._exit(3)

        def watch():
            kernel32.WaitForSingleObject(parent, INFINITE)
            os._exit(3)
    else:
        # The app holds the other end of stdin; the read returns when it
        # goes. The raw descriptor, not sys.stdin.buffer: a daemon thread
        # parked inside the buffered reader holds its lock, and interpreter
        # shutdown then aborts ("could not acquire lock for <stdin>").
        def watch():
            while os.read(0, 65536):
                pass
            os._exit(3)

    threading.Thread(target=watch, daemon=True).start()


def cmd_info(_args):
    import torch
    import demucs
    import faster_whisper
    import ctranslate2
    import onnxruntime

    emit(
        "result",
        python=platform.python_version(),
        executable=sys.executable,
        platform=platform.platform(),
        torch=torch.__version__,
        cuda=torch.cuda.is_available(),
        mps=torch.backends.mps.is_available(),
        demucs=demucs.__version__,
        faster_whisper=faster_whisper.__version__,
        ctranslate2=ctranslate2.__version__,
        onnxruntime=onnxruntime.__version__,
    )


def cmd_prefetch(args):
    started = time.monotonic()
    emit("stage", stage="demucs-model", status="start", text=f"Fetching the {DEMUCS_MODEL} separation model")
    from demucs.pretrained import get_model

    get_model(DEMUCS_MODEL)
    emit("stage", stage="demucs-model", status="done")

    emit("stage", stage="whisper-model", status="start", text=f"Fetching the Whisper {args.whisper} model")
    from faster_whisper import download_model

    download_model(args.whisper)
    emit("stage", stage="whisper-model", status="done")
    emit("result", seconds=round(time.monotonic() - started, 2))


def separate(input_path, out_dir, device):
    from demucs.separate import main as demucs_main

    # The same arguments as app/scenes/build-pack.mjs, so stems match production.
    demucs_args = ["--two-stems=vocals", "-n", DEMUCS_MODEL]
    if device != "auto":
        demucs_args += ["-d", device]
    with tempfile.TemporaryDirectory(prefix="dub-off-demucs-") as work:
        demucs_main([*demucs_args, "-o", work, str(input_path)])
        stem_dir = Path(work) / DEMUCS_MODEL / input_path.name.rsplit(".", 1)[0]
        stems = {}
        for stem in ("vocals", "no_vocals"):
            target = out_dir / f"{stem}.wav"
            shutil.move(str(stem_dir / f"{stem}.wav"), target)
            stems[stem] = str(target)
    return stems


def transcribe(audio_path, model_size, duration_hint):
    from faster_whisper import WhisperModel

    # The model was fetched during setup; never reach the network here.
    model = WhisperModel(model_size, device="cpu", compute_type="int8", local_files_only=True)
    # Word times make the line boundaries; segment times are too coarse. The
    # VAD filter skips the stem's near-silent gaps, where Whisper otherwise
    # hallucinates a stray "Cheers." or "Hard." from leftover music.
    segments, info = model.transcribe(str(audio_path), word_timestamps=True, vad_filter=True)
    emit("log", text=f"Detected language {info.language} ({info.language_probability:.2f})")
    total = info.duration or duration_hint or 1
    words = []
    segment_list = []
    for segment in segments:
        segment_list.append({"start": round(segment.start, 2), "end": round(segment.end, 2), "text": segment.text.strip()})
        for w in segment.words or []:
            words.append({"word": w.word, "start": round(w.start, 2), "end": round(w.end, 2), "probability": round(w.probability, 3)})
        emit("progress", stage="transcribe", fraction=min(1, segment.end / total), text=segment.text.strip())
    return {
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 2),
        "segments": segment_list,
        # Lines are made from these in the app (src/core/proposeLines.ts).
        "words": words,
    }


def cmd_run(args):
    input_path = Path(args.input).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    timings = {}

    started = time.monotonic()
    import torch  # noqa: F401  (timed on its own: it dominates start-up)

    timings["import_torch"] = round(time.monotonic() - started, 2)

    stems = {}
    audio_for_whisper = input_path
    if args.separate:
        emit("stage", stage="separate", status="start", text="Separating the vocals")
        started = time.monotonic()
        stems = separate(input_path, out_dir, args.device)
        timings["separate"] = round(time.monotonic() - started, 2)
        emit("stage", stage="separate", status="done", seconds=timings["separate"])
        audio_for_whisper = Path(stems["vocals"])

    emit("stage", stage="transcribe", status="start", text="Transcribing the dialogue")
    started = time.monotonic()
    transcript = transcribe(audio_for_whisper, args.whisper, None)
    timings["transcribe"] = round(time.monotonic() - started, 2)
    emit("stage", stage="transcribe", status="done", seconds=timings["transcribe"])

    (out_dir / "transcript.json").write_text(json.dumps(transcript, indent=2), encoding="utf-8")
    emit(
        "result",
        stems=stems,
        transcript_path=str(out_dir / "transcript.json"),
        language=transcript["language"],
        language_probability=transcript["language_probability"],
        words=transcript["words"],
        timings=timings,
        peak_rss_mb=peak_rss_mb(),
        device=args.device,
    )


def cmd_separate(args):
    # The build's separation, when the trim changed after Analyse: the same
    # Demucs run, no transcript.
    input_path = Path(args.input).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    emit("stage", stage="separate", status="start", text="Separating the vocals")
    stems = separate(input_path, out_dir, args.device)
    emit("stage", stage="separate", status="done", seconds=round(time.monotonic() - started, 2))
    emit("result", stems=stems)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("info")
    prefetch = sub.add_parser("prefetch")
    prefetch.add_argument("--whisper", default="small")
    run = sub.add_parser("run")
    run.add_argument("--input", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--whisper", default="small")
    # "auto" is demucs's own choice (CUDA, then Apple's MPS, then CPU), which
    # is what production's command line gets.
    run.add_argument("--device", default="auto", choices=["auto", "cpu", "mps"])
    # Unticked in the app: Whisper hears the clip's own mix and no stems are made.
    run.add_argument("--no-separate", dest="separate", action="store_false")
    separate_only = sub.add_parser("separate")
    separate_only.add_argument("--input", required=True)
    separate_only.add_argument("--out", required=True)
    separate_only.add_argument("--device", default="auto", choices=["auto", "cpu", "mps"])
    args = parser.parse_args()
    if os.environ.get("DUB_VOICE_WATCH_STDIN") == "1":
        exit_when_parent_goes()
    try:
        {"info": cmd_info, "prefetch": cmd_prefetch, "run": cmd_run, "separate": cmd_separate}[args.command](args)
    except SystemExit as error:
        # demucs reports bad input by calling sys.exit with a message.
        if error.code not in (0, None):
            emit("error", message=f"exited: {error.code}")
        raise
    except Exception as error:
        traceback.print_exc()
        emit("error", message=f"{type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
