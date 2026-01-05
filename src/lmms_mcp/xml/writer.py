"""Write LMMS .mmp project files."""

import zlib
from pathlib import Path

from lxml import etree

from lmms_mcp.models.project import Project
from lmms_mcp.models.track import (
    Track, InstrumentTrack, SampleTrack, BBTrack, BBInstrument,
    AutomationTrack, AutomationClip
)
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.models.note import Note


LMMS_VERSION = "1.2.2"

# LMMS uses 192 ticks per bar in 4/4 time
TICKS_PER_BAR = 192
TICKS_PER_BEAT = 48  # 192 / 4 beats per bar


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

    # FX Mixer with master channel
    fxmixer = etree.SubElement(song, "fxmixer")
    fxmixer.set("width", "600")
    fxmixer.set("height", "200")
    master_channel = etree.SubElement(fxmixer, "mixerchannel")
    master_channel.set("num", "0")
    master_channel.set("name", "Master")
    master_channel.set("volume", "1")
    master_channel.set("muted", "0")

    # Controller rack (empty)
    controller_rack = etree.SubElement(song, "ControllerRackView")
    controller_rack.set("width", "350")
    controller_rack.set("height", "200")

    # Piano roll (empty)
    pianoroll = etree.SubElement(song, "pianoroll")
    pianoroll.set("width", "600")
    pianoroll.set("height", "480")

    # Automation editor
    automationeditor = etree.SubElement(song, "automationeditor")
    automationeditor.set("width", "600")
    automationeditor.set("height", "400")

    # Project notes
    projectnotes = etree.SubElement(song, "projectnotes")

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
        inst_track.set("pitchrange", "1")
        inst_track.set("fxch", "0")
        inst_track.set("basenote", "57")  # A3
        inst_track.set("usemasterpitch", "1")
        inst_track.set("firstkey", "0")
        inst_track.set("lastkey", "127")

        # Instrument element with plugin
        instrument = etree.SubElement(inst_track, "instrument")
        instrument.set("name", track.instrument)
        inst_plugin = create_instrument_xml(track.instrument)
        instrument.append(inst_plugin)

        # Envelope/LFO data (basic defaults)
        eldata = etree.SubElement(inst_track, "eldata")
        eldata.set("ftype", "0")
        eldata.set("fcut", "14000")
        eldata.set("fres", "0.5")
        eldata.set("fwet", "0")

        # Effects chain (empty)
        fxchain = etree.SubElement(inst_track, "fxchain")
        fxchain.set("enabled", "0")
        fxchain.set("numofeffects", "0")

        # MIDI port
        midiport = etree.SubElement(inst_track, "midiport")
        midiport.set("readable", "0")
        midiport.set("writable", "0")
        midiport.set("inputchannel", "0")
        midiport.set("outputchannel", "1")
        midiport.set("basevelocity", "127")
        midiport.set("fixedinputvelocity", "-1")
        midiport.set("fixedoutputvelocity", "-1")
        midiport.set("fixedoutputnote", "-1")

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

    elif isinstance(track, BBTrack):
        elem.set("type", "1")  # BB Track type

        bbtrack_elem = etree.SubElement(elem, "bbtrack")

        # BB track container
        bb_trackcontainer = etree.SubElement(bbtrack_elem, "trackcontainer")
        bb_trackcontainer.set("type", "bbtrackcontainer")
        bb_trackcontainer.set("width", "580")
        bb_trackcontainer.set("height", "300")
        bb_trackcontainer.set("x", "610")
        bb_trackcontainer.set("y", "5")
        bb_trackcontainer.set("maximized", "0")
        bb_trackcontainer.set("minimized", "0")
        bb_trackcontainer.set("visible", "1")

        # Add each BB instrument as a track within the BB container
        for bb_inst in track.instruments:
            inst_elem = create_bb_instrument_xml(bb_inst, track.num_steps)
            bb_trackcontainer.append(inst_elem)

        # BB Track Content Object (places BB in song timeline)
        bbtco = etree.SubElement(elem, "bbtco")
        bbtco.set("name", track.name)
        bbtco.set("muted", "1" if track.muted else "0")
        bbtco.set("pos", str(track.bb_position * TICKS_PER_BAR))
        bbtco.set("len", str(track.bb_length * TICKS_PER_BAR))
        bbtco.set("usestyle", "1")
        bbtco.set("color", "4282417407")

    elif isinstance(track, AutomationTrack):
        elem.set("type", "6")  # Automation track type (visible)

        # Automation track element (usually empty)
        automationtrack = etree.SubElement(elem, "automationtrack")

        # Add automation clips/patterns
        for clip in track.clips:
            clip_elem = create_automation_clip_xml(clip)
            elem.append(clip_elem)

    return elem


