"""
Ableton Live 12 Native MIDI Tool and Max for Live integration.

Generates native dictionaries for `live.miditool.out` and builds/installs
the `Midison Generator.amxd` MIDI Tool directly into Ableton Live 12's
`MIDI Tools/Max Generators` user library folder.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from midison.events import ResolvedProgression, TimedNote, resolve_progression_notes
from midison.midi_writer import GenerationRequest

logger = logging.getLogger("midison.miditool")


def to_miditool_dict(request: GenerationRequest) -> dict[str, Any]:
    """
    Convert a GenerationRequest into the dictionary structure expected
    by Ableton Live 12's `live.miditool.out`.
    """
    resolved = resolve_progression_notes(request)
    notes_payload = [
        {
            "pitch": int(n.pitch),
            "start_time": float(round(n.start_beat, 4)),
            "duration": float(round(n.duration_beats, 4)),
            "velocity": int(n.velocity),
            "mute": 0,
            "probability": 1.0,
        }
        for n in resolved.notes
    ]
    return {
        "notes": notes_payload,
        "metadata": {
            "key": request.key_center,
            "mode": request.scale_type,
            "total_beats": resolved.total_beats,
            "chords": [m["numeral"] for m in resolved.resolved_metadata],
        },
    }


def find_ableton_midi_tools_dir() -> Path:
    """Find the user library path for Ableton Live 12 MIDI Generators."""
    default_path = Path.home() / "Music/Ableton/User Library/MIDI Tools/Max Generators"
    default_path.mkdir(parents=True, exist_ok=True)
    return default_path


def create_amxd_container(patcher_json: dict[str, Any], device_type: str = "nagg") -> bytes:
    """
    Package a Max patcher dictionary into a valid Cycling '74 AMXD container file.
    device_type:
      'nagg': Live 12 MIDI Tool Generator
      'natt': Live 12 MIDI Tool Transformation
      'mmmm': MIDI Effect
    """
    json_str = json.dumps(patcher_json, indent="\t")
    json_bytes = json_str.encode("utf-8") + b"\x00"

    # Header:
    # ampf (4) + len(type) (4) + type (4) + meta (4) + len(meta) (4) + meta_val (4) + ptch (4) + len(ptch) (4)
    header = (
        b"ampf\x04\x00\x00\x00"
        + device_type.encode("ascii")
        + b"meta\x04\x00\x00\x00\x00\x00\x00\x00"
        + b"ptch"
        + len(json_bytes).to_bytes(4, "little")
    )
    return header + json_bytes


MIDISON_GENERATOR_JS = r"""autowatch = 1;
inlets = 1;
outlets = 1;

var PRESETS = [
    "ii7 - V7 - Imaj7",
    "Imaj7 - vi7 - ii7 - V7",
    "I - V - vi - IV",
    "i7 - iv7 - v7 - i7",
    "ii9 - V13 - Imaj9",
    "Imaj9 - IVmaj7",
    "i9 - IV9",
    "iiø7 - V7b9 - i",
    "I - bVII - IV - I",
    "Imaj7 - V7/vi - vi7 - ii7"
];

var VOICINGS = ["Close", "Drop 2", "Drop 3", "Drop 2&4", "Spread"];
var GROOVES = [
    "Block", "Charleston", "Bossa", "Strum", "Tresillo",
    "Waltz", "4 on Floor", "Arp Up", "Arp Down", "Comp Sync"
];

var currentProgression = PRESETS[0];
var currentVoicing = "Drop 2";
var currentGroove = "Block";
var currentOctave = 3;
var currentVoiceLead = 1;
var currentRootless = 0;
var currentHumanize = 0;

var currentRootPc = 0;
var currentScaleIntervals = [0, 2, 4, 5, 7, 9, 11];
var clipSelectionBeats = null;

var romanDegrees = {
    "i": 0, "ii": 1, "iii": 2, "iv": 3, "v": 4, "vi": 5, "vii": 6
};

function splitProgression(str) {
    if (!str) return ["I"];
    var cleaned = str.replace(/[–—]/g, "-").trim();
    var parts = cleaned.split(/\s*,\s*|\s+-\s+|\s+/);
    var tokens = [];
    for (var i = 0; i < parts.length; i++) {
        var t = parts[i].trim().replace(/^-+|-+$/g, "");
        if (t.length > 0) tokens.push(t);
    }
    return tokens.length > 0 ? tokens : ["I"];
}

