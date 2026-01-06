"""Voice-to-track MCP tools for LMMS.

These tools enable recording voice/audio and converting it to LMMS tracks
with automatically detected notes and instrument matching.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from lmms_mcp.xml.parser import parse_project
from lmms_mcp.xml.writer import write_project
from lmms_mcp.models.track import SF2InstrumentTrack
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.models.note import Note


# MIDI note number to frequency conversion
def midi_to_freq(midi_note: int) -> float:
    """Convert MIDI note number to frequency in Hz."""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def freq_to_midi(freq: float) -> int:
    """Convert frequency in Hz to nearest MIDI note number."""
    if freq <= 0:
        return 0
    return int(round(69 + 12 * np.log2(freq / 440.0)))


def midi_to_note_name(midi_note: int) -> str:
    """Convert MIDI note number to note name (e.g., 60 -> 'C4')."""
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (midi_note // 12) - 1
    note = note_names[midi_note % 12]
    return f"{note}{octave}"


def record_audio_sox(output_path: str, duration: float, sample_rate: int = 44100) -> bool:
    """Record audio using sox (system fallback)."""
    try:
        cmd = [
            "sox", "-d", "-r", str(sample_rate), "-c", "1", "-b", "16",
            output_path, "trim", "0", str(duration)
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=duration + 5)
        return result.returncode == 0
    except Exception:
        return False


def record_audio_sounddevice(output_path: str, duration: float, sample_rate: int = 44100) -> bool:
    """Record audio using sounddevice library."""
    try:
        import sounddevice as sd
        import soundfile as sf

        samples = int(duration * sample_rate)
        audio = sd.rec(samples, samplerate=sample_rate, channels=1, dtype='float32')
        sd.wait()
        sf.write(output_path, audio, sample_rate)
        return True
    except Exception:
        return False


def analyze_pitch_crepe(audio_path: str, sample_rate: int = 44100) -> list[dict]:
    """Analyze pitch using CREPE neural network (most accurate)."""
    try:
        import crepe
        import soundfile as sf

        audio, sr = sf.read(audio_path)
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)  # Convert to mono

        # Run CREPE pitch detection
        time, frequency, confidence, _ = crepe.predict(
            audio, sr, viterbi=True, step_size=10  # 10ms steps
        )

        return [
            {"time": float(t), "frequency": float(f), "confidence": float(c)}
            for t, f, c in zip(time, frequency, confidence)
        ]
    except ImportError:
        return []


def analyze_pitch_librosa(audio_path: str, sample_rate: int = 44100) -> list[dict]:
    """Analyze pitch using librosa's pyin algorithm (fallback)."""
    try:
        import librosa

        y, sr = librosa.load(audio_path, sr=sample_rate)

        # Use pyin for pitch tracking
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'),
            sr=sr, frame_length=2048
        )

        times = librosa.times_like(f0, sr=sr)

        results = []
        for t, f, v, p in zip(times, f0, voiced_flag, voiced_probs):
            if not np.isnan(f) and v:
                results.append({
                    "time": float(t),
                    "frequency": float(f),
                    "confidence": float(p)
                })

        return results
    except ImportError:
        return []


def pitch_to_notes(
    pitch_data: list[dict],
    bpm: float = 120,
    min_duration: float = 0.1,
    confidence_threshold: float = 0.5,
    quantize: bool = True
) -> list[dict]:
    """Convert pitch analysis data to discrete notes.

    Args:
        pitch_data: List of {time, frequency, confidence} dicts
        bpm: Tempo for beat conversion
        min_duration: Minimum note duration in seconds
        confidence_threshold: Minimum confidence to include note
        quantize: Whether to quantize to 16th notes

    Returns:
        List of note dicts with pitch, start, length, velocity
    """
    if not pitch_data:
        return []

    beats_per_second = bpm / 60.0
    notes = []

    # Filter by confidence
    filtered = [p for p in pitch_data if p["confidence"] >= confidence_threshold]
    if not filtered:
        return []

    # Group consecutive pitches into notes
    current_note = None
    note_start = 0
    note_pitches = []

    for i, p in enumerate(filtered):
        midi = freq_to_midi(p["frequency"])

        if current_note is None:
            current_note = midi
            note_start = p["time"]
            note_pitches = [midi]
        elif abs(midi - current_note) <= 1:  # Same note (allow semitone wobble)
            note_pitches.append(midi)
        else:
            # End current note, start new one
            duration = p["time"] - note_start
            if duration >= min_duration:
                avg_pitch = int(round(np.mean(note_pitches)))
                avg_confidence = np.mean([x["confidence"] for x in filtered
                                         if note_start <= x["time"] < p["time"]])

                start_beat = note_start * beats_per_second
                length_beats = duration * beats_per_second

                if quantize:
                    # Quantize to 16th notes
                    start_beat = round(start_beat * 4) / 4
                    length_beats = max(0.25, round(length_beats * 4) / 4)

                notes.append({
                    "pitch": avg_pitch,
                    "note_name": midi_to_note_name(avg_pitch),
                    "start": start_beat,
                    "length": length_beats,
                    "velocity": int(min(127, avg_confidence * 127)),
                })

            current_note = midi
            note_start = p["time"]
            note_pitches = [midi]

    # Handle last note
    if current_note is not None and note_pitches:
        duration = filtered[-1]["time"] - note_start + 0.1
        if duration >= min_duration:
            avg_pitch = int(round(np.mean(note_pitches)))
            start_beat = note_start * beats_per_second
            length_beats = duration * beats_per_second

            if quantize:
                start_beat = round(start_beat * 4) / 4
                length_beats = max(0.25, round(length_beats * 4) / 4)

            notes.append({
                "pitch": avg_pitch,
                "note_name": midi_to_note_name(avg_pitch),
                "start": start_beat,
                "length": length_beats,
                "velocity": 100,
            })

    return notes


