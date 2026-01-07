"""Synthesizer instrument MCP tools for LMMS."""

from pathlib import Path
from typing import Any

from lmms_mcp.xml.parser import parse_project
from lmms_mcp.xml.writer import write_project
from lmms_mcp.models.track import (
    WAVE_SHAPES, MODULATION_ALGOS,
    Oscillator, TripleOscillatorTrack, KickerTrack, MonstroTrack,
    FilterSettings, Pattern,
)


def register(mcp):
    """Register synth tools with the MCP server."""

    @mcp.tool()
    def add_tripleoscillator_track(
        path: str,
        name: str,
        osc1_wave: str | int = "saw",
        osc2_wave: str | int = "saw",
        osc3_wave: str | int = "square",
        osc1_vol: float = 100,
        osc2_vol: float = 100,
        osc3_vol: float = 50,
        osc1_detune: int = 0,
        osc2_detune: int = -12,
        osc3_detune: int = 0,
        mod_algo: str | int = "pm",
    ) -> dict[str, Any]:
        """Add a Triple Oscillator synthesizer track.

        Triple Oscillator is LMMS's classic 3-oscillator subtractive synth.
        Great for bass, leads, pads - everything!

        Waveforms: sine, triangle, saw, square, moogsaw, exp, noise

        Modulation algorithms:
        - pm: Phase modulation (Osc2 modulates Osc1)
        - am: Amplitude modulation
        - mix: Simple mix of all oscillators
        - sync: Oscillator sync
        - fm: Frequency modulation

        Args:
            path: Path to .mmp or .mmpz file
            name: Track name
            osc1_wave: Oscillator 1 waveform (default saw)
            osc2_wave: Oscillator 2 waveform (default saw)
            osc3_wave: Oscillator 3 waveform (default square)
            osc1_vol: Oscillator 1 volume 0-200 (default 100)
            osc2_vol: Oscillator 2 volume 0-200 (default 100)
            osc3_vol: Oscillator 3 volume 0-200 (default 50)
            osc1_detune: Oscillator 1 coarse detune in semitones (default 0)
            osc2_detune: Oscillator 2 coarse detune (default -12, one octave down)
            osc3_detune: Oscillator 3 coarse detune (default 0)
            mod_algo: Modulation algorithm (default pm)

        Returns:
            New track info
        """
        project = parse_project(Path(path))

        # Parse waveforms
        def parse_wave(w):
            if isinstance(w, str):
                return WAVE_SHAPES.get(w.lower(), 2)  # default to saw
            return int(w)

        # Parse modulation algo
        if isinstance(mod_algo, str):
            algo = MODULATION_ALGOS.get(mod_algo.lower(), 2)  # default to pm
        else:
            algo = int(mod_algo)

        track = TripleOscillatorTrack(
            name=name,
            osc1=Oscillator(
                wave=parse_wave(osc1_wave),
                volume=osc1_vol,
                coarse=osc1_detune,
            ),
            osc2=Oscillator(
                wave=parse_wave(osc2_wave),
                volume=osc2_vol,
                coarse=osc2_detune,
            ),
            osc3=Oscillator(
                wave=parse_wave(osc3_wave),
                volume=osc3_vol,
                coarse=osc3_detune,
            ),
            mod_algo1=algo,
            mod_algo2=algo,
            filter=FilterSettings(),
            effects=[],
            patterns=[],
        )

        project.tracks.append(track)
        track_id = len(project.tracks) - 1
        write_project(project, Path(path))

        return {
            "status": "created",
            "track_id": track_id,
            "name": name,
            "instrument": "tripleoscillator",
            "oscillators": {
                "osc1": {"wave": osc1_wave, "vol": osc1_vol, "detune": osc1_detune},
                "osc2": {"wave": osc2_wave, "vol": osc2_vol, "detune": osc2_detune},
                "osc3": {"wave": osc3_wave, "vol": osc3_vol, "detune": osc3_detune},
            },
            "mod_algo": mod_algo,
        }

    @mcp.tool()
    def add_kicker_track(
        path: str,
        name: str = "Kick",
        start_freq: float = 400,
        end_freq: float = 40,
        decay: float = 200,
        distortion: float = 0.8,
        gain: float = 1.0,
    ) -> dict[str, Any]:
        """Add a Kicker synthesizer track for bass drums and sub bass.

        Kicker generates a pitch-sweeping sine wave perfect for:
        - Punchy kick drums
        - Deep sub bass
        - 808-style bass

        The pitch sweeps from start_freq down to end_freq over decay time.

        Args:
            path: Path to .mmp or .mmpz file
            name: Track name (default "Kick")
            start_freq: Starting frequency in Hz (default 400)
            end_freq: Ending frequency in Hz (default 40)
            decay: Decay time in ms (default 200)
            distortion: Distortion amount 0-1 (default 0.8)
            gain: Output gain (default 1.0)

        Returns:
            New track info
        """
        project = parse_project(Path(path))

        track = KickerTrack(
            name=name,
            start_freq=start_freq,
            end_freq=end_freq,
            decay=decay,
            distortion=distortion,
            gain=gain,
            effects=[],
            patterns=[],
        )

        project.tracks.append(track)
        track_id = len(project.tracks) - 1
        write_project(project, Path(path))

        return {
            "status": "created",
            "track_id": track_id,
            "name": name,
            "instrument": "kicker",
            "settings": {
                "start_freq": start_freq,
                "end_freq": end_freq,
                "decay": decay,
                "distortion": distortion,
                "gain": gain,
            },
            "tip": "Add notes at low pitches (C1-C2) for sub bass, higher for punch",
        }

    @mcp.tool()
    def add_monstro_track(
        path: str,
        name: str = "Monstro",
        osc1_wave: int = 2,
        osc2_wave: int = 2,
        osc3_wave: int = 0,
        lfo1_rate: float = 1.0,
        lfo2_rate: float = 0.5,
    ) -> dict[str, Any]:
        """Add a Monstro modular synthesizer track.

        Monstro is LMMS's most powerful synth with:
        - 3 oscillators with multiple waveforms
        - 2 LFOs with matrix routing
        - 2 envelopes
        - Sub-oscillator
        - Extensive modulation matrix

        Great for complex evolving sounds, pads, and sound design.

        Args:
            path: Path to .mmp or .mmpz file
            name: Track name (default "Monstro")
            osc1_wave: Oscillator 1 waveform 0-6 (default 2=saw)
            osc2_wave: Oscillator 2 waveform (default 2=saw)
            osc3_wave: Oscillator 3 waveform (default 0=sine for sub)
            lfo1_rate: LFO 1 rate (default 1.0)
            lfo2_rate: LFO 2 rate (default 0.5)

        Returns:
            New track info
        """
        project = parse_project(Path(path))

        track = MonstroTrack(
            name=name,
            osc1_wave=osc1_wave,
            osc2_wave=osc2_wave,
            osc3_wave=osc3_wave,
            lfo1_rate=lfo1_rate,
            lfo2_rate=lfo2_rate,
            filter=FilterSettings(),
            effects=[],
            patterns=[],
        )

        project.tracks.append(track)
        track_id = len(project.tracks) - 1
        write_project(project, Path(path))

        return {
            "status": "created",
            "track_id": track_id,
            "name": name,
            "instrument": "monstro",
            "settings": {
                "osc1_wave": osc1_wave,
                "osc2_wave": osc2_wave,
                "osc3_wave": osc3_wave,
                "lfo1_rate": lfo1_rate,
                "lfo2_rate": lfo2_rate,
            },
        }

    @mcp.tool()
    def set_oscillator_params(
        path: str,
        track_id: int,
        osc_num: int,
        wave: str | int | None = None,
        volume: float | None = None,
        pan: float | None = None,
        coarse: int | None = None,
        fine_l: float | None = None,
        fine_r: float | None = None,
        phase: float | None = None,
    ) -> dict[str, Any]:
        """Modify oscillator parameters on a Triple Oscillator track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of Triple Oscillator track
            osc_num: Oscillator number (1, 2, or 3)
            wave: Waveform (sine, triangle, saw, square, moogsaw, exp, noise)
            volume: Volume 0-200 (default 100)
            pan: Pan -100 to 100 (default 0)
            coarse: Coarse detune in semitones
            fine_l: Fine detune left channel
            fine_r: Fine detune right channel
            phase: Phase offset 0-360

        Returns:
            Updated oscillator info
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, TripleOscillatorTrack):
            return {"status": "error", "error": f"Track {track_id} is not a Triple Oscillator"}

        if osc_num not in (1, 2, 3):
            return {"status": "error", "error": "osc_num must be 1, 2, or 3"}

        # Get the oscillator
        osc = getattr(track, f"osc{osc_num}")

        # Update provided params
        if wave is not None:
            if isinstance(wave, str):
                osc.wave_shape = WAVE_SHAPES.get(wave.lower(), osc.wave_shape)
            else:
                osc.wave_shape = int(wave)

        if volume is not None:
            osc.volume = volume
        if pan is not None:
            osc.pan = pan
        if coarse is not None:
            osc.coarse = coarse
        if fine_l is not None:
            osc.fine_left = fine_l
        if fine_r is not None:
            osc.fine_right = fine_r
        if phase is not None:
            osc.phase_offset = phase

        write_project(project, Path(path))

        return {
            "status": "updated",
            "track_id": track_id,
            "oscillator": osc_num,
            "settings": {
                "wave": osc.wave_shape,
                "volume": osc.volume,
                "pan": osc.pan,
                "coarse": osc.coarse,
                "fine_l": osc.fine_left,
                "fine_r": osc.fine_right,
                "phase": osc.phase_offset,
            },
        }

    @mcp.tool()
    def set_kicker_params(
        path: str,
        track_id: int,
        start_freq: float | None = None,
        end_freq: float | None = None,
        decay: float | None = None,
        distortion: float | None = None,
        gain: float | None = None,
        env: float | None = None,
        noise: float | None = None,
        click: float | None = None,
        slope: float | None = None,
    ) -> dict[str, Any]:
        """Modify Kicker synth parameters.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of Kicker track
            start_freq: Starting frequency in Hz
            end_freq: Ending frequency in Hz
            decay: Decay time in ms
            distortion: Distortion amount 0-1
            gain: Output gain
            env: Envelope amount (pitch sweep depth)
            noise: Noise amount for attack
            click: Click amount for attack punch
            slope: Pitch envelope slope

        Returns:
            Updated Kicker info
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, KickerTrack):
            return {"status": "error", "error": f"Track {track_id} is not a Kicker"}

        # Update provided params
        if start_freq is not None:
            track.start_freq = start_freq
        if end_freq is not None:
            track.end_freq = end_freq
        if decay is not None:
            track.decay = decay
        if distortion is not None:
            track.distortion = distortion
        if gain is not None:
            track.gain = gain
        if env is not None:
            track.env = env
        if noise is not None:
            track.noise = noise
        if click is not None:
            track.click = click
        if slope is not None:
            track.slope = slope

        write_project(project, Path(path))

        return {
            "status": "updated",
            "track_id": track_id,
            "settings": {
                "start_freq": track.start_freq,
                "end_freq": track.end_freq,
                "decay": track.decay,
                "distortion": track.distortion,
                "gain": track.gain,
            },
        }

    @mcp.tool()
    def list_waveforms() -> dict[str, Any]:
        """List all available waveforms for synth oscillators.

        Returns:
            Dictionary of waveform names and numbers
        """
        descriptions = {
            "sine": "Pure sine wave - smooth, clean",
            "triangle": "Triangle wave - softer harmonics",
            "saw": "Sawtooth wave - bright, buzzy, GREAT FOR BASS",
            "square": "Square wave - hollow, woody",
            "moogsaw": "Moog-style saw - thick, fat",
            "exp": "Exponential wave - unique timbre",
            "noise": "White noise - for drums, effects",
        }

        return {
            "waveforms": {
                name: {"number": num, "description": descriptions.get(name, "")}
                for name, num in WAVE_SHAPES.items()
            },
            "recommended_for_dubstep": {
                "bass": ["saw", "moogsaw", "square"],
                "sub": ["sine", "triangle"],
                "lead": ["saw", "square"],
            },
        }

    @mcp.tool()
    def list_modulation_algos() -> dict[str, Any]:
        """List modulation algorithms for Triple Oscillator.

        Returns:
            Dictionary of algorithm names and descriptions
        """
        descriptions = {
            "pm": "Phase Modulation - Osc2 modulates Osc1 phase, FM-like",
            "am": "Amplitude Modulation - Osc2 modulates Osc1 volume",
            "mix": "Simple mix - All oscillators mixed together",
            "sync": "Oscillator Sync - Hard sync for aggressive timbres",
            "fm": "Frequency Modulation - Classic FM synthesis",
        }

        return {
            "modulation_algorithms": {
                name: {"number": num, "description": descriptions.get(name, "")}
                for name, num in MODULATION_ALGOS.items()
            },
            "recommended_for_dubstep": ["pm", "fm", "sync"],
        }
