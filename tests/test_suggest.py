"""Tests for midison.suggest: Next chord recommender and harmonic navigator."""

from __future__ import annotations

import pytest

from midison.suggest import (
    VALID_PATHWAYS,
    ChordSuggestion,
    suggest_next_chords,
)
from midison.theory import parse_roman_numeral


def _assert_valid_suggestions(suggestions: list[ChordSuggestion], expected_min: int = 4, expected_max: int = 6) -> None:
    """Helper to verify common invariants across any suggestion list."""
    assert expected_min <= len(suggestions) <= expected_max, (
        f"Expected between {expected_min} and {expected_max} suggestions, got {len(suggestions)}"
    )
    for s in suggestions:
        assert isinstance(s, ChordSuggestion)
        assert isinstance(s.numeral, str) and len(s.numeral.strip()) > 0
        assert isinstance(s.chord_name, str) and len(s.chord_name.strip()) > 0
        assert s.pathway in VALID_PATHWAYS, f"Invalid pathway '{s.pathway}'"
        assert isinstance(s.explanation, str) and len(s.explanation.strip()) > 0
        assert isinstance(s.mood_descriptor, str) and len(s.mood_descriptor.strip()) > 0
        # Ensure the suggested numeral is valid syntax
        parse_roman_numeral(s.numeral)


class TestSuggestTonic:
    """Test recommendations after tonic chords (I, Imaj7)."""

    def test_after_tonic_I(self):
        suggestions = suggest_next_chords("I", key_center="C", scale_type="major")
        _assert_valid_suggestions(suggestions)

        numerals = [s.numeral for s in suggestions]
        pathways = {s.pathway for s in suggestions}

        assert "IVmaj7" in numerals
        assert "vi7" in numerals

        # Should span multiple distinct pathways
        assert len(pathways) >= 4
        assert "diatonic" in pathways
        assert "secondary_dominant" in pathways
        assert "modal_mixture" in pathways
        assert "tritone_sub" in pathways

        # Check specific expected suggestions in C major
        chord_map = {s.numeral: s.chord_name for s in suggestions}
        assert "IVmaj7" in chord_map
        assert chord_map["IVmaj7"] == "Fmaj7"
        assert "vi7" in chord_map
        assert chord_map["vi7"] == "Am7"
        assert "iv7" in chord_map
        assert chord_map["iv7"] == "Fm7"
        assert "bII7" in chord_map
        assert chord_map["bII7"] == "Db7"

    def test_after_tonic_Imaj7(self):
        suggestions = suggest_next_chords("Imaj7", key_center="C", scale_type="major")
        _assert_valid_suggestions(suggestions)

        numerals = [s.numeral for s in suggestions]
        assert "Imaj7" not in numerals  # Should not recommend the same chord

    def test_after_tonic_in_g_major(self):
        suggestions = suggest_next_chords("I", key_center="G", scale_type="major")
        _assert_valid_suggestions(suggestions)

        chord_map = {s.numeral: s.chord_name for s in suggestions}
        assert chord_map.get("IVmaj7") == "Cmaj7"
        assert chord_map.get("vi7") == "Em7"
        assert chord_map.get("iv7") == "Cm7"


class TestSuggestSubdominant:
    """Test recommendations after subdominant chords (ii7, IV)."""

    def test_after_ii7(self):
        suggestions = suggest_next_chords("ii7", key_center="C", scale_type="major")
        _assert_valid_suggestions(suggestions)

        numerals = [s.numeral for s in suggestions]
        pathways = {s.pathway for s in suggestions}

        assert "diatonic" in pathways
        assert "secondary_dominant" in pathways
        assert "modal_mixture" in pathways

        # Suggests dominant resolution (V7 or V13)
        assert "V7" in numerals or "V13" in numerals
        chord_map = {s.numeral: s.chord_name for s in suggestions}
        if "V7" in chord_map:
            assert chord_map["V7"] == "G7"
        if "V13" in chord_map:
            assert chord_map["V13"] == "G13"

        # Secondary dominant V7/V -> D7
        assert "V7/V" in chord_map
        assert chord_map["V7/V"] == "D7"

        # Minor plagal borrow iv7 -> Fm7
        assert "iv7" in chord_map
        assert chord_map["iv7"] == "Fm7"

    def test_after_IV(self):
        suggestions = suggest_next_chords("IV", key_center="C", scale_type="major")
        _assert_valid_suggestions(suggestions)

        numerals = [s.numeral for s in suggestions]
        pathways = {s.pathway for s in suggestions}

        # Between IV and V, suggests #IVdim7
        assert "#IVdim7" in numerals
        assert "passing" in pathways
        chord_map = {s.numeral: s.chord_name for s in suggestions}
        assert chord_map["#IVdim7"] == "F#dim7"
        assert chord_map["V7"] == "G7"


