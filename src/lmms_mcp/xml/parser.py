"""Parse LMMS .mmp/.mmpz project files."""

import zlib
from pathlib import Path

from lxml import etree

from lmms_mcp.models.project import Project
from lmms_mcp.models.track import (
    InstrumentTrack, SampleTrack, Track, BBTrack, BBInstrument, BBStep,
    AutomationTrack, AutomationClip, AutomationPoint, SF2InstrumentTrack
)
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.models.note import Note


# LMMS tick constants
TICKS_PER_BAR = 192  # In 4/4 time
TICKS_PER_BEAT = 48  # 192 / 4 beats


def decompress_mmpz(data: bytes) -> bytes:
    """Decompress .mmpz file data.

    LMMS uses qCompress which prepends a 4-byte big-endian size header
    before the zlib data.
    """
    # Skip 4-byte size header
    return zlib.decompress(data[4:])


def parse_project(path: Path) -> Project:
    """Parse an LMMS project file.

    Args:
        path: Path to .mmp or .mmpz file

    Returns:
        Parsed Project object
    """
    data = path.read_bytes()

    # Decompress if .mmpz
    if path.suffix.lower() == ".mmpz":
        data = decompress_mmpz(data)

    root = etree.fromstring(data)

    # Parse header
    head = root.find("head")
    if head is None:
        head = etree.Element("head")

    project = Project(
        name=path.stem,
        bpm=int(head.get("bpm", 120)),
        time_sig_num=int(head.get("timesig_numerator", 4)),
        time_sig_den=int(head.get("timesig_denominator", 4)),
        master_volume=float(head.get("mastervol", 100)) / 100.0,
        master_pitch=int(head.get("masterpitch", 0)),
    )

    # Store raw XML for round-tripping unknown elements
    project._raw_xml = root

    # Parse tracks
    song = root.find("song")
    if song is not None:
        trackcontainer = song.find("trackcontainer")
        if trackcontainer is not None:
            for track_elem in trackcontainer.findall("track"):
                track = parse_track(track_elem)
                if track:
                    project.add_track(track)

    return project


