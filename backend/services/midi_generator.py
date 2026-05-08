"""
MIDI Generation Service for SurUnplugged - IMPROVED VERSION

Generates guitar-style MIDI backing tracks with CONTINUOUS strumming,
like a real acoustic guitarist would play.

Key improvements over basic version:
1. Fills gaps between detected chords (no silence)
2. Continuous strumming pattern throughout the song
3. Realistic rhythm patterns
"""
from pathlib import Path


# MIDI note numbers for each note (octave 3)
NOTE_MIDI = {
    "C": 48, "C#": 49, "Db": 49,
    "D": 50, "D#": 51, "Eb": 51,
    "E": 52,
    "F": 53, "F#": 54, "Gb": 54,
    "G": 55, "G#": 56, "Ab": 56,
    "A": 57, "A#": 58, "Bb": 58,
    "B": 59,
}

# Chord intervals (semitones from root)
CHORD_INTERVALS = {
    "": [0, 4, 7],           # Major
    "m": [0, 3, 7],          # Minor
    "7": [0, 4, 7, 10],      # Dominant 7th
    "m7": [0, 3, 7, 10],     # Minor 7th
    "maj7": [0, 4, 7, 11],   # Major 7th
    "dim": [0, 3, 6],        # Diminished
    "aug": [0, 4, 8],        # Augmented
    "sus4": [0, 5, 7],       # Suspended 4th
    "sus2": [0, 2, 7],       # Suspended 2nd
    "add9": [0, 4, 7, 14],   # Add 9
}


def parse_chord_name(chord: str) -> tuple[str, str]:
    """Parse chord name into root and type."""
    if not chord or chord == "N":
        return ("", "")
    
    if len(chord) > 1 and chord[1] in "#b":
        root = chord[:2]
        chord_type = chord[2:]
    else:
        root = chord[0]
        chord_type = chord[1:]
    
    return (root, chord_type)


def chord_to_midi_notes(chord: str, octave: int = 3) -> list[int]:
    """Convert a chord name to MIDI note numbers."""
    root, chord_type = parse_chord_name(chord)
    
    if not root or root not in NOTE_MIDI:
        return []
    
    root_note = NOTE_MIDI[root] + (octave - 3) * 12
    intervals = CHORD_INTERVALS.get(chord_type, CHORD_INTERVALS[""])
    
    return [root_note + interval for interval in intervals]


def fill_chord_gaps(chords: list[dict], total_duration: float = None) -> list[dict]:
    """
    Fill gaps between chords by extending the previous chord.
    This ensures continuous music with no silent gaps.
    """
    if not chords:
        return chords
    
    filled = []
    
    for i, chord in enumerate(chords):
        current_start = chord.get("time", 0)
        current_chord = chord.get("chord", "")
        
        # Skip empty chords but remember we need to fill
        if not current_chord or current_chord == "N":
            continue
        
        # Calculate duration: until the next chord starts
        if i + 1 < len(chords):
            next_start = chords[i + 1].get("time", current_start + 2)
            duration = next_start - current_start
        else:
            # Last chord - extend to total duration or use 4 seconds
            duration = chord.get("duration", 4.0)
            if total_duration and current_start + duration < total_duration:
                duration = total_duration - current_start
        
        # Ensure minimum duration
        duration = max(duration, 0.5)
        
        filled.append({
            "time": current_start,
            "duration": duration,
            "chord": current_chord,
        })
    
    return filled


