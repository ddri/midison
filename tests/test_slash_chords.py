"""Tests for slash chords, scalar bass movement, and inverted basslines (Issue #9)."""

from __future__ import annotations

from midison.events import resolve_progression_notes
from midison.midi_writer import ChordSpec, GenerationRequest
from midison.theory import (
    QUALITY_MAJOR,
    QUALITY_MINOR,
    build_chord,
    parse_roman_numeral,
)
from midison.voicings import apply_voicing


class TestSlashChordParsing:
    """Test Roman numeral and letter slash chord parsing."""

    def test_first_inversion_third_in_bass(self):
        p = parse_roman_numeral("I/3")
        assert p.degree == 1
        assert p.quality == QUALITY_MAJOR
        assert p.bass_degree == 3
        assert p.bass_interval == 3
        assert p.inversion == 1
        assert p.has_bass_override

    def test_first_inversion_letter_bass(self):
        p = parse_roman_numeral("I/E")
        assert p.degree == 1
        assert p.bass_pc == 4  # E
        assert p.has_bass_override

    def test_leading_tone_in_bass(self):
        # V/7: leading tone in bass / first inversion seventh
        p = parse_roman_numeral("V/7")
        assert p.degree == 5
        assert p.quality == QUALITY_MAJOR
        assert p.bass_degree == 7
        assert p.inversion == 1
        assert p.has_bass_override

    def test_leading_tone_letter_bass(self):
        p = parse_roman_numeral("V/B")
        assert p.degree == 5
        assert p.bass_pc == 11  # B
        assert p.has_bass_override

    def test_second_inversion_fifth_in_bass(self):
        # IV/5: 5th in bass / second inversion
        p = parse_roman_numeral("IV/5")
        assert p.degree == 4
        assert p.quality == QUALITY_MAJOR
        assert p.bass_degree == 5
        assert p.bass_interval == 5
        assert p.inversion == 2
        assert p.has_bass_override

    def test_second_inversion_letter_bass(self):
        p = parse_roman_numeral("IV/C")
        assert p.degree == 4
        assert p.bass_pc == 0  # C
        assert p.has_bass_override

    def test_explicit_root_pedal(self):
        p = parse_roman_numeral("I/1")
        assert p.degree == 1
        assert p.bass_degree == 1
        assert p.inversion == 0
        assert p.has_bass_override

    def test_pedal_point_ii_over_tonic(self):
        p = parse_roman_numeral("ii/1")
        assert p.degree == 2
        assert p.quality == QUALITY_MINOR
        assert p.bass_degree == 1
        assert p.has_bass_override

    def test_pedal_point_iv_over_tonic(self):
        p = parse_roman_numeral("IV/1")
        assert p.degree == 4
        assert p.quality == QUALITY_MAJOR
        assert p.bass_degree == 1
        assert p.has_bass_override

    def test_letter_bass_notation(self):
        p_ce = parse_roman_numeral("C/E")
        assert p_ce.root_pc == 0
        assert p_ce.bass_pc == 4
        assert p_ce.inversion == 1
        assert p_ce.has_bass_override

        p_gb = parse_roman_numeral("G/B")
        assert p_gb.root_pc == 7
        assert p_gb.bass_pc == 11
        assert p_gb.inversion == 1
        assert p_gb.has_bass_override

        p_fa = parse_roman_numeral("F/A")
        assert p_fa.root_pc == 5
        assert p_fa.bass_pc == 9
        assert p_fa.inversion == 1
        assert p_fa.has_bass_override

        p_dmc = parse_roman_numeral("Dm/C")
        assert p_dmc.root_pc == 2
        assert p_dmc.quality == QUALITY_MINOR
        assert p_dmc.bass_pc == 0
        assert p_dmc.has_bass_override


