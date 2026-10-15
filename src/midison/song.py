"""
Multi-Section Song Architecture Generator with Ableton Live Scene Synchronization.

Provides curated multi-section song templates (Neo-Soul, Pop Anthem, Lo-Fi Chill,
Cinematic Minor, City Pop) across verse, pre-chorus, chorus, and bridge sections.
Supports automated voice leading, section-specific energy dynamics, MIDI generation,
and direct OSC synchronization into Ableton Live session scenes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from midison.events import resolve_progression_notes
from midison.midi_writer import ChordSpec, GenerationRequest, HumanizeSpec, generate
from midison.theory import parse_roman_numeral

if TYPE_CHECKING:
    from midison.ableton import AbletonClient


@dataclass
class SectionPlan:
    name: str                 # 'verse', 'pre_chorus', 'chorus', 'bridge', 'outro'
    progression: str          # Roman numeral progression string, e.g. 'ii7 - V7 - Imaj7'
    duration_beats_per_chord: float = 4.0
    voicing: str = "drop2"
    pattern: str = "block"
    energy_level: float = 0.5  # 0.0 to 1.0
    description: str = ""


@dataclass
class SongTemplate:
    template_id: str          # 'neo_soul', 'pop_anthem', 'lofi_chill', 'cinematic_minor', 'city_pop'
    name: str
    description: str
    recommended_bpm: int
    recommended_key: str
    recommended_scale: str
    sections: list[SectionPlan]


@dataclass
class GeneratedSongSection:
    section_plan: SectionPlan
    generation_request: GenerationRequest
    midi_path: Path | None = None
    notes_count: int = 0
    total_beats: float = 0.0


@dataclass
class SongArrangement:
    template: SongTemplate
    key_center: str
    scale_type: str
    bpm: int
    sections: list[GeneratedSongSection]
    total_beats: float


# ---------------------------------------------------------------------------
# Curated Song Templates
# ---------------------------------------------------------------------------

CURATED_TEMPLATES: dict[str, SongTemplate] = {
    "neo_soul": SongTemplate(
        template_id="neo_soul",
        name="Neo-Soul",
        description="Lush, jazzy neo-soul architecture featuring extended 9th and 13th harmonies with altered dominants.",
        recommended_bpm=78,
        recommended_key="Eb",
        recommended_scale="major",
        sections=[
            SectionPlan(
                name="verse",
                progression="ii9 - V13 - Imaj9 - Imaj7",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.4,
                description="Smooth ii-V-I foundation with 9th and 13th extensions",
            ),
            SectionPlan(
                name="pre_chorus",
                progression="IVmaj9 - iii7 - ii9 - V7b9",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.6,
                description="Stepwise descending cadence building tension with altered V7b9 dominant",
            ),
            SectionPlan(
                name="chorus",
                progression="Imaj9 - V7/vi - vi7 - ii9 - V13",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.8,
                description="Secondary dominant lift into vi with rich resolution",
            ),
            SectionPlan(
                name="bridge",
                progression="iiø7 - V7b9 - i7 - iv7",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.5,
                description="Dark minor-key departure featuring half-diminished iiø7",
            ),
        ],
    ),
    "pop_anthem": SongTemplate(
        template_id="pop_anthem",
        name="Pop Anthem",
        description="Uplifting, high-energy pop progression architecture with anthemic hooks and dynamic build.",
        recommended_bpm=120,
        recommended_key="C",
        recommended_scale="major",
        sections=[
            SectionPlan(
                name="verse",
                progression="I - V - vi - IV",
                duration_beats_per_chord=4.0,
                voicing="close",
                pattern="block",
                energy_level=0.4,
                description="Classic four-chord pop storytelling verse",
            ),
            SectionPlan(
                name="pre_chorus",
                progression="ii - IV - vi - V",
                duration_beats_per_chord=4.0,
                voicing="close",
                pattern="block",
                energy_level=0.7,
                description="Rising emotional pre-chorus driving toward dominant V",
            ),
            SectionPlan(
                name="chorus",
                progression="IV - I - V - vi",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.95,
                description="Euphoric chorus opening with subdominant lift",
            ),
            SectionPlan(
                name="bridge",
                progression="vi - V - IV - V",
                duration_beats_per_chord=4.0,
                voicing="close",
                pattern="block",
                energy_level=0.6,
                description="Introspective minor vi descent resetting dynamic tension",
            ),
        ],
    ),
    "lofi_chill": SongTemplate(
        template_id="lofi_chill",
        name="Lo-Fi Chill",
        description="Relaxed lo-fi hip hop progression with minor plagal cadences and warm modal borrowings.",
        recommended_bpm=80,
        recommended_key="Eb",
        recommended_scale="major",
        sections=[
            SectionPlan(
                name="verse",
                progression="Imaj9 - iv9",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.3,
                description="Dreamy 2-chord vamp with minor plagal iv9 borrow",
            ),
            SectionPlan(
                name="pre_chorus",
                progression="ii7 - V7 - iii7 - vi7",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.5,
                description="Gentle circle-of-fifths turnaround",
            ),
            SectionPlan(
                name="chorus",
                progression="Imaj7 - bVII - IVmaj7 - Imaj7",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.65,
                description="Warm mixolydian bVII borrow with major 7th resolution",
            ),
            SectionPlan(
                name="bridge",
                progression="iv7 - bVII7 - Imaj7",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.4,
                description="Backdoor dominant turnaround (iv7 - bVII7 - I)",
            ),
        ],
    ),
    "cinematic_minor": SongTemplate(
        template_id="cinematic_minor",
        name="Cinematic Minor",
        description="Dramatic film score harmony with chromatic mediants, Andalusian descents, and Neapolitan tension.",
        recommended_bpm=85,
        recommended_key="C",
        recommended_scale="minor",
        sections=[
            SectionPlan(
                name="verse",
                progression="i - bVI - bIII - bVII",
                duration_beats_per_chord=4.0,
                voicing="close",
                pattern="block",
                energy_level=0.4,
                description="Epic minor chord sequence (i - bVI - bIII - bVII)",
            ),
            SectionPlan(
                name="pre_chorus",
                progression="iv - v - bVI - V7",
                duration_beats_per_chord=4.0,
                voicing="close",
                pattern="block",
                energy_level=0.7,
                description="Ascending stepwise build towards harmonic minor dominant V7",
            ),
            SectionPlan(
                name="chorus",
                progression="i - bVII - bVI - V7",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.9,
                description="Dramatic descending Andalusian cadence",
            ),
            SectionPlan(
                name="bridge",
                progression="bII - i - bVI - V7b9",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.6,
                description="Dark Neapolitan bII chord resolving to altered dominant V7b9",
            ),
        ],
    ),
    "city_pop": SongTemplate(
        template_id="city_pop",
        name="City Pop",
        description="80s Japanese City Pop harmony featuring the Royal Road progression and sparkling dominant cadences.",
        recommended_bpm=116,
        recommended_key="F",
        recommended_scale="major",
        sections=[
            SectionPlan(
                name="verse",
                progression="IVmaj7 - V7 - iii7 - vi7",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.5,
                description="Iconic Japanese Royal Road (IVmaj7 - V7 - iii7 - vi7)",
            ),
            SectionPlan(
                name="pre_chorus",
                progression="ii7 - V7 - Imaj7 - I7",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.7,
                description="Smooth major ii-V-I cadence transitioning via tonic dominant I7",
            ),
            SectionPlan(
                name="chorus",
                progression="IVmaj7 - V/vi - vi7 - ii7 - V7",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.85,
                description="Sparkling city pop chorus with secondary dominant V/vi",
            ),
            SectionPlan(
                name="bridge",
                progression="bVImaj7 - bVII7 - Imaj7",
                duration_beats_per_chord=4.0,
                voicing="drop2",
                pattern="block",
                energy_level=0.6,
                description="Classic J-pop modal mixture backdoor cadence",
            ),
        ],
    ),
}


# ---------------------------------------------------------------------------
# Template Query Functions
# ---------------------------------------------------------------------------

def list_song_templates() -> list[SongTemplate]:
    """Return a list of all curated song templates."""
    return list(CURATED_TEMPLATES.values())


def get_song_template(template_id: str) -> SongTemplate:
    """Retrieve a specific song template by its ID."""
    if template_id not in CURATED_TEMPLATES:
        available = ", ".join(CURATED_TEMPLATES.keys())
        raise ValueError(f"Unknown template ID '{template_id}'. Available templates: {available}")
    return CURATED_TEMPLATES[template_id]


# ---------------------------------------------------------------------------
# Section & Arrangement Generation
# ---------------------------------------------------------------------------

def _parse_section_chords(plan: SectionPlan) -> list[ChordSpec]:
    """Parse a section's progression string into a list of ChordSpec objects."""
    s = plan.progression.strip()
    if not s:
        raise ValueError(f"Progression string in section '{plan.name}' is empty")

    # Remove optional parenthetical/bracketed comments like '[Royal Road]'
    s = re.sub(r"\[.*?\]|\(.*?\)", "", s)
    # Normalize separators (comma, dash, whitespace)
    cleaned = re.sub(r"\s*,\s*|\s*-\s*|\s+", " ", s).strip()
    tokens = [t.strip() for t in cleaned.split(" ") if t.strip()]

    if not tokens:
        raise ValueError(f"No chord tokens found in section '{plan.name}'")

    chords: list[ChordSpec] = []
    for i, tok in enumerate(tokens):
        if ":" in tok:
            numeral, dur_str = tok.rsplit(":", 1)
            try:
                duration = float(dur_str)
                if duration <= 0:
                    raise ValueError
            except ValueError:
                raise ValueError(f"Invalid duration '{dur_str}' in token '{tok}' in section '{plan.name}'")
        else:
            numeral = tok
            duration = plan.duration_beats_per_chord

        # Validate Roman numeral syntax early
        try:
            parse_roman_numeral(numeral)
        except Exception as exc:
            raise ValueError(
                f"Invalid Roman numeral '{numeral}' in section '{plan.name}' at chord {i + 1}: {exc}"
            ) from exc

        chords.append(
            ChordSpec(
                numeral=numeral,
                duration_beats=duration,
                voicing=plan.voicing,  # type: ignore[arg-type]
                pattern=plan.pattern,
            )
        )

    return chords