function parseChordToken(tok, rootPc, scaleIntervals) {
    var raw = tok.trim();
    if (!raw) return null;
    var dur = 4.0;
    if (raw.indexOf(":") !== -1) {
        var parts = raw.split(":");
        raw = parts[0];
        dur = parseFloat(parts[1]) || 4.0;
    }

    var targetDeg = null;
    if (raw.indexOf("/") !== -1) {
        var slashParts = raw.split("/");
        raw = slashParts[0];
        var targetStr = slashParts[1].toLowerCase().replace(/[^a-z]/g, "");
        targetDeg = romanDegrees[targetStr];
    }

    var accidental = 0;
    if (raw.charAt(0) === "b" || raw.charAt(0) === "♭") {
        accidental = -1;
        raw = raw.substring(1);
    } else if (raw.charAt(0) === "#" || raw.charAt(0) === "♯") {
        accidental = 1;
        raw = raw.substring(1);
    }

    var match = raw.match(/^([ivIV]+)(.*)$/);
    if (!match) return null;
    var numeral = match[1];
    var suffix = match[2] || "";
    var isUpper = (numeral === numeral.toUpperCase());
    var baseDeg = romanDegrees[numeral.toLowerCase()] || 0;

    var chordRootPc;
    if (targetDeg !== undefined && targetDeg !== null) {
        var targetPc = (rootPc + scaleIntervals[targetDeg % scaleIntervals.length]) % 12;
        chordRootPc = (targetPc + 7) % 12;
    } else {
        var scaleDegInterval = scaleIntervals[baseDeg % scaleIntervals.length] || 0;
        chordRootPc = (rootPc + scaleDegInterval + accidental + 12) % 12;
    }

    var intervals;
    var s = suffix.toLowerCase();
    if (s.indexOf("maj9") !== -1) intervals = [0, 4, 7, 11, 14];
    else if (s.indexOf("maj13") !== -1) intervals = [0, 4, 7, 11, 14, 21];
    else if (s.indexOf("maj7") !== -1 || (s.indexOf("m7") === -1 && s.indexOf("maj") !== -1)) intervals = [0, 4, 7, 11];
    else if (s.indexOf("m7b5") !== -1 || s.indexOf("ø") !== -1) intervals = [0, 3, 6, 10];
    else if (s.indexOf("dim7") !== -1 || s.indexOf("°7") !== -1) intervals = [0, 3, 6, 9];
    else if (s.indexOf("dim") !== -1 || s.indexOf("°") !== -1) intervals = [0, 3, 6];
    else if (s.indexOf("m11") !== -1) intervals = [0, 3, 7, 10, 14, 17];
    else if (s.indexOf("m9") !== -1 || s.indexOf("min9") !== -1) intervals = [0, 3, 7, 10, 14];
    else if (s.indexOf("m7") !== -1 || s.indexOf("min7") !== -1) intervals = [0, 3, 7, 10];
    else if (s.indexOf("7b9") !== -1) intervals = [0, 4, 7, 10, 13];
    else if (s.indexOf("7#9") !== -1) intervals = [0, 4, 7, 10, 15];
    else if (s.indexOf("13") !== -1) intervals = [0, 4, 7, 10, 14, 21];
    else if (s.indexOf("9") !== -1) intervals = [0, 4, 7, 10, 14];
    else if (s.indexOf("7") !== -1) {
        intervals = isUpper ? [0, 4, 7, 10] : [0, 3, 7, 10];
    } else if (s.indexOf("sus4") !== -1) intervals = [0, 5, 7];
    else if (s.indexOf("sus2") !== -1) intervals = [0, 2, 7];
    else if (s.indexOf("aug") !== -1 || s.indexOf("+") !== -1) intervals = [0, 4, 8];
    else {
        intervals = isUpper ? [0, 4, 7] : [0, 3, 7];
    }

    return { rootPc: chordRootPc, intervals: intervals, duration: dur };
}

function applyVoicing(chordNotes, voicing) {
    var notes = chordNotes.slice();
    if (voicing === "Drop 2" && notes.length >= 4) {
        notes[notes.length - 2] -= 12;
        notes.sort(function(a, b) { return a - b; });
    } else if (voicing === "Drop 3" && notes.length >= 4) {
        notes[notes.length - 3] -= 12;
        notes.sort(function(a, b) { return a - b; });
    } else if (voicing === "Drop 2&4" && notes.length >= 4) {
        notes[notes.length - 2] -= 12;
        notes[notes.length - 4] -= 12;
        notes.sort(function(a, b) { return a - b; });
    } else if (voicing === "Spread") {
        var root = notes[0] - 12;
        var upper = notes.slice(1);
        notes = [root].concat(upper);
    }
    return notes;
}

function optimizeVoiceLeading(candidateChords, prevChordNotes) {
    if (!prevChordNotes || prevChordNotes.length === 0) return candidateChords;
    var bestChord = candidateChords;
    var minDisplacement = Infinity;

    var n = candidateChords.length;
    for (var inv = 0; inv < n; inv++) {
        var inverted = [];
        for (var i = 0; i < n; i++) {
            var idx = (i + inv) % n;
            var note = candidateChords[idx];
            if (idx < inv) note += 12;
            inverted.push(note);
        }
        inverted.sort(function(a, b) { return a - b; });

        for (var octShift = -12; octShift <= 12; octShift += 12) {
            var shifted = inverted.map(function(p) { return p + octShift; });
            var disp = 0;
            var len = Math.min(shifted.length, prevChordNotes.length);
            for (var k = 0; k < len; k++) {
                disp += Math.abs(shifted[k] - prevChordNotes[k]);
            }
            if (disp < minDisplacement) {
                minDisplacement = disp;
                bestChord = shifted;
            }
        }
    }
    return bestChord;
}

