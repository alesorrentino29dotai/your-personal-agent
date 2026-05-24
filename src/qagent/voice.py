"""Optional voice I/O for qagent.

Heavy dependencies (sounddevice, numpy, faster_whisper, edge_tts, simpleaudio)
are imported lazily inside each function so the base install stays slim.
Install with:

    pip install -e '.[voice]'
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qagent.agent import Agent

_MISSING_DEPS_MSG = (
    "Voice deps not installed. Run: pip install -e '.[voice]'"
)


class VoiceDepsMissing(RuntimeError):
    """Raised when an optional voice dependency cannot be imported."""


def _require(module_name: str, pip_hint: str | None = None) -> Any:
    try:
        return __import__(module_name)
    except ImportError as exc:
        hint = pip_hint or _MISSING_DEPS_MSG
        raise VoiceDepsMissing(f"{hint} (missing: {module_name})") from exc


def record_audio(seconds: float = 8.0, samplerate: int = 16000) -> bytes | None:
    """Record `seconds` of mono audio at `samplerate` Hz.

    Returns raw 16-bit PCM bytes, or None if recording was aborted.
    Heavy deps (sounddevice, numpy) are imported lazily.
    """
    sd = _require("sounddevice")
    np = _require("numpy")

    frames = int(seconds * samplerate)
    print(f"[recording {seconds:.1f}s @ {samplerate}Hz...]", flush=True)
    try:
        audio = sd.rec(
            frames,
            samplerate=samplerate,
            channels=1,
            dtype="int16",
        )
        sd.wait()
    except KeyboardInterrupt:
        print("[recording aborted]", flush=True)
        return None
    except Exception as exc:
        print(f"[recording failed: {exc}]", flush=True)
        return None

    arr = np.asarray(audio, dtype=np.int16)
    return arr.tobytes()


def _write_wav(path: Path, pcm: bytes, samplerate: int = 16000) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(pcm)


def transcribe(audio_path: str | Path) -> str:
    """Transcribe a wav file to text using faster-whisper (CPU, int8)."""
    fw = _require("faster_whisper")
    WhisperModel = fw.WhisperModel

    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(audio_path))
    parts = [seg.text for seg in segments]
    return " ".join(p.strip() for p in parts).strip()


async def _edge_synthesize(text: str, voice: str, out_path: Path) -> None:
    edge_tts = _require("edge_tts")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def synthesize(
    text: str,
    voice: str = "en-US-AriaNeural",
    out_path: Path | None = None,
) -> Path:
    """Synthesize `text` to an mp3 using edge-tts. Returns the output path."""
    _require("edge_tts")

    if out_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        out_path = Path(tmp.name)
    else:
        out_path = Path(out_path)

    asyncio.run(_edge_synthesize(text, voice, out_path))
    return out_path


def _which(name: str) -> str | None:
    return shutil.which(name)


def play_audio(path: Path) -> None:
    """Play an audio file. Tries simpleaudio (wav), then ffplay/aplay/afplay."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()

    if suffix == ".wav":
        try:
            import simpleaudio  # type: ignore

            wave_obj = simpleaudio.WaveObject.from_wave_file(str(path))
            play_obj = wave_obj.play()
            play_obj.wait_done()
            return
        except ImportError:
            pass
        except Exception as exc:
            print(f"[simpleaudio failed: {exc}, falling back...]", flush=True)

    if _which("ffplay"):
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", str(path)],
            check=False,
        )
        return
    if suffix == ".wav" and _which("aplay"):
        subprocess.run(["aplay", "-q", str(path)], check=False)
        return
    if _which("afplay"):
        subprocess.run(["afplay", str(path)], check=False)
        return
    if _which("mpg123") and suffix == ".mp3":
        subprocess.run(["mpg123", "-q", str(path)], check=False)
        return

    raise VoiceDepsMissing(
        "No audio player found. Install simpleaudio, ffmpeg (ffplay), "
        "or alsa-utils (aplay)."
    )


def run_voice_loop(
    agent: "Agent",
    *,
    seconds: float = 8.0,
    voice: str = "en-US-AriaNeural",
) -> None:
    """Push-to-talk voice loop: record -> STT -> agent.ask -> TTS -> play."""
    print("Voice loop ready.")
    print(f"  recording length : {seconds:.1f}s")
    print(f"  TTS voice        : {voice}")
    print("  press Enter to record a turn, type 'q' + Enter to quit.")
    print()

    while True:
        try:
            cmd = input("Press Enter to start recording (or 'q' to quit): ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if cmd.strip().lower() in {"q", "quit", "exit"}:
            break

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            wav_path = tmp / "input.wav"
            mp3_path = tmp / "reply.mp3"

            try:
                pcm = record_audio(seconds=seconds)
            except VoiceDepsMissing as exc:
                print(str(exc), file=sys.stderr)
                return
            if not pcm:
                print("[no audio captured, skipping turn]")
                continue

            _write_wav(wav_path, pcm)

            try:
                text = transcribe(wav_path)
            except VoiceDepsMissing as exc:
                print(str(exc), file=sys.stderr)
                return

            text = text.strip()
            if not text:
                print("[no speech detected]")
                continue

            print(f"you: {text}")

            try:
                reply = agent.ask(text)
            except Exception as exc:
                print(f"[agent error: {exc}]", file=sys.stderr)
                continue

            reply = (reply or "").strip()
            print(f"agent: {reply}")
            if not reply:
                continue

            try:
                synthesize(reply, voice=voice, out_path=mp3_path)
                play_audio(mp3_path)
            except VoiceDepsMissing as exc:
                print(str(exc), file=sys.stderr)
                return
            except Exception as exc:
                print(f"[playback failed: {exc}]", file=sys.stderr)