class TestSlashChordBuilding:
    """Test building ResolvedChord with slash bass overrides."""

    def test_I_3_produces_first_inversion_with_third_in_bass(self):
        p = parse_roman_numeral("I/3")
        chord = build_chord(p, key_pc=0, mode="major", octave=4)
        assert chord.inversion == 1
        # In C major, 3rd is E (pc 4). Bass note must be E.
        assert chord.midi_notes[0] % 12 == 4
        # Notes should be E, G, C (or E4, G4, C5)
        assert set(chord.pitch_classes) == {0, 4, 7}

    def test_I_E_produces_first_inversion(self):
        p = parse_roman_numeral("I/E")
        chord = build_chord(p, key_pc=0, mode="major", octave=4)
        assert chord.inversion == 1
        assert chord.midi_notes[0] % 12 == 4  # E in bass

    def test_IV_1_pedal_point_produces_subdominant_triad_over_tonic_bass(self):
        # IV/1: IV triad (F, A, C) with tonic (C) in the bass
        p = parse_roman_numeral("IV/1")
        chord = build_chord(p, key_pc=0, mode="major", octave=4)
        # Lowest note must be C (tonic bass, pc 0)
        assert chord.midi_notes[0] % 12 == 0
        # Triad tones: F (5), A (9), C (0)
        assert set(chord.pitch_classes) == {0, 5, 9}

    def test_ii_1_pedal_point_produces_minor_triad_over_tonic_bass(self):
        # ii/1: Dm triad (D, F, A) with tonic (C) in the bass
        p = parse_roman_numeral("ii/1")
        chord = build_chord(p, key_pc=0, mode="major", octave=4)
        # Lowest note must be C (tonic bass, pc 0)
        assert chord.midi_notes[0] % 12 == 0
        # Must contain D (2), F (5), A (9)
        assert {2, 5, 9}.issubset(set(chord.pitch_classes))

    def test_V_7_produces_leading_tone_in_bass(self):
        p = parse_roman_numeral("V/7")
        chord = build_chord(p, key_pc=0, mode="major", octave=4)
        assert chord.inversion == 1
        # Leading tone of C major is B (pc 11)
        assert chord.midi_notes[0] % 12 == 11
        # Chord tones of G major: G (7), B (11), D (2)
        assert set(chord.pitch_classes) == {7, 11, 2}

    def test_V_B_produces_first_inversion_seventh(self):
        p = parse_roman_numeral("V/B")
        chord = build_chord(p, key_pc=0, mode="major", octave=4)
        assert chord.inversion == 1
        assert chord.midi_notes[0] % 12 == 11  # B in bass

    def test_IV_5_produces_second_inversion(self):
        p = parse_roman_numeral("IV/5")
        chord = build_chord(p, key_pc=0, mode="major", octave=4)
        assert chord.inversion == 2
        # 5th of IV (F) is C (pc 0)
        assert chord.midi_notes[0] % 12 == 0

    def test_IV_C_produces_second_inversion(self):
        p = parse_roman_numeral("IV/C")
        chord = build_chord(p, key_pc=0, mode="major", octave=4)
        assert chord.inversion == 2
        assert chord.midi_notes[0] % 12 == 0

    def test_lead_sheet_chords(self):
        c_e = build_chord(parse_roman_numeral("C/E"), key_pc=0, mode="major")
        assert c_e.midi_notes[0] % 12 == 4  # E
        assert set(c_e.pitch_classes) == {0, 4, 7}

        g_b = build_chord(parse_roman_numeral("G/B"), key_pc=0, mode="major")
        assert g_b.midi_notes[0] % 12 == 11  # B
        assert set(g_b.pitch_classes) == {7, 11, 2}

        f_a = build_chord(parse_roman_numeral("F/A"), key_pc=0, mode="major")
        assert f_a.midi_notes[0] % 12 == 9  # A
        assert set(f_a.pitch_classes) == {5, 9, 0}

        dm_c = build_chord(parse_roman_numeral("Dm/C"), key_pc=0, mode="major")
        assert dm_c.midi_notes[0] % 12 == 0  # C
        assert {2, 5, 9}.issubset(set(dm_c.pitch_classes))