def create_automation_clip_xml(clip: AutomationClip) -> etree._Element:
    """Create XML element for an automation clip."""
    elem = etree.Element("automationpattern")
    elem.set("name", clip.name)
    elem.set("pos", str(clip.position * TICKS_PER_BAR))
    elem.set("len", str(clip.length * TICKS_PER_BAR))
    elem.set("prog", str(clip.progression))
    elem.set("tens", str(clip.tension))
    elem.set("mute", "1" if clip.muted else "0")

    # Add automation points
    for point in clip.points:
        time_elem = etree.SubElement(elem, "time")
        time_elem.set("pos", str(int(point.time * TICKS_PER_BEAT)))
        time_elem.set("value", str(point.value))
        if point.out_value is not None:
            time_elem.set("outValue", str(point.out_value))
        time_elem.set("inTan", str(point.in_tan))
        time_elem.set("outTan", str(point.out_tan))

    return elem


def create_instrument_xml(instrument_name: str) -> etree._Element:
    """Create XML element for an instrument plugin with default settings."""
    if instrument_name == "tripleoscillator":
        return create_tripleoscillator_xml()
    elif instrument_name == "audiofileprocessor":
        return create_audiofileprocessor_xml()
    else:
        # Generic empty element for unknown instruments
        return etree.Element(instrument_name)


def create_tripleoscillator_xml() -> etree._Element:
    """Create TripleOscillator with default settings."""
    elem = etree.Element("tripleoscillator")

    # Oscillator volumes (default: equal mix of 3 oscillators)
    elem.set("vol0", "33")
    elem.set("vol1", "33")
    elem.set("vol2", "33")

    # Panning (centered)
    elem.set("pan0", "0")
    elem.set("pan1", "0")
    elem.set("pan2", "0")

    # Coarse detuning (semitones) - slight octave spread
    elem.set("coarse0", "0")
    elem.set("coarse1", "0")
    elem.set("coarse2", "-12")  # One octave down

    # Fine detuning (cents)
    elem.set("finel0", "0")
    elem.set("finer0", "0")
    elem.set("finel1", "-4")  # Slight detune for thickness
    elem.set("finer1", "4")
    elem.set("finel2", "0")
    elem.set("finer2", "0")

    # Phase offset
    elem.set("phoffset0", "0")
    elem.set("phoffset1", "0")
    elem.set("phoffset2", "0")

    # Stereo phase detuning
    elem.set("stphdetun0", "0")
    elem.set("stphdetun1", "0")
    elem.set("stphdetun2", "0")

    # Wave types: 0=Sine, 1=Triangle, 2=Sawtooth, 3=Square, 4=User
    elem.set("wavetype0", "2")  # Sawtooth
    elem.set("wavetype1", "2")  # Sawtooth
    elem.set("wavetype2", "0")  # Sine for sub

    # Modulation algorithms: 0=Mix, 1=AM, 2=FM, 3=PM, 4=Sync
    elem.set("modalgo1", "0")  # Mix
    elem.set("modalgo2", "0")  # Mix

    # Wave table mode
    elem.set("useWaveTable0", "1")
    elem.set("useWaveTable1", "1")
    elem.set("useWaveTable2", "1")

    # User wave files (empty)
    elem.set("userwavefile0", "")
    elem.set("userwavefile1", "")
    elem.set("userwavefile2", "")

    return elem


def create_audiofileprocessor_xml(src: str = "") -> etree._Element:
    """Create AudioFileProcessor with default settings."""
    elem = etree.Element("audiofileprocessor")
    elem.set("src", src)
    elem.set("amp", "100")
    elem.set("sframe", "0")
    elem.set("lframe", "0")
    elem.set("eframe", "1")
    elem.set("looped", "0")
    elem.set("reversed", "0")
    elem.set("interp", "1")
    elem.set("stutter", "0")
    return elem


