"""
Harmonic Navigator & 'Next Chord' Recommender for midison.

Recommends musically compelling next chords from a given point in a chord
progression across multiple harmonic pathways:
- Diatonic cadential motions
- Secondary dominants / tonicizations
- Modal mixture / borrowed chords
- Tritone substitutions
- Chromatic passing chords
"""

from __future__ import annotations

from dataclasses import dataclass

from midison.cli import parse_progression_string
from midison.theory import (
    NOTE_TO_PITCH_CLASS,
    ParsedNumeral,
    build_chord,
    parse_pitch_class,
    parse_roman_numeral,
    pitch_class_name,
)

LETTERS = ["C", "D", "E", "F", "G", "A", "B"]

VALID_PATHWAYS = {
    "diatonic",
    "secondary_dominant",
    "modal_mixture",
    "tritone_sub",
    "passing",
}


@dataclass
class ChordSuggestion:
    numeral: str
    chord_name: str           # e.g. 'Fm7' in C major
    pathway: str              # 'diatonic', 'secondary_dominant', 'modal_mixture', 'tritone_sub', 'passing'
    explanation: str          # e.g. 'Minor plagal cadence (borrowed iv): creates a bittersweet, emotional release.'
    mood_descriptor: str      # e.g. 'Bittersweet / Vulnerable'


def _resolve_root_name(parsed: ParsedNumeral, key_center: str, scale_type: str) -> str:
    """Resolve the enharmonically correct letter name for a chord's root."""
    key_pc = parse_pitch_class(key_center)
    built = build_chord(parsed, key_pc, scale_type)
    root_pc = built.root_pc

    key_letter = key_center[0].upper()
    if parsed.secondary_of is not None:
        target_letter_idx = (LETTERS.index(key_letter) + parsed.secondary_of - 1) % 7
        letter_idx = (target_letter_idx + parsed.degree - 1) % 7
    else:
        letter_idx = (LETTERS.index(key_letter) + parsed.degree - 1) % 7

    base_letter = LETTERS[letter_idx]
    base_pc = NOTE_TO_PITCH_CLASS[base_letter]
    diff = (root_pc - base_pc + 6) % 12 - 6
    acc = {0: "", 1: "#", -1: "b", 2: "##", -2: "bb"}.get(diff)
    if acc is not None:
        return f"{base_letter}{acc}"

    prefer_flats = parsed.accidental < 0 or "b" in key_center.lower()
    return pitch_class_name(root_pc, prefer_flats=prefer_flats)


def format_chord_symbol(parsed: ParsedNumeral, key_center: str, scale_type: str) -> str:
    """Format a human-readable chord symbol (e.g. 'Fm7', 'G13', 'Db7', 'Dm7b5')."""
    root = _resolve_root_name(parsed, key_center, scale_type)
    q = parsed.quality
    exts = parsed.extensions
    has_maj7 = -7 in exts
    num_exts = [e for e in exts if e > 0]

    if q == "M":
        if has_maj7:
            if 13 in num_exts:
                return f"{root}maj13"
            elif 9 in num_exts:
                return f"{root}maj9"
            return f"{root}maj7"
        elif 13 in num_exts:
            return f"{root}13"
        elif 11 in num_exts:
            return f"{root}11"
        elif 9 in num_exts:
            return f"{root}9"
        elif 7 in num_exts:
            return f"{root}7"
        return root
    elif q == "m":
        if has_maj7:
            return f"{root}m(maj7)"
        elif 13 in num_exts:
            return f"{root}m13"
        elif 11 in num_exts:
            return f"{root}m11"
        elif 9 in num_exts:
            return f"{root}m9"
        elif 7 in num_exts:
            return f"{root}m7"
        return f"{root}m"
    elif q == "d":
        if "ø" in parsed.raw or "m7b5" in parsed.raw:
            return f"{root}m7b5"
        elif 7 in num_exts:
            return f"{root}dim7"
        return f"{root}dim"
    elif q == "A":
        if 7 in num_exts:
            return f"{root}aug7"
        return f"{root}aug"
    return root