class TestVoicingTransformationAnchoring:
    """Test that voicing transformations keep the slash bass anchored at the bottom."""

    def test_drop2_anchors_bass(self):
        # Cmaj7/E in 1st inversion: [64, 67, 72, 79] (E4, G4, C5, B5)
        # Without anchor, drop2 would drop 72 to 60 (C4), overtaking the bass E4 (64).
        # With anchor, E must remain the lowest note.
        notes = [64, 67, 72, 79]
        voiced = apply_voicing(notes, "drop2", bass_pc=4)
        assert min(voiced) % 12 == 4
        assert voiced[0] % 12 == 4

    def test_spread_anchors_bass(self):
        notes = [64, 67, 72, 79]
        voiced = apply_voicing(notes, "spread", bass_pc=4)
        assert min(voiced) % 12 == 4
        assert voiced[0] % 12 == 4

    def test_close_anchors_bass(self):
        notes = [64, 67, 72, 79]
        voiced = apply_voicing(notes, "close", bass_pc=4)
        assert min(voiced) % 12 == 4
        assert voiced[0] % 12 == 4

    def test_drop3_anchors_bass(self):
        notes = [64, 67, 72, 79]
        voiced = apply_voicing(notes, "drop3", bass_pc=4)
        assert min(voiced) % 12 == 4
        assert voiced[0] % 12 == 4

    def test_drop2and4_anchors_bass(self):
        notes = [64, 67, 72, 79]
        voiced = apply_voicing(notes, "drop2and4", bass_pc=4)
        assert min(voiced) % 12 == 4
        assert voiced[0] % 12 == 4

    def test_pedal_point_anchored_under_drop2(self):
        # IV/1 with tonic C in bass: [60, 65, 69, 72]
        notes = [60, 65, 69, 72]
        voiced = apply_voicing(notes, "drop2", bass_pc=0)
        assert min(voiced) % 12 == 0
        assert voiced[0] % 12 == 0


class TestStepwiseDescendingBassline:
    """
    Test stepwise descending bassline:
    I - V/7 - vi - I/5 - IV - I/3 - ii7 - V7
    """

    PROGRESSION = ("I", "V/7", "vi", "I/5", "IV", "I/3", "ii7", "V7")

    def test_stepwise_descending_bassline_pitch_classes(self):
        """Direct chord building should yield descending scalar bass motion C-B-A-G-F-E-D."""
        chords = [
            build_chord(parse_roman_numeral(token), key_pc=0, mode="major", octave=4)
            for token in self.PROGRESSION
        ]
        bass_pcs = [c.midi_notes[0] % 12 for c in chords]
        # I(C) -> V/7(B) -> vi(A) -> I/5(G) -> IV(F) -> I/3(E) -> ii7(D) -> V7(G)
        expected = [0, 11, 9, 7, 5, 4, 2, 7]
        assert bass_pcs == expected

    def test_resolve_progression_notes_descending_bassline_no_voice_lead(self):
        specs = [ChordSpec(numeral=tok, duration_beats=4.0) for tok in self.PROGRESSION]
        req = GenerationRequest(
            key_center="C",
            scale_type="major",
            bpm=120,
            chords=specs,
            voice_lead=False,
        )
        resolved = resolve_progression_notes(req)
        assert len(resolved.resolved_metadata) == 8
        bass_pcs = [c["midi"][0] % 12 for c in resolved.resolved_metadata]
        expected = [0, 11, 9, 7, 5, 4, 2, 7]
        assert bass_pcs == expected
        assert len(resolved.notes) > 0

    def test_resolve_progression_notes_descending_bassline_with_voice_lead(self):
        specs = [ChordSpec(numeral=tok, duration_beats=4.0) for tok in self.PROGRESSION]
        req = GenerationRequest(
            key_center="C",
            scale_type="major",
            bpm=120,
            chords=specs,
            voice_lead=True,
        )
        resolved = resolve_progression_notes(req)
        assert len(resolved.resolved_metadata) == 8

        # Explicit slash chords MUST preserve their specified bass note
        assert resolved.resolved_metadata[1]["midi"][0] % 12 == 11  # V/7 has B in bass
        assert resolved.resolved_metadata[3]["midi"][0] % 12 == 7   # I/5 has G in bass
        assert resolved.resolved_metadata[5]["midi"][0] % 12 == 4   # I/3 has E in bass

        # Timed notes should cover 32 beats (8 chords * 4 beats)
        assert resolved.total_beats == 32.0
        assert len(resolved.notes) > 0

    def test_resolve_progression_notes_with_drop2_voicing(self):
        specs = [
            ChordSpec(numeral=tok, duration_beats=4.0, voicing="drop2")
            for tok in self.PROGRESSION
        ]
        req = GenerationRequest(
            key_center="C",
            scale_type="major",
            bpm=120,
            chords=specs,
            voice_lead=True,
        )
        resolved = resolve_progression_notes(req)
        assert len(resolved.resolved_metadata) == 8
        # Slash chords must still anchor their bass notes under drop2
        assert resolved.resolved_metadata[1]["midi"][0] % 12 == 11  # V/7 -> B
        assert resolved.resolved_metadata[3]["midi"][0] % 12 == 7   # I/5 -> G
        assert resolved.resolved_metadata[5]["midi"][0] % 12 == 4   # I/3 -> E
