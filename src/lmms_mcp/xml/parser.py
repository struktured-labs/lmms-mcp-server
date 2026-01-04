"""Parse LMMS .mmp/.mmpz project files."""

import zlib
from pathlib import Path

from lxml import etree

from lmms_mcp.models.project import Project
from lmms_mcp.models.track import InstrumentTrack, SampleTrack, Track
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.models.note import Note


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

        if instrument_elem is not None:
            volume = float(instrument_elem.get("vol", 100)) / 100.0
            pan = float(instrument_elem.get("pan", 0)) / 100.0  # LMMS uses -100 to 100

            # Get instrument plugin name
            for child in instrument_elem:
                if child.tag == "instrument":
                    inst_child = list(child)
                    if inst_child:
                        instrument = inst_child[0].tag

        track = InstrumentTrack(
            name=name,
            instrument=instrument,
            volume=volume,
            pan=pan,
            muted=muted,
            solo=solo,
        )

        # Parse patterns
        for pattern_elem in elem.findall("pattern"):
            pattern = parse_pattern(pattern_elem)
            track.patterns.append(pattern)

        return track

    elif track_type == 2:
        # Sample track
        sample_path = ""
        sampletrack_elem = elem.find("sampletrack")
        if sampletrack_elem is not None:
            sample_path = sampletrack_elem.get("src", "")

        track = SampleTrack(
            name=name,
            sample_path=sample_path,
            muted=muted,
            solo=solo,
        )
        return track

    # TODO: Handle other track types
    return None


def parse_pattern(elem: etree._Element) -> Pattern:
    """Parse a pattern element."""
    name = elem.get("name", "Pattern")
    pos = int(elem.get("pos", 0))
    # Convert position from ticks to bars (assuming 192 ticks per beat, 4 beats per bar)
    position_bars = pos // (192 * 4)

    pattern = Pattern(
        name=name,
        position=position_bars,
    )

    # Parse notes
    for note_elem in elem.findall("note"):
        note = parse_note(note_elem)
        pattern.notes.append(note)

    # Calculate pattern length from note positions
    if pattern.notes:
        max_end = max(n.start + n.length for n in pattern.notes)
        pattern.length = max(4, int(max_end / 4) + 1)  # At least 4 bars

    return pattern


def parse_note(elem: etree._Element) -> Note:
    """Parse a note element."""
    # LMMS stores position and length in ticks (192 ticks per beat)
    ticks_per_beat = 192.0

    pos = int(elem.get("pos", 0))
    length = int(elem.get("len", 192))
    key = int(elem.get("key", 60))
    vol = int(elem.get("vol", 100))
    pan = int(elem.get("pan", 0))

    return Note(
        pitch=key,
        start=pos / ticks_per_beat,
        length=length / ticks_per_beat,
        velocity=vol,
        pan=pan / 100.0,
    )
