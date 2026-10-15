"""Unit tests for the Emotion & Genre Vibe Translation Engine."""

from __future__ import annotations

import pytest

from midison.cli import parse_progression_string
from midison.events import resolve_progression_notes
from midison.midi_writer import GenerationRequest
from midison.vibes import (
    VibeDefinition,
    VibeNotFoundError,
    find_vibes,
    get_vibe,
    list_all_vibes,
)


class TestVibeCatalog:
    """Tests verifying the structure and completeness of the vibe catalog."""

    def test_list_all_vibes_contains_at_least_10(self):
        vibes = list_all_vibes()
        assert len(vibes) >= 10

    def test_required_vibes_exist(self):
        required_ids = [
            "melancholy_city_pop",
            "dreamy_lofi_nostalgia",
            "dark_cinematic_tension",
            "euphoric_neo_soul",
            "indie_sunshine_anthem",
            "sad_girl_autumn",
            "funky_dorian_groove",
            "dark_rnb_midnight",
            "gospel_uplift",
            "vaporwave_mall",
        ]
        vibes_dict = {v.vibe_id: v for v in list_all_vibes()}
        for vid in required_ids:
            assert vid in vibes_dict, f"Missing required vibe {vid}"

    def test_vibe_definitions_have_valid_fields(self):
        for v in list_all_vibes():
            assert isinstance(v, VibeDefinition)
            assert v.vibe_id and isinstance(v.vibe_id, str)
            assert v.title and isinstance(v.title, str)
            assert len(v.mood_tags) > 0 and all(isinstance(t, str) for t in v.mood_tags)
            assert v.description and isinstance(v.description, str)
            assert v.suggested_key and isinstance(v.suggested_key, str)
            assert v.suggested_scale and isinstance(v.suggested_scale, str)
            assert v.suggested_bpm > 0 and isinstance(v.suggested_bpm, int)
            assert v.progression and isinstance(v.progression, str)
            assert v.suggested_voicing and isinstance(v.suggested_voicing, str)
            assert v.suggested_groove and isinstance(v.suggested_groove, str)
            assert v.suggested_octave > 0 and isinstance(v.suggested_octave, int)
            assert v.harmonic_context and isinstance(v.harmonic_context, str)


class TestVibeLookup:
    """Tests for get_vibe exact and case-insensitive lookup."""

    def test_exact_vibe_id_lookup(self):
        vibe = get_vibe("melancholy_city_pop")
        assert vibe.vibe_id == "melancholy_city_pop"
        assert vibe.title == "Melancholy City Pop"
        assert "city pop" in vibe.mood_tags
        assert vibe.suggested_key == "F"
        assert vibe.suggested_bpm == 116

    def test_case_insensitive_lookup(self):
        vibe = get_vibe("Melancholy_City_Pop")
        assert vibe.vibe_id == "melancholy_city_pop"

    def test_unknown_vibe_raises_error(self):
        with pytest.raises((KeyError, ValueError, VibeNotFoundError)):
            get_vibe("nonexistent_vibe_name")


class TestVibeSearch:
    """Tests for find_vibes fuzzy/tag/description ranking search."""

    def test_empty_query_returns_empty_list(self):
        assert find_vibes("") == []
        assert find_vibes("   ") == []

    def test_city_pop_search(self):
        results = find_vibes("city pop")
        assert len(results) > 0
        assert results[0].vibe_id == "melancholy_city_pop"

    def test_lofi_search(self):
        results = find_vibes("lofi")
        assert len(results) > 0
        assert results[0].vibe_id == "dreamy_lofi_nostalgia"

    def test_dark_search(self):
        results = find_vibes("dark")
        result_ids = [v.vibe_id for v in results]
        assert "dark_cinematic_tension" in result_ids
        assert "dark_rnb_midnight" in result_ids
        # Both top results should be dark vibes
        assert results[0].vibe_id in ("dark_cinematic_tension", "dark_rnb_midnight")

    def test_soul_search(self):
        results = find_vibes("soul")
        result_ids = [v.vibe_id for v in results]
        assert "euphoric_neo_soul" in result_ids
        assert results[0].vibe_id == "euphoric_neo_soul"

    def test_japanese_tag_search(self):
        results = find_vibes("japanese")
        assert len(results) > 0
        assert results[0].vibe_id == "melancholy_city_pop"

    def test_nonexistent_query_returns_empty(self):
        assert find_vibes("completely_unrelated_nonsense_xyz123") == []


class TestVibeHarmonicResolution:
    """Tests ensuring every vibe's progression can be fully resolved into MIDI notes."""

    @pytest.mark.parametrize("vibe", list_all_vibes(), ids=lambda v: v.vibe_id)
    def test_vibe_resolves_to_valid_midi_notes(self, vibe: VibeDefinition):
        chords = parse_progression_string(
            vibe.progression,
            default_voicing=vibe.suggested_voicing,
            default_pattern=vibe.suggested_groove,
        )
        assert len(chords) > 0

        req = GenerationRequest(
            key_center=vibe.suggested_key,
            scale_type=vibe.suggested_scale,
            bpm=vibe.suggested_bpm,
            chords=chords,
            octave=vibe.suggested_octave,
        )

        resolved = resolve_progression_notes(req)
        assert len(resolved.notes) > 0
        assert resolved.total_beats > 0
        assert len(resolved.resolved_metadata) == len(chords)

        # Ensure all generated note pitches are valid MIDI numbers
        for note in resolved.notes:
            assert 0 <= note.pitch <= 127
            assert note.start_beat >= 0
            assert note.duration_beats > 0
            assert 1 <= note.velocity <= 127
