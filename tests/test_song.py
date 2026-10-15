"""
Unit tests for multi-section song architecture generator and Ableton scene sync.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from midison.ableton import AbletonClient
from midison.song import (
    GeneratedSongSection,
    SectionPlan,
    SongArrangement,
    SongTemplate,
    generate_song_arrangement,
    get_song_template,
    inject_song_into_ableton,
    list_song_templates,
)


def test_list_song_templates():
    templates = list_song_templates()
    assert len(templates) >= 5
    ids = {t.template_id for t in templates}
    expected_ids = {"neo_soul", "pop_anthem", "lofi_chill", "cinematic_minor", "city_pop"}
    assert expected_ids.issubset(ids)


def test_get_song_template():
    tmpl = get_song_template("neo_soul")
    assert isinstance(tmpl, SongTemplate)
    assert tmpl.template_id == "neo_soul"
    assert len(tmpl.sections) == 4
    section_names = [s.name for s in tmpl.sections]
    assert section_names == ["verse", "pre_chorus", "chorus", "bridge"]

    with pytest.raises(ValueError, match="Unknown template ID 'invalid_id'"):
        get_song_template("invalid_id")


@pytest.mark.parametrize(
    "template_id",
    ["neo_soul", "pop_anthem", "lofi_chill", "cinematic_minor", "city_pop"],
)
def test_all_five_templates_generate_valid_notes_and_durations(template_id: str):
    arrangement = generate_song_arrangement(template_id)

    assert isinstance(arrangement, SongArrangement)
    assert arrangement.template.template_id == template_id
    assert arrangement.key_center == arrangement.template.recommended_key
    assert arrangement.scale_type == arrangement.template.recommended_scale
    assert arrangement.bpm == arrangement.template.recommended_bpm

    assert len(arrangement.sections) == 4
    expected_names = ["verse", "pre_chorus", "chorus", "bridge"]
    actual_names = [s.section_plan.name for s in arrangement.sections]
    assert actual_names == expected_names

    cumulative_beats = 0.0
    for sec in arrangement.sections:
        assert isinstance(sec, GeneratedSongSection)
        assert sec.notes_count > 0, f"Section {sec.section_plan.name} in {template_id} generated 0 notes"
        assert sec.total_beats > 0.0, f"Section {sec.section_plan.name} in {template_id} has <= 0 total beats"
        # Each chord defaults to 4.0 beats, so section total beats must be a multiple of chord count
        num_chords = len(sec.generation_request.chords)
        assert sec.total_beats == num_chords * 4.0
        cumulative_beats += sec.total_beats

    assert arrangement.total_beats == cumulative_beats
    assert arrangement.total_beats > 0.0


def test_custom_key_bpm_scale_overrides():
    arrangement = generate_song_arrangement(
        "pop_anthem",
        key_center="F#",
        scale_type="major",
        bpm=140,
    )

    assert arrangement.key_center == "F#"
    assert arrangement.scale_type == "major"
    assert arrangement.bpm == 140

    for sec in arrangement.sections:
        assert sec.generation_request.key_center == "F#"
        assert sec.generation_request.scale_type == "major"
        assert sec.generation_request.bpm == 140
        assert sec.notes_count > 0
        assert sec.total_beats > 0.0


def test_generate_song_arrangement_with_output_dir(tmp_path: Path):
    arrangement = generate_song_arrangement("city_pop", output_dir=tmp_path)

    assert len(arrangement.sections) == 4
    for idx, sec in enumerate(arrangement.sections):
        assert sec.midi_path is not None
        assert sec.midi_path.exists()
        assert sec.midi_path.suffix == ".mid"
        assert sec.midi_path.stat().st_size > 0

        # Check sidecar markdown
        sidecar_path = sec.midi_path.with_suffix(".md")
        assert sidecar_path.exists()
        assert sidecar_path.stat().st_size > 0

        expected_filename = f"city_pop_{idx:02d}_{sec.section_plan.name}.mid"
        assert sec.midi_path.name == expected_filename


def test_inject_song_into_ableton_with_mock_client():
    arrangement = generate_song_arrangement("cinematic_minor")
    mock_client = MagicMock(spec=AbletonClient)

    # Configure mock return value for inject_progression
    def mock_inject(req, track_index=0, clip_index=0, fire=False, sync_session=False):
        return {
            "status": "success",
            "track_index": track_index,
            "clip_index": clip_index,
            "total_beats": 16.0,
            "notes_count": 16,
            "chords": [c.numeral for c in req.chords],
            "fired": fire,
            "session_synced": sync_session,
        }

    mock_client.inject_progression.side_effect = mock_inject

    results = inject_song_into_ableton(arrangement, mock_client, track_index=2)

    assert len(results) == 4
    assert mock_client.inject_progression.call_count == 4

    expected_sections = ["verse", "pre_chorus", "chorus", "bridge"]
    for scene_idx, res in enumerate(results):
        assert res["status"] == "success"
        assert res["track_index"] == 2
        assert res["clip_index"] == scene_idx  # Scene 0, 1, 2, 3
        assert res["section_name"] == expected_sections[scene_idx]
        assert res["section_index"] == scene_idx

        # Verify call args
        call_args = mock_client.inject_progression.call_args_list[scene_idx]
        assert call_args.kwargs["track_index"] == 2
        assert call_args.kwargs["clip_index"] == scene_idx
        assert call_args.kwargs["fire"] is False
        assert call_args.kwargs["sync_session"] is False


def test_inject_song_into_ableton_with_live_client_osc_mock():
    mock_udp = MagicMock()
    arrangement = generate_song_arrangement("lofi_chill")

    with patch("pythonosc.udp_client.SimpleUDPClient", return_value=mock_udp):
        client = AbletonClient()
        results = inject_song_into_ableton(arrangement, client, track_index=0)

    assert len(results) == 4
    for scene_idx, res in enumerate(results):
        assert res["status"] == "success"
        assert res["track_index"] == 0
        assert res["clip_index"] == scene_idx
        assert res["notes_count"] > 0
        assert res["total_beats"] > 0

    # Ensure create_clip and note messages were sent for all 4 clips
    create_clip_calls = [
        c for c in mock_udp.send_message.call_args_list
        if c[0][0] == "/live/clip_slot/create_clip"
    ]
    assert len(create_clip_calls) == 4
    for scene_idx, c in enumerate(create_clip_calls):
        assert c[0][1][0] == 0  # track_index
        assert c[0][1][1] == scene_idx  # clip_index (scene)


def test_parse_section_chords_error_handling():
    # Empty progression
    empty_plan = SectionPlan(name="broken", progression="")
    with pytest.raises(ValueError, match="Progression string in section 'broken' is empty"):
        from midison.song import _parse_section_chords
        _parse_section_chords(empty_plan)

    # Invalid Roman numeral
    invalid_plan = SectionPlan(name="bad_numeral", progression="I - XYZ - V")
    with pytest.raises(ValueError, match="Invalid Roman numeral 'XYZ' in section 'bad_numeral'"):
        from midison.song import _parse_section_chords
        _parse_section_chords(invalid_plan)