def generate_song_arrangement(
    template_id: str,
    key_center: str | None = None,
    scale_type: str | None = None,
    bpm: int | None = None,
    output_dir: Path | None = None,
) -> SongArrangement:
    """
    Generate a complete multi-section song arrangement from a template.

    Custom key_center, scale_type, and bpm override template recommendations.
    If output_dir is provided, generates .mid files and sidecar metadata files for each section.
    """
    template = get_song_template(template_id)
    resolved_key = key_center if key_center is not None else template.recommended_key
    resolved_scale = scale_type if scale_type is not None else template.recommended_scale
    resolved_bpm = bpm if bpm is not None else template.recommended_bpm

    if output_dir is not None:
        output_dir = Path(output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

    generated_sections: list[GeneratedSongSection] = []

    for idx, plan in enumerate(template.sections):
        chords = _parse_section_chords(plan)

        # Scale velocity and dynamics according to the section's energy level (0.0 - 1.0)
        base_vel = max(40, min(120, round(50 + plan.energy_level * 50)))
        vel_range = max(4, round(plan.energy_level * 10))
        humanize = HumanizeSpec(
            velocity_range=vel_range,
            timing_ms=6 if plan.energy_level > 0.5 else 4,
            base_velocity=base_vel,
        )

        filename = f"{template.template_id}_{idx:02d}_{plan.name}.mid"
        req = GenerationRequest(
            key_center=resolved_key,
            scale_type=resolved_scale,
            bpm=resolved_bpm,
            chords=chords,
            voice_lead=True,
            humanize=humanize,
            filename=filename,
            prompt_context=f"{template.name} - {plan.name.replace('_', ' ').title()}",
            generation_notes=plan.description or f"Section {idx + 1}: {plan.name}",
        )

        if output_dir is not None:
            gen_res = generate(req, output_dir)
            midi_path = gen_res.filepath
            resolved = resolve_progression_notes(req)
            notes_count = len(resolved.notes)
            total_beats = gen_res.total_beats
        else:
            resolved = resolve_progression_notes(req)
            midi_path = None
            notes_count = len(resolved.notes)
            total_beats = resolved.total_beats

        generated_sections.append(
            GeneratedSongSection(
                section_plan=plan,
                generation_request=req,
                midi_path=midi_path,
                notes_count=notes_count,
                total_beats=total_beats,
            )
        )

    total_beats = sum(s.total_beats for s in generated_sections)

    return SongArrangement(
        template=template,
        key_center=resolved_key,
        scale_type=resolved_scale,
        bpm=resolved_bpm,
        sections=generated_sections,
        total_beats=total_beats,
    )


# ---------------------------------------------------------------------------
# Ableton Live Scene Synchronization
# ---------------------------------------------------------------------------

def inject_song_into_ableton(
    arrangement: SongArrangement,
    client: AbletonClient,
    track_index: int = 0,
) -> list[dict[str, Any]]:
    """
    Populates Ableton Live scene clip slots on `track_index` with each section of the arrangement.
    Scene 0 (Verse), Scene 1 (Pre-Chorus), Scene 2 (Chorus), Scene 3 (Bridge), etc.

    Returns a list of status dictionaries reporting the track index, clip (scene) index,
    section name, note count, and total beats for each injected scene.
    """
    results: list[dict[str, Any]] = []

    for scene_idx, sec in enumerate(arrangement.sections):
        res = client.inject_progression(
            sec.generation_request,
            track_index=track_index,
            clip_index=scene_idx,
            fire=False,
            sync_session=False,
        )

        if isinstance(res, dict):
            res_dict = dict(res)
            res_dict["section_name"] = sec.section_plan.name
            res_dict["section_index"] = scene_idx
            results.append(res_dict)
        else:
            results.append({
                "status": "success",
                "track_index": track_index,
                "clip_index": scene_idx,
                "section_name": sec.section_plan.name,
                "section_index": scene_idx,
                "result": res,
            })

    return results