def generate_backing_midi(
    chords: list[dict],
    output_path: Path | str,
    style: str = "continuous_strum",
    tempo: int = 100,
    total_duration: float = None
) -> Path:
    """
    Generate a MIDI backing track with CONTINUOUS strumming.
    
    Args:
        chords: List of chord objects with time, duration, chord
        output_path: Path to save MIDI file
        style: Guitar style:
            - "continuous_strum": Steady strumming pattern (default, best for singing)
            - "ballad": Slower, more gentle pattern
            - "fingerpick": Arpeggiated pattern
        tempo: Tempo in BPM (default 100 - good for ballads)
        total_duration: Total song duration to fill
        
    Returns:
        Path to generated MIDI file
    """
    output_path = Path(output_path)
    
    try:
        import pretty_midi
    except ImportError:
        raise RuntimeError("pretty_midi not installed. Install with: pip install pretty-midi")
    
    if not chords:
        raise ValueError("No chords provided")
    
    # Fill gaps between chords - this is the key fix!
    filled_chords = fill_chord_gaps(chords, total_duration)
    
    print(f"  ℹ️  Original chords: {len(chords)}, After filling gaps: {len(filled_chords)}")
    
    # Create MIDI object
    midi = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    
    # Create acoustic guitar instrument (program 25 = Acoustic Guitar Steel)
    guitar = pretty_midi.Instrument(program=25, name="Acoustic Guitar")
    
    # Calculate beat duration from tempo
    beat_duration = 60.0 / tempo
    
    for chord_obj in filled_chords:
        start_time = chord_obj.get("time", 0)
        duration = chord_obj.get("duration", 2.0)
        chord_name = chord_obj.get("chord", "")
        
        if not chord_name or chord_name == "N":
            continue
        
        notes = chord_to_midi_notes(chord_name)
        if not notes:
            continue
        
        if style == "continuous_strum":
            _add_continuous_strum(guitar, notes, start_time, duration, beat_duration)
        elif style == "ballad":
            _add_ballad_pattern(guitar, notes, start_time, duration, beat_duration)
        elif style == "fingerpick":
            _add_fingerpick_pattern(guitar, notes, start_time, duration, beat_duration)
        else:
            _add_continuous_strum(guitar, notes, start_time, duration, beat_duration)
    
    midi.instruments.append(guitar)
    
    # Write MIDI file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(output_path))
    
    return output_path


def _add_continuous_strum(
    instrument, 
    notes: list[int], 
    start: float, 
    duration: float,
    beat_duration: float
):
    """
    Add continuous strumming pattern - like a guitarist strumming steadily.
    
    Pattern: Down-up-down-up strumming, with emphasis on beats 1 and 3.
    This creates a consistent, rhythmic backing that's easy to sing over.
    """
    import pretty_midi
    
    # Strum interval: strum every half beat for consistent rhythm
    strum_interval = beat_duration / 2  # Eighth note strumming
    
    time = start
    strum_count = 0
    
    while time < start + duration - 0.05:
        # Determine if this is a downstroke (strong) or upstroke (weak)
        is_downstroke = (strum_count % 2 == 0)
        
        # Emphasize beats 1 and 3 (every 4th strum in 4/4 time)
        is_strong_beat = (strum_count % 4 == 0)
        
        if is_downstroke:
            # Downstroke: play full chord, bass to treble
            _add_single_strum(
                instrument, 
                notes, 
                time, 
                strum_interval * 0.9,
                downstroke=True,
                velocity=75 if is_strong_beat else 65
            )
        else:
            # Upstroke: play upper notes only, treble to bass (quieter)
            upper_notes = notes[-2:] if len(notes) > 2 else notes
            _add_single_strum(
                instrument, 
                upper_notes, 
                time, 
                strum_interval * 0.7,
                downstroke=False,
                velocity=50
            )
        
        time += strum_interval
        strum_count += 1


def _add_ballad_pattern(
    instrument, 
    notes: list[int], 
    start: float, 
    duration: float,
    beat_duration: float
):
    """
    Slower, more gentle pattern for ballads.
    Pattern: bass note, then chord, then bass note, then partial chord.
    """
    import pretty_midi
    
    if len(notes) < 2:
        _add_continuous_strum(instrument, notes, start, duration, beat_duration)
        return
    
    sorted_notes = sorted(notes)
    bass = sorted_notes[0]
    chord_notes = sorted_notes[1:]
    
    # Pattern repeats every 2 beats
    pattern_duration = beat_duration * 2
    
    time = start
    
    while time < start + duration - 0.1:
        # Beat 1: Bass note
        note = pretty_midi.Note(
            velocity=70,
            pitch=bass,
            start=time,
            end=time + beat_duration * 0.8
        )
        instrument.notes.append(note)
        
        # Beat 1.5: Chord (upper notes)
        for i, pitch in enumerate(chord_notes):
            note = pretty_midi.Note(
                velocity=55,
                pitch=pitch,
                start=time + beat_duration * 0.5 + (i * 0.015),
                end=time + beat_duration * 1.3
            )
            instrument.notes.append(note)
        
        # Beat 2: Bass note again
        if time + beat_duration < start + duration:
            note = pretty_midi.Note(
                velocity=60,
                pitch=bass,
                start=time + beat_duration,
                end=time + beat_duration * 1.7
            )
            instrument.notes.append(note)
        
        # Beat 2.5: Partial chord
        if time + beat_duration * 1.5 < start + duration:
            for pitch in chord_notes[:2]:
                note = pretty_midi.Note(
                    velocity=45,
                    pitch=pitch,
                    start=time + beat_duration * 1.5,
                    end=time + beat_duration * 1.9
                )
                instrument.notes.append(note)
        
        time += pattern_duration