def parse_track(elem: etree._Element) -> Track | None:
    """Parse a track element."""
    track_type = int(elem.get("type", 0))
    name = elem.get("name", "Track")
    muted = elem.get("muted", "0") == "1"
    solo = elem.get("solo", "0") == "1"

    # Track types in LMMS:
    # 0 = InstrumentTrack
    # 1 = BBTrack (beat/bassline)
    # 2 = SampleTrack
    # 5 = AutomationTrack

    if track_type == 0:
        # Instrument track
        instrument_elem = elem.find("instrumenttrack")
        instrument = "tripleoscillator"
        volume = 1.0
        pan = 0.0
        sf2_data = None
        sample_path = None  # For audiofileprocessor

        if instrument_elem is not None:
            volume = float(instrument_elem.get("vol", 100)) / 100.0
            pan = float(instrument_elem.get("pan", 0)) / 100.0  # LMMS uses -100 to 100

            # Get instrument plugin name and check for special instruments
            for child in instrument_elem:
                if child.tag == "instrument":
                    inst_child = list(child)
                    if inst_child:
                        instrument = inst_child[0].tag
                        if instrument == "sf2player":
                            sf2_data = parse_sf2player(inst_child[0])
                        elif instrument == "audiofileprocessor":
                            # Extract sample path for audiofileprocessor
                            sample_path = inst_child[0].get("src", "")

        # Create SF2 track if sf2player instrument detected
        if sf2_data is not None:
            track = SF2InstrumentTrack(
                name=name,
                volume=volume,
                pan=pan,
                muted=muted,
                solo=solo,
                **sf2_data
            )
        else:
            track = InstrumentTrack(
                name=name,
                instrument=instrument,
                volume=volume,
                pan=pan,
                muted=muted,
                solo=solo,
                sample_path=sample_path,  # Store sample path for audiofileprocessor
            )

        # Parse patterns
        for pattern_elem in elem.findall("pattern"):
            pattern = parse_pattern(pattern_elem)
            track.patterns.append(pattern)

        return track

    elif track_type == 1:
        # BB Track (Beat/Bassline)
        bbtrack_elem = elem.find("bbtrack")
        if bbtrack_elem is None:
            return None

        bb_track = BBTrack(
            name=name,
            muted=muted,
            solo=solo,
        )

        # Parse BB Track Content Object for timeline placement
        bbtco = elem.find("bbtco")
        if bbtco is not None:
            bb_track.bb_position = int(bbtco.get("pos", 0)) // TICKS_PER_BAR
            bb_track.bb_length = int(bbtco.get("len", 192)) // TICKS_PER_BAR

        # Parse BB track container for instruments
        bb_container = bbtrack_elem.find("trackcontainer")
        if bb_container is not None:
            for inst_track_elem in bb_container.findall("track"):
                bb_instrument = parse_bb_instrument(inst_track_elem)
                if bb_instrument:
                    bb_track.add_instrument(bb_instrument)

        return bb_track

    elif track_type == 2:
        # Sample track
        sample_path = ""
        volume = 1.0
        pan = 0.0
        sampletrack_elem = elem.find("sampletrack")
        if sampletrack_elem is not None:
            sample_path = sampletrack_elem.get("src", "")
            volume = float(sampletrack_elem.get("vol", 100)) / 100.0
            pan = float(sampletrack_elem.get("pan", 0)) / 100.0

        track = SampleTrack(
            name=name,
            sample_path=sample_path,
            volume=volume,
            pan=pan,
            muted=muted,
            solo=solo,
        )

        # Parse patterns for sample track
        for pattern_elem in elem.findall("pattern"):
            pattern = parse_pattern(pattern_elem)
            track.patterns.append(pattern)

        return track

    elif track_type == 5 or track_type == 6:
        # Automation track (type 5 = hidden, type 6 = visible)
        auto_track = AutomationTrack(
            name=name,
            muted=muted,
            solo=solo,
        )

        # Parse automation patterns/clips
        for pattern_elem in elem.findall("automationpattern"):
            clip = parse_automation_clip(pattern_elem)
            auto_track.add_clip(clip)

        return auto_track

    # Unknown track types are skipped
    return None


