"""
The .mid writer and the live path (Ableton, streaming, Max for Live, songs)
must voice every chord identically. They once carried separate copies of the
chord-resolution loop with different max_octave clamps, so the same request
produced different chords in Ableton than in the exported file.
"""

import itertools

import pytest

from midison.events import resolve_progression_notes
from midison.midi_writer import ChordSpec, GenerationRequest, generate

NUMERALS = ["I", "vi", "IV", "V7", "ii7", "Imaj9", "V13", "iii", "V/vi", "bVII"]


@pytest.mark.parametrize(
    ("voice_lead", "max_octave", "octave", "rootless"),
    list(itertools.product([False, True], [2, 3, 4, 5], [2, 3, 4, 5], [False, True])),
)
def test_file_and_live_paths_voice_chords_identically(
    tmp_path, voice_lead, max_octave, octave, rootless
):
    request = GenerationRequest(
        key_center="C",
        scale_type="major",
        bpm=120,
        chords=[
            ChordSpec(n, 4, rootless=rootless and n.endswith(("7", "9", "13")))
            for n in NUMERALS
        ],
        voice_lead=voice_lead,
        octave=octave,
        max_octave=max_octave,
        seed=1,
        filename="parity",
    )
    file_meta = generate(request, tmp_path).resolved
    live_meta = resolve_progression_notes(request).resolved_metadata
    assert file_meta == live_meta


def test_live_path_keeps_voicing_order_under_clamp():
    # V13 at octave 4 exceeds max_octave=5's ceiling. The whole chord must
    # shift as a unit; folding single notes down scrambles the voicing.
    request = GenerationRequest(
        key_center="C",
        scale_type="major",
        bpm=120,
        chords=[ChordSpec("V13", 4)],
        octave=4,
    )
    midi = resolve_progression_notes(request).resolved_metadata[0]["midi"]
    assert midi == sorted(midi)
