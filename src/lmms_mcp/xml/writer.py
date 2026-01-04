"""Write LMMS .mmp project files."""

import zlib
from pathlib import Path

from lxml import etree

from lmms_mcp.models.project import Project
from lmms_mcp.models.track import Track, InstrumentTrack, SampleTrack
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.models.note import Note


LMMS_VERSION = "1.2.2"
TICKS_PER_BEAT = 192


def write_project(project: Project, path: Path) -> None:
    """Write a project to an LMMS .mmp file.

    Args:
        project: Project to write
        path: Output path (.mmp format)
    """
    # If we have raw XML from parsing, update it in place
    if project._raw_xml is not None:
        root = update_xml(project)
    else:
        root = create_xml(project)

    # Write XML
    xml_bytes = etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )

    # Compress if .mmpz
    if path.suffix.lower() == ".mmpz":
        compressed = zlib.compress(xml_bytes)
        # Add 4-byte big-endian size header (qCompress format)
        size_header = len(xml_bytes).to_bytes(4, byteorder="big")
        path.write_bytes(size_header + compressed)
    else:
        path.write_bytes(xml_bytes)


def create_xml(project: Project) -> etree._Element:
    """Create XML tree from scratch."""
    root = etree.Element("lmms-project")
    root.set("version", "1.0")
    root.set("creator", "LMMS")
    root.set("creatorversion", LMMS_VERSION)
    root.set("type", "song")

    # Head
    head = etree.SubElement(root, "head")
    head.set("bpm", str(project.bpm))
    head.set("timesig_numerator", str(project.time_sig_num))
    head.set("timesig_denominator", str(project.time_sig_den))
    head.set("mastervol", str(int(project.master_volume * 100)))
    head.set("masterpitch", str(project.master_pitch))

    # Song
    song = etree.SubElement(root, "song")

    # Track container
    trackcontainer = etree.SubElement(song, "trackcontainer")
    trackcontainer.set("type", "song")
    trackcontainer.set("width", "600")
    trackcontainer.set("x", "0")
    trackcontainer.set("y", "0")
    trackcontainer.set("maximized", "0")
    trackcontainer.set("visible", "1")

    # Write tracks
    for track in project.tracks:
        track_elem = create_track_xml(track)
        trackcontainer.append(track_elem)

    # FX Mixer (empty default)
    fxmixer = etree.SubElement(song, "fxmixer")
    fxmixer.set("width", "600")
    fxmixer.set("height", "200")

    # Controller rack (empty)
    controller_rack = etree.SubElement(song, "ControllerRackView")
    controller_rack.set("width", "350")
    controller_rack.set("height", "200")

    # Piano roll (empty)
    pianoroll = etree.SubElement(song, "pianoroll")
    pianoroll.set("width", "600")
    pianoroll.set("height", "480")

    return root


def update_xml(project: Project) -> etree._Element:
    """Update existing XML tree with project changes."""
    root = project._raw_xml

    # Update head
    head = root.find("head")
    if head is not None:
        head.set("bpm", str(project.bpm))
        head.set("timesig_numerator", str(project.time_sig_num))
        head.set("timesig_denominator", str(project.time_sig_den))
        head.set("mastervol", str(int(project.master_volume * 100)))
        head.set("masterpitch", str(project.master_pitch))

    # Update tracks
    song = root.find("song")
    if song is not None:
        trackcontainer = song.find("trackcontainer")
        if trackcontainer is not None:
            # Remove existing tracks
            for track_elem in trackcontainer.findall("track"):
                trackcontainer.remove(track_elem)

            # Add current tracks
            for track in project.tracks:
                track_elem = create_track_xml(track)
                trackcontainer.append(track_elem)

    return root


def create_track_xml(track: Track) -> etree._Element:
    """Create XML element for a track."""
    elem = etree.Element("track")
    elem.set("name", track.name)
    elem.set("muted", "1" if track.muted else "0")
    elem.set("solo", "1" if track.solo else "0")

    if isinstance(track, InstrumentTrack):
        elem.set("type", "0")

        # Instrument track settings
        inst_track = etree.SubElement(elem, "instrumenttrack")
        inst_track.set("vol", str(int(track.volume * 100)))
        inst_track.set("pan", str(int(track.pan * 100)))
        inst_track.set("pitch", "0")
        inst_track.set("fxch", "0")
        inst_track.set("basenote", "57")

        # Instrument element
        instrument = etree.SubElement(inst_track, "instrument")
        inst_plugin = etree.SubElement(instrument, track.instrument)
        # TODO: Add instrument-specific parameters

        # Patterns
        for pattern in track.patterns:
            pattern_elem = create_pattern_xml(pattern)
            elem.append(pattern_elem)

    elif isinstance(track, SampleTrack):
        elem.set("type", "2")

        sample_track = etree.SubElement(elem, "sampletrack")
        sample_track.set("vol", str(int(track.volume * 100)))
        sample_track.set("pan", str(int(track.pan * 100)))
        sample_track.set("src", track.sample_path)

    return elem


def create_pattern_xml(pattern: Pattern) -> etree._Element:
    """Create XML element for a pattern."""
    elem = etree.Element("pattern")
    elem.set("name", pattern.name)
    elem.set("type", "1")  # 1 = melody pattern
    elem.set("muted", "0")

    # Position in ticks (192 ticks per beat, 4 beats per bar)
    pos_ticks = pattern.position * 4 * TICKS_PER_BEAT
    elem.set("pos", str(pos_ticks))

    # Length in ticks
    len_ticks = pattern.length * 4 * TICKS_PER_BEAT
    elem.set("len", str(len_ticks))

    # Notes
    for note in pattern.notes:
        note_elem = create_note_xml(note)
        elem.append(note_elem)

    return elem


def create_note_xml(note: Note) -> etree._Element:
    """Create XML element for a note."""
    elem = etree.Element("note")
    elem.set("key", str(note.pitch))
    elem.set("pos", str(int(note.start * TICKS_PER_BEAT)))
    elem.set("len", str(int(note.length * TICKS_PER_BEAT)))
    elem.set("vol", str(note.velocity))
    elem.set("pan", str(int(note.pan * 100)))
    return elem