def parse_automation_clip(elem: etree._Element) -> AutomationClip:
    """Parse an automation clip/pattern element."""
    name = elem.get("name", "Automation")
    pos = int(elem.get("pos", 0))
    length = int(elem.get("len", 192))
    progression = int(elem.get("prog", 0))
    tension = float(elem.get("tens", 1.0))
    muted = elem.get("mute", "0") == "1"

    clip = AutomationClip(
        name=name,
        position=pos // TICKS_PER_BAR,
        length=max(1, length // TICKS_PER_BAR),
        progression=progression,
        tension=tension,
        muted=muted,
    )

    # Parse automation points
    for time_elem in elem.findall("time"):
        time_pos = int(time_elem.get("pos", 0))
        value = float(time_elem.get("value", 0))
        out_value_str = time_elem.get("outValue")
        out_value = float(out_value_str) if out_value_str else None
        in_tan = float(time_elem.get("inTan", 0))
        out_tan = float(time_elem.get("outTan", 0))

        point = AutomationPoint(
            time=time_pos / TICKS_PER_BEAT,
            value=value,
            out_value=out_value,
            in_tan=in_tan,
            out_tan=out_tan,
        )
        clip.points.append(point)

    return clip


def parse_sf2player(elem: etree._Element) -> dict:
    """Parse sf2player instrument settings.

    Returns dict of SF2InstrumentTrack kwargs.
    """
    return {
        "sf2_path": elem.get("src", ""),
        "bank": int(elem.get("bank", 0)),
        "patch": int(elem.get("patch", 0)),
        "gain": float(elem.get("gain", 1.0)),
        # Reverb
        "reverb_on": elem.get("reverbOn", "0") == "1",
        "reverb_room_size": float(elem.get("reverbRoomSize", 0.2)),
        "reverb_damping": float(elem.get("reverbDamping", 0.0)),
        "reverb_width": float(elem.get("reverbWidth", 0.5)),
        "reverb_level": float(elem.get("reverbLevel", 0.9)),
        # Chorus
        "chorus_on": elem.get("chorusOn", "0") == "1",
        "chorus_num": int(float(elem.get("chorusNum", 3))),
        "chorus_level": float(elem.get("chorusLevel", 2.0)),
        "chorus_speed": float(elem.get("chorusSpeed", 0.3)),
        "chorus_depth": float(elem.get("chorusDepth", 8.0)),
    }


def parse_bb_instrument(elem: etree._Element) -> BBInstrument | None:
    """Parse a BB instrument (drum row) from a track element inside bbtrack."""
    name = elem.get("name", "Drum")
    muted = elem.get("muted", "0") == "1"

    # Get instrument details
    instrument_elem = elem.find("instrumenttrack")
    instrument = "tripleoscillator"
    sample_path = None
    volume = 1.0
    pan = 0.0

    if instrument_elem is not None:
        volume = float(instrument_elem.get("vol", 100)) / 100.0
        pan = float(instrument_elem.get("pan", 0)) / 100.0

        # Get instrument plugin name and sample path
        for child in instrument_elem:
            if child.tag == "instrument":
                for inst_child in child:
                    instrument = inst_child.tag
                    if instrument == "audiofileprocessor":
                        sample_path = inst_child.get("src")
                    break

    bb_inst = BBInstrument(
        name=name,
        instrument=instrument,
        sample_path=sample_path,
        volume=volume,
        pan=pan,
        muted=muted,
    )

    # Parse pattern to get steps
    pattern_elem = elem.find("pattern")
    if pattern_elem is not None:
        num_steps = int(pattern_elem.get("steps", 16))
        bb_inst.num_steps = num_steps

        # Each note in the pattern represents an active step
        ticks_per_step = TICKS_PER_BAR // num_steps
        for note_elem in pattern_elem.findall("note"):
            pos = int(note_elem.get("pos", 0))
            vol = int(note_elem.get("vol", 100))
            step_num = pos // ticks_per_step if ticks_per_step > 0 else 0
            bb_inst.steps.append(BBStep(step=step_num, enabled=True, velocity=min(vol, 127)))

    return bb_inst


def parse_pattern(elem: etree._Element) -> Pattern:
    """Parse a pattern element."""
    name = elem.get("name", "Pattern")
    pos = int(elem.get("pos", 0))
    pattern_len = int(elem.get("len", 192))
    pattern_type = int(elem.get("type", 1))  # 0=BeatClip, 1=MelodyClip

    # LMMS uses 192 ticks per bar (in 4/4 time), so 48 ticks per beat
    ticks_per_bar = 192
    position_bars = pos // ticks_per_bar
    length_bars = max(1, pattern_len // ticks_per_bar)

    pattern = Pattern(
        name=name,
        position=position_bars,
        length=length_bars,
    )

    # Parse notes
    for note_elem in elem.findall("note"):
        note = parse_note(note_elem)
        pattern.notes.append(note)

    return pattern


def parse_note(elem: etree._Element) -> Note:
    """Parse a note element."""
    pos = int(elem.get("pos", 0))
    length = int(elem.get("len", 48))  # Default to 1 beat
    key = int(elem.get("key", 60))
    vol = int(elem.get("vol", 100))
    pan = int(elem.get("pan", 0))

    # Handle negative length (means full pattern length)
    if length < 0:
        length = TICKS_PER_BAR  # Default to 1 bar

    return Note(
        pitch=key,
        start=pos / TICKS_PER_BEAT,  # Position in beats
        length=length / TICKS_PER_BEAT,  # Length in beats
        velocity=min(vol, 127),  # LMMS uses 0-200, clamp to MIDI range
        pan=pan / 100.0,
    )
