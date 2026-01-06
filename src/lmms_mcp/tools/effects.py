"""Effects chain MCP tools for LMMS."""

from pathlib import Path
from typing import Any

from lmms_mcp.xml.parser import parse_project
from lmms_mcp.xml.writer import write_project
from lmms_mcp.models.track import (
    Effect, BUILTIN_EFFECTS,
    TripleOscillatorTrack, MonstroTrack, KickerTrack, SF2InstrumentTrack,
    InstrumentTrack,
)


def _get_track_with_effects(project, track_id: int):
    """Get a track that supports effects."""
    if track_id >= len(project.tracks):
        return None, f"Track {track_id} not found"

    track = project.tracks[track_id]
    effect_types = (TripleOscillatorTrack, MonstroTrack, KickerTrack, SF2InstrumentTrack, InstrumentTrack)

    if not isinstance(track, effect_types):
        return None, f"Track {track_id} does not support effects"

    # Ensure effects list exists
    if not hasattr(track, 'effects'):
        track.effects = []

    return track, None


def register(mcp):
    """Register effects tools with the MCP server."""

    @mcp.tool()
    def add_effect(
        path: str,
        track_id: int,
        effect_name: str,
        wet: float = 1.0,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Add an effect to a track's effects chain.

        Built-in effects: dualfilter, waveshaper, bassbooster, delay, flanger,
        reverbsc, compressor, bitcrush, stereoenhancer, amplifier, eq

        For LADSPA plugins, use effect_name="ladspaeffect" and provide
        plugin_file and plugin_name in params.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track to add effect to
            effect_name: Name of effect plugin
            wet: Wet/dry mix 0.0-1.0 (default 1.0)
            params: Effect-specific parameters (optional)

        Returns:
            New effect info
        """
        project = parse_project(Path(path))
        track, error = _get_track_with_effects(project, track_id)
        if error:
            return {"status": "error", "error": error}

        effect = Effect(
            name=effect_name,
            wet=wet,
            params=params or {},
        )

        # Handle LADSPA plugins
        if effect_name == "ladspaeffect" and params:
            effect.plugin_file = params.get("plugin_file")
            effect.plugin_name = params.get("plugin_name")

        track.effects.append(effect)
        write_project(project, Path(path))

        return {
            "status": "added",
            "track_id": track_id,
            "effect_index": len(track.effects) - 1,
            "effect": effect.describe(),
            "total_effects": len(track.effects),
        }

    @mcp.tool()
    def remove_effect(
        path: str,
        track_id: int,
        effect_index: int,
    ) -> dict[str, Any]:
        """Remove an effect from a track's effects chain.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track
            effect_index: Index of effect to remove

        Returns:
            Removal status
        """
        project = parse_project(Path(path))
        track, error = _get_track_with_effects(project, track_id)
        if error:
            return {"status": "error", "error": error}

        if effect_index >= len(track.effects):
            return {"status": "error", "error": f"Effect {effect_index} not found"}

        removed = track.effects.pop(effect_index)
        write_project(project, Path(path))

        return {
            "status": "removed",
            "track_id": track_id,
            "removed_effect": removed.name,
            "remaining_effects": len(track.effects),
        }

    @mcp.tool()
    def set_effect_params(
        path: str,
        track_id: int,
        effect_index: int,
        params: dict,
        wet: float | None = None,
        enabled: bool | None = None,
    ) -> dict[str, Any]:
        """Modify parameters of an existing effect.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track
            effect_index: Index of effect to modify
            params: Parameters to update (merged with existing)
            wet: New wet/dry value (optional)
            enabled: Enable/disable effect (optional)

        Returns:
            Updated effect info
        """
        project = parse_project(Path(path))
        track, error = _get_track_with_effects(project, track_id)
        if error:
            return {"status": "error", "error": error}

        if effect_index >= len(track.effects):
            return {"status": "error", "error": f"Effect {effect_index} not found"}

        effect = track.effects[effect_index]

        # Update params
        effect.params.update(params)

        if wet is not None:
            effect.wet = wet
        if enabled is not None:
            effect.enabled = enabled

        write_project(project, Path(path))

        return {
            "status": "updated",
            "track_id": track_id,
            "effect_index": effect_index,
            "effect": effect.describe(),
        }

    @mcp.tool()
    def list_track_effects(
        path: str,
        track_id: int,
    ) -> dict[str, Any]:
        """List all effects on a track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track

        Returns:
            List of effects with their settings
        """
        project = parse_project(Path(path))
        track, error = _get_track_with_effects(project, track_id)
        if error:
            return {"status": "error", "error": error}

        return {
            "track_id": track_id,
            "track_name": track.name,
            "effect_count": len(track.effects),
            "effects": [
                {"index": i, **e.describe()}
                for i, e in enumerate(track.effects)
            ],
        }

    @mcp.tool()
    def list_available_effects() -> dict[str, Any]:
        """List all available built-in effects with their parameters.

        Returns:
            Dictionary of effects with default parameters
        """
        effect_descriptions = {
            "dualfilter": "Two parallel filters - GREAT FOR WOBBLE BASS",
            "waveshaper": "Distortion/waveshaping - adds harmonics and grit",
            "bassbooster": "Low frequency boost - makes it THICC",
            "delay": "Echo/delay with LFO modulation",
            "flanger": "Flanging effect with LFO",
            "reverbsc": "High-quality reverb",
            "compressor": "Dynamic range compression - tightens sound",
            "bitcrush": "Bit reduction - lo-fi/digital distortion",
            "stereoenhancer": "Stereo width control",
            "amplifier": "Gain/volume/pan control",
            "eq": "3-band equalizer",
        }

        return {
            "builtin_effects": {
                name: {
                    "description": effect_descriptions.get(name, ""),
                    "default_params": params,
                }
                for name, params in BUILTIN_EFFECTS.items()
            },
            "plugin_effects": {
                "ladspaeffect": "LADSPA plugin wrapper - requires plugin_file and plugin_name",
                "lv2effect": "LV2 plugin wrapper",
                "vsteffect": "VST plugin wrapper",
            },
            "recommended_for_dubstep": [
                {"name": "dualfilter", "reason": "Moog filter for wobble"},
                {"name": "waveshaper", "reason": "Distortion for aggression"},
                {"name": "compressor", "reason": "Tighten the bass"},
                {"name": "bassbooster", "reason": "Extra low-end weight"},
            ],
        }

    @mcp.tool()
    def add_dubstep_wobble_chain(
        path: str,
        track_id: int,
        cutoff: float = 100,
        resonance: float = 0.8,
        distortion: float = 0.5,
    ) -> dict[str, Any]:
        """Add a preset dubstep wobble effects chain to a track.

        Adds: DualFilter (Moog) -> WaveShaper -> Compressor

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track
            cutoff: Filter cutoff frequency (default 100 Hz)
            resonance: Filter resonance (default 0.8)
            distortion: Distortion amount 0-1 (default 0.5)

        Returns:
            Added effects info
        """
        project = parse_project(Path(path))
        track, error = _get_track_with_effects(project, track_id)
        if error:
            return {"status": "error", "error": error}

        # DualFilter with Moog-style settings
        filter_effect = Effect(
            name="dualfilter",
            wet=1.0,
            params={
                "cut1": cutoff,
                "res1": resonance,
                "gain1": 1.5,
                "enabled1": 1,
                "cut2": 14000,
                "res2": 0.0,
                "enabled2": 0,
                "mix": 0,
            },
        )

        # WaveShaper for distortion
        distort_effect = Effect(
            name="waveshaper",
            wet=distortion,
            params={
                "input": 1.0 + distortion,
                "output": 1.0,
                "clip": 1,
            },
        )

        # Compressor to tighten
        comp_effect = Effect(
            name="compressor",
            wet=1.0,
            params={
                "threshold": -15,
                "ratio": 4.0,
                "attack": 5,
                "release": 50,
                "knee": 3.0,
                "makeupgain": 3.0,
            },
        )

        track.effects.extend([filter_effect, distort_effect, comp_effect])
        write_project(project, Path(path))

        return {
            "status": "added",
            "track_id": track_id,
            "chain": "DualFilter -> WaveShaper -> Compressor",
            "settings": {
                "cutoff": cutoff,
                "resonance": resonance,
                "distortion": distortion,
            },
            "total_effects": len(track.effects),
            "tip": "Use set_filter_lfo() on the track to add wobble modulation!",
        }