function renderGrooveNotes(chordNotes, startBeat, durationBeats, groove, humanize) {
    var outNotes = [];
    var velBase = 92;
    var dur = durationBeats;

    function addNote(pitch, time, durLen, vel) {
        var p = pitch;
        var t = time;
        var d = durLen;
        var v = vel;
        if (humanize) {
            v = Math.max(1, Math.min(127, Math.round(v + (Math.random() * 16 - 8))));
            t = Math.max(0, t + (Math.random() * 0.03 - 0.015));
        }
        outNotes.push({
            pitch: p,
            start_time: Math.round(t * 10000) / 10000,
            duration: Math.round(d * 10000) / 10000,
            velocity: v,
            mute: 0,
            probability: 1.0
        });
    }

    if (groove === "Charleston") {
        for (var b = 0; b < dur; b += 2.0) {
            for (var i = 0; i < chordNotes.length; i++) {
                addNote(chordNotes[i], startBeat + b + 0.0, 1.25, 96);
                if (b + 1.5 < dur) {
                    addNote(chordNotes[i], startBeat + b + 1.5, 0.45, 82);
                }
            }
        }
    } else if (groove === "Bossa") {
        for (var b = 0; b < dur; b += 4.0) {
            var hits = [
                { offset: 0.0, dur: 0.5, vel: 95 },
                { offset: 1.5, dur: 0.5, vel: 80 },
                { offset: 3.0, dur: 0.5, vel: 88 }
            ];
            for (var h = 0; h < hits.length; h++) {
                if (b + hits[h].offset < dur) {
                    for (var i = 0; i < chordNotes.length; i++) {
                        addNote(chordNotes[i], startBeat + b + hits[h].offset, hits[h].dur, hits[h].vel);
                    }
                }
            }
        }
    } else if (groove === "Strum") {
        for (var i = 0; i < chordNotes.length; i++) {
            var stagger = i * 0.025;
            addNote(chordNotes[i], startBeat + stagger, Math.max(0.5, dur - stagger), 90 + i * 2);
        }
    } else if (groove === "Tresillo") {
        for (var b = 0; b < dur; b += 4.0) {
            var hits = [
                { offset: 0.0, dur: 1.4, vel: 95 },
                { offset: 1.5, dur: 1.4, vel: 85 },
                { offset: 3.0, dur: 0.9, vel: 90 }
            ];
            for (var h = 0; h < hits.length; h++) {
                if (b + hits[h].offset < dur) {
                    for (var i = 0; i < chordNotes.length; i++) {
                        addNote(chordNotes[i], startBeat + b + hits[h].offset, hits[h].dur, hits[h].vel);
                    }
                }
            }
        }
    } else if (groove === "Waltz") {
        var bass = chordNotes[0];
        var upper = chordNotes.slice(1);
        addNote(bass, startBeat + 0.0, 0.9, 95);
        for (var k = 0; k < upper.length; k++) {
            addNote(upper[k], startBeat + 1.0, 0.8, 80);
            addNote(upper[k], startBeat + 2.0, 0.8, 80);
        }
    } else if (groove === "4 on Floor") {
        for (var b = 0; b < dur; b += 1.0) {
            for (var i = 0; i < chordNotes.length; i++) {
                addNote(chordNotes[i], startBeat + b, 0.75, b === 0 ? 98 : 85);
            }
        }
    } else if (groove === "Arp Up") {
        var step = 0.25;
        var noteIdx = 0;
        for (var t = 0; t < dur; t += step) {
            addNote(chordNotes[noteIdx % chordNotes.length], startBeat + t, step * 0.9, 90);
            noteIdx++;
        }
    } else if (groove === "Arp Down") {
        var step = 0.25;
        var noteIdx = chordNotes.length - 1;
        for (var t = 0; t < dur; t += step) {
            addNote(chordNotes[(noteIdx % chordNotes.length + chordNotes.length) % chordNotes.length], startBeat + t, step * 0.9, 90);
            noteIdx--;
        }
    } else if (groove === "Comp Sync") {
        var compHits = [0.5, 2.0, 3.5];
        for (var h = 0; h < compHits.length; h++) {
            if (compHits[h] < dur) {
                for (var i = 0; i < chordNotes.length; i++) {
                    addNote(chordNotes[i], startBeat + compHits[h], 0.45, 90);
                }
            }
        }
    } else {
        for (var i = 0; i < chordNotes.length; i++) {
            addNote(chordNotes[i], startBeat, dur, velBase);
        }
    }
    return outNotes;
}