def suggest_instrument(notes: list[dict]) -> dict:
    """Suggest best instrument based on note range and character.

    Returns dict with sf2_path, bank, patch recommendations.
    """
    if not notes:
        return {"bank": 0, "patch": 0, "name": "Acoustic Grand Piano"}

    pitches = [n["pitch"] for n in notes]
    min_pitch = min(pitches)
    max_pitch = max(pitches)
    avg_pitch = np.mean(pitches)

    # Vocal ranges and suggested instruments
    # Bass: E2(40) - E4(64) -> Cello, Bass, or low synth
    # Tenor: C3(48) - C5(72) -> Trumpet, Sax, or synth lead
    # Alto: F3(53) - F5(77) -> Violin, Flute, or synth
    # Soprano: C4(60) - C6(84) -> Flute, Violin, or high synth

    if avg_pitch < 48:  # Bass range
        return {"bank": 0, "patch": 42, "name": "Cello"}
    elif avg_pitch < 60:  # Tenor/baritone range
        return {"bank": 0, "patch": 66, "name": "Tenor Sax"}
    elif avg_pitch < 72:  # Alto range
        return {"bank": 0, "patch": 40, "name": "Violin"}
    else:  # Soprano range
        return {"bank": 0, "patch": 73, "name": "Flute"}