def _add_fingerpick_pattern(
    instrument, 
    notes: list[int], 
    start: float, 
    duration: float,
    beat_duration: float
):
    """
    Fingerpicking arpeggio pattern.
    Pattern: bass - middle - high - middle, repeated.
    """
    import pretty_midi
    
    if len(notes) < 3:
        _add_ballad_pattern(instrument, notes, start, duration, beat_duration)
        return
    
    sorted_notes = sorted(notes)
    
    # Create picking pattern: bass, mid, high, mid
    pattern = [
        sorted_notes[0],   # bass
        sorted_notes[1],   # mid
        sorted_notes[-1],  # high
        sorted_notes[1],   # mid
    ]
    
    # Each pick is an eighth note
    pick_interval = beat_duration / 2
    
    time = start
    pick_index = 0
    
    while time < start + duration - 0.05:
        pitch = pattern[pick_index % len(pattern)]
        
        # Emphasize bass notes
        velocity = 70 if pick_index % 4 == 0 else 55
        
        note = pretty_midi.Note(
            velocity=velocity,
            pitch=pitch,
            start=time,
            end=time + pick_interval * 0.8
        )
        instrument.notes.append(note)
        
        time += pick_interval
        pick_index += 1


def _add_single_strum(
    instrument,
    notes: list[int],
    start: float,
    duration: float,
    downstroke: bool = True,
    velocity: int = 65
):
    """Add a single strum (all notes with slight timing offset for realism)."""
    import pretty_midi
    
    strum_delay = 0.015  # 15ms between strings - fast strum
    
    # Order notes for strum direction
    if downstroke:
        ordered_notes = sorted(notes)  # Low to high
    else:
        ordered_notes = sorted(notes, reverse=True)  # High to low
    
    for i, pitch in enumerate(ordered_notes):
        note_start = start + (i * strum_delay)
        note_velocity = max(35, velocity - (i * 3))
        
        note = pretty_midi.Note(
            velocity=note_velocity,
            pitch=pitch,
            start=note_start,
            end=note_start + duration
        )
        instrument.notes.append(note)


# For testing
if __name__ == "__main__":
    # Test with a simple progression (simulating "Tum Hi Ho" style)
    test_chords = [
        {"time": 0.0, "duration": 4.0, "chord": "Am"},
        {"time": 4.0, "duration": 4.0, "chord": "F"},
        {"time": 8.0, "duration": 4.0, "chord": "C"},
        {"time": 12.0, "duration": 4.0, "chord": "G"},
    ]
    
    print("Testing MIDI generation with continuous strumming...")
    
    # Test continuous strum
    output = Path("test_continuous.mid")
    generate_backing_midi(test_chords, output, style="continuous_strum", tempo=100)
    print(f"✅ Generated: {output} (continuous strumming)")
    
    # Test ballad style
    output2 = Path("test_ballad.mid")
    generate_backing_midi(test_chords, output2, style="ballad", tempo=80)
    print(f"✅ Generated: {output2} (ballad style)")
    
    # Test fingerpick
    output3 = Path("test_fingerpick.mid")
    generate_backing_midi(test_chords, output3, style="fingerpick", tempo=90)
    print(f"✅ Generated: {output3} (fingerpick style)")
    
    print("\n🎸 These should all have CONTINUOUS guitar throughout!")
    print("   No more random silence between notes.")
    
    # Test MIDI generation
    progression = [
        {"time": 0.0, "duration": 2.0, "chord": "C"},
        {"time": 2.0, "duration": 2.0, "chord": "Am"},
        {"time": 4.0, "duration": 2.0, "chord": "F"},
        {"time": 6.0, "duration": 2.0, "chord": "G"},
    ]
    
    output = Path("test_backing.mid")
    generate_backing_midi(progression, output, style="soft_strum")
    print(f"\nGenerated: {output}")