function parseScaleAndSelectionFromDict(d) {
    if (!d) return;
    try {
        if (d.contains("scale::root_note")) {
            currentRootPc = parseInt(d.get("scale::root_note"), 10) || 0;
        }
        if (d.contains("scale::scale_intervals")) {
            var si = d.get("scale::scale_intervals");
            if (si && si.length) {
                currentScaleIntervals = [];
                for (var k = 0; k < si.length; k++) currentScaleIntervals.push(parseInt(si[k], 10));
            }
        }
    } catch (e1) {}

    try {
        if (d.contains("scale")) {
            var s = d.get("scale");
            if (s) {
                if (typeof s.get === "function") {
                    if (s.contains("root_note")) currentRootPc = parseInt(s.get("root_note"), 10) || 0;
                    if (s.contains("scale_intervals")) {
                        var si2 = s.get("scale_intervals");
                        if (si2 && si2.length) {
                            currentScaleIntervals = [];
                            for (var k2 = 0; k2 < si2.length; k2++) currentScaleIntervals.push(parseInt(si2[k2], 10));
                        }
                    }
                } else if (typeof s === "object") {
                    if (s.root_note !== undefined) currentRootPc = parseInt(s.root_note, 10) || 0;
                    if (s.scale_intervals && s.scale_intervals.length) {
                        currentScaleIntervals = [];
                        for (var k3 = 0; k3 < s.scale_intervals.length; k3++) currentScaleIntervals.push(parseInt(s.scale_intervals[k3], 10));
                    }
                }
            }
        }
    } catch (e2) {}

    try {
        if (d.contains("time_selection_start") && d.contains("time_selection_end")) {
            var dur1 = d.get("time_selection_end") - d.get("time_selection_start");
            if (dur1 > 0) clipSelectionBeats = dur1;
        }
    } catch (e3) {}

    try {
        if (d.contains("selection::start_time") && d.contains("selection::end_time")) {
            var dur2 = d.get("selection::end_time") - d.get("selection::start_time");
            if (dur2 > 0) clipSelectionBeats = dur2;
        }
    } catch (e4) {}
}

function generate() {
    var rootPc = currentRootPc;
    var scaleIntervals = currentScaleIntervals;

    var tokens = splitProgression(currentProgression);

    var parsedChords = [];
    var hasExplicitBeats = false;

    for (var i = 0; i < tokens.length; i++) {
        var c = parseChordToken(tokens[i], rootPc, scaleIntervals);
        if (c) {
            parsedChords.push(c);
            if (tokens[i].indexOf(":") !== -1) hasExplicitBeats = true;
        }
    }
    if (parsedChords.length === 0) return;

    var defaultBeatsPerChord = 4.0;
    if (!hasExplicitBeats) {
        if (clipSelectionBeats && clipSelectionBeats >= parsedChords.length * 2.0) {
            defaultBeatsPerChord = clipSelectionBeats / parsedChords.length;
        } else {
            defaultBeatsPerChord = 4.0;
        }
    }

    var allNotes = [];
    var beatOffset = 0.0;
    var prevChordNotes = null;
    var baseOctaveMidi = (currentOctave + 1) * 12;

    for (var cIdx = 0; cIdx < parsedChords.length; cIdx++) {
        var chord = parsedChords[cIdx];
        var chordDur = hasExplicitBeats ? chord.duration : defaultBeatsPerChord;

        var rawPitches = [];
        var chordRootMidi = baseOctaveMidi + chord.rootPc;
        for (var p = 0; p < chord.intervals.length; p++) {
            rawPitches.push(chordRootMidi + chord.intervals[p]);
        }
        rawPitches.sort(function(a, b) { return a - b; });

        var voicedPitches = applyVoicing(rawPitches, currentVoicing);

        if (currentRootless && voicedPitches.length > 2) {
            voicedPitches = voicedPitches.slice(1);
        }

        if (currentVoiceLead && prevChordNotes) {
            voicedPitches = optimizeVoiceLeading(voicedPitches, prevChordNotes);
        }
        prevChordNotes = voicedPitches.slice();

        var grooveNotes = renderGrooveNotes(voicedPitches, beatOffset, chordDur, currentGroove, currentHumanize);
        for (var gn = 0; gn < grooveNotes.length; gn++) {
            allNotes.push(grooveNotes[gn]);
        }

        beatOffset += chordDur;
    }

    try {
        var outDict = new Dict();
        outDict.parse(JSON.stringify({ notes: allNotes }));
        outlet(0, "dictionary", outDict.name);
    } catch (err) {}
}

function dictionary(dictName) {
    try {
        var d = new Dict(dictName);
        parseScaleAndSelectionFromDict(d);
    } catch (e) {}
    generate();
}

