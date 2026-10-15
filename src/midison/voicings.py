"""
Voicing transformations.

Each function takes a list of MIDI note numbers in close, root-position order
(root, 3rd, 5th, 7th, 9th, ...) and returns a re-voiced list. The number of
notes is preserved unless explicitly noted (rootless drops the root).

Voicing definitions follow standard jazz pedagogy:
- close:      no transformation; notes within an octave above the root.
- drop2:      drop the 2nd-from-top voice down an octave.
- drop3:      drop the 3rd-from-top voice down an octave.
- drop2and4:  drop the 2nd and 4th from top down an octave each.
- spread:     wide voicing — root in bass, upper structure in close position
              roughly an octave above. Useful for piano LH/RH separation.
- rootless:   omit the root. Common in jazz piano (bassist plays the root).
              For 7th/9th chords, the 3rd is the lowest note.
"""

from __future__ import annotations

VoicingName = str  # one of: 'close', 'drop2', 'drop3', 'drop2and4', 'spread', 'rootless'


def apply_voicing(
    notes: list[int],
    voicing: VoicingName,
    bass_note: int | None = None,
    bass_pc: int | None = None,
) -> list[int]:
    """Dispatch to the named voicing transformation.

    If bass_note or bass_pc is provided (explicit slash chord bass override),
    anchors that bass pitch class at the bottom of the voicing.
    """
    notes = sorted(notes)
    if voicing == "close":
        result = _close(notes)
    elif voicing == "drop2":
        result = _drop_n_from_top(notes, [2])
    elif voicing == "drop3":
        result = _drop_n_from_top(notes, [3])
    elif voicing == "drop2and4":
        result = _drop_n_from_top(notes, [2, 4])
    elif voicing == "spread":
        result = _spread(notes)
    elif voicing == "rootless":
        result = _rootless(notes)
    else:
        raise ValueError(f"Unknown voicing: {voicing!r}")

    target_pc = bass_pc if bass_pc is not None else (bass_note % 12 if bass_note is not None else None)
    if target_pc is not None:
        result = _anchor_bass(result, target_pc)

    return result


def _anchor_bass(notes: list[int], bass_pc: int) -> list[int]:
    """Ensure that the note with pitch class bass_pc is the lowest note in notes."""
    notes = sorted(notes)
    if not notes:
        return notes
    if notes[0] % 12 == bass_pc:
        return notes

    candidates = [n for n in notes if n % 12 == bass_pc]
    if candidates:
        chosen = min(candidates)
        other_notes = [n for n in notes if n != chosen or candidates.count(n) > 1]
        other_lowest = min(other_notes) if other_notes else chosen
        shifted = chosen
        while shifted >= other_lowest:
            shifted -= 12
        new_notes = list(notes)
        new_notes.remove(chosen)
        new_notes.append(shifted)
        return sorted(new_notes)
    else:
        lowest = notes[0]
        bass_val = lowest - ((lowest - bass_pc) % 12)
        if bass_val == lowest:
            bass_val -= 12
        while bass_val >= lowest:
            bass_val -= 12
        return sorted([bass_val] + notes)


def _close(notes: list[int]) -> list[int]:
    """
    Force notes into close position above the root: each upper voice within
    an octave of the one below it. Useful when extensions have pushed notes
    into a wider span than intended.
    """
    if not notes:
        return notes
    out = [notes[0]]
    for n in notes[1:]:
        prev = out[-1]
        while n - prev > 12:
            n -= 12
        while n <= prev:
            n += 12
        out.append(n)
    return out


def _drop_n_from_top(notes: list[int], positions: list[int]) -> list[int]:
    """
    Drop the Nth-from-top voices down an octave. positions is 1-indexed:
    position 1 = topmost note, 2 = second from top, etc.
    """
    if len(notes) < 2:
        return notes
    notes = list(notes)
    for pos in positions:
        idx = len(notes) - pos
        if 0 <= idx < len(notes):
            notes[idx] -= 12
    return sorted(notes)


def _spread(notes: list[int]) -> list[int]:
    """
    Wide voicing: keep the root in the bass, then place the rest as an
    upper structure roughly an octave above. Drop the root an octave from
    its close-position location to open up the gap.
    """
    if len(notes) < 2:
        return notes
    notes = list(notes)
    notes[0] -= 12
    return sorted(notes)


def _rootless(notes: list[int]) -> list[int]:
    """
    Omit the root entirely. The next-lowest chord tone (typically the 3rd)
    becomes the bass.
    """
    if len(notes) <= 1:
        return notes
    return notes[1:]
