"""Audio spectrum analysis and instrument verification tools."""

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

try:
    import librosa
    import numpy as np
    import soundfile as sf
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


def register(mcp: FastMCP) -> None:
    """Register audio analysis tools with the MCP server."""

    @mcp.tool()
    def analyze_spectrum(audio_path: str) -> dict[str, Any]:
        """Perform FFT spectrum analysis on an audio file.

        Analyzes frequency content, spectral characteristics, and attempts
        to identify instrument type based on spectral signature.

        Args:
            audio_path: Path to audio file (wav, flac, ogg, mp3)

        Returns:
            Spectral analysis including:
            - frequency_bands: Energy distribution across frequency ranges
            - spectral_centroid: Center of mass of spectrum (brightness)
            - spectral_rolloff: Frequency below which 85% of energy is contained
            - zero_crossing_rate: Texture indicator (noisy vs tonal)
            - dominant_frequencies: Top frequency peaks
            - instrument_characteristics: Inferred instrument type
        """
        if not AUDIO_AVAILABLE:
            return {
                "status": "error",
                "message": "librosa not installed. Install with: pip install librosa soundfile"
            }

        # Load audio
        y, sr = librosa.load(audio_path, sr=None, duration=3.0)

        # FFT spectrum
        fft = np.fft.fft(y)
        magnitude = np.abs(fft)
        frequency = np.fft.fftfreq(len(fft), 1/sr)

        # Get positive frequencies only
        positive_freq_idx = frequency > 0
        frequency = frequency[positive_freq_idx]
        magnitude = magnitude[positive_freq_idx]

        # Frequency band energy (bass, mids, highs)
        def band_energy(freqs, mag, low, high):
            mask = (freqs >= low) & (freqs < high)
            return float(np.sum(mag[mask]))

        band_energy_vals = {
            "sub_bass_20_60": band_energy(frequency, magnitude, 20, 60),
            "bass_60_250": band_energy(frequency, magnitude, 60, 250),
            "low_mids_250_500": band_energy(frequency, magnitude, 250, 500),
            "mids_500_2k": band_energy(frequency, magnitude, 500, 2000),
            "high_mids_2k_4k": band_energy(frequency, magnitude, 2000, 4000),
            "presence_4k_6k": band_energy(frequency, magnitude, 4000, 6000),
            "brilliance_6k_20k": band_energy(frequency, magnitude, 6000, 20000),
        }

        # Normalize band energies
        total_energy = sum(band_energy_vals.values())
        if total_energy > 0:
            band_percentages = {k: (v/total_energy)*100 for k, v in band_energy_vals.items()}
        else:
            band_percentages = {k: 0.0 for k in band_energy_vals.keys()}

        # Spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]

        # Dominant frequencies (top 5 peaks)
        peak_indices = np.argsort(magnitude)[-5:][::-1]
        dominant_freqs = [
            {"frequency": float(frequency[i]), "magnitude": float(magnitude[i])}
            for i in peak_indices
        ]

        # Instrument characteristic inference
        avg_centroid = float(np.mean(spectral_centroids))
        avg_zcr = float(np.mean(zero_crossing_rate))
        high_freq_energy = band_percentages["brilliance_6k_20k"]

        # Classify based on spectral characteristics
        characteristics = []

        if high_freq_energy > 30 and avg_zcr > 0.15:
            characteristics.append("cymbal-like (high frequency noise)")
        elif high_freq_energy > 20 and avg_centroid > 3000:
            characteristics.append("bright metallic (possible hi-hat or cymbal)")
        elif avg_centroid < 500 and band_percentages["bass_60_250"] > 40:
            characteristics.append("bass-heavy (kick drum or bass synth)")
        elif avg_zcr > 0.2:
            characteristics.append("noisy/percussive")
        elif avg_zcr < 0.05:
            characteristics.append("tonal/pitched")

        if band_percentages["presence_4k_6k"] > 15:
            characteristics.append("cutting presence")

        if not characteristics:
            characteristics.append("unclear - mixed spectral content")

        return {
            "status": "success",
            "path": audio_path,
            "sample_rate": int(sr),
            "duration": float(len(y) / sr),
            "frequency_bands_percent": band_percentages,
            "spectral_centroid_hz": float(avg_centroid),
            "spectral_rolloff_hz": float(np.mean(spectral_rolloff)),
            "zero_crossing_rate": float(avg_zcr),
            "dominant_frequencies": dominant_freqs,
            "instrument_characteristics": characteristics,
            "interpretation": _interpret_spectrum(band_percentages, avg_centroid, avg_zcr, high_freq_energy),
        }

    @mcp.tool()
    def extract_sf2_note(
        sf2_path: str,
        output_path: str,
        bank: int = 0,
        patch: int = 0,
        note: int = 60,
        duration: float = 2.0,
    ) -> dict[str, Any]:
        """Extract a single note from an SF2 soundfont to audio file.

        Creates a minimal LMMS project with single note, renders it,
        allowing spectrum analysis before using in production.

        Args:
            sf2_path: Path to .sf2 or .sf3 soundfont file
            output_path: Path to save extracted audio (wav recommended)
            bank: Bank number (0-999, use 128 for drums)
            patch: Patch/program number (0-127)
            note: MIDI note number (0-127)
            duration: Duration in seconds (default 2.0)

        Returns:
            Extraction info with path to audio file ready for spectrum analysis
        """
        import tempfile
        import subprocess
        from lmms_mcp.xml.parser import parse_project
        from lmms_mcp.xml.writer import write_project
        from lmms_mcp.models.project import Project
        from lmms_mcp.models.track import SF2InstrumentTrack
        from lmms_mcp.models.pattern import Pattern
        from lmms_mcp.models.note import Note

        # Create temporary project
        temp_dir = Path(tempfile.gettempdir())
        temp_project = temp_dir / "sf2_extract_test.mmp"

        # Build minimal project
        project = Project(name="SF2 Extract", bpm=120, time_sig_num=4, time_sig_den=4)

        # Add SF2 track
        track = SF2InstrumentTrack(
            name="Extract",
            sf2_path=sf2_path,
            bank=bank,
            patch=patch,
        )
        project.add_track(track)

        # Add single note pattern
        beats = duration * 2  # 120 BPM = 2 beats per second
        pattern = Pattern(name="Note", position=0, length=1)
        pattern.add_note(Note(pitch=note, start=0, length=beats, velocity=100))
        track.add_pattern(pattern)

        # Write project
        write_project(project, temp_project)

        # Render with LMMS
        try:
            result = subprocess.run(
                [
                    "lmms",
                    "render",
                    "-f", "wav",
                    "-o", output_path,
                    str(temp_project),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {
                    "status": "error",
                    "message": f"LMMS render failed: {result.stderr}",
                }

            return {
                "status": "success",
                "output_path": output_path,
                "sf2_path": sf2_path,
                "bank": bank,
                "patch": patch,
                "note": note,
                "duration": duration,
                "message": f"Extracted note {note} from bank {bank} patch {patch} → {output_path}",
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "LMMS render timed out during extraction",
            }
        except FileNotFoundError:
            return {
                "status": "error",
                "message": "lmms command not found",
            }


def _interpret_spectrum(
    bands: dict[str, float],
    centroid: float,
    zcr: float,
    high_freq: float,
) -> str:
    """Interpret spectral characteristics in plain English."""

    interpretation = []

    # Frequency distribution
    if high_freq > 30:
        interpretation.append("VERY bright with strong high-frequency content (cymbal/hi-hat territory)")
    elif high_freq > 15:
        interpretation.append("Bright with significant high frequencies (possible cymbal or metallic percussion)")
    elif centroid > 2000:
        interpretation.append("Bright/cutting sound (high spectral center)")
    elif centroid < 500:
        interpretation.append("Dark/bass-heavy sound (low spectral center)")
    else:
        interpretation.append("Mid-range focused sound")

    # Texture
    if zcr > 0.15:
        interpretation.append("Noisy/unpitched texture (typical of percussion/cymbals)")
    elif zcr < 0.05:
        interpretation.append("Smooth/tonal texture (typical of pitched instruments)")

    # Specific bands
    if bands.get("brilliance_6k_20k", 0) > 25:
        interpretation.append("Strong brilliance/air (6-20kHz) - definitely cymbal-like")

    if bands.get("bass_60_250", 0) > 50:
        interpretation.append("Bass-dominant (likely kick drum or bass synth)")

    return " | ".join(interpretation) if interpretation else "Mixed/unclear characteristics"