function preset_idx(idx) {
    var i = parseInt(idx, 10);
    if (!isNaN(i) && i >= 0 && i < PRESETS.length) {
        currentProgression = PRESETS[i];
    }
    generate();
}

function preset(val) {
    if (typeof val === "number") {
        preset_idx(val);
        return;
    }
    var i = parseInt(val, 10);
    if (!isNaN(i) && i >= 0 && i < PRESETS.length && ("" + i) === ("" + val).trim()) {
        preset_idx(i);
        return;
    }
    if (arguments.length > 1) {
        var parts = [];
        for (var k = 0; k < arguments.length; k++) parts.push(arguments[k]);
        currentProgression = parts.join(" ");
    } else {
        currentProgression = "" + val;
    }
    generate();
}

function voicing_idx(idx) {
    var i = parseInt(idx, 10);
    if (!isNaN(i) && i >= 0 && i < VOICINGS.length) {
        currentVoicing = VOICINGS[i];
    }
    generate();
}

function voicing(val) {
    if (typeof val === "number" || (!isNaN(parseInt(val, 10)) && ("" + parseInt(val, 10)) === ("" + val).trim())) {
        voicing_idx(val);
        return;
    }
    if (arguments.length > 1) {
        var parts = [];
        for (var k = 0; k < arguments.length; k++) parts.push(arguments[k]);
        currentVoicing = parts.join(" ");
    } else {
        currentVoicing = "" + val;
    }
    generate();
}

function groove_idx(idx) {
    var i = parseInt(idx, 10);
    if (!isNaN(i) && i >= 0 && i < GROOVES.length) {
        currentGroove = GROOVES[i];
    }
    generate();
}

function groove(val) {
    if (typeof val === "number" || (!isNaN(parseInt(val, 10)) && ("" + parseInt(val, 10)) === ("" + val).trim())) {
        groove_idx(val);
        return;
    }
    if (arguments.length > 1) {
        var parts = [];
        for (var k = 0; k < arguments.length; k++) parts.push(arguments[k]);
        currentGroove = parts.join(" ");
    } else {
        currentGroove = "" + val;
    }
    generate();
}

function octave(val) {
    currentOctave = parseInt(val, 10) || 3;
    generate();
}

function voice_lead(val) {
    currentVoiceLead = parseInt(val, 10) ? 1 : 0;
    generate();
}

function rootless(val) {
    currentRootless = parseInt(val, 10) ? 1 : 0;
    generate();
}

function humanize(val) {
    currentHumanize = parseInt(val, 10) ? 1 : 0;
    generate();
}

