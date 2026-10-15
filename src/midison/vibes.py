"""
Emotion & Genre Vibe Translation Engine for Midison.

Translates high-level emotional intentions and genre aesthetics into
musically coherent Roman numeral chord progressions, suggested voicings,
groove patterns, keys, scales, and BPMs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class VibeDefinition:
    """A curated musical vibe mapping emotion/genre to harmonic and performance specs."""

    vibe_id: str  # e.g. 'melancholy_city_pop'
    title: str  # 'Melancholy City Pop'
    mood_tags: list[str]  # ['melancholy', 'japanese', 'city pop', 'nostalgic', 'anime']
    description: str
    suggested_key: str  # 'F'
    suggested_scale: str  # 'major'
    suggested_bpm: int  # 116
    progression: str  # 'IVmaj7 - V7 - iii7 - vi'
    suggested_voicing: str  # 'drop2'
    suggested_groove: str  # 'charleston'
    suggested_octave: int  # 3
    harmonic_context: str  # Explanation of why this harmonic choice creates the vibe


class VibeNotFoundError(KeyError, ValueError):
    """Raised when a requested vibe_id is not found in the catalog."""


_VIBES_CATALOG: list[VibeDefinition] = [
    VibeDefinition(
        vibe_id="melancholy_city_pop",
        title="Melancholy City Pop",
        mood_tags=["melancholy", "japanese", "city pop", "nostalgic", "anime", "80s", "bittersweet"],
        description="Nostalgic 80s Tokyo dusk drive aesthetic with lush extensions and bittersweet descending cadences.",
        suggested_key="F",
        suggested_scale="major",
        suggested_bpm=116,
        progression="IVmaj7 - V7 - iii7 - vi",
        suggested_voicing="drop2",
        suggested_groove="charleston",
        suggested_octave=3,
        harmonic_context=(
            "The iconic Japanese Royal Road (Oudou) progression begins on the IVmaj7 subdominant, "
            "generating floating, bittersweet yearning before stepping down through the minor mediant iii7 to vi."
        ),
    ),
    VibeDefinition(
        vibe_id="dreamy_lofi_nostalgia",
        title="Dreamy Lo-Fi Nostalgia",
        mood_tags=["lofi", "nostalgia", "dreamy", "chill", "tape", "study", "vintage", "cozy"],
        description="Warm tape-saturated keys with bittersweet minor plagal resolution for reflective studying.",
        suggested_key="Eb",
        suggested_scale="major",
        suggested_bpm=78,
        progression="Imaj9 - iv9",
        suggested_voicing="spread",
        suggested_groove="strum",
        suggested_octave=3,
        harmonic_context=(
            "The iv9 chord is borrowed from the parallel minor (Aeolian mode), creating a poignant minor "
            "plagal cadence that tugs at nostalgic longing and vintage warmth."
        ),
    ),
    VibeDefinition(
        vibe_id="dark_cinematic_tension",
        title="Dark Cinematic Tension",
        mood_tags=["dark", "cinematic", "tension", "phrygian", "suspense", "dramatic", "trailer", "ominous"],
        description="Unsettling psychological thriller tension and ominous dread built on Phrygian half-step shifts.",
        suggested_key="D",
        suggested_scale="minor",
        suggested_bpm=90,
        progression="i - bII - vii°7 - i",
        suggested_voicing="close",
        suggested_groove="block",
        suggested_octave=3,
        harmonic_context=(
            "The Neapolitan / Phrygian bII triad brings visceral danger and suspense, while the leading-tone "
            "diminished seventh vii°7 ratchets up harmonic claustrophobia before collapsing to the minor tonic."
        ),
    ),
    VibeDefinition(
        vibe_id="euphoric_neo_soul",
        title="Euphoric Neo-Soul",
        mood_tags=["neo-soul", "soul", "r&b", "euphoric", "warm", "jazzy", "lush", "gospel"],
        description="Warm, velvety Sunday afternoon neo-soul groove rich with colorful upper extensions.",
        suggested_key="Db",
        suggested_scale="major",
        suggested_bpm=88,
        progression="ii9 - V13 - Imaj9",
        suggested_voicing="drop2",
        suggested_groove="charleston",
        suggested_octave=3,
        harmonic_context=(
            "Extended 9th and 13th color tones across the classic jazz ii-V-I turnaround soften dominant tension "
            "into effortless, glowing harmonic warmth."
        ),
    ),
    VibeDefinition(
        vibe_id="indie_sunshine_anthem",
        title="Indie Sunshine Anthem",
        mood_tags=["indie", "sunshine", "anthem", "upbeat", "summer", "pop", "festival", "bright", "happy"],
        description="Driving, euphoric festival pop-rock anthem with unstoppable singalong momentum.",
        suggested_key="G",
        suggested_scale="major",
        suggested_bpm=124,
        progression="I - V - vi - IV",
        suggested_voicing="close",
        suggested_groove="four_on_floor",
        suggested_octave=3,
        harmonic_context=(
            "The quintessential 4-chord pop progression balances radiant major uplift against the reflective "
            "submediant vi before driving home via IV."
        ),
    ),
    VibeDefinition(
        vibe_id="sad_girl_autumn",
        title="Sad Girl Autumn",
        mood_tags=["sad", "autumn", "melancholy", "acoustic", "singer-songwriter", "emotional", "folk"],
        description="Intimate confessional songwriting drenched in rainy autumn nostalgia.",
        suggested_key="C",
        suggested_scale="major",
        suggested_bpm=72,
        progression="vi - IV - I - V",
        suggested_voicing="spread",
        suggested_groove="strum",
        suggested_octave=3,
        harmonic_context=(
            "Starting on the minor submediant vi grounds the progression in vulnerability and sorrow, giving "
            "the subsequent major tonic a fleeting, reflective quality."
        ),
    ),
    VibeDefinition(
        vibe_id="funky_dorian_groove",
        title="Funky Dorian Groove",
        mood_tags=["funky", "dorian", "groove", "funk", "disco", "danceable", "70s", "vamp"],
        description="Hypnotic two-chord modal funk dance vamp dripping with late-night swagger.",
        suggested_key="D",
        suggested_scale="dorian",
        suggested_bpm=112,
        progression="i9 - IV9",
        suggested_voicing="drop2",
        suggested_groove="comp_syncopated",
        suggested_octave=3,
        harmonic_context=(
            "The major IV9 chord highlights the Dorian mode's signature natural 6th, avoiding the heavy gloom "
            "of natural minor in favor of breezy, danceable funk momentum."
        ),
    ),
    VibeDefinition(
        vibe_id="dark_rnb_midnight",
        title="Dark R&B Midnight",
        mood_tags=["dark", "rnb", "midnight", "moody", "trap", "sensual", "slow jam"],
        description="Moody, late-night atmospheric R&B with altered dominants and simmering romantic tension.",
        suggested_key="C",
        suggested_scale="minor",
        suggested_bpm=68,
        progression="i7 - iv7 - bVImaj7 - V7b9",
        suggested_voicing="drop2",
        suggested_groove="charleston",
        suggested_octave=3,
        harmonic_context=(
            "Minor plagal motion toward the dramatic bVImaj7 and high-tension V7b9 creates an intoxicating "
            "atmosphere of midnight longing and unresolved desire."
        ),
    ),
    VibeDefinition(
        vibe_id="gospel_uplift",
        title="Gospel Uplift",
        mood_tags=["gospel", "uplift", "church", "spiritual", "joyful", "soulful", "praise", "hymn"],
        description="Joyful Sunday morning church walk with moving bass and chromatic minor plagal release.",
        suggested_key="Ab",
        suggested_scale="major",
        suggested_bpm=96,
        progression="I - I7/3 - IV - iv - I/5 - V7 - I",
        suggested_voicing="close",
        suggested_groove="charleston",
        suggested_octave=3,
        harmonic_context=(
            "The classic gospel bass walk climbs 1 -> 3 -> 4 through first inversion I7/3, touches the borrowed "
            "minor plagal iv, and lands on a second-inversion cadence (I/5 -> V7 -> I) for soaring release."
        ),
    ),
    VibeDefinition(
        vibe_id="vaporwave_mall",
        title="Vaporwave Mall",
        mood_tags=["vaporwave", "mall", "80s", "retro", "aesthetic", "smooth", "nostalgic", "chill"],
        description="Dreamy slowed-down elevator jazz drifting through a neon 1989 shopping mall atrium.",
        suggested_key="Bb",
        suggested_scale="major",
        suggested_bpm=84,
        progression="IVmaj7 - V6 - iii7 - vi7",
        suggested_voicing="spread",
        suggested_groove="charleston",
        suggested_octave=3,
        harmonic_context=(
            "The first-inversion V6 passing chord creates an elegant stepwise descending bassline connecting "
            "IVmaj7 to iii7, evoking hazy consumer nostalgia and effortless luxury."
        ),
    ),
    VibeDefinition(
        vibe_id="cyberpunk_dystopia",
        title="Cyberpunk Dystopia",
        mood_tags=["cyberpunk", "dystopian", "industrial", "dark", "sci-fi", "synthetic", "relentless"],
        description="Gritty neon-drenched dystopia driven by relentless Aeolian natural minor power movements.",
        suggested_key="E",
        suggested_scale="minor",
        suggested_bpm=128,
        progression="i - bVI - bIII - bVII",
        suggested_voicing="close",
        suggested_groove="four_on_floor",
        suggested_octave=2,
        harmonic_context=(
            "Heavy root movement across the natural minor scale's flattened degrees (bVI, bIII, bVII) conveys "
            "mechanized force and grim cyberpunk momentum."
        ),
    ),
    VibeDefinition(
        vibe_id="bossa_sunset",
        title="Bossa Sunset",
        mood_tags=["bossa", "latin", "sunset", "brazilian", "beach", "warm", "jazz", "acoustic"],
        description="Gentle Rio seaside breeze with warm syncopated acoustic jazz harmonies.",
        suggested_key="F",
        suggested_scale="major",
        suggested_bpm=130,
        progression="Imaj7 - VI7 - ii7 - V7",
        suggested_voicing="drop2",
        suggested_groove="bossa",
        suggested_octave=3,
        harmonic_context=(
            "The secondary dominant VI7 (functioning as V7/ii) injects chromatic sparkle and momentum into "
            "the circle-of-fifths turnaround."
        ),
    ),
]

_VIBES_BY_ID: dict[str, VibeDefinition] = {v.vibe_id: v for v in _VIBES_CATALOG}


def list_all_vibes() -> list[VibeDefinition]:
    """Return a list of all curated vibes in the catalog."""
    return list(_VIBES_CATALOG)


def get_vibe(vibe_id: str) -> VibeDefinition:
    """
    Retrieve a vibe by its identifier.

    Raises VibeNotFoundError if the vibe_id is not found.
    """
    normalized_id = vibe_id.strip().lower()
    vibe = _VIBES_BY_ID.get(normalized_id)
    if vibe is None:
        valid_ids = sorted(_VIBES_BY_ID.keys())
        raise VibeNotFoundError(f"Unknown vibe_id: {vibe_id!r}. Valid options: {valid_ids}")
    return vibe


def find_vibes(query: str) -> list[VibeDefinition]:
    """
    Search and rank vibes matching the given query across tags, title, description, and vibe_id.

    Returns vibes sorted by relevance score in descending order.
    Returns an empty list if query is empty or no vibes match.
    """
    q = query.strip().lower()
    if not q:
        return []

    tokens = [tok for tok in re.split(r"[\s,\-_/]+", q) if tok]

    scored: list[tuple[float, VibeDefinition]] = []
    for vibe in _VIBES_CATALOG:
        score = 0.0
        v_id = vibe.vibe_id.lower()
        v_title = vibe.title.lower()
        v_desc = vibe.description.lower()
        v_harmonic = vibe.harmonic_context.lower()
        v_tags = [t.lower() for t in vibe.mood_tags]

        # 1. Exact full-query matches
        if q == v_id or q == v_id.replace("_", " "):
            score += 150.0
        elif q == v_title:
            score += 120.0
        elif q in v_tags:
            score += 100.0

        # 2. Substring matches for entire query
        if q in v_id or q.replace(" ", "_") in v_id:
            score += 60.0
        if q in v_title:
            score += 50.0
        if any(q in t for t in v_tags):
            score += 40.0
        if q in v_desc:
            score += 30.0
        if q in v_harmonic:
            score += 15.0

        # 3. Individual token matches
        for t in tokens:
            if not t:
                continue
            # Token in ID
            if t == v_id:
                score += 50.0
            elif t in v_id:
                score += 20.0

            # Token in Title
            title_words = [w for w in re.split(r"[\s,\-_]+", v_title) if w]
            if t in title_words:
                score += 30.0
            elif t in v_title:
                score += 15.0

            # Token in Tags
            if t in v_tags:
                score += 35.0
            elif any(t in tag for tag in v_tags):
                score += 20.0

            # Token in Description
            desc_words = [w for w in re.split(r"[\s,\-_.:;!?()]+", v_desc) if w]
            if t in desc_words:
                score += 10.0
            elif t in v_desc:
                score += 5.0

            # Token in Harmonic Context
            harmonic_words = [w for w in re.split(r"[\s,\-_.:;!?()]+", v_harmonic) if w]
            if t in harmonic_words:
                score += 5.0
            elif t in v_harmonic:
                score += 2.0

        if score > 0.0:
            scored.append((score, vibe))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [vibe for _, vibe in scored]
