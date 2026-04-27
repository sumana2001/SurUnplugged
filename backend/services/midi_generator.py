"""
MIDI Generation Service for SurUnplugged

Generates guitar-style MIDI backing tracks from chord progressions.
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
    """
    Parse chord name into root and type.
    
    Examples:
        "Am" -> ("A", "m")
        "C#maj7" -> ("C#", "maj7")
        "G" -> ("G", "")
    """
    if not chord or chord == "N":
        return ("", "")
    
    # Handle sharps and flats
    if len(chord) > 1 and chord[1] in "#b":
        root = chord[:2]
        chord_type = chord[2:]
    else:
        root = chord[0]
        chord_type = chord[1:]
    
    return (root, chord_type)


def chord_to_midi_notes(chord: str, octave: int = 3) -> list[int]:
    """
    Convert a chord name to MIDI note numbers.
    
    Args:
        chord: Chord name (e.g., "Am", "C#maj7")
        octave: Base octave (default 3, middle range for guitar)
        
    Returns:
        List of MIDI note numbers
    """
    root, chord_type = parse_chord_name(chord)
    
    if not root or root not in NOTE_MIDI:
        return []
    
    # Get root note
    root_note = NOTE_MIDI[root] + (octave - 3) * 12
    
    # Get intervals for chord type
    intervals = CHORD_INTERVALS.get(chord_type, CHORD_INTERVALS[""])
    
    # Build chord notes
    return [root_note + interval for interval in intervals]


def generate_backing_midi(
    chords: list[dict],
    output_path: Path | str,
    style: str = "soft_strum",
    tempo: int = 120
) -> Path:
    """
    Generate a MIDI backing track from chord progression.
    
    Args:
        chords: List of chord objects with time, duration, chord
        output_path: Path to save MIDI file
        style: Guitar style (soft_strum, fingerpick, sustained)
        tempo: Tempo in BPM
        
    Returns:
        Path to generated MIDI file
    """
    output_path = Path(output_path)
    
    try:
        import pretty_midi
    except ImportError:
        raise RuntimeError("pretty_midi not installed. Install with: pip install pretty-midi")
    
    # Create MIDI object
    midi = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    
    # Create acoustic guitar instrument (program 25 = Acoustic Guitar Steel)
    guitar = pretty_midi.Instrument(program=25, name="Acoustic Guitar")
    
    for chord_obj in chords:
        start_time = chord_obj.get("time", 0)
        duration = chord_obj.get("duration", 1.0)
        chord_name = chord_obj.get("chord", "")
        
        if not chord_name or chord_name == "N":
            continue
        
        notes = chord_to_midi_notes(chord_name)
        if not notes:
            continue
        
        if style == "soft_strum":
            # Strum: play notes with slight delay between them
            _add_strum_pattern(guitar, notes, start_time, duration)
        elif style == "fingerpick":
            # Fingerpicking: arpeggiate the chord
            _add_fingerpick_pattern(guitar, notes, start_time, duration)
        else:
            # Sustained: play all notes together
            _add_sustained_chord(guitar, notes, start_time, duration)
    
    midi.instruments.append(guitar)
    
    # Write MIDI file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(output_path))
    
    return output_path


def _add_strum_pattern(instrument, notes: list[int], start: float, duration: float):
    """Add a gentle strum pattern."""
    import pretty_midi
    
    strum_delay = 0.02  # 20ms between strings
    base_velocity = 70
    
    for i, pitch in enumerate(notes):
        note_start = start + (i * strum_delay)
        note_duration = duration - (i * strum_delay)
        velocity = max(40, base_velocity - (i * 5))
        
        note = pretty_midi.Note(
            velocity=velocity,
            pitch=pitch,
            start=note_start,
            end=note_start + max(0.1, note_duration * 0.9)
        )
        instrument.notes.append(note)


def _add_fingerpick_pattern(instrument, notes: list[int], start: float, duration: float):
    """Add an arpeggio/fingerpick pattern."""
    import pretty_midi
    
    if len(notes) < 2:
        _add_sustained_chord(instrument, notes, start, duration)
        return
    
    # Pattern: bass - high - mid - high (repeat)
    pattern_duration = min(0.5, duration / 4)
    
    # Reorder notes: lowest first, then others
    sorted_notes = sorted(notes)
    bass = sorted_notes[0]
    others = sorted_notes[1:]
    
    time = start
    beat = 0
    
    while time < start + duration - 0.05:
        if beat % 4 == 0:
            # Bass note
            pitch = bass
        elif len(others) > 0:
            # Alternate other notes
            pitch = others[(beat // 2) % len(others)]
        else:
            pitch = bass
        
        note = pretty_midi.Note(
            velocity=65 if beat % 4 == 0 else 55,
            pitch=pitch,
            start=time,
            end=time + pattern_duration * 0.8
        )
        instrument.notes.append(note)
        
        time += pattern_duration
        beat += 1


def _add_sustained_chord(instrument, notes: list[int], start: float, duration: float):
    """Add sustained chord (all notes together)."""
    import pretty_midi
    
    for i, pitch in enumerate(notes):
        note = pretty_midi.Note(
            velocity=60,
            pitch=pitch,
            start=start,
            end=start + duration * 0.95
        )
        instrument.notes.append(note)


# For testing
if __name__ == "__main__":
    # Test chord conversion
    test_chords = ["C", "Am", "F", "G", "Dm7", "E7"]
    print("Chord to MIDI notes:")
    for chord in test_chords:
        notes = chord_to_midi_notes(chord)
        print(f"  {chord:6} -> {notes}")
    
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