function bang() {
    generate();
}
"""


def get_midison_generator_patcher() -> dict[str, Any]:
    """
    Generate the Max Patcher JSON definition for Midison Generator (Live 12 MIDI Tool).
    Configured with native Live 12 UI widgets in presentation mode (width: 152px, height: 144px).
    """
    presets = [
        "ii7 - V7 - Imaj7",
        "Imaj7 - vi7 - ii7 - V7",
        "I - V - vi - IV",
        "i7 - iv7 - v7 - i7",
        "ii9 - V13 - Imaj9",
        "Imaj9 - IVmaj7",
        "i9 - IV9",
        "iiø7 - V7b9 - i",
        "I - bVII - IV - I",
        "Imaj7 - V7/vi - vi7 - ii7",
    ]
    voicings = ["Close", "Drop 2", "Drop 3", "Drop 2&4", "Spread"]
    grooves = [
        "Block",
        "Charleston",
        "Bossa",
        "Strum",
        "Tresillo",
        "Waltz",
        "4 on Floor",
        "Arp Up",
        "Arp Down",
        "Comp Sync",
    ]

    boxes: list[dict[str, Any]] = [
        # Native Live 12 MIDI Tool I/O
        {
            "box": {
                "id": "obj-in",
                "maxclass": "newobj",
                "text": "live.miditool.in",
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", ""],
                "patching_rect": [30.0, 30.0, 95.0, 22.0],
            }
        },
        {
            "box": {
                "id": "obj-out",
                "maxclass": "newobj",
                "text": "live.miditool.out",
                "numinlets": 1,
                "numoutlets": 0,
                "patching_rect": [30.0, 520.0, 100.0, 22.0],
            }
        },
        # JavaScript Engine Object
        {
            "box": {
                "id": "obj-js",
                "maxclass": "newobj",
                "text": "js midison_generator.js",
                "numinlets": 1,
                "numoutlets": 1,
                "outlettype": [""],
                "patching_rect": [30.0, 460.0, 135.0, 22.0],
                "saved_object_attributes": {
                    "code": MIDISON_GENERATOR_JS,
                },
            }
        },
        # Trigger bang into live.miditool.in on UI parameter changes
        {
            "box": {
                "id": "obj-trigger-in",
                "maxclass": "newobj",
                "text": "t b",
                "numinlets": 1,
                "numoutlets": 1,
                "outlettype": ["bang"],
                "patching_rect": [150.0, 30.0, 25.0, 22.0],
            }
        },
        # Presentation Header (compact, fits 144px total height)
        {
            "box": {
                "id": "obj-title",
                "maxclass": "live.comment",
                "text": "MIDISON",
                "fontface": 1,
                "fontsize": 11.0,
                "presentation": 1,
                "presentation_rect": [6.0, 3.0, 68.0, 15.0],
                "patching_rect": [250.0, 30.0, 120.0, 20.0],
            }
        },
        {
            "box": {
                "id": "obj-sub",
                "maxclass": "live.comment",
                "text": "Chords & Grooves",
                "fontsize": 8.5,
                "presentation": 1,
                "presentation_rect": [78.0, 4.0, 68.0, 13.0],
                "patching_rect": [250.0, 55.0, 135.0, 18.0],
            }
        },
        {
            "box": {
                "id": "obj-line1",
                "maxclass": "live.line",
                "presentation": 1,
                "presentation_rect": [6.0, 19.0, 140.0, 2.0],
                "patching_rect": [250.0, 80.0, 136.0, 5.0],
            }
        },
        # Preset Selector
        {
            "box": {
                "id": "obj-lbl-preset",
                "maxclass": "live.comment",
                "text": "Progression",
                "fontsize": 9.0,
                "presentation": 1,
                "presentation_rect": [6.0, 22.0, 140.0, 12.0],
                "patching_rect": [250.0, 95.0, 120.0, 18.0],
            }
        },
        {
            "box": {
                "id": "obj-menu-preset",
                "maxclass": "live.menu",
                "varname": "Preset",
                "parameter_enable": 1,
                "numinlets": 1,
                "numoutlets": 3,
                "outlettype": ["", "", "float"],
                "presentation": 1,
                "presentation_rect": [6.0, 35.0, 140.0, 15.0],
                "patching_rect": [250.0, 115.0, 136.0, 16.0],
                "saved_attribute_attributes": {
                    "valueof": {
                        "parameter_type": 2,
                        "parameter_longname": "Preset",
                        "parameter_shortname": "Preset",
                        "parameter_enum": presets,
                        "parameter_initial_enable": 1,
                        "parameter_initial": [0],
                    }
                },
            }
        },
        # Voicing & Groove Row
        {
            "box": {
                "id": "obj-lbl-voicing",
                "maxclass": "live.comment",
                "text": "Voicing",
                "fontsize": 9.0,
                "presentation": 1,
                "presentation_rect": [6.0, 52.0, 68.0, 12.0],
                "patching_rect": [250.0, 145.0, 60.0, 18.0],
            }
        },
        {
            "box": {
                "id": "obj-lbl-groove",
                "maxclass": "live.comment",
                "text": "Groove",
                "fontsize": 9.0,
                "presentation": 1,
                "presentation_rect": [78.0, 52.0, 68.0, 12.0],
                "patching_rect": [325.0, 145.0, 60.0, 18.0],
            }
        },
        {
            "box": {
                "id": "obj-menu-voicing",
                "maxclass": "live.menu",
                "varname": "Voicing",
                "parameter_enable": 1,
                "numinlets": 1,
                "numoutlets": 3,
                "outlettype": ["", "", "float"],
                "presentation": 1,
                "presentation_rect": [6.0, 65.0, 68.0, 15.0],
                "patching_rect": [250.0, 165.0, 64.0, 16.0],
                "saved_attribute_attributes": {
                    "valueof": {
                        "parameter_type": 2,
                        "parameter_longname": "Voicing",
                        "parameter_shortname": "Voicing",
                        "parameter_enum": voicings,
                        "parameter_initial_enable": 1,
                        "parameter_initial": [1],  # Drop 2
                    }
                },
            }
        },
        {
            "box": {
                "id": "obj-menu-groove",
                "maxclass": "live.menu",
                "varname": "Groove",
                "parameter_enable": 1,
                "numinlets": 1,
                "numoutlets": 3,
                "outlettype": ["", "", "float"],
                "presentation": 1,
                "presentation_rect": [78.0, 65.0, 68.0, 15.0],
                "patching_rect": [325.0, 165.0, 66.0, 16.0],
                "saved_attribute_attributes": {
                    "valueof": {
                        "parameter_type": 2,
                        "parameter_longname": "Groove",
                        "parameter_shortname": "Groove",
                        "parameter_enum": grooves,
                        "parameter_initial_enable": 1,
                        "parameter_initial": [0],  # Block
                    }
                },
            }
        },
        # Octave & Humanize Row
        {
            "box": {
                "id": "obj-lbl-oct",
                "maxclass": "live.comment",
                "text": "Octave",
                "fontsize": 9.0,
                "presentation": 1,
                "presentation_rect": [6.0, 82.0, 68.0, 12.0],
                "patching_rect": [250.0, 195.0, 60.0, 18.0],
            }
        },
        {
            "box": {
                "id": "obj-lbl-human",
                "maxclass": "live.comment",
                "text": "Humanize",
                "fontsize": 9.0,
                "presentation": 1,
                "presentation_rect": [78.0, 82.0, 68.0, 12.0],
                "patching_rect": [325.0, 195.0, 60.0, 18.0],
            }
        },
        {
            "box": {
                "id": "obj-num-oct",
                "maxclass": "live.numbox",
                "varname": "Octave",
                "parameter_enable": 1,
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", "float"],
                "presentation": 1,
                "presentation_rect": [6.0, 95.0, 68.0, 15.0],
                "patching_rect": [250.0, 215.0, 64.0, 16.0],
                "saved_attribute_attributes": {
                    "valueof": {
                        "parameter_type": 1,
                        "parameter_longname": "Octave",
                        "parameter_shortname": "Octave",
                        "parameter_unitstyle": 0,
                        "parameter_mmin": 1.0,
                        "parameter_mmax": 6.0,
                        "parameter_initial_enable": 1,
                        "parameter_initial": [3.0],
                    }
                },
            }
        },
        {
            "box": {
                "id": "obj-btn-human",
                "maxclass": "live.text",
                "varname": "Humanize",
                "parameter_enable": 1,
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", ""],
                "text": "Off",
                "texton": "On",
                "presentation": 1,
                "presentation_rect": [78.0, 95.0, 68.0, 15.0],
                "patching_rect": [325.0, 215.0, 66.0, 16.0],
                "saved_attribute_attributes": {
                    "valueof": {
                        "parameter_type": 2,
                        "parameter_mmax": 1.0,
                        "parameter_enum": ["val1", "val2"],
                        "parameter_longname": "Humanize",
                        "parameter_shortname": "Humanize",
                        "parameter_initial_enable": 1,
                        "parameter_initial": [0],
                    }
                },
            }
        },
        # Voice Lead & Rootless Row
        {
            "box": {
                "id": "obj-btn-lead",
                "maxclass": "live.text",
                "varname": "VoiceLead",
                "parameter_enable": 1,
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", ""],
                "text": "Lead",
                "texton": "Lead",
                "presentation": 1,
                "presentation_rect": [6.0, 114.0, 68.0, 18.0],
                "patching_rect": [250.0, 265.0, 64.0, 16.0],
                "saved_attribute_attributes": {
                    "valueof": {
                        "parameter_type": 2,
                        "parameter_mmax": 1.0,
                        "parameter_enum": ["val1", "val2"],
                        "parameter_longname": "VoiceLead",
                        "parameter_shortname": "VoiceLead",
                        "parameter_initial_enable": 1,
                        "parameter_initial": [1],  # On by default
                    }
                },
            }
        },
        {
            "box": {
                "id": "obj-btn-rootless",
                "maxclass": "live.text",
                "varname": "Rootless",
                "parameter_enable": 1,
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", ""],
                "text": "Rootless",
                "texton": "Rootless",
                "presentation": 1,
                "presentation_rect": [78.0, 114.0, 68.0, 18.0],
                "patching_rect": [325.0, 265.0, 66.0, 16.0],
                "saved_attribute_attributes": {
                    "valueof": {
                        "parameter_type": 2,
                        "parameter_mmax": 1.0,
                        "parameter_enum": ["val1", "val2"],
                        "parameter_longname": "Rootless",
                        "parameter_shortname": "Rootless",
                        "parameter_initial_enable": 1,
                        "parameter_initial": [0],
                    }
                },
            }
        },
        {
            "box": {
                "id": "obj-vert-limit",
                "maxclass": "live.line",
                "presentation": 1,
                "presentation_rect": [0.0, 144.0, 152.0, 1.0],
                "patching_rect": [0.0, 144.0, 152.0, 1.0],
            }
        },
        # Prepender routing objects to JS
        {
            "box": {
                "id": "obj-prep-preset",
                "maxclass": "newobj",
                "text": "prepend preset_idx",
                "patching_rect": [250.0, 380.0, 110.0, 22.0],
            }
        },
        {
            "box": {
                "id": "obj-prep-voicing",
                "maxclass": "newobj",
                "text": "prepend voicing_idx",
                "patching_rect": [250.0, 410.0, 110.0, 22.0],
            }
        },
        {
            "box": {
                "id": "obj-prep-groove",
                "maxclass": "newobj",
                "text": "prepend groove_idx",
                "patching_rect": [325.0, 410.0, 110.0, 22.0],
            }
        },
        {
            "box": {
                "id": "obj-prep-octave",
                "maxclass": "newobj",
                "text": "prepend octave",
                "patching_rect": [250.0, 440.0, 90.0, 22.0],
            }
        },
        {
            "box": {
                "id": "obj-prep-human",
                "maxclass": "newobj",
                "text": "prepend humanize",
                "patching_rect": [325.0, 440.0, 105.0, 22.0],
            }
        },
        {
            "box": {
                "id": "obj-prep-lead",
                "maxclass": "newobj",
                "text": "prepend voice_lead",
                "patching_rect": [250.0, 470.0, 110.0, 22.0],
            }
        },
        {
            "box": {
                "id": "obj-prep-rootless",
                "maxclass": "newobj",
                "text": "prepend rootless",
                "patching_rect": [325.0, 470.0, 100.0, 22.0],
            }
        },
    ]

    lines: list[dict[str, Any]] = [
        # live.miditool.in -> obj-js (outlet 0: notes, outlet 1: context)
        {"patchline": {"destination": ["obj-js", 0], "source": ["obj-in", 0]}},
        {"patchline": {"destination": ["obj-js", 0], "source": ["obj-in", 1]}},
        # obj-js -> live.miditool.out
        {"patchline": {"destination": ["obj-out", 0], "source": ["obj-js", 0]}},
        # Control routings: outlet 0 (integer index) -> prepend -> obj-js
        {"patchline": {"destination": ["obj-prep-preset", 0], "source": ["obj-menu-preset", 0]}},
        {"patchline": {"destination": ["obj-js", 0], "source": ["obj-prep-preset", 0]}},
        {"patchline": {"destination": ["obj-prep-voicing", 0], "source": ["obj-menu-voicing", 0]}},
        {"patchline": {"destination": ["obj-js", 0], "source": ["obj-prep-voicing", 0]}},
        {"patchline": {"destination": ["obj-prep-groove", 0], "source": ["obj-menu-groove", 0]}},
        {"patchline": {"destination": ["obj-js", 0], "source": ["obj-prep-groove", 0]}},
        {"patchline": {"destination": ["obj-prep-octave", 0], "source": ["obj-num-oct", 0]}},
        {"patchline": {"destination": ["obj-js", 0], "source": ["obj-prep-octave", 0]}},
        {"patchline": {"destination": ["obj-prep-human", 0], "source": ["obj-btn-human", 0]}},
        {"patchline": {"destination": ["obj-js", 0], "source": ["obj-prep-human", 0]}},
        {"patchline": {"destination": ["obj-prep-lead", 0], "source": ["obj-btn-lead", 0]}},
        {"patchline": {"destination": ["obj-js", 0], "source": ["obj-prep-lead", 0]}},
        {"patchline": {"destination": ["obj-prep-rootless", 0], "source": ["obj-btn-rootless", 0]}},
        {"patchline": {"destination": ["obj-js", 0], "source": ["obj-prep-rootless", 0]}},
        # Parameter changes trigger bang into obj-trigger-in -> live.miditool.in
        {"patchline": {"destination": ["obj-trigger-in", 0], "source": ["obj-menu-preset", 0]}},
        {"patchline": {"destination": ["obj-trigger-in", 0], "source": ["obj-menu-voicing", 0]}},
        {"patchline": {"destination": ["obj-trigger-in", 0], "source": ["obj-menu-groove", 0]}},
        {"patchline": {"destination": ["obj-trigger-in", 0], "source": ["obj-num-oct", 0]}},
        {"patchline": {"destination": ["obj-trigger-in", 0], "source": ["obj-btn-human", 0]}},
        {"patchline": {"destination": ["obj-trigger-in", 0], "source": ["obj-btn-lead", 0]}},
        {"patchline": {"destination": ["obj-trigger-in", 0], "source": ["obj-btn-rootless", 0]}},
        {"patchline": {"destination": ["obj-in", 0], "source": ["obj-trigger-in", 0]}},
    ]

    return {
        "patcher": {
            "fileversion": 1,
            "appversion": {
                "major": 9,
                "minor": 0,
                "revision": 0,
                "architecture": "x64",
                "modernui": 1,
            },
            "classnamespace": "box",
            "rect": [100.0, 100.0, 520.0, 600.0],
            "openrect": [0.0, 0.0, 152.0, 144.0],
            "openinpresentation": 1,
            "default_fontsize": 10.0,
            "default_fontname": "Arial Bold",
            "boxes": boxes,
            "lines": lines,
        }
    }


def build_amxd_device(output_path: Path) -> Path:
    """Build the Midison Generator.amxd file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    patcher = get_midison_generator_patcher()
    amxd_bytes = create_amxd_container(patcher, device_type="nagg")
    output_path.write_bytes(amxd_bytes)
    return output_path


def install_m4l_device(target_dir: Path | None = None) -> Path:
    """
    Install Midison Generator.amxd into Ableton Live 12's user MIDI Tools folder.
    """
    if target_dir is None:
        target_dir = find_ableton_midi_tools_dir()
    else:
        target_dir = Path(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    device_path = target_dir / "Midison Generator.amxd"
    build_amxd_device(device_path)
    return device_path