def create_pattern_xml(pattern: Pattern) -> etree._Element:
    """Create XML element for a pattern."""
    elem = etree.Element("pattern")
    elem.set("name", pattern.name)
    elem.set("type", "1")  # 1 = MelodyClip (melodic pattern)
    elem.set("muted", "0")

    # Position in ticks (192 ticks per bar)
    pos_ticks = pattern.position * TICKS_PER_BAR
    elem.set("pos", str(pos_ticks))

    # Length in ticks
    len_ticks = pattern.length * TICKS_PER_BAR
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
    # Position and length in ticks (48 ticks per beat)
    elem.set("pos", str(int(note.start * TICKS_PER_BEAT)))
    elem.set("len", str(int(note.length * TICKS_PER_BEAT)))
    # Volume: LMMS uses 0-200, we store 0-127
    elem.set("vol", str(note.velocity))
    elem.set("pan", str(int(note.pan * 100)))
    return elem


def create_bb_instrument_xml(bb_inst: BBInstrument, num_steps: int) -> etree._Element:
    """Create XML element for a BB instrument (drum row).

    Args:
        bb_inst: BB instrument to create XML for
        num_steps: Number of steps in the pattern
    """
    elem = etree.Element("track")
    elem.set("type", "0")  # Instrument track type
    elem.set("name", bb_inst.name)
    elem.set("muted", "1" if bb_inst.muted else "0")
    elem.set("solo", "0")

    # Instrument track settings
    inst_track = etree.SubElement(elem, "instrumenttrack")
    inst_track.set("vol", str(int(bb_inst.volume * 100)))
    inst_track.set("pan", str(int(bb_inst.pan * 100)))
    inst_track.set("pitch", "0")
    inst_track.set("pitchrange", "1")
    inst_track.set("mixch", "0")
    inst_track.set("basenote", "57")
    inst_track.set("usemasterpitch", "1")

    # Instrument element with plugin
    instrument = etree.SubElement(inst_track, "instrument")
    instrument.set("name", bb_inst.instrument)

    if bb_inst.instrument == "audiofileprocessor":
        afp = create_audiofileprocessor_xml(bb_inst.sample_path or "")
        instrument.append(afp)
    elif bb_inst.instrument == "tripleoscillator":
        tri = create_tripleoscillator_xml()
        instrument.append(tri)
    else:
        inst_elem = etree.Element(bb_inst.instrument)
        instrument.append(inst_elem)

    # Envelope/LFO data
    eldata = etree.SubElement(inst_track, "eldata")
    eldata.set("ftype", "0")
    eldata.set("fcut", "14000")
    eldata.set("fres", "0.5")
    eldata.set("fwet", "0")

    # Chord creator (disabled)
    chordcreator = etree.SubElement(inst_track, "chordcreator")
    chordcreator.set("chord-enabled", "0")
    chordcreator.set("chord", "0")
    chordcreator.set("chordrange", "1")

    # Arpeggiator (disabled)
    arpeggiator = etree.SubElement(inst_track, "arpeggiator")
    arpeggiator.set("arp-enabled", "0")
    arpeggiator.set("arp", "0")
    arpeggiator.set("arpdir", "0")
    arpeggiator.set("arprange", "1")
    arpeggiator.set("arpgate", "100")

    # MIDI port
    midiport = etree.SubElement(inst_track, "midiport")
    midiport.set("readable", "0")
    midiport.set("writable", "0")
    midiport.set("inputchannel", "0")
    midiport.set("outputchannel", "1")
    midiport.set("basevelocity", "127")

    # FX chain
    fxchain = etree.SubElement(inst_track, "fxchain")
    fxchain.set("enabled", "0")
    fxchain.set("numofeffects", "0")

    # Pattern with steps
    pattern = etree.SubElement(elem, "pattern")
    pattern.set("type", "0")  # Step-based pattern
    pattern.set("name", bb_inst.name)
    pattern.set("muted", "0")
    pattern.set("pos", "0")
    pattern.set("steps", str(num_steps))
    pattern.set("len", str(TICKS_PER_BAR))  # 1 bar = 192 ticks

    # Add notes for each active step
    # In step sequencer, each step is evenly spaced
    ticks_per_step = TICKS_PER_BAR // num_steps
    for step in bb_inst.steps:
        if step.enabled:
            note_elem = etree.SubElement(pattern, "note")
            note_elem.set("key", "57")  # A3 (base note for drums)
            note_elem.set("pos", str(step.step * ticks_per_step))
            note_elem.set("len", str(ticks_per_step))
            note_elem.set("vol", str(step.velocity))
            note_elem.set("pan", "0")

    return elem