def suggest_next_chords(
    current_progression: str,
    key_center: str = "C",
    scale_type: str = "major",
) -> list[ChordSuggestion]:
    """
    Recommend 4-6 diverse next chords from the final chord in the given progression.

    Parameters:
        current_progression: Progression string, e.g. 'ii7 - V7' or 'Imaj7'.
        key_center: Tonic pitch name, e.g. 'C', 'G', 'Eb', 'A'.
        scale_type: Scale mode, e.g. 'major', 'minor', 'aeolian'.

    Returns:
        A list of 4-6 ChordSuggestion instances spanning distinct harmonic pathways.
    """
    specs = parse_progression_string(current_progression)
    last_spec = specs[-1]
    parsed = parse_roman_numeral(last_spec.numeral)

    # Normalize inputs
    norm_mode = scale_type.strip().lower()
    is_minor = norm_mode in ("minor", "aeolian", "harmonic_minor")
    norm_key = key_center.strip()
    norm_key = norm_key[0].upper() + norm_key[1:].lower()

    candidates: list[tuple[str, str, str, str]] = []

    if not is_minor:
        # -----------------------------------------------------------------------
        # Major key recommendations
        # -----------------------------------------------------------------------
        if parsed.degree == 1 and parsed.accidental == 0 and parsed.secondary_of is None:
            # After Tonic (I, Imaj7)
            candidates = [
                (
                    "IVmaj7",
                    "diatonic",
                    "Subdominant expansion (IVmaj7): moves away from home to initiate open harmonic movement.",
                    "Open / Uplifting",
                ),
                (
                    "vi7",
                    "diatonic",
                    "Relative minor descent (vi7): provides gentle emotional depth while maintaining tonic stability.",
                    "Introspective / Warm",
                ),
                (
                    "V7/vi",
                    "secondary_dominant",
                    "Secondary dominant (V7/vi): creates chromatic drive towards the relative minor.",
                    "Dramatic / Yearning",
                ),
                (
                    "iv7",
                    "modal_mixture",
                    "Minor plagal cadence (borrowed iv): creates a bittersweet, emotional release.",
                    "Bittersweet / Vulnerable",
                ),
                (
                    "bII7",
                    "tritone_sub",
                    "Tritone substitution / chromatic approach (bII7): sleek jazz color sliding around the tonic.",
                    "Sleek / Sophisticated",
                ),
                (
                    "#IVdim7",
                    "passing",
                    "Chromatic passing diminished (#IVdim7): introduces mysterious tension lifting toward dominant harmony.",
                    "Mysterious / Dreamy",
                ),
            ]
        elif parsed.degree in (2, 4) and parsed.secondary_of is None:
            # After Subdominant / Predominant (ii, ii7, IV, IVmaj7, iv, iv7)
            candidates = [
                (
                    "V7",
                    "diatonic",
                    "Cadential dominant resolution (V7): standard authentic cadence building strong harmonic tension.",
                    "Tense / Driving",
                ),
                (
                    "V13",
                    "diatonic",
                    "Extended dominant resolution (V13): lush jazz cadence leading smoothly toward resolution.",
                    "Lush / Sophisticated",
                ),
                (
                    "V7/V",
                    "secondary_dominant",
                    "Secondary dominant (V7/V): bright chromatic lift pushing relentlessly toward the dominant.",
                    "Bright / Anticipatory",
                ),
                (
                    "iv7",
                    "modal_mixture",
                    "Minor plagal cadence (borrowed iv): creates a bittersweet, emotional release.",
                    "Bittersweet / Vulnerable",
                ),
                (
                    "bII7",
                    "tritone_sub",
                    "Tritone substitution (bII7): chromatically prepares the tonic with a slick half-step descent.",
                    "Urban / Slick",
                ),
                (
                    "#IVdim7",
                    "passing",
                    "Chromatic passing chord (#IVdim7): smooth voice-leading bridge ascending from IV to V.",
                    "Tension / Transition",
                ),
            ]
        elif (parsed.degree in (5, 7) and parsed.accidental == 0) or parsed.secondary_of is not None:
            # After Dominant (V, V7, V13, vii°, secondary dominants)
            candidates = [
                (
                    "Imaj7",
                    "diatonic",
                    "Authentic cadential resolution (Imaj7): ultimate release of harmonic tension back to tonic.",
                    "Resolved / Complete",
                ),
                (
                    "vi7",
                    "diatonic",
                    "Deceptive cadential resolution (vi7): subverts expectation by landing softly on the relative minor.",
                    "Surprising / Bittersweet",
                ),
                (
                    "V7/vi",
                    "secondary_dominant",
                    "Secondary dominant chain (V7/vi): redirects dominant energy toward the relative minor.",
                    "Dramatic / Yearning",
                ),
                (
                    "bVImaj7",
                    "modal_mixture",
                    "Modal deceptive resolution (borrowed bVI): epic cinematic shift to the flat submediant.",
                    "Heroic / Wonder",
                ),
                (
                    "bII7",
                    "tritone_sub",
                    "Tritone substitute cadence (bII7): chromatic half-step descent directly into tonic.",
                    "Sleek / Sultry",
                ),
                (
                    "bVII",
                    "modal_mixture",
                    "Subtonic borrowed chord (bVII): classic rock/soul modal evasion bypassing the tonic.",
                    "Triumphant / Energetic",
                ),
            ]
        elif parsed.degree in (6, 3):
            # After Submediant / Mediant (vi, vi7, iii, iii7)
            candidates = [
                (
                    "ii7",
                    "diatonic",
                    "Circle of fifths progression (vi -> ii): natural diatonic momentum into predominant harmony.",
                    "Flowing / Balanced",
                ),
                (
                    "IVmaj7",
                    "diatonic",
                    "Stepwise diatonic descent to subdominant (IVmaj7): rich harmonic expansion.",
                    "Open / Reflective",
                ),
                (
                    "V7/V",
                    "secondary_dominant",
                    "Secondary dominant (V7/V): boosts diatonic energy straight into dominant anticipation.",
                    "Optimistic / Bright",
                ),
                (
                    "bVImaj7",
                    "modal_mixture",
                    "Modal mixture shift (borrowed bVI): mysterious chromatic mediant slip.",
                    "Haunting / Cinematic",
                ),
                (
                    "bII7",
                    "tritone_sub",
                    "Tritone substitute approach (bII7): chromatically prepares the tonic resolution.",
                    "Slick / Sophisticated",
                ),
                (
                    "#IVdim7",
                    "passing",
                    "Chromatic passing diminished (#IVdim7): bridges diatonic harmony with mysterious tension.",
                    "Mysterious / Dreamy",
                ),
            ]
        else:
            # General / Chromatic borrow fallback
            candidates = [
                (
                    "Imaj7",
                    "diatonic",
                    "Resolution to tonic (Imaj7): stabilizes harmonic motion home.",
                    "Resolved / Grounded",
                ),
                (
                    "V7",
                    "diatonic",
                    "Dominant setup (V7): drives energy toward cadential resolution.",
                    "Tense / Driving",
                ),
                (
                    "V7/ii",
                    "secondary_dominant",
                    "Secondary dominant (V7/ii): charges into the supertonic predominant.",
                    "Soulful / Warm",
                ),
                (
                    "iv7",
                    "modal_mixture",
                    "Minor plagal borrow (iv7): melancholic emotional release.",
                    "Bittersweet / Vulnerable",
                ),
                (
                    "bII7",
                    "tritone_sub",
                    "Tritone substitution (bII7): sleek chromatic approach to tonic.",
                    "Sleek / Sophisticated",
                ),
            ]
    else:
        # -----------------------------------------------------------------------
        # Minor key recommendations
        # -----------------------------------------------------------------------
        if parsed.degree == 1 and parsed.accidental == 0 and parsed.secondary_of is None:
            # After Minor Tonic (i, i7)
            candidates = [
                (
                    "iv7",
                    "diatonic",
                    "Diatonic subdominant expansion (iv7): deepens the minor tonality with natural melancholia.",
                    "Dark / Reflective",
                ),
                (
                    "V7",
                    "diatonic",
                    "Harmonic minor dominant (V7): introduces leading-tone tension driving back to tonic.",
                    "Dramatic / Imperative",
                ),
                (
                    "V7/iv",
                    "secondary_dominant",
                    "Secondary dominant (V7/iv): tonicizes the minor subdominant with bluesy intensity.",
                    "Intense / Bluesy",
                ),
                (
                    "IV7",
                    "modal_mixture",
                    "Dorian borrowed IV (IV7): hopeful glimmer of major subdominant brightness.",
                    "Soulful / Radiant",
                ),
                (
                    "bII7",
                    "tritone_sub",
                    "Tritone substitute / Neapolitan (bII7): dramatic operatic tension descending to tonic.",
                    "Tragic / Gripping",
                ),
                (
                    "VII",
                    "passing",
                    "Modal subtonic step (VII): classic folk/rock modal movement away from tonic.",
                    "Epic / Driving",
                ),
            ]
        elif parsed.degree in (2, 4) and parsed.secondary_of is None:
            # After Minor Subdominant / Predominant (iv, iv7, iiø7)
            candidates = [
                (
                    "V7",
                    "diatonic",
                    "Harmonic minor cadence (V7): traditional dominant arrival with sharp leading tone.",
                    "Tense / Gripping",
                ),
                (
                    "v7",
                    "diatonic",
                    "Natural minor dominant (v7): modal aeolian continuation without sharp leading tone.",
                    "Misty / Somber",
                ),
                (
                    "V7/V",
                    "secondary_dominant",
                    "Secondary dominant (V7/V): sharp chromatic push into the harmonic dominant.",
                    "Urgent / Driving",
                ),
                (
                    "VImaj7",
                    "modal_mixture",
                    "Submediant expansion (VImaj7): emotional blooming into relative major harmony.",
                    "Hopeful / Bittersweet",
                ),
                (
                    "bII7",
                    "tritone_sub",
                    "Tritone substitute cadence (bII7): chromatic slide toward the tonic.",
                    "Sleek / Sophisticated",
                ),
                (
                    "#iv°7",
                    "passing",
                    "Chromatic passing diminished (#iv°7): chromatic voice-leading elevator into dominant.",
                    "Anxious / Thrilling",
                ),
            ]
        elif (parsed.degree in (5, 7) and parsed.accidental == 0) or parsed.secondary_of is not None:
            # After Minor Dominant (V7, v, v7, vii°7, secondary dominants)
            candidates = [
                (
                    "i7",
                    "diatonic",
                    "Authentic minor resolution (i7): dark, powerful arrival back on tonic.",
                    "Resolved / Somber",
                ),
                (
                    "VImaj7",
                    "diatonic",
                    "Deceptive cadence in minor (VImaj7): emotional explosion onto the submediant.",
                    "Dramatic / Heartbreaking",
                ),
                (
                    "V7/iv",
                    "secondary_dominant",
                    "Secondary dominant diversion (V7/iv): redirects cadential momentum into subdominant territory.",
                    "Restless / Searching",
                ),
                (
                    "IV7",
                    "modal_mixture",
                    "Dorian borrowed IV (IV7): unexpected major lift out of dominant tension.",
                    "Radiant / Yearning",
                ),
                (
                    "bII7",
                    "tritone_sub",
                    "Tritone substitution (bII7): sleek chromatic descent directly to tonic.",
                    "Sultry / Dark",
                ),
                (
                    "VII",
                    "passing",
                    "Subtonic evasion (VII): avoids resolution to tonic, stepping into cyclic modal groove.",
                    "Epic / Flowing",
                ),
            ]
        elif parsed.degree in (6, 3):
            # After Submediant / Mediant in minor (VI, VImaj7, III, IIImaj7)
            candidates = [
                (
                    "iv7",
                    "diatonic",
                    "Subdominant motion (iv7): continues descending diatonic progression in minor.",
                    "Dark / Flowing",
                ),
                (
                    "V7",
                    "diatonic",
                    "Harmonic dominant leap (V7): charges forward into cadential tension.",
                    "Urgent / Tense",
                ),
                (
                    "V7/iv",
                    "secondary_dominant",
                    "Secondary dominant (V7/iv): tonicizes the minor subdominant.",
                    "Soulful / Intense",
                ),
                (
                    "iiø7",
                    "modal_mixture",
                    "Half-diminished predominant setup (iiø7): sets up traditional minor turnaround.",
                    "Melancholic / Suspenseful",
                ),
                (
                    "bII7",
                    "tritone_sub",
                    "Tritone substitute approach (bII7): chromatic descent toward tonic.",
                    "Sleek / Sophisticated",
                ),
                (
                    "VII",
                    "passing",
                    "Modal step (VII): smooth modal voice leading across natural scale degrees.",
                    "Heroic / Resolute",
                ),
            ]
        else:
            candidates = [
                (
                    "i7",
                    "diatonic",
                    "Return to tonic (i7): grounds harmonic motion in the home key.",
                    "Resolved / Somber",
                ),
                (
                    "V7",
                    "diatonic",
                    "Dominant setup (V7): builds tension toward authentic minor cadence.",
                    "Dramatic / Driving",
                ),
                (
                    "V7/iv",
                    "secondary_dominant",
                    "Secondary dominant (V7/iv): bluesy tonicization of subdominant.",
                    "Intense / Bluesy",
                ),
                (
                    "VImaj7",
                    "modal_mixture",
                    "Submediant release (VImaj7): emotional warmth in relative major.",
                    "Warm / Nostalgic",
                ),
                (
                    "bII7",
                    "tritone_sub",
                    "Tritone substitution (bII7): chromatic approach toward tonic.",
                    "Sleek / Dark",
                ),
            ]

    # Convert candidates to ChordSuggestion objects, filtering out direct duplicates
    suggestions: list[ChordSuggestion] = []
    seen_numerals: set[str] = set()

    # Raw numeral without duration suffix or spaces
    current_raw = last_spec.numeral.strip()

    for numeral, pathway, explanation, mood in candidates:
        if numeral == current_raw or numeral in seen_numerals:
            continue
        try:
            p_sugg = parse_roman_numeral(numeral)
            chord_name = format_chord_symbol(p_sugg, norm_key, norm_mode)
        except Exception:
            # Fallback if parsing fails
            chord_name = numeral

        seen_numerals.add(numeral)
        suggestions.append(
            ChordSuggestion(
                numeral=numeral,
                chord_name=chord_name,
                pathway=pathway,
                explanation=explanation,
                mood_descriptor=mood,
            )
        )

    # Return between 4 and 6 suggestions
    return suggestions[:6]
