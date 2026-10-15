"""
Music theory primitives for midison.

Conventions:
- Pitch class: integer 0-11, where 0 = C, 1 = C#/Db, ..., 11 = B.
- MIDI note number: integer 0-127, where 60 = middle C (C4).
- Scale degrees are 1-indexed (1 = tonic, 7 = leading tone).
- Roman numerals follow standard analysis: case denotes triad quality
  (uppercase = major/augmented, lowercase = minor/diminished); modifiers
  follow the numeral.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Pitch class primitives
# ---------------------------------------------------------------------------

PITCH_CLASS_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PITCH_CLASS_NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

NOTE_TO_PITCH_CLASS = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "E#": 5, "F": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11, "B#": 0,
}


def parse_pitch_class(name: str) -> int:
    """Parse a note name like 'C', 'F#', 'Bb' into a pitch class (0-11)."""
    if name not in NOTE_TO_PITCH_CLASS:
        raise ValueError(f"Unknown note name: {name!r}")
    return NOTE_TO_PITCH_CLASS[name]


def pitch_class_name(pc: int, prefer_flats: bool = False) -> str:
    """Render a pitch class (0-11) as a note name."""
    pc = pc % 12
    return PITCH_CLASS_NAMES_FLAT[pc] if prefer_flats else PITCH_CLASS_NAMES_SHARP[pc]


def midi_note_name(midi: int, prefer_flats: bool = False) -> str:
    """Render a MIDI note number as e.g. 'C4', 'F#3'."""
    pc = midi % 12
    octave = (midi // 12) - 1  # MIDI 60 = C4
    return f"{pitch_class_name(pc, prefer_flats)}{octave}"


# ---------------------------------------------------------------------------
# Scales / modes
# ---------------------------------------------------------------------------

# Intervals from tonic in semitones for each diatonic mode.
MODE_INTERVALS: dict[str, tuple[int, ...]] = {
    "major":      (0, 2, 4, 5, 7, 9, 11),   # Ionian
    "ionian":     (0, 2, 4, 5, 7, 9, 11),
    "dorian":     (0, 2, 3, 5, 7, 9, 10),
    "phrygian":   (0, 1, 3, 5, 7, 8, 10),
    "lydian":     (0, 2, 4, 6, 7, 9, 11),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "minor":              (0, 2, 3, 5, 7, 8, 10),   # Aeolian (natural minor)
    "aeolian":            (0, 2, 3, 5, 7, 8, 10),
    "locrian":            (0, 1, 3, 5, 6, 8, 10),
    "harmonic_minor":     (0, 2, 3, 5, 7, 8, 11),
    "melodic_minor":      (0, 2, 3, 5, 7, 9, 11),
    "phrygian_dominant": (0, 1, 4, 5, 7, 8, 10),
    "lydian_dominant":   (0, 2, 4, 6, 7, 9, 10),
    "altered":            (0, 1, 3, 4, 6, 8, 10),
}

# Default triad quality on each scale degree per mode.
# 'M' = major, 'm' = minor, 'd' = diminished, 'A' = augmented.
MODE_TRIAD_QUALITIES: dict[str, tuple[str, ...]] = {
    "major":              ("M", "m", "m", "M", "M", "m", "d"),
    "ionian":             ("M", "m", "m", "M", "M", "m", "d"),
    "dorian":             ("m", "m", "M", "M", "m", "d", "M"),
    "phrygian":           ("m", "M", "M", "m", "d", "M", "m"),
    "lydian":             ("M", "M", "m", "d", "M", "m", "m"),
    "mixolydian":         ("M", "m", "d", "M", "m", "m", "M"),
    "minor":              ("m", "d", "M", "m", "m", "M", "M"),
    "aeolian":            ("m", "d", "M", "m", "m", "M", "M"),
    "locrian":            ("d", "M", "m", "m", "M", "M", "m"),
    "harmonic_minor":     ("m", "d", "A", "m", "M", "M", "d"),
    "melodic_minor":      ("m", "m", "A", "M", "M", "d", "d"),
    "phrygian_dominant": ("M", "M", "d", "m", "d", "M", "m"),
    "lydian_dominant":   ("M", "m", "d", "d", "m", "m", "M"),
    "altered":            ("d", "m", "m", "M", "M", "M", "m"),
}


def scale_pitch_classes(tonic_pc: int, mode: str) -> tuple[int, ...]:
    """Return the seven pitch classes of a scale, starting on the tonic."""
    if mode not in MODE_INTERVALS:
        raise ValueError(f"Unknown mode: {mode!r}")
    return tuple((tonic_pc + iv) % 12 for iv in MODE_INTERVALS[mode])


# ---------------------------------------------------------------------------
# Roman numeral parsing
# ---------------------------------------------------------------------------

ROMAN_TO_DEGREE = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}

# Quality inferred from the case + symbol on the numeral itself.
# Symbols: 'o' or '°' = diminished, '+' = augmented, otherwise case decides.
QUALITY_DIMINISHED = "d"
QUALITY_AUGMENTED = "A"
QUALITY_MAJOR = "M"
QUALITY_MINOR = "m"

# Recognised seventh / extension shorthands. Order matters: longer keys first.
EXTENSION_TOKENS = ("maj13", "maj11", "maj9", "maj7", "13", "11", "9", "7")

# Recognised alteration tokens.
ALTERATION_PATTERN = re.compile(r"([b#])(5|9|11|13)")


LETTER_CHORD_PATTERN = re.compile(r"^([A-G][b#]?)(.*)$")
LETTER_TO_DEGREE = {"C": 1, "D": 2, "E": 3, "F": 4, "G": 5, "A": 6, "B": 7}


@dataclass
class ParsedNumeral:
    """A parsed Roman numeral, fully resolved against a key + mode."""
    raw: str
    degree: int                      # 1..7 within the (possibly secondary) key
    quality: str                     # 'M' | 'm' | 'd' | 'A'
    extensions: tuple[int, ...]      # e.g. (7,) or (7, 9, 13). Always sorted.
    alterations: tuple[str, ...]     # e.g. ('b9', '#11')
    inversion: int                   # 0..3, derived from slash or explicit
    accidental: int                  # semitone offset on the root: -1 (b), 0, +1 (#)
    secondary_of: int | None = None  # if 'V/vi', this is 6 (the target degree)
    bass_degree: int | None = None   # for slash chords like 'I/3' or 'V/B'
    bass_interval: int | None = None # 1, 3, 5, 7 for chord interval in bass
    bass_pc: int | None = None       # explicit pitch class (0..11) for letter bass
    bass_accidental: int = 0         # accidental on bass degree (e.g. b7)
    root_pc: int | None = None       # explicit root pitch class (0..11) for letter chords

    @property
    def has_bass_override(self) -> bool:
        return (
            self.bass_degree is not None
            or self.bass_interval is not None
            or self.bass_pc is not None
        )


def parse_roman_numeral(raw: str) -> ParsedNumeral:
    """
    Parse a Roman numeral string into structured form.

    Supported syntax (examples):
        I, ii, iii, IV, V, vi, vii°, vii, III+
        Imaj7, ii7, V7, V13, vi9, ivm9 (lowercase 'm' is redundant but accepted)
        V7b9, V7#11, ii7b5
        bVII, bIII, #IV (modal mixture / chromatic roots)
        V/vi, V7/ii, viio7/V (secondary function)
        V6, V64, I6 (figured-bass inversion shorthand: 6 = first, 64 = second, 65/43/42 = seventh inversions)
        Slash chord bass overrides: I/3, I/E, V/7, V/B, IV/5, IV/C, I/1, ii/1, IV/1
        Letter chords: C/E, G/B, F/A, Dm/C

    The grammar is intentionally permissive but strict about ambiguity.
    """
    s = raw.strip()
    if not s:
        raise ValueError("Empty numeral")

    # 1. Split off secondary function or bass slash override.
    secondary_of: int | None = None
    bass_degree: int | None = None
    bass_interval: int | None = None
    bass_pc: int | None = None
    bass_accidental: int = 0
    slash_inversion: int | None = None

    if "/" in s:
        head, tail = s.rsplit("/", 1)
        tail = tail.strip()
        # Distinguish secondary function (e.g. 'V/vi', 'V/V', 'V7/ii')
        # from bass overrides ('I/3', 'V/7', 'IV/5', 'I/1', 'ii/1', 'IV/1', 'I/E', 'C/E', etc.)
        if _looks_like_numeral(tail) and tail.upper() not in ("I",):
            secondary_of = _numeral_to_degree(tail)
            s = head
        else:
            s = head
            tail_clean = tail
            if tail_clean.startswith("b"):
                tail_core = tail_clean[1:]
                acc = -1
            elif tail_clean.startswith("#"):
                tail_core = tail_clean[1:]
                acc = 1
            else:
                tail_core = tail_clean
                acc = 0

            if tail_clean in NOTE_TO_PITCH_CLASS:
                bass_pc = NOTE_TO_PITCH_CLASS[tail_clean]
            elif tail_core.isdigit():
                d = int(tail_core)
                bass_accidental = acc
                if d == 1:
                    bass_degree = 1
                    slash_inversion = 0
                elif d == 3:
                    bass_interval = 3
                    bass_degree = 3
                    slash_inversion = 1
                elif d == 5:
                    bass_interval = 5
                    bass_degree = 5
                    slash_inversion = 2
                elif d == 7:
                    bass_degree = 7
                    # V/7 means leading tone in bass / first inversion seventh
                    if head.upper().startswith("V"):
                        slash_inversion = 1
                    else:
                        bass_interval = 7
                        slash_inversion = 3
                else:
                    bass_degree = d
            elif tail_clean.upper() in ("I",):
                bass_degree = 1
                slash_inversion = 0
            else:
                raise ValueError(f"Unknown bass override {tail!r} in numeral {raw!r}")

    # Check for letter chord root (e.g. C, Dm, G, F, Bb, F#m, etc.)
    letter_match = None
    if re.match(r"^[A-G]", s):
        letter_match = LETTER_CHORD_PATTERN.match(s)

    if letter_match:
        root_name = letter_match.group(1)
        s = letter_match.group(2)
        root_pc = parse_pitch_class(root_name)
        degree = LETTER_TO_DEGREE[root_name[0]]
        accidental = 0
        is_uppercase = True

        # Quality marker immediately after root note
        quality_override: str | None = None
        if s.startswith(("o", "°")):
            quality_override = QUALITY_DIMINISHED
            s = s[1:]
        elif s.startswith("dim"):
            quality_override = QUALITY_DIMINISHED
            s = s[3:]
        elif s.startswith("ø"):
            quality_override = QUALITY_DIMINISHED
            s = "7" + s[1:]
        elif s.startswith("+"):
            quality_override = QUALITY_AUGMENTED
            s = s[1:]
        elif s.startswith("aug"):
            quality_override = QUALITY_AUGMENTED
            s = s[3:]
        elif s.startswith("m") and not s.startswith("maj"):
            quality_override = QUALITY_MINOR
            s = s[1:]

        quality = quality_override if quality_override is not None else QUALITY_MAJOR
    else:
        root_pc = None
        # 2. Leading accidental on the root (b, #).
        accidental = 0
        if s.startswith("b"):
            accidental = -1
            s = s[1:]
        elif s.startswith("#"):
            accidental = 1
            s = s[1:]

        # 3. The numeral itself: longest match from {VII, VI, IV, V, III, II, I}, case-sensitive.
        numeral_match = re.match(r"(VII|VI|IV|V|III|II|I|vii|vi|iv|v|iii|ii|i)", s)
        if not numeral_match:
            raise ValueError(f"Could not find Roman numeral in {raw!r}")
        numeral = numeral_match.group(1)
        s = s[numeral_match.end():]
        degree = ROMAN_TO_DEGREE[numeral.upper()]
        is_uppercase = numeral.isupper()

        # 4. Quality marker immediately after numeral: o, °, +, or lowercase 'm'.
        quality_override = None
        if s.startswith(("o", "°")):
            quality_override = QUALITY_DIMINISHED
            s = s[1:]
        elif s.startswith("dim"):
            quality_override = QUALITY_DIMINISHED
            s = s[3:]
        elif s.startswith("ø"):
            quality_override = QUALITY_DIMINISHED
            s = "7" + s[1:]
        elif s.startswith("+"):
            quality_override = QUALITY_AUGMENTED
            s = s[1:]
        elif s.startswith("m") and not s.startswith("maj"):
            quality_override = QUALITY_MINOR
            s = s[1:]

        if quality_override is not None:
            quality = quality_override
        else:
            quality = QUALITY_MAJOR if is_uppercase else QUALITY_MINOR

    # 5. Extensions (maj7, 7, 9, 11, 13, etc).
    extensions: list[int] = []
    while True:
        matched = False
        for tok in EXTENSION_TOKENS:
            if s.startswith(tok):
                if tok.startswith("maj"):
                    n = int(tok[3:])
                    extensions.append(n)
                    for implied in (7, 9, 11):
                        if implied < n and implied not in extensions:
                            extensions.append(implied)
                    s = s[len(tok):]
                    matched = True
                    extensions.append(-7)  # sentinel: maj7
                    break
                else:
                    n = int(tok)
                    extensions.append(n)
                    for implied in (7, 9, 11):
                        if implied < n and implied not in extensions:
                            extensions.append(implied)
                    s = s[len(tok):]
                    matched = True
                    break
        if not matched:
            break

    # 6. Alterations (b5, #5, b9, #9, #11, b13).
    alterations: list[str] = []
    for m in ALTERATION_PATTERN.finditer(s):
        alterations.append(f"{m.group(1)}{m.group(2)}")
    s = ALTERATION_PATTERN.sub("", s)

    # 7. Figured-bass inversion shorthand or explicit bass-note slash.
    inversion = slash_inversion if slash_inversion is not None else 0
    s = s.strip()
    if s in ("6", "63"):
        inversion = 1
    elif s in ("64",):
        inversion = 2
    elif s in ("7", "65"):
        if s == "65":
            inversion = 1
    elif s == "43":
        inversion = 2
    elif s == "42" or s == "2":
        inversion = 3
    elif s:
        raise ValueError(f"Unparsed remainder {s!r} in numeral {raw!r}")

    # If bass_pc is given and slash_inversion was not explicitly set:
    if slash_inversion is None and bass_pc is not None and root_pc is not None:
        third_pc = (root_pc + (3 if quality in (QUALITY_MINOR, QUALITY_DIMINISHED) else 4)) % 12
        fifth_pc = (root_pc + (6 if quality == QUALITY_DIMINISHED else 8 if quality == QUALITY_AUGMENTED else 7)) % 12
        seventh_pc = (root_pc + (11 if -7 in extensions else 10)) % 12
        if bass_pc == third_pc:
            inversion = 1
        elif bass_pc == fifth_pc:
            inversion = 2
        elif 7 in extensions and bass_pc == seventh_pc:
            inversion = 3
        elif bass_pc == root_pc:
            inversion = 0

    # Dedupe + sort extensions, keeping the maj7 sentinel if present.
    has_maj7 = -7 in extensions
    ext_clean = sorted({e for e in extensions if e > 0})
    if has_maj7:
        ext_clean = [-7] + ext_clean

    return ParsedNumeral(
        raw=raw,
        degree=degree,
        quality=quality,
        extensions=tuple(ext_clean),
        alterations=tuple(alterations),
        inversion=inversion,
        accidental=accidental,
        secondary_of=secondary_of,
        bass_degree=bass_degree,
        bass_interval=bass_interval,
        bass_pc=bass_pc,
        bass_accidental=bass_accidental,
        root_pc=root_pc,
    )


def _looks_like_numeral(s: str) -> bool:
    """Heuristic: does this token look like a Roman numeral?"""
    s = s.lstrip("b#")
    return bool(re.match(r"^(VII|VI|IV|V|III|II|I|vii|vi|iv|v|iii|ii|i)", s))


def _numeral_to_degree(s: str) -> int:
    """Extract just the scale degree from a numeral token."""
    s = s.lstrip("b#")
    m = re.match(r"(VII|VI|IV|V|III|II|I|vii|vi|iv|v|iii|ii|i)", s)
    if not m:
        raise ValueError(f"Not a numeral: {s!r}")
    return ROMAN_TO_DEGREE[m.group(1).upper()]


# ---------------------------------------------------------------------------
# Chord building
# ---------------------------------------------------------------------------

@dataclass
class ResolvedChord:
    """A fully resolved chord: pitch classes and a suggested register."""
    numeral: str
    root_pc: int
    quality: str
    pitch_classes: tuple[int, ...]   # in chord-tone order: root, 3rd, 5th, ...
    midi_notes: tuple[int, ...]      # voiced in a specific octave
    inversion: int = 0
    bass_pc: int | None = None


# Triad interval signatures from the root, in semitones.
TRIAD_INTERVALS = {
    QUALITY_MAJOR:      (0, 4, 7),
    QUALITY_MINOR:      (0, 3, 7),
    QUALITY_DIMINISHED: (0, 3, 6),
    QUALITY_AUGMENTED:  (0, 4, 8),
}


def build_chord(
    parsed: ParsedNumeral,
    key_pc: int,
    mode: str,
    octave: int = 4,
) -> ResolvedChord:
    """
    Build a chord's pitch classes and a default close-position voicing.

    The voicing returned here is the raw 'stack of thirds' starting at the
    given octave, with inversion or slash chord bass override applied.
    Voicing transformations (drop2, rootless, etc.) are applied in voicings.py.
    """
    # Resolve the root pitch class.
    if parsed.root_pc is not None:
        root_pc = parsed.root_pc
    elif parsed.secondary_of is not None:
        target_scale = scale_pitch_classes(key_pc, mode)
        temp_tonic_pc = target_scale[parsed.secondary_of - 1]
        root_pc = scale_pitch_classes(temp_tonic_pc, "major")[parsed.degree - 1]
        root_pc = (root_pc + parsed.accidental) % 12
    else:
        scale = scale_pitch_classes(key_pc, mode)
        root_pc = scale[parsed.degree - 1]
        root_pc = (root_pc + parsed.accidental) % 12

    # Build the triad.
    intervals = list(TRIAD_INTERVALS[parsed.quality])

    # Add seventh / extensions.
    has_maj7 = -7 in parsed.extensions
    numeric_exts = [e for e in parsed.extensions if e > 0]

    if 7 in numeric_exts:
        # Default seventh: minor 7 for dominant/minor/half-dim, major 7 only
        # if explicitly maj7 or if the triad quality is major and the
        # numeral didn't specify plain '7'.
        if has_maj7:
            intervals.append(11)
        elif parsed.quality == QUALITY_DIMINISHED and not has_maj7:
            # Half-diminished (m7) vs fully-diminished (bb7). We default to
            # half-diminished here; the 'ø' shorthand has already injected '7'.
            intervals.append(10)
        else:
            intervals.append(10)

    if 9 in numeric_exts:
        intervals.append(14)
    if 11 in numeric_exts:
        intervals.append(17)
    if 13 in numeric_exts:
        intervals.append(21)

    # Apply alterations.
    for alt in parsed.alterations:
        sign, deg = alt[0], int(alt[1:])
        delta = -1 if sign == "b" else 1
        target_interval = {5: 7, 9: 14, 11: 17, 13: 21}[deg]
        if target_interval in intervals:
            idx = intervals.index(target_interval)
            intervals[idx] = target_interval + delta
        else:
            intervals.append(target_interval + delta)

    intervals = sorted(set(intervals))

    # Voice in the requested octave: root at C{octave} reference,
    # i.e. root MIDI = (octave + 1) * 12 + root_pc.
    root_midi = (octave + 1) * 12 + root_pc
    midi_notes = tuple(root_midi + iv for iv in intervals)

    # Determine target bass pitch class if an explicit bass override exists
    target_bass_pc: int | None = None
    if parsed.bass_pc is not None:
        target_bass_pc = parsed.bass_pc % 12
    elif parsed.bass_interval is not None:
        if parsed.bass_interval == 1:
            target_bass_pc = root_pc
        elif parsed.bass_interval == 3:
            third_ivs = [iv for iv in intervals if 2 <= iv <= 5]
            target_bass_pc = (root_pc + (third_ivs[0] if third_ivs else 4)) % 12
        elif parsed.bass_interval == 5:
            fifth_ivs = [iv for iv in intervals if 6 <= iv <= 8]
            target_bass_pc = (root_pc + (fifth_ivs[0] if fifth_ivs else 7)) % 12
        elif parsed.bass_interval == 7:
            seventh_ivs = [iv for iv in intervals if 9 <= iv <= 11]
            target_bass_pc = (root_pc + (seventh_ivs[0] if seventh_ivs else 10)) % 12
    elif parsed.bass_degree is not None:
        scale = scale_pitch_classes(key_pc, mode)
        target_bass_pc = (scale[parsed.bass_degree - 1] + parsed.bass_accidental) % 12

    inversion = parsed.inversion

    # Apply bass override or inversion
    if target_bass_pc is not None:
        # Determine inversion based on target_bass_pc
        if target_bass_pc == root_pc:
            inversion = 0
        elif target_bass_pc in [(root_pc + iv) % 12 for iv in intervals if 2 <= iv <= 5]:
            inversion = 1
        elif target_bass_pc in [(root_pc + iv) % 12 for iv in intervals if 6 <= iv <= 8]:
            inversion = 2
        elif target_bass_pc in [(root_pc + iv) % 12 for iv in intervals if 9 <= iv <= 11]:
            inversion = 3

        notes = list(midi_notes)
        if target_bass_pc in [n % 12 for n in notes]:
            count = 0
            while notes[0] % 12 != target_bass_pc and count < len(notes):
                lowest = notes.pop(0)
                notes.append(lowest + 12)
                notes.sort()
                count += 1
            octave_base = (octave + 1) * 12
            while notes[0] >= octave_base + 12:
                notes = [n - 12 for n in notes]
            while notes[0] < octave_base - 12:
                notes = [n + 12 for n in notes]
        else:
            # Pedal point: note not in chord (e.g. ii/1 where C is not in Dm)
            lowest = notes[0]
            bass_note = lowest - ((lowest - target_bass_pc) % 12)
            if bass_note == lowest:
                bass_note -= 12
            while bass_note >= lowest:
                bass_note -= 12
            notes.insert(0, bass_note)
            notes.sort()
        midi_notes = tuple(notes)
    elif parsed.inversion > 0:
        notes = list(midi_notes)
        for _ in range(min(parsed.inversion, len(notes) - 1)):
            notes[0] += 12
            notes.sort()
        midi_notes = tuple(notes)

    pitch_classes = tuple((root_pc + iv) % 12 for iv in intervals)
    if target_bass_pc is not None and target_bass_pc not in pitch_classes:
        pitch_classes = (target_bass_pc,) + pitch_classes

    return ResolvedChord(
        numeral=parsed.raw,
        root_pc=root_pc,
        quality=parsed.quality,
        pitch_classes=pitch_classes,
        midi_notes=midi_notes,
        inversion=inversion,
        bass_pc=target_bass_pc,
    )