class TestSuggestDominant:
    """Test recommendations after dominant chords (V7, V13)."""

    def test_after_V7(self):
        suggestions = suggest_next_chords("V7", key_center="C", scale_type="major")
        _assert_valid_suggestions(suggestions)

        numerals = [s.numeral for s in suggestions]
        pathways = {s.pathway for s in suggestions}

        assert "Imaj7" in numerals
        assert "vi7" in numerals

        assert "diatonic" in pathways
        assert "secondary_dominant" in pathways
        assert "modal_mixture" in pathways
        assert "tritone_sub" in pathways

        chord_map = {s.numeral: s.chord_name for s in suggestions}
        # Authentic cadential resolution to Imaj7
        assert "Imaj7" in chord_map
        assert chord_map["Imaj7"] == "Cmaj7"

        # Deceptive cadential resolution to vi7
        assert "vi7" in chord_map
        assert chord_map["vi7"] == "Am7"

        # Secondary dominant chain V7/vi -> E7
        assert "V7/vi" in chord_map
        assert chord_map["V7/vi"] == "E7"

        # Modal mixture borrow bVImaj7 -> Abmaj7
        assert "bVImaj7" in chord_map
        assert chord_map["bVImaj7"] == "Abmaj7"

        # Tritone substitution bII7 -> Db7
        assert "bII7" in chord_map
        assert chord_map["bII7"] == "Db7"

    def test_after_V13(self):
        suggestions = suggest_next_chords("V13", key_center="C", scale_type="major")
        _assert_valid_suggestions(suggestions)

        numerals = [s.numeral for s in suggestions]
        assert "Imaj7" in numerals


class TestSuggestMinorKeys:
    """Test recommendations in minor keys (after i7, iv7, v7)."""

    def test_after_minor_tonic_i7(self):
        suggestions = suggest_next_chords("i7", key_center="A", scale_type="minor")
        _assert_valid_suggestions(suggestions)

        numerals = [s.numeral for s in suggestions]
        pathways = {s.pathway for s in suggestions}

        assert "iv7" in numerals
        assert "V7" in numerals

        assert "diatonic" in pathways
        assert "modal_mixture" in pathways
        assert "tritone_sub" in pathways

        chord_map = {s.numeral: s.chord_name for s in suggestions}
        # Diatonic iv7 -> Dm7
        assert "iv7" in chord_map
        assert chord_map["iv7"] == "Dm7"

        # Harmonic dominant V7 -> E7
        assert "V7" in chord_map
        assert chord_map["V7"] == "E7"

        # Dorian borrowed IV7 -> D7
        assert "IV7" in chord_map
        assert chord_map["IV7"] == "D7"

        # Neapolitan / Tritone sub bII7 -> Bb7
        assert "bII7" in chord_map
        assert chord_map["bII7"] == "Bb7"

    def test_after_minor_subdominant_iv7(self):
        suggestions = suggest_next_chords("iv7", key_center="A", scale_type="minor")
        _assert_valid_suggestions(suggestions)

        chord_map = {s.numeral: s.chord_name for s in suggestions}
        # Harmonic minor dominant V7 -> E7
        assert "V7" in chord_map
        assert chord_map["V7"] == "E7"

        # Aeolian natural minor dominant v7 -> Em7
        assert "v7" in chord_map
        assert chord_map["v7"] == "Em7"

        # Secondary dominant V7/V -> B7
        assert "V7/V" in chord_map
        assert chord_map["V7/V"] == "B7"

        # Passing diminished #iv°7 -> D#dim7
        assert "#iv°7" in chord_map
        assert chord_map["#iv°7"] == "D#dim7"

    def test_after_minor_dominant_v7(self):
        suggestions = suggest_next_chords("v7", key_center="A", scale_type="minor")
        _assert_valid_suggestions(suggestions)

        chord_map = {s.numeral: s.chord_name for s in suggestions}
        # Authentic minor resolution to i7 -> Am7
        assert "i7" in chord_map
        assert chord_map["i7"] == "Am7"

        # Deceptive resolution in minor to VImaj7 -> Fmaj7
        assert "VImaj7" in chord_map
        assert chord_map["VImaj7"] == "Fmaj7"

        # Tritone substitution bII7 -> Bb7
        assert "bII7" in chord_map
        assert chord_map["bII7"] == "Bb7"


class TestProgressionParsing:
    """Test progression parsing and edge cases."""

    def test_multi_chord_progression(self):
        # In 'ii7 - V7', recommender inspects V7
        suggestions = suggest_next_chords("ii7 - V7", key_center="C", scale_type="major")
        _assert_valid_suggestions(suggestions)
        numerals = [s.numeral for s in suggestions]
        assert "Imaj7" in numerals or "vi7" in numerals

    def test_progression_with_durations(self):
        # In 'ii7:2 - V7:2', recommender inspects V7
        suggestions = suggest_next_chords("ii7:2 - V7:2", key_center="C", scale_type="major")
        _assert_valid_suggestions(suggestions)
        numerals = [s.numeral for s in suggestions]
        assert "Imaj7" in numerals or "vi7" in numerals

    def test_empty_progression_raises(self):
        with pytest.raises(ValueError):
            suggest_next_chords("")

    def test_invalid_numeral_raises(self):
        with pytest.raises(ValueError):
            suggest_next_chords("ii7 - INVALID")