def register(mcp):
    """Register voice tools with the MCP server."""

    @mcp.tool()
    def record_voice(
        output_path: str,
        duration: float = 5.0,
        sample_rate: int = 44100,
    ) -> dict[str, Any]:
        """Record audio from microphone.

        Args:
            output_path: Path to save the recorded audio (wav/flac)
            duration: Recording duration in seconds (default 5.0)
            sample_rate: Sample rate in Hz (default 44100)

        Returns:
            Recording status and file info
        """
        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Try sounddevice first, fall back to sox
        if record_audio_sounddevice(output_path, duration, sample_rate):
            method = "sounddevice"
            success = True
        elif record_audio_sox(output_path, duration, sample_rate):
            method = "sox"
            success = True
        else:
            return {
                "status": "error",
                "error": "Could not record audio. Install sounddevice or sox.",
            }

        return {
            "status": "recorded",
            "output_path": output_path,
            "duration": duration,
            "sample_rate": sample_rate,
            "method": method,
        }

    @mcp.tool()
    def analyze_voice(
        audio_path: str,
        bpm: float = 120.0,
        min_note_duration: float = 0.1,
        confidence_threshold: float = 0.5,
        quantize: bool = True,
    ) -> dict[str, Any]:
        """Analyze recorded audio and extract notes.

        Uses neural network pitch detection (CREPE) or librosa as fallback.

        Args:
            audio_path: Path to audio file to analyze
            bpm: Tempo for beat timing (default 120)
            min_note_duration: Minimum note length in seconds (default 0.1)
            confidence_threshold: Pitch confidence threshold 0-1 (default 0.5)
            quantize: Quantize notes to 16th notes (default True)

        Returns:
            Detected notes and suggested instrument
        """
        if not Path(audio_path).exists():
            return {"status": "error", "error": f"Audio file not found: {audio_path}"}

        # Try CREPE first (more accurate), fall back to librosa
        pitch_data = analyze_pitch_crepe(audio_path)
        method = "crepe"

        if not pitch_data:
            pitch_data = analyze_pitch_librosa(audio_path)
            method = "librosa"

        if not pitch_data:
            return {
                "status": "error",
                "error": "Could not analyze pitch. Install crepe or librosa[audio].",
            }

        notes = pitch_to_notes(
            pitch_data,
            bpm=bpm,
            min_duration=min_note_duration,
            confidence_threshold=confidence_threshold,
            quantize=quantize,
        )

        instrument = suggest_instrument(notes)

        return {
            "status": "analyzed",
            "method": method,
            "pitch_points": len(pitch_data),
            "note_count": len(notes),
            "notes": notes,
            "suggested_instrument": instrument,
            "note_range": {
                "min": min(n["pitch"] for n in notes) if notes else None,
                "max": max(n["pitch"] for n in notes) if notes else None,
                "min_name": min(notes, key=lambda n: n["pitch"])["note_name"] if notes else None,
                "max_name": max(notes, key=lambda n: n["pitch"])["note_name"] if notes else None,
            },
        }

    @mcp.tool()
    def voice_to_track(
        project_path: str,
        audio_path: str,
        track_name: str = "Voice Track",
        sf2_path: str | None = None,
        bank: int | None = None,
        patch: int | None = None,
        bpm: float | None = None,
        pattern_position: int = 0,
    ) -> dict[str, Any]:
        """Convert recorded voice to an LMMS instrument track.

        Full pipeline: analyzes audio, detects notes, creates SF2 track
        with appropriate instrument, and adds detected notes as a pattern.

        Args:
            project_path: Path to .mmp or .mmpz project file
            audio_path: Path to recorded audio file
            track_name: Name for the new track (default "Voice Track")
            sf2_path: Path to soundfont file (auto-selects if None)
            bank: SF2 bank number (auto-selects if None)
            patch: SF2 patch number (auto-selects if None)
            bpm: Override BPM for note timing (uses project BPM if None)
            pattern_position: Bar position for the pattern (default 0)

        Returns:
            New track info with notes and instrument selection
        """
        if not Path(audio_path).exists():
            return {"status": "error", "error": f"Audio file not found: {audio_path}"}

        project = parse_project(Path(project_path))

        # Use project BPM if not specified
        if bpm is None:
            bpm = float(project.bpm)

        # Analyze the voice recording
        pitch_data = analyze_pitch_crepe(audio_path)
        method = "crepe"
        if not pitch_data:
            pitch_data = analyze_pitch_librosa(audio_path)
            method = "librosa"

        if not pitch_data:
            return {
                "status": "error",
                "error": "Could not analyze pitch. Install crepe or librosa.",
            }

        notes = pitch_to_notes(pitch_data, bpm=bpm)

        if not notes:
            return {
                "status": "error",
                "error": "No notes detected in audio.",
            }

        # Get instrument suggestion or use provided values
        suggested = suggest_instrument(notes)

        if sf2_path is None:
            sf2_path = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
        if bank is None:
            bank = suggested["bank"]
        if patch is None:
            patch = suggested["patch"]

        # Create SF2 track
        sf2_track = SF2InstrumentTrack(
            name=track_name,
            sf2_path=sf2_path,
            bank=bank,
            patch=patch,
        )
        project.add_track(sf2_track)

        # Calculate pattern length (round up to nearest 4 bars)
        max_end = max(n["start"] + n["length"] for n in notes)
        pattern_length = int(np.ceil(max_end / 4) * 4 / 4)  # In bars
        pattern_length = max(4, pattern_length)

        # Create pattern
        pattern = Pattern(
            name=f"{track_name} - Converted",
            position=pattern_position,
            length=pattern_length,
        )
        sf2_track.patterns.append(pattern)

        # Add notes to pattern
        for n in notes:
            note = Note(
                pitch=n["pitch"],
                start=n["start"],
                length=n["length"],
                velocity=n["velocity"],
            )
            pattern.notes.append(note)

        write_project(project, Path(project_path))

        return {
            "status": "created",
            "track": sf2_track.describe(),
            "analysis_method": method,
            "note_count": len(notes),
            "notes": notes,
            "suggested_instrument": suggested,
            "used_instrument": {
                "sf2_path": sf2_path,
                "bank": bank,
                "patch": patch,
            },
            "pattern": {
                "name": pattern.name,
                "position": pattern_position,
                "length": pattern_length,
            },
        }

    @mcp.tool()
    def analyze_audio_file(
        audio_path: str,
    ) -> dict[str, Any]:
        """Get basic info about an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Audio file information (duration, sample rate, channels)
        """
        try:
            import soundfile as sf
            info = sf.info(audio_path)
            return {
                "status": "success",
                "path": audio_path,
                "duration": info.duration,
                "sample_rate": info.samplerate,
                "channels": info.channels,
                "format": info.format,
                "subtype": info.subtype,
            }
        except ImportError:
            # Fall back to sox
            try:
                result = subprocess.run(
                    ["soxi", audio_path],
                    capture_output=True,
                    text=True,
                )
                return {
                    "status": "success",
                    "path": audio_path,
                    "info": result.stdout,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}
